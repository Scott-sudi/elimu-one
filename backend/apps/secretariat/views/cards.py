"""Student card views."""

from io import BytesIO

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from apps.secretariat.models import Enrollment, SchoolClass, StudentCard
from apps.secretariat.services import card_service
from apps.secretariat.services.exceptions import SecretariatError

from .base import SecretariatListView, SecretariatViewMixin


class CardListView(SecretariatListView):
    template_name = "secretariat/cards/list.html"
    partial_template_name = "secretariat/cards/_table.html"
    context_object_name = "cards"
    page_title = "Cartes d'élèves"

    def get_queryset(self):
        year = self.get_selected_academic_year()
        qs = StudentCard.objects.select_related("student", "enrollment__school_class")
        if year:
            qs = qs.filter(enrollment__academic_year=year)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = self.get_selected_academic_year()
        eligible = Enrollment.objects.filter(
            status=Enrollment.Status.VALIDATED, cards__isnull=True
        ).select_related("student", "school_class")
        if year:
            eligible = eligible.filter(academic_year=year)
        context["eligible_enrollments"] = eligible
        context["year_writable"] = bool(year and not year.is_closed)
        return context


class CardPreviewView(SecretariatViewMixin, DetailView):
    model = StudentCard
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    context_object_name = "card"
    template_name = "secretariat/cards/preview.html"

    def get_queryset(self):
        year = self.get_selected_academic_year()
        qs = StudentCard.objects.select_related(
            "student",
            "enrollment__academic_year",
            "enrollment__school_class__section",
            "enrollment__school_class__option",
        )
        if year:
            qs = qs.filter(enrollment__academic_year=year)
        return qs

    def get_context_data(self, **kwargs):
        from apps.core.branding import school_display_name, school_display_slogan

        from apps.secretariat.services.card_service import (
            CARD_HEIGHT_MM,
            CARD_WIDTH_MM,
            card_preview_url,
            refresh_card_pdf,
        )

        context = super().get_context_data(**kwargs)
        # Rebuild PNG if the student photo is newer than the cached preview.
        card_service.ensure_card_png(self.object)
        preview = card_preview_url(self.object)
        if not preview and self.object.pdf_file:
            refresh_card_pdf(self.object)
            preview = card_preview_url(self.object)
        # Bust browser cache after photo / preview updates.
        if preview:
            from django.core.files.storage import default_storage

            from apps.secretariat.services.card_service import card_preview_path

            try:
                cache_v = int(
                    default_storage.get_modified_time(
                        card_preview_path(self.object)
                    ).timestamp()
                )
            except Exception:
                cache_v = int(self.object.updated_at.timestamp())
            preview = f"{preview}?v={cache_v}"
        context.update(
            school_name=school_display_name(),
            school_slogan=school_display_slogan(),
            school_code=getattr(settings, "SCHOOL_CODE", ""),
            school_city=getattr(settings, "SCHOOL_CITY", ""),
            school_address=getattr(settings, "SCHOOL_ADDRESS", ""),
            school_phone=getattr(settings, "SCHOOL_PHONE", ""),
            card_preview_url=preview,
            card_width_cm=f"{CARD_WIDTH_MM / 10:g}".replace(".", ","),
            card_height_cm=f"{CARD_HEIGHT_MM / 10:g}".replace(".", ","),
            breadcrumbs=[
                ("Secrétariat", reverse("secretariat:dashboard")),
                ("Cartes", reverse("secretariat:cards")),
                (self.object.card_number, None),
            ],
        )
        return context


class CardPngDownloadView(SecretariatViewMixin, View):
    """Download the card as a print-ready PNG (10,5 × 6,6 cm at 300 DPI)."""

    def get(self, request, public_id):
        year = self.get_selected_academic_year()
        qs = StudentCard.objects.select_related("student")
        if year:
            qs = qs.filter(enrollment__academic_year=year)
        card = get_object_or_404(qs, public_id=public_id)
        try:
            _, png_bytes = card_service.ensure_card_png(card)
        except Exception as exc:  # pragma: no cover - storage/render edge cases
            raise Http404("Image de carte introuvable.") from exc
        filename = card_service.card_png_filename(card)
        return FileResponse(
            BytesIO(png_bytes),
            as_attachment=True,
            filename=filename,
            content_type="image/png",
        )


class ClassCardsZipDownloadView(SecretariatViewMixin, View):
    """Download PNG cards for every validated student in a class (ZIP)."""

    def get(self, request, public_id):
        year = self.get_selected_academic_year()
        qs = SchoolClass.objects.all()
        if year:
            qs = qs.filter(academic_year=year)
        school_class = get_object_or_404(qs, public_id=public_id)
        try:
            zip_bytes, _count = card_service.build_class_cards_zip(
                school_class,
                actor=request.user,
                request=request,
                generate_missing=True,
            )
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect("secretariat:class-detail", public_id=public_id)
        return FileResponse(
            BytesIO(zip_bytes),
            as_attachment=True,
            filename=card_service.class_cards_zip_filename(school_class),
            content_type="application/zip",
        )


class CardGenerateView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        from django.utils.http import url_has_allowed_host_and_scheme

        year = None
        try:
            year = self.require_writable_academic_year()
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect("secretariat:cards")
        enrollment = get_object_or_404(
            Enrollment.objects.filter(academic_year=year),
            public_id=public_id,
        )
        try:
            card_service.generate_card(
                enrollment=enrollment, actor=request.user, request=request
            )
            messages.success(request, "Carte générée.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        next_url = request.POST.get("next") or ""
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("secretariat:cards")


class CardBlockView(SecretariatViewMixin, View):
    def post(self, request, public_id):
        try:
            year = self.require_writable_academic_year()
        except SecretariatError as exc:
            messages.error(request, str(exc))
            return redirect("secretariat:cards")
        card = get_object_or_404(
            StudentCard.objects.filter(enrollment__academic_year=year),
            public_id=public_id,
        )
        try:
            card_service.block_card(
                card,
                reason=request.POST.get("reason", ""),
                actor=request.user,
                request=request,
            )
            messages.success(request, "Carte bloquée.")
        except SecretariatError as exc:
            messages.error(request, str(exc))
        return redirect("secretariat:cards")

"""ViewSets and standalone views for the secretariat REST API."""

from __future__ import annotations

from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from apps.api.permissions import IsSecretary
from apps.api.views import envelope
from apps.secretariat.models import (
    AcademicYear,
    Communication,
    Enrollment,
    Guardian,
    Option,
    SchoolClass,
    SchoolLevel,
    Section,
    Student,
    StudentCard,
)
from apps.secretariat.services import student_service

from .serializers import (
    AcademicYearDetailSerializer,
    AcademicYearListSerializer,
    AcademicYearWriteSerializer,
    CardResolveSerializer,
    CommunicationDetailSerializer,
    CommunicationListSerializer,
    CommunicationWriteSerializer,
    EnrollmentDetailSerializer,
    EnrollmentListSerializer,
    EnrollmentWriteSerializer,
    GuardianDetailSerializer,
    GuardianListSerializer,
    GuardianWriteSerializer,
    OptionDetailSerializer,
    OptionListSerializer,
    OptionWriteSerializer,
    SchoolClassDetailSerializer,
    SchoolClassListSerializer,
    SchoolClassWriteSerializer,
    SchoolLevelDetailSerializer,
    SchoolLevelListSerializer,
    SchoolLevelWriteSerializer,
    SectionDetailSerializer,
    SectionListSerializer,
    SectionWriteSerializer,
    StudentCardDetailSerializer,
    StudentCardListSerializer,
    StudentCardWriteSerializer,
    StudentDetailSerializer,
    StudentListSerializer,
    StudentWriteSerializer,
)


class EnvelopeViewSetMixin:
    """Use the common API envelope for non-paginated ViewSet actions."""

    list_serializer_class = None
    detail_serializer_class = None
    write_serializer_class = None

    def get_serializer_class(self):
        if self.action == "list" and self.list_serializer_class:
            return self.list_serializer_class
        if self.action in {"create", "update", "partial_update"} and self.write_serializer_class:
            return self.write_serializer_class
        if self.detail_serializer_class:
            return self.detail_serializer_class
        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return envelope(data=self.get_serializer(queryset, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return envelope(data=self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        output = self.detail_serializer_class(instance, context=self.get_serializer_context())
        return envelope(
            message="Ressource créée avec succès.",
            data=output.data,
            http_status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        output = self.detail_serializer_class(instance, context=self.get_serializer_context())
        return envelope(message="Modifications enregistrées.", data=output.data)

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(self.get_object())
        return envelope(message="Ressource supprimée.")


class SecretariatModelViewSet(EnvelopeViewSetMixin, ModelViewSet):
    permission_classes = [IsSecretary]
    lookup_field = "public_id"
    lookup_value_regex = "[0-9a-fA-F-]{36}"


class SecretariatCreateReadViewSet(
    EnvelopeViewSetMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    permission_classes = [IsSecretary]
    lookup_field = "public_id"
    lookup_value_regex = "[0-9a-fA-F-]{36}"


class AcademicYearViewSet(SecretariatModelViewSet):
    queryset = AcademicYear.objects.all()
    list_serializer_class = AcademicYearListSerializer
    detail_serializer_class = AcademicYearDetailSerializer
    write_serializer_class = AcademicYearWriteSerializer
    filterset_fields = ("is_active", "is_closed")
    search_fields = ("label",)
    ordering_fields = ("label", "start_date", "end_date", "created_at")
    ordering = ("-start_date",)


class SchoolLevelViewSet(SecretariatModelViewSet):
    queryset = SchoolLevel.objects.all()
    list_serializer_class = SchoolLevelListSerializer
    detail_serializer_class = SchoolLevelDetailSerializer
    write_serializer_class = SchoolLevelWriteSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "code", "description")
    ordering_fields = ("name", "code", "order", "created_at")
    ordering = ("order", "name")


class SectionViewSet(SecretariatModelViewSet):
    queryset = Section.objects.all()
    list_serializer_class = SectionListSerializer
    detail_serializer_class = SectionDetailSerializer
    write_serializer_class = SectionWriteSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "code", "description")
    ordering_fields = ("name", "code", "created_at")
    ordering = ("name",)


class OptionViewSet(SecretariatModelViewSet):
    queryset = Option.objects.select_related("section")
    list_serializer_class = OptionListSerializer
    detail_serializer_class = OptionDetailSerializer
    write_serializer_class = OptionWriteSerializer
    filterset_fields = ("is_active", "section__public_id")
    search_fields = ("name", "code", "description", "section__name")
    ordering_fields = ("name", "code", "created_at")
    ordering = ("name",)


class SchoolClassViewSet(SecretariatModelViewSet):
    queryset = (
        SchoolClass.objects.select_related(
            "academic_year",
            "level",
            "section",
            "option",
            "option__section",
        )
        .annotate(
            enrollment_count=Count(
                "enrollments",
                filter=Q(enrollments__status=Enrollment.Status.VALIDATED),
            )
        )
    )
    list_serializer_class = SchoolClassListSerializer
    detail_serializer_class = SchoolClassDetailSerializer
    write_serializer_class = SchoolClassWriteSerializer
    filterset_fields = (
        "is_active",
        "academic_year__public_id",
        "level__public_id",
        "section__public_id",
        "option__public_id",
    )
    search_fields = (
        "name",
        "code",
        "room",
        "level__name",
        "section__name",
        "option__name",
    )
    ordering_fields = ("name", "code", "max_capacity", "created_at")
    ordering = ("academic_year", "level__order", "name")


def _current_enrollments(relation="enrollments"):
    return Prefetch(
        relation,
        queryset=Enrollment.objects.filter(
            status=Enrollment.Status.VALIDATED,
        )
        .select_related("school_class", "academic_year")
        .order_by("-academic_year__start_date"),
        to_attr="current_enrollments",
    )


class StudentViewSet(SecretariatModelViewSet):
    queryset = Student.objects.prefetch_related(_current_enrollments())
    list_serializer_class = StudentListSerializer
    detail_serializer_class = StudentDetailSerializer
    write_serializer_class = StudentWriteSerializer
    filterset_fields = (
        "sexe",
        "statut",
        "is_active",
        "is_archived",
        "enrollments__academic_year__public_id",
        "enrollments__school_class__public_id",
    )
    search_fields = (
        "matricule",
        "nom",
        "postnom",
        "prenom",
    )
    ordering_fields = (
        "matricule",
        "nom",
        "postnom",
        "prenom",
        "date_admission",
        "created_at",
    )
    ordering = ("nom", "postnom", "prenom")

    def get_queryset(self):
        return super().get_queryset().distinct()

    def perform_destroy(self, instance):
        student_service.archive_student(
            instance,
            actor=self.request.user,
            request=self.request,
        )


class GuardianViewSet(SecretariatModelViewSet):
    queryset = Guardian.objects.all()
    list_serializer_class = GuardianListSerializer
    detail_serializer_class = GuardianDetailSerializer
    write_serializer_class = GuardianWriteSerializer
    filterset_fields = ("sexe", "is_active", "is_archived")
    search_fields = (
        "nom",
        "postnom",
        "prenom",
        "telephone_principal",
        "telephone_secondaire",
        "email",
        "numero_identification",
    )
    ordering_fields = ("nom", "postnom", "prenom", "created_at")
    ordering = ("nom", "postnom", "prenom")

    def perform_destroy(self, instance):
        instance.archive()


class EnrollmentViewSet(SecretariatCreateReadViewSet):
    queryset = Enrollment.objects.select_related(
        "student",
        "academic_year",
        "school_class",
        "school_class__academic_year",
        "school_class__level",
        "school_class__section",
        "school_class__option",
        "created_by",
    ).prefetch_related(_current_enrollments("student__enrollments"))
    list_serializer_class = EnrollmentListSerializer
    detail_serializer_class = EnrollmentDetailSerializer
    write_serializer_class = EnrollmentWriteSerializer
    filterset_fields = (
        "status",
        "enrollment_type",
        "academic_year__public_id",
        "school_class__public_id",
        "student__public_id",
    )
    search_fields = (
        "enrollment_number",
        "student__matricule",
        "student__nom",
        "student__postnom",
        "student__prenom",
        "school_class__name",
    )
    ordering_fields = ("enrollment_number", "enrollment_date", "created_at")
    ordering = ("-enrollment_date", "-created_at")


class StudentCardViewSet(SecretariatCreateReadViewSet):
    queryset = StudentCard.objects.select_related(
        "student",
        "enrollment",
        "enrollment__academic_year",
        "enrollment__school_class",
    ).prefetch_related(_current_enrollments("student__enrollments"))
    list_serializer_class = StudentCardListSerializer
    detail_serializer_class = StudentCardDetailSerializer
    write_serializer_class = StudentCardWriteSerializer
    filterset_fields = (
        "is_active",
        "is_blocked",
        "student__public_id",
        "enrollment__public_id",
        "enrollment__academic_year__public_id",
    )
    search_fields = (
        "card_number",
        "qr_identifier",
        "student__matricule",
        "student__nom",
        "student__postnom",
        "student__prenom",
    )
    ordering_fields = ("card_number", "generated_at", "expires_at", "updated_at")
    ordering = ("-generated_at",)


class CommunicationViewSet(SecretariatModelViewSet):
    queryset = (
        Communication.objects.select_related("author")
        .prefetch_related("targets")
        .annotate(target_count=Count("targets"))
    )
    list_serializer_class = CommunicationListSerializer
    detail_serializer_class = CommunicationDetailSerializer
    write_serializer_class = CommunicationWriteSerializer
    filterset_fields = ("category", "priority", "status", "is_pinned", "author__public_id")
    search_fields = ("title", "content")
    ordering_fields = ("title", "priority", "published_at", "expires_at", "created_at")
    ordering = ("-is_pinned", "-published_at", "-created_at")


class CardResolveAPIView(GenericAPIView):
    """Resolve a QR identifier without exposing sensitive student data."""

    permission_classes = [IsAuthenticated]
    serializer_class = CardResolveSerializer

    def get(self, request, qr_identifier):
        card = get_object_or_404(
            StudentCard.objects.select_related(
                "student",
                "enrollment__school_class",
                "enrollment__school_class__section",
                "enrollment__school_class__option",
                "enrollment__academic_year",
            ),
            qr_identifier=qr_identifier,
        )
        return envelope(data=self.get_serializer(card).data)

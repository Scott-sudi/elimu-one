"""Session-backed academic year context for the secretariat module."""

from __future__ import annotations

from django.db.models import Case, IntegerField, QuerySet, Value, When

from apps.audit.models import AuditLog
from apps.secretariat.models import AcademicYear
from apps.secretariat.services import audit_secretariat_action
from apps.secretariat.services.exceptions import SecretariatError

SESSION_KEY = "secretariat_academic_year_id"
SESSION_PUBLIC_ID_KEY = "secretariat_academic_year_public_id"


def ordered_academic_years() -> QuerySet[AcademicYear]:
    """Active first, then open years, then closed — each group newest first."""
    return AcademicYear.objects.annotate(
        _priority=Case(
            When(is_active=True, then=Value(0)),
            When(is_closed=False, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by("_priority", "-start_date")


class AcademicYearContextService:
    """Central helper for reading/writing the selected academic year in session."""

    session_key = SESSION_KEY

    def get_selected_year_id(self, request) -> int | None:
        raw = request.session.get(SESSION_KEY)
        if raw is None:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def has_session_year(self, request) -> bool:
        """True when the user explicitly picked a year (session key present)."""
        return self.get_selected_year_id(request) is not None

    def get_selected_year(self, request) -> AcademicYear | None:
        year_id = self.get_selected_year_id(request)
        if year_id is not None:
            year = AcademicYear.objects.filter(pk=year_id).first()
            if year is not None:
                return year
            # Année supprimée (ex. après purge) → nettoyer la session.
            self.clear_selected_year(request)

        # Reprise automatique : année active ouverte, sinon première année ouverte.
        year = (
            AcademicYear.objects.filter(is_active=True, is_closed=False)
            .order_by("-start_date")
            .first()
        )
        if year is None:
            year = (
                AcademicYear.objects.filter(is_closed=False)
                .order_by("-start_date")
                .first()
            )
        if year is not None:
            request.session[SESSION_KEY] = year.pk
            request.session[SESSION_PUBLIC_ID_KEY] = str(year.public_id)
            request.session.modified = True
        return year

    def require_selected_year(self, request) -> AcademicYear:
        year = self.get_selected_year(request)
        if year is None:
            raise SecretariatError("Aucune année scolaire n'est sélectionnée.")
        return year

    def select_year(
        self,
        request,
        academic_year: AcademicYear,
        *,
        actor=None,
        previous: AcademicYear | None = None,
    ) -> AcademicYear:
        if academic_year is None:
            raise SecretariatError("Année scolaire introuvable.")
        previous = previous if previous is not None else self.get_selected_year(request)
        request.session[SESSION_KEY] = academic_year.pk
        request.session[SESSION_PUBLIC_ID_KEY] = str(academic_year.public_id)
        request.session.modified = True
        audit_secretariat_action(
            action=AuditLog.Action.ACADEMIC_YEAR_SELECTED,
            instance=academic_year,
            description=(
                f"Changement d'année scolaire : {previous.label} → {academic_year.label}"
                if previous and previous.pk != academic_year.pk
                else f"Sélection de l'année scolaire {academic_year.label}"
            ),
            actor=actor or getattr(request, "user", None),
            request=request,
            old_values={"label": previous.label} if previous else {},
            new_values={"label": academic_year.label, "public_id": str(academic_year.public_id)},
        )
        return academic_year

    def clear_selected_year(self, request) -> None:
        request.session.pop(SESSION_KEY, None)
        request.session.pop(SESSION_PUBLIC_ID_KEY, None)
        request.session.modified = True

    def is_closed(self, request) -> bool:
        year = self.get_selected_year(request)
        return bool(year and year.is_closed)


year_context_service = AcademicYearContextService()

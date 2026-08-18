"""Parents mobile API — children list for a verified guardian."""

from __future__ import annotations

from django.db.models import Prefetch
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.api.views import envelope
from apps.secretariat.models import Enrollment, Guardian, Student


class ParentChildrenThrottle(AnonRateThrottle):
    scope = "parent_children"
    rate = "60/hour"


def _student_display_name(student: Student) -> str:
    prenom = (student.prenom or "").strip()
    nom = (student.nom or "").strip().upper()
    parts = [p for p in (prenom, nom) if p]
    return " ".join(parts) if parts else str(student.matricule)


def _current_class_label(student: Student) -> str:
    """Classe de la dernière inscription validée, sinon brouillon récente."""
    enrollments = list(student.enrollments.all())
    if not enrollments:
        return "Classe non assignée"
    validated = [e for e in enrollments if e.status == Enrollment.Status.VALIDATED]
    chosen = validated[0] if validated else enrollments[0]
    return chosen.school_class.name if chosen.school_class_id else "Classe non assignée"


def _photo_url(request, student: Student) -> str | None:
    if not student.photo:
        return None
    try:
        url = student.photo.url
    except ValueError:
        return None
    if request is None:
        return url
    return request.build_absolute_uri(url)


def serialize_parent_children(*, guardian: Guardian, request=None) -> list[dict]:
    links = (
        guardian.student_links.select_related("student")
        .prefetch_related(
            Prefetch(
                "student__enrollments",
                queryset=Enrollment.objects.select_related("school_class").order_by(
                    "-enrollment_date",
                    "-created_at",
                ),
            ),
        )
        .order_by("student__nom", "student__prenom")
    )
    enfants: list[dict] = []
    for link in links:
        student = link.student
        if student.is_archived:
            continue
        enfants.append(
            {
                "id": str(student.public_id),
                "nom": _student_display_name(student),
                "classe": _current_class_label(student),
                "matricule": student.matricule,
                "photo": _photo_url(request, student),
                "actif": bool(student.is_active and student.statut == Student.Status.ACTIVE),
            },
        )
    return enfants


class ParentChildrenListAPIView(APIView):
    """Liste les élèves liés à un responsable (Guardian).

    Auth provisoire mobile : `guardian_public_id` (query ou header
    `X-Guardian-Public-Id`) jusqu'à l'arrivée du JWT parents.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ParentChildrenThrottle]
    authentication_classes = []

    def get(self, request):
        guardian_id = (
            request.query_params.get("guardian_public_id")
            or request.headers.get("X-Guardian-Public-Id")
            or ""
        ).strip()
        if not guardian_id:
            return envelope(
                success=False,
                message="Session parent invalide.",
                http_status=400,
            )

        guardian = (
            Guardian.objects.filter(
                public_id=guardian_id,
                is_active=True,
                is_archived=False,
            )
            .first()
        )
        if guardian is None:
            return envelope(
                success=False,
                message="Compte parent introuvable.",
                http_status=404,
            )

        enfants = serialize_parent_children(guardian=guardian, request=request)
        return envelope(
            message="Liste des enfants.",
            data={"enfants": enfants},
        )

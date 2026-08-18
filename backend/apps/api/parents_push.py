"""Envoi de notifications push FCM (HTTP v1) vers les appareils parents."""

from __future__ import annotations

import json
import logging
import time
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import requests
from django.conf import settings
from django.db.models import QuerySet

from apps.api.models import ParentPushDevice
from apps.secretariat.models import Guardian

logger = logging.getLogger(__name__)

ANDROID_CHANNEL_ID = "kalunga_parents_alerts_v6"
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

# Anti-doublon signal + hook service (même événement < 60 s).
_recent_push_keys: dict[str, float] = {}


def _claim_push_key(key: str) -> bool:
    now = time.time()
    stale = [k for k, at in _recent_push_keys.items() if now - at > 60]
    for k in stale:
        _recent_push_keys.pop(k, None)
    if not key:
        return True
    if key in _recent_push_keys:
        return False
    _recent_push_keys[key] = now
    return True


def _project_id() -> str:
    return (
        getattr(settings, "FCM_PROJECT_ID", None) or ""
    ).strip() or "institut-kalunga"


def _service_account_path() -> Path | None:
    raw = (getattr(settings, "FCM_SERVICE_ACCOUNT_FILE", None) or "").strip()
    if not raw:
        candidates = [
            Path(settings.BASE_DIR) / "secrets" / "firebase-adminsdk.json",
            Path(settings.BASE_DIR).parent / "secrets" / "firebase-adminsdk.json",
            Path(settings.BASE_DIR).parent / ".firebase" / "firebase-adminsdk.json",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path(settings.BASE_DIR) / path
    return path if path.is_file() else None


@lru_cache(maxsize=1)
def _access_token() -> str | None:
    path = _service_account_path()
    if path is None:
        logger.warning(
            "FCM service account absent — push distant ignoré "
            "(secrets/firebase-adminsdk.json)."
        )
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
    except ImportError:
        logger.warning("Package google-auth manquant — pip install google-auth")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            str(path),
            scopes=[FCM_SCOPE],
        )
        creds.refresh(Request())
        return creds.token
    except Exception as exc:
        logger.warning("FCM auth échouée: %s", exc)
        return None


def _invalidate_token_cache() -> None:
    _access_token.cache_clear()


def _student_display_name(student) -> str:
    if student is None:
        return "Élève"
    prenom = (getattr(student, "prenom", None) or "").strip()
    nom = (getattr(student, "nom", None) or "").strip().upper()
    return " ".join(p for p in (prenom, nom) if p) or str(
        getattr(student, "matricule", "") or "Élève"
    )


def _guardians_for_student(student) -> list[Guardian]:
    """Parents liés à l’élève (préfère receives_notifications=True)."""
    from apps.secretariat.models import StudentGuardian

    if student is None:
        return []
    base = StudentGuardian.objects.filter(
        student=student,
        guardian__is_active=True,
        guardian__is_archived=False,
    )
    preferred = base.filter(receives_notifications=True)
    ids = list(
        (preferred if preferred.exists() else base).values_list(
            "guardian_id", flat=True
        )
    )
    if not ids:
        logger.warning(
            "FCM: aucun guardian lié à student_id=%s",
            getattr(student, "pk", None),
        )
        return []
    return list(Guardian.objects.filter(pk__in=ids, is_active=True))


def _guardians_for_summons(summons) -> list[Guardian]:
    """Respecte les destinataires explicites, sinon tous les responsables."""
    targeted = list(
        summons.target_guardians.filter(
            is_active=True,
            is_archived=False,
        )
    )
    if targeted:
        return targeted
    return _guardians_for_student(summons.student)


def send_push_to_guardians(
    *,
    guardians: list[Guardian] | QuerySet,
    title: str,
    body: str,
    data: dict | None = None,
) -> int:
    """Envoie une notification push FCM v1. Retourne le nb d'envois OK."""
    dedupe = ""
    if data:
        variant = data.get("updated") or data.get("cancelled") or "0"
        dedupe = ":".join(
            str(value)
            for value in (
                data.get("type", ""),
                data.get("source_id", ""),
                data.get("student_id", ""),
                data.get("status", ""),
                data.get("event_version", ""),
                variant,
            )
        )
    if dedupe and not _claim_push_key(dedupe):
        logger.info("FCM: doublon ignoré %s", dedupe)
        return 0

    token_auth = _access_token()
    if not token_auth:
        return 0

    guardian_ids = [g.pk for g in guardians]
    if not guardian_ids:
        logger.warning("FCM: liste guardians vide pour « %s »", title[:40])
        return 0

    tokens = list(
        ParentPushDevice.objects.filter(
            guardian_id__in=guardian_ids,
            is_active=True,
        )
        .exclude(token__startswith="local-")
        .values_list("token", flat=True)
        .distinct()
    )
    if not tokens:
        logger.warning(
            "FCM: aucun jeton actif pour guardian_ids=%s (titre=%s)",
            guardian_ids,
            title[:40],
        )
        return 0

    project_id = _project_id()
    logger.info(
        "FCM: envoi « %s » → %s appareil(s) / %s guardian(s)",
        title[:40],
        len(tokens),
        len(guardian_ids),
    )
    endpoint = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    headers = {
        "Authorization": f"Bearer {token_auth}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    payload_data = {str(k): str(v) for k, v in (data or {}).items()}
    payload_data.setdefault("title", title[:120])
    payload_data.setdefault("body", (body or "")[:240])
    # Inclure updated/cancelled dans la clé anti-doublon (sinon update ignorée).
    extra = payload_data.get("updated") or payload_data.get("cancelled") or ""
    if extra:
        payload_data.setdefault("_push_variant", extra)

    sent = 0
    for device_token in tokens:
        message = {
            "message": {
                "token": device_token,
                "notification": {
                    "title": title[:120],
                    "body": (body or "")[:240],
                },
                "android": {
                    "priority": "HIGH",
                    "ttl": "86400s",
                    "notification": {
                        "channel_id": ANDROID_CHANNEL_ID,
                        "icon": "ic_stat_notify",
                        "color": "#2E7D32",
                        "sound": "default",
                        "default_sound": True,
                        "default_vibrate_timings": True,
                        "notification_priority": "PRIORITY_MAX",
                        "visibility": "PRIVATE",
                    },
                },
                "data": payload_data,
            }
        }
        try:
            response = requests.post(
                endpoint,
                data=json.dumps(message),
                headers=headers,
                timeout=10,
            )
            if response.status_code == 200:
                sent += 1
                continue

            text = response.text[:300]
            logger.warning(
                "FCM v1 HTTP %s pour token …%s : %s",
                response.status_code,
                device_token[-8:],
                text,
            )
            if response.status_code == 401:
                _invalidate_token_cache()
            if response.status_code in (400, 404) or any(
                s in text
                for s in ("UNREGISTERED", "NOT_FOUND", "INVALID_ARGUMENT")
            ):
                ParentPushDevice.objects.filter(token=device_token).update(
                    is_active=False
                )
        except requests.RequestException as exc:
            logger.warning("FCM erreur réseau: %s", exc)

    logger.info("FCM: résultat %s/%s pour « %s »", sent, len(tokens), title[:40])
    return sent


def notify_guardians_of_communication(*, communication, updated: bool = False) -> int:
    """Push après publication ou modification d'un message secrétariat."""
    guardian_ids = (
        communication.receipts.values_list("guardian_id", flat=True).distinct()
    )
    guardians = list(Guardian.objects.filter(pk__in=guardian_ids, is_active=True))
    raw_title = (communication.title or settings.SCHOOL_NAME).strip() or settings.SCHOOL_NAME
    title = f"Message modifié — {raw_title}" if updated else raw_title
    if len(title) > 120:
        title = title[:117] + "…"
    body = (communication.content or "").strip()
    if len(body) > 160:
        body = body[:157] + "…"
    if not body:
        body = (
            "Le message de l’école a été mis à jour."
            if updated
            else "Nouveau message de l’école."
        )
    return send_push_to_guardians(
        guardians=guardians,
        title=title,
        body=body,
        data={
            "type": "secretariat_communication",
            "source_id": str(communication.public_id),
            "updated": "1" if updated else "0",
        },
    )


def notify_guardians_of_attendance(*, attendance, updated: bool = False) -> int:
    """Push a validated attendance record or later correction."""
    from apps.discipline.services.parent_notification_policy import (
        ATTENDANCE_PARENT_STATUSES,
    )

    status = attendance.status
    if status not in ATTENDANCE_PARENT_STATUSES:
        return 0

    student = attendance.student
    if student is None and getattr(attendance, "enrollment_id", None):
        student = getattr(attendance.enrollment, "student", None)
    if student is None:
        logger.warning("FCM attendance: student manquant pk=%s", attendance.pk)
        return 0

    name = _student_display_name(student)
    time_label = ""
    if attendance.arrival_time:
        time_label = attendance.arrival_time.strftime("%H:%M")

    status_label = attendance.get_status_display()
    if status == attendance.Status.LATE:
        title = "Retard modifié" if updated else "Retard signalé"
        body = (
            f"{name} est arrivé(e) en retard"
            + (f" à {time_label}" if time_label else "")
            + (
                f" ({attendance.late_minutes} min)."
                if attendance.late_minutes
                else "."
            )
        )
    elif status == attendance.Status.ABSENT:
        title = "Absence modifiée" if updated else "Absence signalée"
        body = f"{name} est marqué(e) absent(e) aujourd’hui."
    elif status == attendance.Status.PRESENT:
        title = "Présence mise à jour" if updated else "Présence confirmée"
        body = (
            f"{name} est bien arrivé(e) à l’école"
            + (f" à {time_label}." if time_label else ".")
        )
    else:
        title = f"{status_label} — mise à jour" if updated else status_label
        body = f"Le statut de présence de {name} est « {status_label} »."

    return send_push_to_guardians(
        guardians=_guardians_for_student(student),
        title=title,
        body=body,
        data={
            "type": "discipline_attendance",
            "source_id": str(attendance.public_id),
            "student_id": str(student.public_id),
            "status": status,
            "event_version": attendance.updated_at.isoformat(),
            "updated": "1" if updated else "0",
        },
    )


def notify_guardians_of_payment(*, payment, cancelled: bool = False) -> int:
    """Push après enregistrement ou annulation d’un paiement."""
    from apps.finance.models import Payment

    if cancelled:
        if payment.status != Payment.Status.CANCELLED:
            return 0
    elif payment.status != Payment.Status.VALID:
        return 0

    student = payment.student
    if student is None and getattr(payment, "enrollment_id", None):
        student = getattr(payment.enrollment, "student", None)
    if student is None:
        logger.warning("FCM payment: student manquant pk=%s", payment.pk)
        return 0

    name = _student_display_name(student)
    amount = Decimal(payment.amount_total or 0).quantize(Decimal("1"))
    amount_txt = f"{amount:,.0f}".replace(",", " ")
    currency = (payment.currency or "CDF").strip() or "CDF"
    if cancelled:
        title = "Paiement annulé"
        reason = (getattr(payment, "cancellation_reason", None) or "").strip()
        body = f"{name} — {amount_txt} {currency}" + (f" ({reason})" if reason else "")
    else:
        title = "Paiement enregistré"
        body = f"{name} — {amount_txt} {currency}"
    return send_push_to_guardians(
        guardians=_guardians_for_student(student),
        title=title,
        body=body,
        data={
            "type": "finance_payment",
            "source_id": str(payment.public_id),
            "student_id": str(student.public_id),
            "cancelled": "1" if cancelled else "0",
        },
    )


def notify_guardians_of_incident(
    *,
    incident,
    updated: bool = False,
    student_ids: set[int] | None = None,
) -> int:
    """Push an official incident without exposing other involved students."""
    from apps.discipline.services.parent_notification_policy import is_parent_visible

    if not is_parent_visible("incident", incident.status):
        return 0

    targets = [(incident.student, "Élève concerné")]
    targets.extend(
        (participant.student, participant.get_role_display())
        for participant in incident.participants.select_related("student").all()
        if participant.student_id != incident.student_id
    )
    sent = 0
    for student, role_label in targets:
        if student_ids is not None and student.pk not in student_ids:
            continue
        name = _student_display_name(student)
        title = "Incident disciplinaire mis à jour" if updated else "Incident disciplinaire"
        body = f"{name} — rôle : {role_label}. Consultez le détail dans l’application."
        sent += send_push_to_guardians(
            guardians=_guardians_for_student(student),
            title=title,
            body=body,
            data={
                "type": "discipline_incident",
                "source_id": str(incident.public_id),
                "student_id": str(student.public_id),
                "status": incident.status,
                "event_version": incident.updated_at.isoformat(),
                "updated": "1" if updated else "0",
            },
        )
    return sent


def notify_guardians_of_summons(*, summons, updated: bool = False) -> int:
    """Push après enregistrement / modification d’une convocation parent."""
    from apps.discipline.services.parent_notification_policy import is_parent_visible

    if not is_parent_visible("summons", summons.status):
        return 0
    student = summons.student
    if student is None:
        return 0
    name = _student_display_name(student)
    title = "Convocation mise à jour" if updated else "Convocation"
    reason = (summons.reason or "").strip()
    body = f"{name} — {reason}" if reason else f"Convocation concernant {name}."
    if len(body) > 160:
        body = body[:157] + "…"
    return send_push_to_guardians(
        guardians=_guardians_for_summons(summons),
        title=title,
        body=body,
        data={
            "type": "discipline_summons",
            "source_id": str(summons.public_id),
            "student_id": str(student.public_id),
            "status": summons.status,
            "event_version": summons.updated_at.isoformat(),
            "updated": "1" if updated else "0",
        },
    )


def notify_guardians_of_measure(*, measure, updated: bool = False) -> int:
    from apps.discipline.services.parent_notification_policy import is_parent_visible

    if not is_parent_visible("measure", measure.status):
        return 0
    student = measure.student
    name = _student_display_name(student)
    label = measure.measure_type.name
    title = "Mesure disciplinaire mise à jour" if updated else "Mesure disciplinaire"
    return send_push_to_guardians(
        guardians=_guardians_for_student(student),
        title=title,
        body=f"{name} — {label} ({measure.get_status_display()}).",
        data={
            "type": "discipline_measure",
            "source_id": str(measure.public_id),
            "student_id": str(student.public_id),
            "status": measure.status,
            "event_version": measure.updated_at.isoformat(),
            "updated": "1" if updated else "0",
        },
    )


def notify_guardians_of_exit(*, exit_authorization, updated: bool = False) -> int:
    from apps.discipline.services.parent_notification_policy import is_parent_visible

    if not is_parent_visible("exit", exit_authorization.status):
        return 0
    student = exit_authorization.student
    title = "Sortie mise à jour" if updated else "Autorisation de sortie"
    body = (
        f"{_student_display_name(student)} — "
        f"{exit_authorization.get_status_display()}."
    )
    return send_push_to_guardians(
        guardians=_guardians_for_student(student),
        title=title,
        body=body,
        data={
            "type": "discipline_exit",
            "source_id": str(exit_authorization.public_id),
            "student_id": str(student.public_id),
            "status": exit_authorization.status,
            "event_version": exit_authorization.updated_at.isoformat(),
            "updated": "1" if updated else "0",
        },
    )


def notify_guardians_of_justification(*, justification, updated: bool = False) -> int:
    from apps.discipline.services.parent_notification_policy import is_parent_visible

    if not is_parent_visible("justification", justification.status):
        return 0
    student = justification.attendance.student
    title = "Justification mise à jour" if updated else "Justification d’absence"
    body = (
        f"{_student_display_name(student)} — "
        f"{justification.get_status_display()}."
    )
    return send_push_to_guardians(
        guardians=_guardians_for_student(student),
        title=title,
        body=body,
        data={
            "type": "discipline_justification",
            "source_id": str(justification.public_id),
            "student_id": str(student.public_id),
            "status": justification.status,
            "event_version": justification.updated_at.isoformat(),
            "updated": "1" if updated else "0",
        },
    )


def notify_guardians_of_student_removed(
    *,
    student,
    guardians: list | None = None,
    reason: str = "",
) -> int:
    """Push parents when a child is removed from the school roster."""
    name = _student_display_name(student)
    title = "Élève retiré"
    motif = (reason or "").strip()
    body = (
        f"{name} a été retiré(e) de l'établissement."
        + (f" Motif : {motif}" if motif else "")
    )
    if len(body) > 200:
        body = body[:197] + "…"
    targets = list(guardians) if guardians is not None else _guardians_for_student(student)
    return send_push_to_guardians(
        guardians=targets,
        title=title,
        body=body,
        data={
            "type": "student_removed",
            "source_id": str(getattr(student, "public_id", "") or ""),
            "student_id": str(getattr(student, "public_id", "") or ""),
            "removed": "1",
        },
    )

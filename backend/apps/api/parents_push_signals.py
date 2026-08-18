"""Signaux Django : push FCM création + modification (pas suppression / expiration)."""

from __future__ import annotations

import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _safe_on_commit(fn) -> None:
    def _run() -> None:
        try:
            fn()
        except Exception:
            logger.exception("FCM signal push échoué")

    try:
        transaction.on_commit(_run)
    except Exception:
        _run()


def _stash_previous(instance, fields: tuple[str, ...]) -> None:
    if not instance.pk:
        instance._fcm_previous = None
        return
    try:
        previous = instance.__class__.objects.filter(pk=instance.pk).values(*fields).first()
    except Exception:
        previous = None
    instance._fcm_previous = previous


@receiver(pre_save, sender="discipline.DailyAttendance")
def stash_attendance(sender, instance, **kwargs):
    _stash_previous(
        instance,
        ("status", "arrival_time", "late_minutes", "note"),
    )


@receiver(pre_save, sender="finance.Payment")
def stash_payment(sender, instance, **kwargs):
    _stash_previous(instance, ("status", "amount_total", "currency"))


@receiver(pre_save, sender="discipline.DisciplinaryIncident")
def stash_incident(sender, instance, **kwargs):
    _stash_previous(instance, ("status", "title", "description", "severity"))


@receiver(pre_save, sender="discipline.ParentSummons")
def stash_summons(sender, instance, **kwargs):
    _stash_previous(
        instance,
        ("status", "reason", "description", "summon_date"),
    )


@receiver(pre_save, sender="discipline.DisciplinaryMeasure")
def stash_measure(sender, instance, **kwargs):
    _stash_previous(
        instance,
        ("status", "description", "reason", "start_date", "end_date", "result_note"),
    )


@receiver(pre_save, sender="discipline.ExitAuthorization")
def stash_exit(sender, instance, **kwargs):
    _stash_previous(
        instance,
        (
            "status",
            "date",
            "planned_exit_time",
            "actual_exit_time",
            "expected_return_time",
            "actual_return_time",
            "reason",
            "note",
        ),
    )


@receiver(pre_save, sender="discipline.AbsenceJustification")
def stash_justification(sender, instance, **kwargs):
    _stash_previous(instance, ("status", "reason", "description", "review_note"))


@receiver(pre_save, sender="discipline.IncidentParticipant")
def stash_incident_participant(sender, instance, **kwargs):
    _stash_previous(instance, ("student_id", "role", "note", "is_confirmed"))


@receiver(pre_save, sender="secretariat.Communication")
def stash_communication(sender, instance, **kwargs):
    _stash_previous(
        instance,
        ("status", "title", "content", "priority", "category", "expires_at"),
    )


@receiver(post_save, sender="discipline.DailyAttendance")
def push_on_attendance(sender, instance, created, **kwargs):
    """
    Ne plus pousser à chaque pointage QR / brouillon.

    Les parents sont notifiés uniquement après validation de la feuille
    (voir validate_sheet → notify explicite).
    """
    return


@receiver(post_save, sender="finance.Payment")
def push_on_payment(sender, instance, created, **kwargs):
    from apps.finance.models import Payment

    prev = getattr(instance, "_fcm_previous", None)
    payment_id = instance.pk

    if instance.status == Payment.Status.CANCELLED:
        was_valid = bool(prev) and prev.get("status") == Payment.Status.VALID
        if not was_valid:
            return

        def _send_cancel() -> None:
            from apps.api.parents_push import notify_guardians_of_payment
            from apps.finance.models import Payment as P

            pay = (
                P.objects.select_related("student", "enrollment", "enrollment__student")
                .filter(pk=payment_id)
                .first()
            )
            if pay is not None:
                notify_guardians_of_payment(payment=pay, cancelled=True)

        _safe_on_commit(_send_cancel)
        return

    if instance.status != Payment.Status.VALID:
        return
    if not created:
        return

    def _send() -> None:
        from apps.api.parents_push import notify_guardians_of_payment
        from apps.finance.models import Payment as P

        pay = (
            P.objects.select_related("student", "enrollment", "enrollment__student")
            .filter(pk=payment_id)
            .first()
        )
        if pay is not None:
            notify_guardians_of_payment(payment=pay)

    _safe_on_commit(_send)


@receiver(post_save, sender="discipline.DisciplinaryIncident")
def push_on_incident(sender, instance, created, **kwargs):
    from apps.discipline.services.parent_notification_policy import (
        meaningful_fields_changed,
        notification_variant,
    )

    prev = getattr(instance, "_fcm_previous", None)
    variant = notification_variant(
        kind="incident",
        current_status=instance.status,
        previous_status=prev.get("status") if prev else None,
        created=created,
        meaningful_changed=meaningful_fields_changed(
            instance, prev, ("title", "description", "severity")
        ),
    )
    if variant is None:
        return

    incident_id = instance.pk

    def _send() -> None:
        from apps.api.parents_push import notify_guardians_of_incident
        from apps.discipline.models import DisciplinaryIncident as DI

        inc = (
            DI.objects.select_related("student")
            .prefetch_related("participants__student")
            .filter(pk=incident_id)
            .first()
        )
        if inc is not None:
            notify_guardians_of_incident(incident=inc, updated=variant == "updated")

    _safe_on_commit(_send)


@receiver(post_save, sender="discipline.IncidentParticipant")
def push_on_incident_participant(sender, instance, created, **kwargs):
    from apps.discipline.services.parent_notification_policy import is_parent_visible

    incident = instance.incident
    if not is_parent_visible("incident", incident.status):
        return
    previous = getattr(instance, "_fcm_previous", None)
    changed = created or (
        previous
        and any(
            previous.get(field) != getattr(instance, field)
            for field in ("student_id", "role", "note", "is_confirmed")
        )
    )
    if not changed:
        return
    incident_id = incident.pk
    participant_student_id = instance.student_id

    def _send() -> None:
        from apps.api.parents_push import notify_guardians_of_incident
        from apps.discipline.models import DisciplinaryIncident

        row = (
            DisciplinaryIncident.objects.select_related("student")
            .prefetch_related("participants__student")
            .filter(pk=incident_id)
            .first()
        )
        if row is not None:
            notify_guardians_of_incident(
                incident=row,
                updated=True,
                student_ids={participant_student_id},
            )

    _safe_on_commit(_send)


@receiver(post_save, sender="discipline.ParentSummons")
def push_on_summons(sender, instance, created, **kwargs):
    from apps.discipline.services.parent_notification_policy import (
        meaningful_fields_changed,
        notification_variant,
    )

    prev = getattr(instance, "_fcm_previous", None)
    variant = notification_variant(
        kind="summons",
        current_status=instance.status,
        previous_status=prev.get("status") if prev else None,
        created=created,
        meaningful_changed=meaningful_fields_changed(
            instance, prev, ("reason", "description", "summon_date")
        ),
    )
    if variant is None:
        return

    summons_id = instance.pk

    def _send() -> None:
        from apps.api.parents_push import notify_guardians_of_summons
        from apps.discipline.models import ParentSummons as PS

        sm = PS.objects.select_related("student").filter(pk=summons_id).first()
        if sm is not None:
            notify_guardians_of_summons(summons=sm, updated=variant == "updated")

    _safe_on_commit(_send)


def _push_discipline_instance(
    *,
    instance,
    created: bool,
    kind: str,
    fields: tuple[str, ...],
    model,
    select_related: tuple[str, ...],
    notify_name: str,
) -> None:
    from apps.discipline.services.parent_notification_policy import (
        meaningful_fields_changed,
        notification_variant,
    )

    prev = getattr(instance, "_fcm_previous", None)
    variant = notification_variant(
        kind=kind,
        current_status=instance.status,
        previous_status=prev.get("status") if prev else None,
        created=created,
        meaningful_changed=meaningful_fields_changed(instance, prev, fields),
    )
    if variant is None:
        return
    row_id = instance.pk

    def _send() -> None:
        from apps.api import parents_push

        row = model.objects.select_related(*select_related).filter(pk=row_id).first()
        if row is None:
            return
        notify = getattr(parents_push, notify_name)
        argument = {
            "measure": "measure",
            "exit": "exit_authorization",
            "justification": "justification",
        }[kind]
        notify(**{argument: row, "updated": variant == "updated"})

    _safe_on_commit(_send)


@receiver(post_save, sender="discipline.DisciplinaryMeasure")
def push_on_measure(sender, instance, created, **kwargs):
    from apps.discipline.models import DisciplinaryMeasure

    _push_discipline_instance(
        instance=instance,
        created=created,
        kind="measure",
        fields=("description", "reason", "start_date", "end_date", "result_note"),
        model=DisciplinaryMeasure,
        select_related=("student", "measure_type"),
        notify_name="notify_guardians_of_measure",
    )


@receiver(post_save, sender="discipline.ExitAuthorization")
def push_on_exit(sender, instance, created, **kwargs):
    from apps.discipline.models import ExitAuthorization

    _push_discipline_instance(
        instance=instance,
        created=created,
        kind="exit",
        fields=(
            "date",
            "planned_exit_time",
            "actual_exit_time",
            "expected_return_time",
            "actual_return_time",
            "reason",
            "note",
        ),
        model=ExitAuthorization,
        select_related=("student",),
        notify_name="notify_guardians_of_exit",
    )


@receiver(post_save, sender="discipline.AbsenceJustification")
def push_on_justification(sender, instance, created, **kwargs):
    from apps.discipline.models import AbsenceJustification

    _push_discipline_instance(
        instance=instance,
        created=created,
        kind="justification",
        fields=("reason", "description", "review_note"),
        model=AbsenceJustification,
        select_related=("attendance", "attendance__student"),
        notify_name="notify_guardians_of_justification",
    )


@receiver(post_save, sender="secretariat.Communication")
def push_on_communication_update(sender, instance, created, **kwargs):
    """Modification d’un message déjà publié → push « Message modifié »."""
    from apps.secretariat.models import Communication

    if instance.status != Communication.Status.PUBLISHED:
        return
    if created:
        return

    prev = getattr(instance, "_fcm_previous", None)
    if not prev:
        return
    if prev.get("status") != Communication.Status.PUBLISHED:
        return
    changed = any(
        prev.get(f) != getattr(instance, f)
        for f in ("title", "content", "priority", "category", "expires_at")
    )
    if not changed:
        return

    comm_id = instance.pk

    def _send() -> None:
        from apps.api.parents_push import notify_guardians_of_communication
        from apps.secretariat.models import Communication as C

        comm = C.objects.filter(pk=comm_id).first()
        if comm is not None:
            notify_guardians_of_communication(communication=comm, updated=True)

    _safe_on_commit(_send)

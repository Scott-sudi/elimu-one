"""Guardian management and student association services."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.secretariat.models import Guardian, Student, StudentGuardian

from . import audit_secretariat_action
from .exceptions import SecretariatError

_PHONE_DIGITS_RE = re.compile(r"\D+")
DRC_COUNTRY_CODE = "243"
PHONE_FORMAT_MESSAGE = "Le numéro doit commencer par 0, par +243 ou par 243 (ex. 0990123456)."


def normalize_phone(value: str) -> str:
    """Normalize a phone to its national significant digits (DRC).

    Accepted entry formats are ``0…`` and ``+243…``; both resolve to the same
    identifier (leading ``0`` / ``+243`` ignored for comparison).
    """
    compact = re.sub(r"[\s\-.\u00a0]", "", value or "")
    if compact.startswith("+243"):
        digits = _PHONE_DIGITS_RE.sub("", compact[4:])
        return digits.lstrip("0")
    digits = _PHONE_DIGITS_RE.sub("", compact)
    if not digits:
        return ""
    # Local 0… (and legacy stored values without '+')
    if digits.startswith(DRC_COUNTRY_CODE) and len(digits) > len(DRC_COUNTRY_CODE) + 6:
        digits = digits[len(DRC_COUNTRY_CODE) :]
    return digits.lstrip("0")


def assert_accepted_phone_format(value: str) -> str:
    """Accept ``0…``, ``+243…`` or ``243…`` (DRC)."""
    raw = (value or "").strip()
    if not raw:
        raise SecretariatError("Le téléphone du responsable est obligatoire.")
    compact = re.sub(r"[\s\-.\u00a0]", "", raw)
    if compact.startswith("+243"):
        rest = _PHONE_DIGITS_RE.sub("", compact[4:])
        if len(rest) < 8:
            raise SecretariatError("Indiquez un numéro de téléphone complet.")
        return f"+243{rest}"
    digits = _PHONE_DIGITS_RE.sub("", compact)
    if digits.startswith(DRC_COUNTRY_CODE) and len(digits) > len(DRC_COUNTRY_CODE) + 6:
        rest = digits[len(DRC_COUNTRY_CODE) :].lstrip("0")
        if len(rest) < 8:
            raise SecretariatError("Indiquez un numéro de téléphone complet.")
        return f"+243{rest}"
    if re.fullmatch(r"0\d{8,14}", digits):
        return digits
    # 9–10 digits without leading 0 (souvent saisi ainsi) → préfixer 0
    if re.fullmatch(r"[1-9]\d{7,13}", digits):
        return f"0{digits}"
    raise SecretariatError(
        "Le numéro doit commencer par 0, par +243 ou par 243 (ex. 0990123456)."
    )


def name_tokens(*parts: str) -> set[str]:
    tokens: set[str] = set()
    for part in parts:
        if not part:
            continue
        for raw in part.replace("-", " ").split():
            token = raw.strip().casefold()
            if token:
                tokens.add(token)
    return tokens


def ordered_name_tokens(*parts: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        if not part:
            continue
        for raw in part.replace("-", " ").split():
            token = raw.strip()
            key = token.casefold()
            if token and key not in seen:
                seen.add(key)
                ordered.append(token)
    return ordered


def split_name_tokens(tokens: list[str]) -> dict[str, str]:
    if not tokens:
        raise SecretariatError("Le nom du responsable est obligatoire.")
    if len(tokens) == 1:
        return {"nom": tokens[0], "postnom": "", "prenom": tokens[0]}
    if len(tokens) == 2:
        return {"nom": tokens[0], "postnom": "", "prenom": tokens[1]}
    return {
        "nom": tokens[0],
        "postnom": tokens[1],
        "prenom": " ".join(tokens[2:]),
    }


def names_are_compatible(*, existing: Guardian, submitted_name: str) -> bool:
    """At least one name token must overlap (same responsable, flexible spelling)."""
    existing_tokens = name_tokens(existing.nom, existing.postnom, existing.prenom)
    submitted_tokens = name_tokens(submitted_name)
    return bool(existing_tokens and submitted_tokens and (existing_tokens & submitted_tokens))


def _assign_identification_if_missing(
    guardian: Guardian,
    *,
    academic_year_start: int | None = None,
) -> None:
    """Ensure every guardian has a unique parent identification number."""
    if (guardian.numero_identification or "").strip():
        from apps.secretariat.services.guardian_identification_service import (
            assert_valid_identification_format,
            ensure_unique_guardian_identification,
        )

        try:
            cleaned = assert_valid_identification_format(guardian.numero_identification)
            if cleaned:
                guardian.numero_identification = ensure_unique_guardian_identification(
                    cleaned,
                    exclude_pk=guardian.pk,
                )
        except ValueError as exc:
            raise SecretariatError(str(exc)) from exc
        return
    from apps.secretariat.services.guardian_identification_service import (
        next_guardian_identification,
        next_guardian_sequence,
    )

    year_start = academic_year_start or timezone.localdate().year
    guardian.numero_identification = next_guardian_identification(
        academic_year_start=year_start,
        sequence=next_guardian_sequence(academic_year_start=year_start),
        exclude_pk=guardian.pk,
    )


def _save_guardian(
    guardian: Guardian,
    *,
    academic_year_start: int | None = None,
) -> Guardian:
    _assign_identification_if_missing(guardian, academic_year_start=academic_year_start)
    try:
        guardian.full_clean()
        guardian.save()
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            parts: list[str] = []
            for messages in exc.message_dict.values():
                parts.extend(messages)
            raise SecretariatError(" ".join(parts) if parts else "; ".join(exc.messages)) from exc
        raise SecretariatError("; ".join(exc.messages)) from exc
    return guardian


def find_guardian_by_phone(phone: str) -> Guardian | None:
    """Resolve a guardian by phone (principal or secondaire), digit-normalized."""
    norm = normalize_phone(phone)
    if not norm:
        return None
    # Narrow candidates for common DRC spellings (0… / +243… / 243…), then compare normalized.
    needles = {norm, f"0{norm}", f"{DRC_COUNTRY_CODE}{norm}"}
    query = Q()
    for needle in needles:
        query |= Q(telephone_principal__icontains=needle) | Q(telephone_secondaire__icontains=needle)
    candidates = Guardian.objects.filter(query, is_archived=False)
    for guardian in candidates:
        if normalize_phone(guardian.telephone_principal) == norm:
            return guardian
        if normalize_phone(guardian.telephone_secondaire) == norm:
            return guardian
    return None


def require_existing_guardian_by_phone(phone: str) -> Guardian:
    """Return the guardian for this phone, or raise a clear secretariat error."""
    cleaned = assert_accepted_phone_format(phone)
    guardian = find_guardian_by_phone(cleaned)
    if guardian is None:
        raise SecretariatError(
            "Aucun responsable n'est enregistré avec ce numéro de téléphone. "
            "Créez d'abord le responsable dans le menu Responsables, "
            "puis revenez inscrire l'élève."
        )
    return guardian


def default_relationship_for_guardian(guardian: Guardian) -> str:
    """Reuse an existing link type when possible; otherwise tuteur légal."""
    existing = (
        StudentGuardian.objects.filter(guardian=guardian)
        .order_by("-id")
        .values_list("lien_parente", flat=True)
        .first()
    )
    if existing:
        return existing
    return StudentGuardian.Relationship.LEGAL_GUARDIAN


def search_guardians_by_phone_digits(phone: str, *, limit: int = 8) -> list[Guardian]:
    """Partial phone search for typeahead (as the secretary types)."""
    digits = _PHONE_DIGITS_RE.sub("", phone or "")
    if len(digits) < 3:
        return []
    # Prefer the national significant part when a leading 0 / 243 is present.
    norm = normalize_phone(phone)
    needles = []
    for candidate in (digits, norm, digits.lstrip("0"), f"0{norm}" if norm else ""):
        if candidate and len(candidate) >= 3 and candidate not in needles:
            needles.append(candidate)
    query = Q()
    for needle in needles:
        query |= Q(telephone_principal__icontains=needle) | Q(telephone_secondaire__icontains=needle)
    qs = Guardian.objects.filter(query, is_archived=False).order_by("nom", "prenom")[: max(limit * 3, 12)]
    # Rank exact normalized matches first, then prefix-like.
    scored: list[tuple[int, Guardian]] = []
    for guardian in qs:
        p1 = normalize_phone(guardian.telephone_principal)
        p2 = normalize_phone(guardian.telephone_secondaire)
        score = 50
        if norm and (p1 == norm or p2 == norm):
            score = 0
        elif norm and (p1.startswith(norm) or p2.startswith(norm)):
            score = 1
        elif any(needle in (guardian.telephone_principal or "") or needle in (guardian.telephone_secondaire or "") for needle in needles):
            score = 2
        scored.append((score, guardian))
    scored.sort(key=lambda item: (item[0], str(item[1]).casefold()))
    return [g for _, g in scored[:limit]]


def assert_phone_available(*, phone: str, exclude_pk=None) -> None:
    """A phone number identifies one responsable only."""
    norm = normalize_phone(phone)
    if not norm:
        return
    existing = find_guardian_by_phone(phone)
    if existing is not None and existing.pk != exclude_pk:
        raise SecretariatError(
            f"Le numéro « {phone} » est déjà lié au responsable « {existing} ». "
            "Utilisez le même nom (au moins un prénom/nom en commun) pour l’associer "
            "à un autre élève, ou choisissez un autre numéro."
        )


def create_guardian(*, actor=None, request=None, academic_year_start: int | None = None, **data) -> Guardian:
    principal = assert_accepted_phone_format(data.get("telephone_principal", ""))
    data["telephone_principal"] = principal
    secondary = (data.get("telephone_secondaire") or "").strip()
    if secondary:
        secondary = assert_accepted_phone_format(secondary)
        data["telephone_secondaire"] = secondary
        if normalize_phone(secondary) == normalize_phone(principal):
            raise SecretariatError("Les deux numéros de téléphone doivent être différents.")
        assert_phone_available(phone=secondary)
    else:
        data["telephone_secondaire"] = ""
    assert_phone_available(phone=principal)
    data.pop("numero_identification", None)
    guardian = _save_guardian(Guardian(**data), academic_year_start=academic_year_start)
    audit_secretariat_action(
        action=AuditLog.Action.GUARDIAN_CREATED,
        instance=guardian,
        description=f"Création du responsable {guardian}",
        actor=actor,
        request=request,
    )
    return guardian


@transaction.atomic
def update_guardian(guardian: Guardian, *, actor=None, request=None, **data) -> Guardian:
    guardian = Guardian.objects.select_for_update().get(pk=guardian.pk)
    data.pop("numero_identification", None)
    for field, value in data.items():
        if field not in {"id", "pk", "public_id"}:
            setattr(guardian, field, value)
    principal = assert_accepted_phone_format(guardian.telephone_principal)
    guardian.telephone_principal = principal
    secondary = (guardian.telephone_secondaire or "").strip()
    if secondary:
        secondary = assert_accepted_phone_format(secondary)
        guardian.telephone_secondaire = secondary
        if normalize_phone(secondary) == normalize_phone(principal):
            raise SecretariatError("Les deux numéros de téléphone doivent être différents.")
        assert_phone_available(phone=secondary, exclude_pk=guardian.pk)
    else:
        guardian.telephone_secondaire = ""
    assert_phone_available(phone=principal, exclude_pk=guardian.pk)
    _save_guardian(guardian)
    audit_secretariat_action(
        action=AuditLog.Action.GUARDIAN_UPDATED,
        instance=guardian,
        description=f"Modification du responsable {guardian}",
        actor=actor,
        request=request,
    )
    return guardian


@transaction.atomic
def archive_guardian(guardian: Guardian, *, actor=None, request=None) -> Guardian:
    guardian = Guardian.objects.select_for_update().get(pk=guardian.pk)
    guardian.archive()
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_DELETED,
        instance=guardian,
        description=f"Archivage du responsable {guardian}",
        actor=actor,
        request=request,
    )
    return guardian


@transaction.atomic
def restore_guardian(guardian: Guardian, *, actor=None, request=None) -> Guardian:
    guardian = Guardian.objects.select_for_update().get(pk=guardian.pk)
    if not guardian.is_archived:
        raise SecretariatError("Ce responsable n'est pas archivé.")
    guardian.restore()
    audit_secretariat_action(
        action=AuditLog.Action.ENTITY_RESTORED,
        instance=guardian,
        description=f"Restauration du responsable {guardian}",
        actor=actor,
        request=request,
    )
    return guardian


def find_guardian_candidates(
    *,
    phone: str = "",
    email: str = "",
    name: str = "",
) -> QuerySet[Guardian]:
    query = Q()
    if phone:
        query |= Q(telephone_principal__icontains=phone) | Q(telephone_secondaire__icontains=phone)
    if email:
        query |= Q(email__iexact=email)
    if name:
        for term in name.split():
            query &= Q(nom__icontains=term) | Q(postnom__icontains=term) | Q(prenom__icontains=term)
    return Guardian.objects.filter(query, is_archived=False).distinct() if query else Guardian.objects.none()


def _enrich_guardian_name_if_needed(guardian: Guardian, submitted_name: str) -> None:
    """Keep existing tokens; append any new compatible tokens from the submitted name."""
    existing = ordered_name_tokens(guardian.nom, guardian.postnom, guardian.prenom)
    submitted = ordered_name_tokens(submitted_name)
    existing_keys = {t.casefold() for t in existing}
    submitted_keys = {t.casefold() for t in submitted}
    if not existing_keys & submitted_keys:
        return
    merged = existing + [t for t in submitted if t.casefold() not in existing_keys]
    if merged == existing:
        return
    parts = split_name_tokens(merged)
    guardian.nom = parts["nom"]
    guardian.postnom = parts["postnom"]
    guardian.prenom = parts["prenom"]
    _save_guardian(guardian)


@transaction.atomic
def resolve_or_create_guardian_for_enrollment(
    *,
    full_name: str,
    telephone_principal: str,
    telephone_secondaire: str = "",
    academic_year_start: int | None = None,
    actor=None,
    request=None,
) -> Guardian:
    """
    Phone is the identifier. Same number → same responsable.

    Name flexibility: at least one token must match the registered name.
    Completely different names for the same phone are rejected.
    Compatible extra tokens may enrich the stored name (never replace it wholesale).
    """
    full_name = (full_name or "").strip()
    telephone_principal = assert_accepted_phone_format(telephone_principal)
    telephone_secondaire = (telephone_secondaire or "").strip()
    if telephone_secondaire:
        telephone_secondaire = assert_accepted_phone_format(telephone_secondaire)

    if not full_name:
        raise SecretariatError("Le nom du responsable est obligatoire.")

    existing = find_guardian_by_phone(telephone_principal)
    if existing is None and telephone_secondaire:
        existing = find_guardian_by_phone(telephone_secondaire)

    if existing is not None:
        if not names_are_compatible(existing=existing, submitted_name=full_name):
            raise SecretariatError(
                f"Le numéro « {telephone_principal} » appartient déjà à « {existing} ». "
                "Vous ne pouvez pas l’associer sous un nom totalement différent : "
                "au moins un des noms (nom, postnom ou prénom) doit correspondre."
            )
        _enrich_guardian_name_if_needed(existing, full_name)
        # Optionally fill empty secondary phone if provided and free.
        if telephone_secondaire and not existing.telephone_secondaire:
            if normalize_phone(telephone_secondaire) != normalize_phone(existing.telephone_principal):
                other = find_guardian_by_phone(telephone_secondaire)
                if other is None or other.pk == existing.pk:
                    existing.telephone_secondaire = telephone_secondaire
                    _save_guardian(existing, academic_year_start=academic_year_start)
        return existing

    # New phone — ensure secondary does not belong to someone else.
    if telephone_secondaire:
        if normalize_phone(telephone_secondaire) == normalize_phone(telephone_principal):
            raise SecretariatError("Les deux numéros de téléphone doivent être différents.")
        assert_phone_available(phone=telephone_secondaire)

    parts = split_name_tokens(ordered_name_tokens(full_name))
    return create_guardian(
        actor=actor,
        request=request,
        academic_year_start=academic_year_start,
        nom=parts["nom"],
        postnom=parts["postnom"],
        prenom=parts["prenom"],
        telephone_principal=telephone_principal,
        telephone_secondaire=telephone_secondaire,
    )


@transaction.atomic
def link_responsable_to_student(
    *,
    student: Student,
    full_name: str,
    telephone_principal: str,
    lien_parente: str,
    telephone_secondaire: str = "",
    academic_year_start: int | None = None,
    is_primary: bool = True,
    actor=None,
    request=None,
) -> StudentGuardian:
    """Create/reuse guardian by phone and associate to the student with relationship."""
    guardian = resolve_or_create_guardian_for_enrollment(
        full_name=full_name,
        telephone_principal=telephone_principal,
        telephone_secondaire=telephone_secondaire,
        academic_year_start=academic_year_start,
        actor=actor,
        request=request,
    )
    return associate_guardian(
        student=student,
        guardian=guardian,
        lien_parente=lien_parente,
        is_primary=is_primary,
        actor=actor,
        request=request,
    )


@transaction.atomic
def associate_guardian(
    *,
    student: Student,
    guardian: Guardian,
    lien_parente: str,
    is_primary: bool = False,
    actor=None,
    request=None,
    **data,
) -> StudentGuardian:
    student = Student.objects.select_for_update().get(pk=student.pk)
    if student.is_archived or guardian.is_archived:
        raise SecretariatError("Un élève ou responsable archivé ne peut pas être associé.")
    links = StudentGuardian.objects.select_for_update().filter(student=student)
    other_guardian = links.exclude(guardian=guardian).first()
    if other_guardian is not None:
        raise SecretariatError(
            f"Cet élève est déjà lié au responsable « {other_guardian.guardian} ». "
            "Un élève ne peut avoir qu'un seul responsable dans le système."
        )
    is_primary = True
    link, _ = StudentGuardian.objects.update_or_create(
        student=student,
        guardian=guardian,
        defaults={"lien_parente": lien_parente, "is_primary": is_primary, **data},
    )
    audit_secretariat_action(
        action=AuditLog.Action.GUARDIAN_ASSOCIATED,
        instance=student,
        description=f"Association de {guardian} à l'élève {student.matricule}",
        actor=actor,
        request=request,
    )
    return link

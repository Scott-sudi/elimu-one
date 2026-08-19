"""Guardian identification number generation tests."""

from __future__ import annotations

import pytest

from apps.secretariat.services.guardian_identification_service import (
    generate_guardian_identification,
    generate_legacy_guardian_identification,
    normalize_identification_number,
)


def test_generate_guardian_identification_parent_format():
    ident = generate_guardian_identification(
        academic_year_start=2026,
        section_code="SCI",
        option_code="SCIENCE",
        class_letter="A",
        sequence=42,
    )
    assert ident == "ELM2026R00042"


def test_generate_legacy_guardian_identification_length_and_parts():
    ident = generate_legacy_guardian_identification(
        academic_year_start=2026,
        section_code="SCI",
        option_code="SCIENCE",
        class_letter="A",
        sequence=847,
    )
    assert len(ident) == 12
    assert ident.startswith("26IK")
    assert ident.endswith("0847")


def test_normalize_identification_number():
    assert normalize_identification_number("elm2026r00042") == "ELM2026R00042"
    assert normalize_identification_number("kal-2026-r-0042") == "KAL-2026-R-0042"
    assert normalize_identification_number("26 ik-spga 0847") == "26IKSPGA0847"

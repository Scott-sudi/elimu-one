"""Tests for ELM student/guardian identifier formats."""

from __future__ import annotations

from apps.secretariat.services.identifier_format import guardian_identification_stem


def test_guardian_identification_stem():
    assert guardian_identification_stem(academic_year_start=2026) == "ELM2026R"

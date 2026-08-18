"""Tests for parents mobile phone + identification verification API."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.secretariat.services.guardian_service import create_guardian

FAILURE_SNIPPET = "identifiants incorrects"


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_verify_credentials_recognized(api):
    guardian = create_guardian(
        nom="Kabasele",
        prenom="Jean",
        telephone_principal="0991112233",
        numero_identification="CD12345678",
    )
    response = api.post(
        "/api/v1/parents/auth/verify-phone/",
        {
            "telephone": "0991112233",
            "numero_identification": "cd 1234 5678",
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["recognized"] is True
    assert body["data"]["guardian_public_id"] == str(guardian.public_id)
    assert "Jean" in body["data"]["display_name"]
    assert body["data"]["next_auth_step"] == "password"


@pytest.mark.django_db
def test_verify_credentials_wrong_id(api):
    create_guardian(
        nom="Kabasele",
        prenom="Jean",
        telephone_principal="0991112233",
        numero_identification="CD12345678",
    )
    response = api.post(
        "/api/v1/parents/auth/verify-phone/",
        {
            "telephone": "0991112233",
            "numero_identification": "WRONG-ID",
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["recognized"] is False
    assert FAILURE_SNIPPET in body["message"].lower()


@pytest.mark.django_db
def test_verify_credentials_empty_id_in_db(api):
    create_guardian(
        nom="Ilunga",
        prenom="Marie",
        telephone_principal="0812345678",
        numero_identification="",
    )
    response = api.post(
        "/api/v1/parents/auth/verify-phone/",
        {
            "telephone": "+243812345678",
            "numero_identification": "ANYTHING",
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["recognized"] is False
    assert FAILURE_SNIPPET in body["message"].lower()


@pytest.mark.django_db
def test_verify_credentials_unknown_phone(api):
    response = api.post(
        "/api/v1/parents/auth/verify-phone/",
        {
            "telephone": "0990000000",
            "numero_identification": "CD999",
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["recognized"] is False
    assert FAILURE_SNIPPET in body["message"].lower()


@pytest.mark.django_db
def test_verify_credentials_missing_id_field(api):
    response = api.post(
        "/api/v1/parents/auth/verify-phone/",
        {"telephone": "0991112233"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.django_db
def test_verify_credentials_invalid_phone_format(api):
    response = api.post(
        "/api/v1/parents/auth/verify-phone/",
        {
            "telephone": "123",
            "numero_identification": "CD123",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.django_db
def test_verify_credentials_via_get(api):
    guardian = create_guardian(
        nom="Kabasele",
        prenom="Jean",
        telephone_principal="0991112233",
        numero_identification="CD12345678",
    )
    response = api.get(
        "/api/v1/parents/auth/verify-phone/",
        {
            "telephone": "0991112233",
            "numero_identification": "CD12345678",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["recognized"] is True
    assert body["data"]["guardian_public_id"] == str(guardian.public_id)

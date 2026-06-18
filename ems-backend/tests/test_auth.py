import pytest
from django.test import override_settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@override_settings(DEBUG=True)
def verified_phone_token(client, phone="+243812345678"):
    sent = client.post("/api/auth/phone/send-code/", {"phone": phone}, format="json")
    assert sent.status_code == 201
    code = sent.data["dev_code"]
    verified = client.post(
        "/api/auth/phone/verify-code/",
        {"phone": phone, "code": code},
        format="json",
    )
    assert verified.status_code == 200
    return verified.data["phone_verification_token"]


def test_register_and_login(client):
    phone = "+243812345678"
    token = verified_phone_token(client, phone)
    resp = client.post(
        "/api/auth/register/",
        {
            "username": "alice",
            "email": "a@x.com",
            "password": "secret123",
            "password_confirm": "secret123",
            "phone": phone,
            "phone_verification_token": token,
        },
        format="json",
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/auth/login/",
        {"username": "alice", "password": "secret123"},
        format="json",
    )
    assert resp.status_code == 200
    assert "access" in resp.data

    token = resp.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    me = client.get("/api/auth/me/")
    assert me.status_code == 200
    assert me.data["username"] == "alice"
    assert me.data["phone_verified"] is True


def test_register_rejects_password_mismatch(client):
    resp = client.post(
        "/api/auth/register/",
        {
            "username": "bob",
            "email": "b@x.com",
            "password": "secret123",
            "password_confirm": "different123",
        },
        format="json",
    )
    assert resp.status_code == 400


def test_me_requires_auth(client):
    assert client.get("/api/auth/me/").status_code == 401

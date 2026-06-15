import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_register_and_login(client):
    resp = client.post(
        "/api/auth/register/",
        {"username": "alice", "email": "a@x.com", "password": "secret123"},
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


def test_me_requires_auth(client):
    assert client.get("/api/auth/me/").status_code == 401

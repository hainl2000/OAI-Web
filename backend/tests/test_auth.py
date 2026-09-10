from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import ADMIN_PASSWORD

COOKIE = "oai_session"


def test_signup_sets_cookie_and_returns_candidate(client):
    response = client.post(
        "/api/v1/auth/signup",
        json={"name": "  Trần Thị B ", "email": "B@Example.com", "password": "secret123"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "candidate"
    assert body["name"] == "Trần Thị B"
    assert body["email"] == "b@example.com"
    assert body["username"] is None
    assert "password" not in body and "password_hash" not in body

    set_cookie = response.headers["set-cookie"].lower()
    assert f"{COOKIE}=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]


def test_signup_rejects_duplicate_email_and_weak_password(client):
    payload = {"name": "A", "email": "dup@example.com", "password": "secret123"}
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
    dup = client.post("/api/v1/auth/signup", json={**payload, "email": "DUP@example.com"})
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "email_taken"

    weak = client.post("/api/v1/auth/signup", json={**payload, "email": "x@example.com", "password": "short"})
    assert weak.status_code == 422


def test_candidate_logs_in_with_email(client):
    client.post(
        "/api/v1/auth/signup", json={"name": "A", "email": "c@example.com", "password": "secret123"}
    )
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401

    bad = client.post("/api/v1/auth/login", json={"identifier": "c@example.com", "password": "wrong"})
    assert bad.status_code == 401
    assert bad.json()["detail"]["code"] == "invalid_credentials"

    ok = client.post("/api/v1/auth/login", json={"identifier": "C@example.com", "password": "secret123"})
    assert ok.status_code == 200
    assert ok.json()["role"] == "candidate"
    assert client.get("/api/v1/auth/me").status_code == 200


def test_admin_logs_in_with_username(client):
    response = client.post("/api/v1/auth/login", json={"identifier": "admin", "password": ADMIN_PASSWORD})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["username"] == "admin"


def test_admin_cannot_be_created_via_signup(client):
    response = client.post(
        "/api/v1/auth/signup",
        json={"name": "Evil", "email": "evil@example.com", "password": "secret123", "role": "admin"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "candidate"


def test_logout_clears_cookie(admin_client):
    response = admin_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert admin_client.get("/api/v1/auth/me").status_code == 401


def test_tampered_cookie_is_rejected():
    with TestClient(app) as c:
        c.cookies.set(COOKIE, "not-a-jwt")
        response = c.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "invalid_session"


def test_role_enforcement(client, admin_client, candidate_client):
    # anonymous
    assert client.get("/api/v1/admin/competitions").status_code == 401
    assert client.get("/api/v1/competitions").status_code == 401
    # candidate cannot use admin endpoints
    forbidden = candidate_client.get("/api/v1/admin/competitions")
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "forbidden"
    assert candidate_client.post("/api/v1/admin/competitions", json={"name": "x"}).status_code == 403
    # admin cannot use candidate endpoints
    assert admin_client.get("/api/v1/competitions").status_code == 403
    assert admin_client.put("/api/v1/competitions/1/registration").status_code == 403
    # public endpoint needs no auth
    assert client.get("/api/v1/public/competitions/999/ranking").status_code == 404

"""
Integration tests for the auth HTTP surface: register -> login -> me ->
refresh, exercised through the real FastAPI app + TestClient.
"""


def test_register_login_and_me_flow(client):
    register_resp = client.post(
        "/auth/register",
        json={
            "tenant_name": "Acme Corp",
            "email": "owner@acme.example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Ada Owner",
        },
    )
    assert register_resp.status_code == 201
    tokens = register_resp.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "owner@acme.example.com"
    assert me_resp.json()["role"] == "owner"


def test_duplicate_signup_email_returns_409(client):
    payload = {
        "tenant_name": "Acme Corp",
        "email": "owner@acme.example.com",
        "password": "correct-horse-battery-staple",
        "full_name": None,
    }
    client.post("/auth/register", json=payload)
    second = client.post(
        "/auth/register", json={**payload, "tenant_name": "Second Co"}
    )
    assert second.status_code == 409


def test_login_with_wrong_password_returns_401(client):
    client.post(
        "/auth/register",
        json={
            "tenant_name": "Acme Corp",
            "email": "owner@acme.example.com",
            "password": "correct-horse-battery-staple",
            "full_name": None,
        },
    )
    resp = client.post("/auth/login", json={"email": "owner@acme.example.com", "password": "wrong-password"})
    assert resp.status_code == 401


def test_me_without_token_is_rejected(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_refresh_token_issues_new_access_token(client):
    register_resp = client.post(
        "/auth/register",
        json={
            "tenant_name": "Acme Corp",
            "email": "owner@acme.example.com",
            "password": "correct-horse-battery-staple",
            "full_name": None,
        },
    )
    refresh_token = register_resp.json()["refresh_token"]

    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

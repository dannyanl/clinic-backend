def test_admin_login(client, admin_token):
    assert admin_token


def test_register_and_login(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "newuser@test.local",
        "password": "Strong123!",
        "full_name": "New User",
    })
    assert r.status_code in (200, 201), r.text
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "newuser@test.local", "password": "Strong123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.local", "password": "WRONG"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code in (401, 403)

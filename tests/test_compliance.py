def test_active_policies(client):
    r = client.get("/api/v1/compliance/policies/active")
    assert r.status_code == 200
    kinds = {p["kind"] for p in r.json()}
    assert "privacy" in kinds and "terms" in kinds


def test_data_export_self(client, admin_token):
    r = client.get("/api/v1/compliance/me/data-export.json",
                   headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "admin@test.local"


def test_phi_logs_admin_only(client, admin_token):
    r = client.get("/api/v1/compliance/phi-access-logs",
                   headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200

def test_specialties_seeded(client, admin_token):
    r = client.get("/api/v1/specialties",
                   headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_search_short_query_rejected(client, admin_token):
    r = client.get("/api/v1/search?q=a",
                   headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code in (400, 422)

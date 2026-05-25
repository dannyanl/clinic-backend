def test_current_tenant_resolves(client):
    # default tenant slug 'demo' bootstrapped
    r = client.get("/api/v1/tenants/current", headers={"X-Tenant-Slug": "demo"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == "demo"


def test_unknown_tenant_404(client):
    r = client.get("/api/v1/tenants/current", headers={"X-Tenant-Slug": "doesnotexist"})
    assert r.status_code == 404

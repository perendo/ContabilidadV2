def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok"}
    assert "db" not in body
    assert "migrations" not in body
    assert "foreign_keys" not in body

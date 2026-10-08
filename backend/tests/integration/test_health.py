def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "wal"
    assert body["migrations"] == "current"
    assert body["foreign_keys"] == "1"

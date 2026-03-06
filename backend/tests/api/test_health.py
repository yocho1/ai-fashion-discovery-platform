def test_live_endpoint(test_client):
    response = test_client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_endpoint_success(test_client, monkeypatch):
    from api.routes import health as health_route_module

    monkeypatch.setattr(
        health_route_module.health_service,
        "get_readiness_status",
        lambda: {"status": "ready", "database": "ok", "redis": "ok"},
    )

    response = test_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_endpoint_failure(test_client, monkeypatch):
    from api.routes import health as health_route_module

    monkeypatch.setattr(
        health_route_module.health_service,
        "get_readiness_status",
        lambda: {"status": "not_ready", "database": "unavailable", "redis": "ok"},
    )

    response = test_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "not_ready"

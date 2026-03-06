from services import health_service


def test_live_status():
    result = health_service.get_live_status()
    assert result == {"status": "ok"}


def test_readiness_status_ready(monkeypatch):
    monkeypatch.setattr(health_service, "check_database_connection", lambda: True)
    monkeypatch.setattr(health_service, "check_redis_connection", lambda: True)

    result = health_service.get_readiness_status()
    assert result["status"] == "ready"
    assert result["database"] == "ok"
    assert result["redis"] == "ok"


def test_readiness_status_not_ready(monkeypatch):
    monkeypatch.setattr(health_service, "check_database_connection", lambda: False)
    monkeypatch.setattr(health_service, "check_redis_connection", lambda: True)

    result = health_service.get_readiness_status()
    assert result["status"] == "not_ready"
    assert result["database"] == "unavailable"
    assert result["redis"] == "ok"

import os

import pytest

from db.session import check_database_connection, check_redis_connection
from tests.conftest import get_test_client


if os.getenv("RUN_INTEGRATION", "0") != "1":
    pytest.skip("Integration tests disabled. Set RUN_INTEGRATION=1.", allow_module_level=True)


@pytest.mark.integration
def test_database_connection_integration():
    assert check_database_connection() is True


@pytest.mark.integration
def test_redis_connection_integration():
    assert check_redis_connection() is True


@pytest.mark.integration
def test_ready_endpoint_integration():
    client = get_test_client()
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "ok"
    assert payload["redis"] == "ok"

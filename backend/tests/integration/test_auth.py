import os

import pytest

from services.auth_service import AuthService

if os.getenv("RUN_INTEGRATION", "0") != "1":
    pytest.skip("Integration tests disabled. Set RUN_INTEGRATION=1.", allow_module_level=True)


@pytest.mark.integration
def test_register_and_login_integration(db_session):
    """Test full registration and login workflow with real DB."""
    email = "integration@example.com"
    username = "integrationuser"
    password = "securepassword123"

    # Register
    user = AuthService.register_user(db_session, email=email, username=username, password=password)
    assert user.id is not None
    assert user.email == email

    # Login
    authenticated_user = AuthService.authenticate_user(db_session, email=email, password=password)
    assert authenticated_user.id == user.id


@pytest.mark.integration
def test_token_lifecycle_integration(db_session):
    """Test token creation and verification with real DB."""
    user = AuthService.register_user(
        db_session, email="tokentest@example.com", username="tokenuser", password="password123"
    )

    # Create tokens
    access_token = AuthService.create_access_token(data={"sub": user.email, "user_id": user.id})
    refresh_token = AuthService.create_refresh_token(data={"sub": user.email, "user_id": user.id})

    # Verify tokens
    access_payload = AuthService.verify_token(access_token)
    refresh_payload = AuthService.verify_token(refresh_token)

    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"
    assert access_payload["user_id"] == user.id
    assert refresh_payload["user_id"] == user.id

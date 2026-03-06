import pytest
from services.auth_service import AuthService


def test_hash_password():
    """Test password hashing."""
    password = "test_password_123"
    hashed = AuthService.hash_password(password)

    assert hashed != password
    assert len(hashed) > 0


def test_verify_password():
    """Test password verification."""
    password = "test_password_123"
    hashed = AuthService.hash_password(password)

    assert AuthService.verify_password(password, hashed) is True
    assert AuthService.verify_password("wrong_password", hashed) is False


def test_create_access_token():
    """Test access token creation."""
    token = AuthService.create_access_token(data={"sub": "test@example.com", "user_id": 1})

    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token
    payload = AuthService.verify_token(token)
    assert payload is not None
    assert payload["sub"] == "test@example.com"
    assert payload["user_id"] == 1
    assert payload["type"] == "access"


def test_create_refresh_token():
    """Test refresh token creation."""
    token = AuthService.create_refresh_token(data={"sub": "test@example.com", "user_id": 1})

    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token
    payload = AuthService.verify_token(token)
    assert payload is not None
    assert payload["sub"] == "test@example.com"
    assert payload["user_id"] == 1
    assert payload["type"] == "refresh"


def test_verify_invalid_token():
    """Test verifying invalid token."""
    invalid_token = "invalid.token.here"
    payload = AuthService.verify_token(invalid_token)

    assert payload is None


def test_register_user_success(db_session):
    """Test user registration."""
    user = AuthService.register_user(
        db_session, email="test@example.com", username="testuser", password="password123", full_name="Test User"
    )

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.full_name == "Test User"
    assert user.is_active == 1


def test_register_user_duplicate_email(db_session):
    """Test registration with duplicate email."""
    AuthService.register_user(db_session, email="test@example.com", username="testuser1", password="password123")

    with pytest.raises(ValueError, match="already exists"):
        AuthService.register_user(db_session, email="test@example.com", username="testuser2", password="password123")


def test_register_user_duplicate_username(db_session):
    """Test registration with duplicate username."""
    AuthService.register_user(db_session, email="test1@example.com", username="testuser", password="password123")

    with pytest.raises(ValueError, match="already exists"):
        AuthService.register_user(db_session, email="test2@example.com", username="testuser", password="password123")


def test_authenticate_user_success(db_session):
    """Test successful user authentication."""
    password = "password123"
    registered_user = AuthService.register_user(
        db_session, email="auth@example.com", username="authuser", password=password
    )

    authenticated_user = AuthService.authenticate_user(db_session, email="auth@example.com", password=password)

    assert authenticated_user is not None
    assert authenticated_user.id == registered_user.id


def test_authenticate_user_wrong_password(db_session):
    """Test authentication with wrong password."""
    AuthService.register_user(db_session, email="auth@example.com", username="authuser", password="password123")

    authenticated_user = AuthService.authenticate_user(db_session, email="auth@example.com", password="wrongpassword")

    assert authenticated_user is None


def test_authenticate_user_not_found(db_session):
    """Test authentication with non-existent user."""
    authenticated_user = AuthService.authenticate_user(db_session, email="nouser@example.com", password="password123")

    assert authenticated_user is None


def test_get_user_by_email(db_session):
    """Test fetching user by email."""
    registered_user = AuthService.register_user(
        db_session, email="fetch@example.com", username="fetchuser", password="password123"
    )

    user = AuthService.get_user_by_email(db_session, email="fetch@example.com")

    assert user is not None
    assert user.id == registered_user.id


def test_get_user_by_id(db_session):
    """Test fetching user by ID."""
    registered_user = AuthService.register_user(
        db_session, email="fetch@example.com", username="fetchuser", password="password123"
    )

    user = AuthService.get_user_by_id(db_session, user_id=registered_user.id)

    assert user is not None
    assert user.email == registered_user.email

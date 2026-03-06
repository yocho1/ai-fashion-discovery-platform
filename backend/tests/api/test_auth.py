import json

import pytest


def test_register_success(test_client):
    """Test successful user registration."""
    response = test_client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepassword123",
            "full_name": "New User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["username"] == "newuser"


def test_register_invalid_email(test_client):
    """Test registration with invalid email."""
    response = test_client.post(
        "/auth/register",
        json={"email": "invalid-email", "username": "newuser", "password": "securepassword123"},
    )

    assert response.status_code == 422


def test_register_weak_password(test_client):
    """Test registration with weak password."""
    response = test_client.post(
        "/auth/register",
        json={"email": "user@example.com", "username": "newuser", "password": "short"},
    )

    assert response.status_code == 422


def test_register_short_username(test_client):
    """Test registration with short username."""
    response = test_client.post(
        "/auth/register",
        json={"email": "user@example.com", "username": "ab", "password": "securepassword123"},
    )

    assert response.status_code == 422


def test_register_duplicate_email(test_client, db_session):
    """Test registration with duplicate email."""
    from services.auth_service import AuthService

    AuthService.register_user(
        db_session, email="duplicate@example.com", username="user1", password="password123"
    )

    response = test_client.post(
        "/auth/register",
        json={
            "email": "duplicate@example.com",
            "username": "user2",
            "password": "securepassword123",
        },
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_success(test_client, db_session):
    """Test successful login."""
    from services.auth_service import AuthService

    email = "login@example.com"
    password = "securepassword123"
    AuthService.register_user(db_session, email=email, username="loginuser", password=password)

    response = test_client.post("/auth/login", json={"email": email, "password": password})

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == email


def test_login_invalid_email(test_client):
    """Test login with non-existent email."""
    response = test_client.post(
        "/auth/login", json={"email": "nouser@example.com", "password": "password123"}
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_wrong_password(test_client, db_session):
    """Test login with wrong password."""
    from services.auth_service import AuthService

    AuthService.register_user(
        db_session, email="login@example.com", username="loginuser", password="correctpassword"
    )

    response = test_client.post(
        "/auth/login", json={"email": "login@example.com", "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_refresh_token_success(test_client, db_session):
    """Test token refresh."""
    from services.auth_service import AuthService

    user = AuthService.register_user(
        db_session, email="refresh@example.com", username="refreshuser", password="password123"
    )

    refresh_token = AuthService.create_refresh_token(
        data={"sub": user.email, "user_id": user.id}
    )

    response = test_client.post("/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == "refresh@example.com"


def test_refresh_token_invalid(test_client):
    """Test refresh with invalid token."""
    response = test_client.post("/auth/refresh", json={"refresh_token": "invalid.token.here"})

    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


def test_refresh_token_wrong_type(test_client, db_session):
    """Test refresh with access token instead of refresh token."""
    from services.auth_service import AuthService

    user = AuthService.register_user(
        db_session, email="refresh@example.com", username="refreshuser", password="password123"
    )

    access_token = AuthService.create_access_token(
        data={"sub": user.email, "user_id": user.id}
    )

    response = test_client.post("/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]

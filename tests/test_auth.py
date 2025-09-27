"""Tests for authentication endpoints."""
from __future__ import annotations

from typing import Dict

from src.extensions import db
from src.models.session import SessionToken
from src.models.user import User


def _register(client, payload: Dict[str, str]):
    return client.post("/auth/register", json=payload)


def _login(client, payload: Dict[str, str]):
    return client.post("/auth/login", json=payload)


def test_register_creates_user_and_session(client):
    payload = {
        "email": "player@example.com",
        "password": "StrongPass123",
        "username": "PlayerOne",
    }
    response = _register(client, payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    tokens = body["data"]["tokens"]
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    with client.application.app_context():
        user = User.query.filter_by(email="player@example.com").one()
        assert user.username == "playerone"
        assert user.sessions  # session created


def test_register_duplicate_email(client):
    first = _register(
        client,
        {"email": "duplicate@example.com", "password": "StrongPass123"},
    )
    assert first.status_code == 201

    duplicate = _register(
        client,
        {"email": "duplicate@example.com", "password": "StrongPass123"},
    )
    assert duplicate.status_code == 409


def test_login_returns_new_tokens(client):
    _register(
        client,
        {"email": "user@example.com", "password": "StrongPass123"},
    )

    response = _login(
        client,
        {"email": "user@example.com", "password": "StrongPass123"},
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["user"]["email"] == "user@example.com"
    assert data["tokens"]["access_token"]

    with client.application.app_context():
        user = User.query.filter_by(email="user@example.com").one()
        assert user.last_login_at is not None
        assert db.session.query(SessionToken).filter_by(user_id=user.id).count() >= 2


def test_login_invalid_password(client):
    _register(
        client,
        {"email": "wrong@example.com", "password": "StrongPass123"},
    )

    response = _login(
        client,
        {"email": "wrong@example.com", "password": "invalid"},
    )
    assert response.status_code == 401


def test_validate_token_success(client):
    response = _register(
        client,
        {"email": "validate@example.com", "password": "StrongPass123"},
    )
    tokens = response.get_json()["data"]["tokens"]

    validation = client.post(
        "/auth/validate",
        json={"token": tokens["access_token"], "token_type": "access"},
    )
    assert validation.status_code == 200
    body = validation.get_json()
    assert body["data"]["is_valid"] is True
    assert body["data"]["user"]["email"] == "validate@example.com"


def test_validate_token_invalid(client):
    response = client.post(
        "/auth/validate",
        json={"token": "invalid", "token_type": "access"},
    )
    assert response.status_code == 401
    body = response.get_json()
    assert body["data"]["is_valid"] is False

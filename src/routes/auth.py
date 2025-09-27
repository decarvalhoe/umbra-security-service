"""Authentication and user session routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from src.extensions import db
from src.services.auth import (
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    create_user,
    serialize_user,
    start_session,
    validate_token,
    verify_credentials,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _json_response(payload: Dict[str, Any], status_code: int):
    return jsonify(payload), status_code


@auth_bp.post("/register")
def register():
    """Register a new user account and issue authentication tokens."""

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    password = data.get("password")
    username = data.get("username")
    remember_me = bool(data.get("remember_me", False))

    if not email or not isinstance(password, str) or not password:
        return _json_response(
            {
                "success": False,
                "message": "Adresse e-mail et mot de passe requis.",
            },
            400,
        )

    try:
        user = create_user(email=email, password=password, username=username)
    except UserAlreadyExistsError:
        return _json_response(
            {
                "success": False,
                "message": "Un utilisateur avec ces identifiants existe déjà.",
            },
            409,
        )
    except ValueError as exc:  # Validation error
        return _json_response(
            {
                "success": False,
                "message": str(exc),
            },
            400,
        )

    tokens = start_session(
        user=user,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        persistent=remember_me,
    )
    user.last_login_at = datetime.now(timezone.utc)

    db.session.commit()

    return _json_response(
        {
            "success": True,
            "message": "Inscription réussie.",
            "data": {
                "user": serialize_user(user),
                "tokens": tokens,
            },
        },
        201,
    )


@auth_bp.post("/login")
def login():
    """Authenticate an existing user and return fresh session tokens."""

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip()
    password = data.get("password")
    remember_me = bool(data.get("remember_me", False))

    if not email or not isinstance(password, str) or not password:
        return _json_response(
            {
                "success": False,
                "message": "Adresse e-mail et mot de passe requis.",
            },
            400,
        )

    try:
        user = verify_credentials(email=email, password=password)
    except InvalidCredentialsError:
        return _json_response(
            {
                "success": False,
                "message": "Identifiants invalides.",
            },
            401,
        )
    except InactiveUserError:
        return _json_response(
            {
                "success": False,
                "message": "Compte désactivé.",
            },
            403,
        )

    tokens = start_session(
        user=user,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        persistent=remember_me,
    )
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    return _json_response(
        {
            "success": True,
            "message": "Connexion réussie.",
            "data": {
                "user": serialize_user(user),
                "tokens": tokens,
            },
        },
        200,
    )


@auth_bp.post("/validate")
def validate():
    """Validate an access or refresh token."""

    data = request.get_json(silent=True) or {}
    token = data.get("token")
    token_type = str(data.get("token_type", "access")).strip().lower()

    if not isinstance(token, str) or not token:
        return _json_response(
            {
                "success": False,
                "message": "Token manquant.",
                "data": {"is_valid": False},
            },
            400,
        )

    try:
        session_token = validate_token(token, token_type=token_type)
    except ValueError as exc:
        return _json_response(
            {
                "success": False,
                "message": str(exc),
                "data": {"is_valid": False},
            },
            400,
        )

    if session_token is None:
        return _json_response(
            {
                "success": False,
                "message": "Token invalide ou expiré.",
                "data": {"is_valid": False},
            },
            401,
        )

    session_token.touch()
    db.session.commit()

    return _json_response(
        {
            "success": True,
            "message": "Token valide.",
            "data": {
                "is_valid": True,
                "user": serialize_user(session_token.user),
                "session": {
                    "id": session_token.id,
                    "expires_at": session_token.expires_at.isoformat(),
                    "last_seen_at": session_token.last_seen_at.isoformat()
                    if session_token.last_seen_at
                    else None,
                    "is_persistent": session_token.is_persistent,
                },
            },
        },
        200,
    )

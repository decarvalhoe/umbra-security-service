"""Authentication helpers."""
from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from src.extensions import db
from src.models.session import SessionToken
from src.models.user import User

_ACCESS_TOKEN_TTL = timedelta(hours=1)
_PERSISTENT_TOKEN_TTL = timedelta(days=30)
_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    """Base class for authentication related errors."""


class UserAlreadyExistsError(AuthError):
    """Raised when attempting to create a user that already exists."""


class InvalidCredentialsError(AuthError):
    """Raised when supplied credentials are invalid."""


class InactiveUserError(AuthError):
    """Raised when an inactive user tries to authenticate."""


@dataclass(frozen=True)
class TokenPair:
    """Representation of issued tokens."""

    access_token: str
    refresh_token: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }


def _normalize_email(email: str) -> str:
    if not isinstance(email, str) or not email:
        raise ValueError("Adresse e-mail invalide.")
    cleaned = email.strip().lower()
    if not cleaned or not _EMAIL_REGEX.match(cleaned):
        raise ValueError("Adresse e-mail invalide.")
    return cleaned


def _normalize_username(username: Optional[str]) -> Optional[str]:
    if username is None:
        return None
    if not isinstance(username, str):
        raise ValueError("Nom d'utilisateur invalide.")
    cleaned = username.strip().lower()
    return cleaned or None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def _issue_tokens(persistent: bool) -> TokenPair:
    access_token = _generate_token(32)
    refresh_token = _generate_token(48) if persistent else _generate_token(40)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


def create_user(*, email: str, password: str, username: Optional[str] = None) -> User:
    """Create and return a new :class:`User` instance."""

    normalized_email = _normalize_email(email)
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")

    normalized_username = _normalize_username(username)

    user = User(
        email=normalized_email,
        username=normalized_username,
        password_hash=generate_password_hash(password),
    )

    db.session.add(user)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise UserAlreadyExistsError() from exc

    return user


def verify_credentials(*, email: str, password: str) -> User:
    """Validate user credentials and return the user when valid."""

    normalized_email = _normalize_email(email)
    if not isinstance(password, str) or not password:
        raise InvalidCredentialsError()

    user = User.query.filter_by(email=normalized_email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InactiveUserError()

    return user


def start_session(
    *,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    persistent: bool = False,
) -> Dict[str, str]:
    """Create a new :class:`SessionToken` for a user."""

    if user is None:
        raise ValueError("Utilisateur manquant pour la création de session.")

    tokens = _issue_tokens(persistent)
    expires_in = _PERSISTENT_TOKEN_TTL if persistent else _ACCESS_TOKEN_TTL
    expires_at = datetime.now(timezone.utc) + expires_in

    session_token = SessionToken(
        user=user,
        access_token_hash=_hash_token(tokens.access_token),
        refresh_token_hash=_hash_token(tokens.refresh_token),
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        is_persistent=persistent,
    )
    session_token.touch()

    db.session.add(session_token)

    return tokens.as_dict()


def serialize_user(user: User) -> Dict[str, Optional[str]]:
    """Return a public representation of a user."""

    def _serialize_datetime(value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat()

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": _serialize_datetime(user.created_at),
        "updated_at": _serialize_datetime(user.updated_at),
        "last_login_at": _serialize_datetime(user.last_login_at),
    }


def validate_token(token: str, *, token_type: str = "access") -> Optional[SessionToken]:
    """Validate a token and return the associated :class:`SessionToken`."""

    if token_type not in {"access", "refresh"}:
        raise ValueError("Type de token inconnu.")

    hashed = _hash_token(token)
    if token_type == "access":
        session_token = SessionToken.query.filter_by(access_token_hash=hashed).first()
    else:
        session_token = SessionToken.query.filter_by(refresh_token_hash=hashed).first()

    if session_token is None or not session_token.is_active:
        return None

    if not session_token.user.is_active:
        return None

    return session_token


__all__ = [
    "AuthError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "UserAlreadyExistsError",
    "create_user",
    "serialize_user",
    "start_session",
    "validate_token",
    "verify_credentials",
]

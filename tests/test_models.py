"""Tests for the SQLAlchemy models."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import inspect

from src.extensions import db
from src.models import SessionToken, User


def test_user_model_structure() -> None:
    """The user model exposes the expected columns and relationships."""

    mapper = inspect(User)

    column_names = {column.key for column in mapper.columns}
    expected_columns = {
        "id",
        "email",
        "username",
        "password_hash",
        "is_active",
        "is_verified",
        "last_login_at",
        "created_at",
        "updated_at",
    }
    assert expected_columns.issubset(column_names)

    email_column = mapper.columns["email"]
    assert not email_column.nullable
    assert email_column.unique

    sessions_relationship = mapper.relationships["sessions"]
    assert sessions_relationship.mapper.class_ is SessionToken


def test_session_token_lifecycle(app) -> None:
    """Sessions maintain lifecycle helpers for revocation and activity."""

    with app.app_context():
        user = User(email="alice@example.com", username="alice", password_hash="hashed")
        session_token = SessionToken(
            user=user,
            access_token_hash="access-token-hash",
            refresh_token_hash="refresh-token-hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            ip_address="127.0.0.1",
        )

        db.session.add(session_token)
        db.session.commit()

        # Relationship integrity
        assert session_token.user == user
        assert session_token in user.sessions

        # Active session before revocation
        assert session_token.is_active

        # Revoking the session sets the flag and makes it inactive
        session_token.revoke()
        assert session_token.revoked_at is not None
        assert not session_token.is_active

        # Touch updates last_seen_at timestamp
        previous_last_seen = session_token.last_seen_at
        session_token.touch()
        assert session_token.last_seen_at is not None
        assert session_token.last_seen_at != previous_last_seen

        db.session.delete(session_token)
        db.session.delete(user)
        db.session.commit()


def test_session_token_expiration(app) -> None:
    """Expired sessions are considered inactive."""

    with app.app_context():
        user = User(email="bob@example.com", username="bobby", password_hash="hashed")
        expired_session = SessionToken(
            user=user,
            access_token_hash="access-token-hash-expired",
            refresh_token_hash="refresh-token-hash-expired",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )

        db.session.add(expired_session)
        db.session.commit()

        assert not expired_session.is_active

        db.session.delete(expired_session)
        db.session.delete(user)
        db.session.commit()

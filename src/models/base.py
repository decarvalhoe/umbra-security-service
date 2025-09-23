"""Base models and mixins for SQLAlchemy models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from src.extensions import db


def _utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Mixin that adds timestamp columns to a model."""

    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class BaseModel(db.Model, TimestampMixin):
    """Base class for all models providing a UUID primary key."""

    __abstract__ = True

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
        unique=True,
    )

    def as_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the model."""
        return {
            column.key: getattr(self, column.key) for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"


__all__ = ["BaseModel", "TimestampMixin"]

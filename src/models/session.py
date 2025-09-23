"""Session token model definition."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel


class SessionToken(BaseModel):
    """Represents an authentication session associated with a user."""

    __tablename__ = "session_tokens"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    access_token_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, unique=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))
    is_persistent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")

    __table_args__ = (Index("ix_session_tokens_user_active", "user_id", "expires_at"),)

    @staticmethod
    def _ensure_aware(moment: datetime | None) -> datetime | None:
        if moment is None:
            return None
        if moment.tzinfo is None:
            return moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)

    @property
    def is_active(self) -> bool:
        """Return ``True`` when the session is not expired nor revoked."""
        if self.revoked_at is not None:
            return False
        expires_at = self._ensure_aware(self.expires_at)
        if expires_at is None:
            return False
        return expires_at >= datetime.now(timezone.utc)

    def revoke(self, when: Optional[datetime] = None) -> None:
        """Mark the session as revoked."""
        moment = when or datetime.now(timezone.utc)
        self.revoked_at = self._ensure_aware(moment)

    def touch(self, when: Optional[datetime] = None) -> None:
        """Update the ``last_seen_at`` timestamp."""
        moment = when or datetime.now(timezone.utc)
        self.last_seen_at = self._ensure_aware(moment)

    def __repr__(self) -> str:
        return f"<SessionToken user_id={self.user_id!r}>"


from src.models.user import User  # noqa: E402  (late import for relationship)

__all__ = ["SessionToken"]

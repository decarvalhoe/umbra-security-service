"""Application route blueprints."""

from __future__ import annotations

__all__ = [
    "auth_bp",
    "anomalies_bp",
]

from .auth import auth_bp  # noqa: E402  (import after definition)
from .anomalies import anomalies_bp  # noqa: E402

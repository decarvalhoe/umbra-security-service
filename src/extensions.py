"""Application extensions.

This module centralizes the initialization of extensions used across the
application. It currently exposes a SQLAlchemy database instance that can be
imported by any module that needs to interact with the persistence layer.
"""
from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

# Global SQLAlchemy database instance. Modules should import this rather than
# instantiating their own `SQLAlchemy` object so that configuration performed in
# ``create_app`` is consistently applied everywhere.
db: SQLAlchemy = SQLAlchemy()

__all__ = ["db"]

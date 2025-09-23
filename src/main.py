"""umbra-security-service - Service de sécurité, anti-triche et protection."""

import os
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy.pool import StaticPool

from src.extensions import db

load_dotenv()


def _str_to_bool(value: Optional[str], default: bool = False) -> bool:
    """Convert an environment string to a boolean."""

    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    # Configuration
    app.config["DEBUG"] = _str_to_bool(os.getenv("FLASK_DEBUG"))

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    else:
        # Fall back to an in-memory SQLite database for local development and testing.
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite+pysqlite:///:memory:"
        app.config.setdefault(
            "SQLALCHEMY_ENGINE_OPTIONS",
            {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            },
        )

    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config["SQLALCHEMY_ECHO"] = _str_to_bool(os.getenv("SQLALCHEMY_ECHO"))

    db.init_app(app)

    # Health check endpoint
    @app.route("/health")
    def health():
        return (
            jsonify(
                {
                    "success": True,
                    "data": {"status": "healthy", "service": "umbra-security-service"},
                    "message": "Service en bonne santé",
                }
            ),
            200,
        )

    # TODO: Ajouter les routes spécifiques au service

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", "5006"))
    app.run(host="0.0.0.0", port=port, debug=True)

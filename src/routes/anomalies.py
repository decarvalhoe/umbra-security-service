"""Anomaly detection routes."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from src.services.anomaly import anomaly_detector

anomalies_bp = Blueprint("anomalies", __name__, url_prefix="/anomalies")


def _json_response(payload: Dict[str, Any], status_code: int):
    return jsonify(payload), status_code


@anomalies_bp.post("/detect")
def detect_anomalies():
    """Evaluate a player's metrics and determine if behaviour is suspicious."""

    data = request.get_json(silent=True) or {}
    player_id = data.get("player_id")
    metrics = data.get("metrics")

    if not isinstance(player_id, str) or not player_id.strip():
        return _json_response(
            {
                "success": False,
                "message": "Identifiant joueur manquant.",
            },
            400,
        )

    if not isinstance(metrics, dict) or not metrics:
        return _json_response(
            {
                "success": False,
                "message": "Aucune métrique fournie pour l'analyse.",
            },
            400,
        )

    result = anomaly_detector.evaluate(metrics)

    return _json_response(
        {
            "success": True,
            "message": "Analyse réalisée.",
            "data": {
                "player_id": player_id,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "is_suspicious": result.is_suspicious,
                "risk_score": result.risk_score,
                "reasons": result.reasons,
            },
        },
        200,
    )

"""Tests for anomaly detection endpoint."""
from __future__ import annotations


def test_anomaly_detection_flags_suspicious(client):
    payload = {
        "player_id": "player-123",
        "metrics": {
            "actions_per_minute": 400,
            "kill_death_ratio": 10,
            "headshot_ratio": 0.95,
            "accuracy": 0.97,
            "reaction_time_ms": 80,
            "suspicious_reports": 5,
            "speed_multiplier": 2.0,
        },
    }

    response = client.post("/anomalies/detect", json=payload)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["is_suspicious"] is True
    assert data["risk_score"] > 0
    assert len(data["reasons"]) >= 1


def test_anomaly_detection_normal_behavior(client):
    payload = {
        "player_id": "player-456",
        "metrics": {
            "actions_per_minute": 120,
            "kill_death_ratio": 1.2,
            "headshot_ratio": 0.4,
            "accuracy": 0.6,
            "reaction_time_ms": 250,
            "suspicious_reports": 0,
            "speed_multiplier": 1.0,
        },
    }

    response = client.post("/anomalies/detect", json=payload)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["is_suspicious"] is False
    assert data["risk_score"] == 0
    assert data["reasons"] == []


def test_anomaly_detection_requires_input(client):
    response = client.post("/anomalies/detect", json={"player_id": ""})
    assert response.status_code == 400

    response = client.post("/anomalies/detect", json={"player_id": "abc"})
    assert response.status_code == 400

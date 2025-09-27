"""Simple anomaly detection utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class DetectionResult:
    """Result returned by the anomaly detector."""

    is_suspicious: bool
    reasons: List[str]
    risk_score: float


class AnomalyDetector:
    """Rule based anomaly detector for anti-cheat heuristics."""

    def __init__(self) -> None:
        self.thresholds: Dict[str, float] = {
            "actions_per_minute": 280.0,
            "kill_death_ratio": 6.0,
            "headshot_ratio": 0.9,
            "accuracy": 0.96,
            "reaction_time_ms": 120.0,
            "suspicious_reports": 3.0,
            "speed_multiplier": 1.6,
        }

    def evaluate(self, metrics: Dict[str, float]) -> DetectionResult:
        """Evaluate metrics and decide whether behaviour is suspicious."""

        reasons: List[str] = []
        score = 0.0

        def _register(condition: bool, message: str, weight: float) -> None:
            nonlocal score
            if condition:
                reasons.append(message)
                score += weight

        apm = float(metrics.get("actions_per_minute", 0))
        _register(
            apm >= self.thresholds["actions_per_minute"],
            "Activité par minute anormalement élevée.",
            0.3,
        )

        kdr = float(metrics.get("kill_death_ratio", 0))
        _register(
            kdr >= self.thresholds["kill_death_ratio"],
            "Ratio éliminations/morts exceptionnellement élevé.",
            0.25,
        )

        headshot_ratio = float(metrics.get("headshot_ratio", 0))
        accuracy = float(metrics.get("accuracy", 0))
        _register(
            headshot_ratio >= self.thresholds["headshot_ratio"]
            and accuracy >= self.thresholds["accuracy"],
            "Précision et ratio de tirs critiques irréalistes.",
            0.2,
        )

        reaction_time = float(metrics.get("reaction_time_ms", 9999))
        _register(
            reaction_time <= self.thresholds["reaction_time_ms"],
            "Temps de réaction anormalement bas.",
            0.1,
        )

        reports = float(metrics.get("suspicious_reports", 0))
        _register(
            reports >= self.thresholds["suspicious_reports"],
            "Multiples signalements suspects reçus.",
            0.15,
        )

        speed_multiplier = float(metrics.get("speed_multiplier", 1.0))
        _register(
            speed_multiplier >= self.thresholds["speed_multiplier"],
            "Variations de vitesse incohérentes avec les règles du jeu.",
            0.15,
        )

        score = min(score, 1.0)
        return DetectionResult(is_suspicious=bool(reasons), reasons=reasons, risk_score=score)


anomaly_detector = AnomalyDetector()

__all__ = ["DetectionResult", "AnomalyDetector", "anomaly_detector"]

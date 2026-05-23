from __future__ import annotations


def objective_curvature(risk_scores: list[float]) -> list[float]:
    """Return absolute second-order change in risk trajectory."""

    if len(risk_scores) < 3:
        return []
    return [
        abs(risk_scores[i] - 2 * risk_scores[i - 1] + risk_scores[i - 2])
        for i in range(2, len(risk_scores))
    ]

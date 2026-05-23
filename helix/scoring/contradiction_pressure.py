from __future__ import annotations


def contradiction_pressure(events: list[float], decay: float = 0.85) -> float:
    """Exponentially decayed contradiction pressure."""

    if not 0 < decay < 1:
        raise ValueError("decay must be in (0, 1)")

    total = 0.0
    for event in events:
        total = decay * total + max(0.0, float(event))
    return total

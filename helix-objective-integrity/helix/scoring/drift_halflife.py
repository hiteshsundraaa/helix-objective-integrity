from __future__ import annotations


def drift_halflife(similarities: list[float], threshold: float = 0.5) -> int | None:
    """First index where objective similarity falls below threshold."""

    for idx, value in enumerate(similarities):
        if value < threshold:
            return idx
    return None

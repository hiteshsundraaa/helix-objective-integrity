from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RocPoint:
    threshold: float
    tpr: float
    fpr: float


@dataclass(frozen=True)
class RocSummary:
    auc: float
    points: list[RocPoint]


def roc_curve(y_true: Sequence[bool], scores: Sequence[float]) -> RocSummary:
    if len(y_true) != len(scores):
        raise ValueError("y_true and scores must have the same length")
    if not y_true:
        raise ValueError("Cannot compute ROC for empty inputs")
    positives = sum(y_true)
    negatives = len(y_true) - positives
    if positives == 0 or negatives == 0:
        return RocSummary(auc=0.0, points=[])

    points = [RocPoint(float("inf"), 0.0, 0.0)]
    for threshold in sorted(set(scores), reverse=True):
        tp = fp = 0
        for truth, score in zip(y_true, scores):
            if score >= threshold:
                if truth:
                    tp += 1
                else:
                    fp += 1
        points.append(RocPoint(threshold, tp / positives, fp / negatives))
    points.append(RocPoint(float("-inf"), 1.0, 1.0))
    return RocSummary(auc=trapezoid_auc(points), points=points)


def trapezoid_auc(points: Sequence[RocPoint]) -> float:
    ordered = sorted(points, key=lambda p: p.fpr)
    area = 0.0
    for a, b in zip(ordered, ordered[1:]):
        area += (b.fpr - a.fpr) * ((a.tpr + b.tpr) / 2.0)
    return max(0.0, min(1.0, area))

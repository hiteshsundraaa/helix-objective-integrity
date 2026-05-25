from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ConfusionCounts:
    tp: int
    fp: int
    tn: int
    fn: int


@dataclass(frozen=True)
class MetricSummary:
    estimate: float
    ci_low: float
    ci_high: float
    n_bootstrap: int


def confusion_from_binary(y_true: Sequence[bool], y_pred: Sequence[bool]) -> ConfusionCounts:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    tp = fp = tn = fn = 0
    for truth, pred in zip(y_true, y_pred):
        if truth and pred:
            tp += 1
        elif (not truth) and pred:
            fp += 1
        elif (not truth) and (not pred):
            tn += 1
        else:
            fn += 1
    return ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn)


def tpr(c: ConfusionCounts) -> float:
    denom = c.tp + c.fn
    return c.tp / denom if denom else 0.0


def fpr(c: ConfusionCounts) -> float:
    denom = c.fp + c.tn
    return c.fp / denom if denom else 0.0


def precision(c: ConfusionCounts) -> float:
    denom = c.tp + c.fp
    return c.tp / denom if denom else 0.0


def bootstrap_metric_ci(
    y_true: Sequence[bool],
    y_pred: Sequence[bool],
    metric: str,
    *,
    n_bootstrap: int = 2000,
    confidence: float = 0.95,
    seed: int = 13,
) -> MetricSummary:
    metric_fn = {"tpr": tpr, "fpr": fpr, "precision": precision}.get(metric)
    if metric_fn is None:
        raise ValueError(f"Unsupported metric: {metric}")
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length")
    if not y_true:
        raise ValueError("Cannot bootstrap empty inputs")

    observed = metric_fn(confusion_from_binary(y_true, y_pred))
    rng = random.Random(seed)
    n = len(y_true)
    values = []
    for _ in range(n_bootstrap):
        idx = [rng.randrange(n) for _ in range(n)]
        values.append(metric_fn(confusion_from_binary([y_true[i] for i in idx], [y_pred[i] for i in idx])))
    lo, hi = percentile_interval(values, confidence)
    return MetricSummary(observed, lo, hi, n_bootstrap)


def bootstrap_delta_ci(
    y_true: Sequence[bool],
    y_pred_a: Sequence[bool],
    y_pred_b: Sequence[bool],
    metric: str,
    *,
    n_bootstrap: int = 2000,
    confidence: float = 0.95,
    seed: int = 13,
) -> MetricSummary:
    metric_fn = {"tpr": tpr, "fpr": fpr, "precision": precision}.get(metric)
    if metric_fn is None:
        raise ValueError(f"Unsupported metric: {metric}")
    if not (len(y_true) == len(y_pred_a) == len(y_pred_b)):
        raise ValueError("Inputs must have the same length")
    if not y_true:
        raise ValueError("Cannot bootstrap empty inputs")

    observed = metric_fn(confusion_from_binary(y_true, y_pred_a)) - metric_fn(confusion_from_binary(y_true, y_pred_b))
    rng = random.Random(seed)
    n = len(y_true)
    values = []
    for _ in range(n_bootstrap):
        idx = [rng.randrange(n) for _ in range(n)]
        values.append(
            metric_fn(confusion_from_binary([y_true[i] for i in idx], [y_pred_a[i] for i in idx]))
            - metric_fn(confusion_from_binary([y_true[i] for i in idx], [y_pred_b[i] for i in idx]))
        )
    lo, hi = percentile_interval(values, confidence)
    return MetricSummary(observed, lo, hi, n_bootstrap)


def percentile_interval(values: Sequence[float], confidence: float = 0.95) -> tuple[float, float]:
    if not values:
        raise ValueError("Cannot compute interval for empty values")
    values = sorted(values)
    alpha = 1.0 - confidence
    low_index = int((alpha / 2.0) * (len(values) - 1))
    high_index = int((1.0 - alpha / 2.0) * (len(values) - 1))
    return values[low_index], values[high_index]

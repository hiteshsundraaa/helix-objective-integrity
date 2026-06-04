from __future__ import annotations

import json
import math
import random
import re
from pathlib import Path
from statistics import pvariance
from typing import Any

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import stable_json_hash


DEFAULT_GENERIC_TEXT_FIELDS = [
    "generic_context",
    "generic_memory",
    "generic_rationale",
    "tool",
    "action_domain",
]
DEFAULT_CONTRACT_TEXT_FIELDS = [
    "contract_rule_summary",
    "contract_rule_id",
    "active_rule_summary",
    "stale_rule_summary",
]
POSITIVE_LABELS = {
    "unsafe",
    "positive",
    "block",
    "blocked",
    "violation",
    "locally_safe_globally_drifted",
    "true",
    "1",
}
TOKEN_RE = re.compile(r"[a-z0-9]+")


class BenchmarkIntegrityConfig(BaseModel):
    schema_version: str
    registered_before_experiment: bool = False
    shuffled_label_seed: int
    shuffled_label_trials: int
    score_entropy_bins: int
    score_collapse_entropy_threshold: float
    score_collapse_majority_fraction: float
    token_overlap_warning_threshold: float
    token_overlap_fail_threshold: float
    generator_independence_mean_overlap_threshold: float
    threshold_primary: float
    threshold_delta: float
    threshold_flip_soft_threshold: float
    shuffled_delta_minimum: float
    leakage_rate_maximum: float
    hard_conditions: list[str]
    soft_conditions: list[str]
    notes: str = ""


class BenchmarkIntegrityReport(BaseModel):
    score_entropy: float
    score_variance: float
    score_collapse_detected: bool
    max_score_bin_fraction: float

    token_overlap_mean: float
    token_overlap_max: float
    high_overlap_case_count: int
    generator_independence: bool

    threshold_primary: float
    threshold_delta: float
    threshold_lower: float
    threshold_upper: float
    lower_threshold_flip_rate: float
    upper_threshold_flip_rate: float
    threshold_sensitivity_delta: float
    result_sensitive_to_threshold: bool

    contract_rule_in_generic_fields: bool
    leakage_rate: float

    true_tpr_at_budget: float | None
    mean_shuffled_tpr_at_budget: float | None
    selectivity_delta_vs_shuffled: float | None
    beats_shuffled_labels: bool | None
    shuffled_label_trials: int

    selectivity_delta_vs_random: float | None

    integrity_passed: bool
    hard_issue_count: int
    soft_issue_count: int
    integrity_issues: list[str] = Field(default_factory=list)
    integrity_warnings: list[str] = Field(default_factory=list)
    integrity_hash: str

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Benchmark Integrity Audit",
            "",
            "## Executive Summary",
            "",
            f"- integrity_passed: `{str(self.integrity_passed).lower()}`",
            f"- hard_issue_count: `{self.hard_issue_count}`",
            f"- soft_issue_count: `{self.soft_issue_count}`",
            f"- integrity_hash: `{self.integrity_hash}`",
            "",
            "## Score Distribution",
            "",
            f"- score_entropy: `{self.score_entropy:.6f}`",
            f"- score_variance: `{self.score_variance:.6f}`",
            f"- score_collapse_detected: `{str(self.score_collapse_detected).lower()}`",
            f"- max_score_bin_fraction: `{self.max_score_bin_fraction:.6f}`",
            "",
            "## Generator Independence",
            "",
            f"- token_overlap_mean: `{self.token_overlap_mean:.6f}`",
            f"- token_overlap_max: `{self.token_overlap_max:.6f}`",
            f"- high_overlap_case_count: `{self.high_overlap_case_count}`",
            f"- generator_independence: `{str(self.generator_independence).lower()}`",
            "",
            "## Threshold Sensitivity",
            "",
            f"- threshold_primary: `{self.threshold_primary:.6f}`",
            f"- threshold_delta: `{self.threshold_delta:.6f}`",
            f"- threshold_lower: `{self.threshold_lower:.6f}`",
            f"- threshold_upper: `{self.threshold_upper:.6f}`",
            f"- lower_threshold_flip_rate: `{self.lower_threshold_flip_rate:.6f}`",
            f"- upper_threshold_flip_rate: `{self.upper_threshold_flip_rate:.6f}`",
            f"- threshold_sensitivity_delta: `{self.threshold_sensitivity_delta:.6f}`",
            f"- result_sensitive_to_threshold: `{str(self.result_sensitive_to_threshold).lower()}`",
            "",
            "## Shuffled Label Baseline",
            "",
            f"- true_tpr_at_budget: `{_format_optional(self.true_tpr_at_budget)}`",
            f"- mean_shuffled_tpr_at_budget: "
            f"`{_format_optional(self.mean_shuffled_tpr_at_budget)}`",
            f"- selectivity_delta_vs_shuffled: "
            f"`{_format_optional(self.selectivity_delta_vs_shuffled)}`",
            f"- beats_shuffled_labels: `{_format_optional(self.beats_shuffled_labels)}`",
            f"- shuffled_label_trials: `{self.shuffled_label_trials}`",
            "",
            "## Leakage / Circularity",
            "",
            f"- leakage_rate: `{self.leakage_rate:.6f}`",
            f"- contract_rule_in_generic_fields: "
            f"`{str(self.contract_rule_in_generic_fields).lower()}`",
            "",
            "## Issues and Warnings",
            "",
        ]
        if self.integrity_issues:
            lines.extend(f"- issue: `{issue}`" for issue in self.integrity_issues)
        else:
            lines.append("- No hard integrity issues detected.")
        if self.integrity_warnings:
            lines.extend(f"- warning: `{warning}`" for warning in self.integrity_warnings)
        else:
            lines.append("- No soft integrity warnings detected.")
        lines.extend(
            [
                "",
                "## What This Supports",
                "",
                "- This integrity audit checks whether benchmark results are likely responding "
                "to labels rather than leakage, score collapse, or threshold artifacts.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- It does not prove external validity.",
                "- It does not replace human audit.",
                "- It does not prove production safety.",
                "- The shuffled-label test is only one falsifiability check.",
                "- Deterministic synthetic datasets still require external validation.",
            ]
        )
        return "\n".join(lines)


def load_integrity_config(path: str | Path) -> BenchmarkIntegrityConfig:
    return BenchmarkIntegrityConfig.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def score_entropy(scores: list[float], n_bins: int) -> float:
    if not scores or n_bins <= 0:
        return 0.0
    counts = [0] * n_bins
    for score in scores:
        unit_score = min(max(float(score), 0.0), 1.0)
        bin_index = min(int(unit_score * n_bins), n_bins - 1)
        counts[bin_index] += 1
    total = len(scores)
    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts
        if count
    )


def score_variance(scores: list[float]) -> float:
    return float(pvariance(scores)) if scores else 0.0


def score_collapse_check(
    scores: list[float],
    config: BenchmarkIntegrityConfig,
) -> dict[str, float | bool]:
    entropy = score_entropy(scores, config.score_entropy_bins)
    max_bin_fraction = _max_score_bin_fraction(scores, config.score_entropy_bins)
    collapse_detected = (
        entropy <= config.score_collapse_entropy_threshold
        or max_bin_fraction >= config.score_collapse_majority_fraction
    )
    return {
        "score_entropy": entropy,
        "score_variance": score_variance(scores),
        "score_collapse_detected": collapse_detected,
        "max_score_bin_fraction": max_bin_fraction,
    }


def tokenize_for_overlap(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def jaccard_overlap(a_tokens: set[str], b_tokens: set[str]) -> float:
    union = a_tokens | b_tokens
    if not union:
        return 0.0
    return len(a_tokens & b_tokens) / len(union)


def compute_generator_independence(
    cases: list[dict[str, Any]],
    *,
    generic_text_fields: list[str] | None = None,
    contract_text_fields: list[str] | None = None,
    high_overlap_threshold: float = 0.20,
    fail_overlap_threshold: float = 0.30,
    mean_overlap_threshold: float = 0.15,
) -> dict[str, float | int | bool]:
    generic_fields = generic_text_fields or DEFAULT_GENERIC_TEXT_FIELDS
    contract_fields = contract_text_fields or DEFAULT_CONTRACT_TEXT_FIELDS
    overlaps = [
        jaccard_overlap(
            tokenize_for_overlap(_join_fields(case, generic_fields)),
            tokenize_for_overlap(_join_fields(case, contract_fields)),
        )
        for case in cases
    ]
    mean_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
    max_overlap = max(overlaps) if overlaps else 0.0
    return {
        "token_overlap_mean": mean_overlap,
        "token_overlap_max": max_overlap,
        "high_overlap_case_count": sum(
            overlap >= high_overlap_threshold for overlap in overlaps
        ),
        "generator_independence": (
            mean_overlap <= mean_overlap_threshold
            and max_overlap <= fail_overlap_threshold
        ),
    }


def threshold_sensitivity(
    cases: list[dict[str, Any]],
    scores: list[float],
    primary_threshold: float,
    delta: float,
) -> dict[str, float]:
    del cases
    if not scores:
        return {
            "lower_threshold": max(0.0, primary_threshold - delta),
            "upper_threshold": min(1.0, primary_threshold + delta),
            "lower_flip_rate": 0.0,
            "upper_flip_rate": 0.0,
            "threshold_sensitivity_delta": 0.0,
        }
    lower = max(0.0, primary_threshold - delta)
    upper = min(1.0, primary_threshold + delta)
    primary_decisions = [score >= primary_threshold for score in scores]
    lower_flip_rate = _decision_flip_rate(
        primary_decisions,
        [score >= lower for score in scores],
    )
    upper_flip_rate = _decision_flip_rate(
        primary_decisions,
        [score >= upper for score in scores],
    )
    return {
        "lower_threshold": lower,
        "upper_threshold": upper,
        "lower_flip_rate": lower_flip_rate,
        "upper_flip_rate": upper_flip_rate,
        "threshold_sensitivity_delta": max(lower_flip_rate, upper_flip_rate),
    }


def shuffled_label_selectivity_test(
    cases: list[dict[str, Any]],
    scores: list[float],
    n_shuffles: int,
    budget: float | int,
    rng_seed: int,
) -> dict[str, float | bool | None]:
    true_tpr = compute_tpr_at_budget(cases, scores, budget)
    labels = [case.get("label") for case in cases]
    if true_tpr is None or not labels or n_shuffles <= 0:
        return {
            "true_tpr_at_budget": true_tpr,
            "mean_shuffled_tpr_at_budget": None,
            "selectivity_delta_vs_shuffled": None,
        }
    rng = random.Random(rng_seed)
    shuffled_tprs: list[float] = []
    for _ in range(n_shuffles):
        shuffled_labels = list(labels)
        rng.shuffle(shuffled_labels)
        shuffled_cases = [
            {**case, "label": label}
            for case, label in zip(cases, shuffled_labels, strict=True)
        ]
        shuffled_tpr = compute_tpr_at_budget(shuffled_cases, scores, budget)
        if shuffled_tpr is not None:
            shuffled_tprs.append(shuffled_tpr)
    mean_shuffled = (
        sum(shuffled_tprs) / len(shuffled_tprs)
        if shuffled_tprs
        else None
    )
    return {
        "true_tpr_at_budget": true_tpr,
        "mean_shuffled_tpr_at_budget": mean_shuffled,
        "selectivity_delta_vs_shuffled": (
            true_tpr - mean_shuffled
            if mean_shuffled is not None
            else None
        ),
    }


def compute_tpr_at_budget(
    cases: list[dict[str, Any]],
    scores: list[float],
    budget: float | int,
) -> float | None:
    if len(cases) != len(scores) or not cases:
        return None
    positive_count = sum(_is_positive_label(case.get("label")) for case in cases)
    if positive_count == 0:
        return None
    selection_count = _budget_count(budget, len(cases))
    ranked_indices = sorted(
        range(len(cases)),
        key=lambda index: (-scores[index], _case_identifier(cases[index], index)),
    )
    selected = set(ranked_indices[:selection_count])
    true_positive_count = sum(
        index in selected and _is_positive_label(case.get("label"))
        for index, case in enumerate(cases)
    )
    return true_positive_count / positive_count


def detect_contract_leakage(
    cases: list[dict[str, Any]],
    *,
    generic_text_fields: list[str] | None = None,
    contract_text_fields: list[str] | None = None,
) -> dict[str, float | bool | int]:
    generic_fields = generic_text_fields or DEFAULT_GENERIC_TEXT_FIELDS
    contract_fields = contract_text_fields or DEFAULT_CONTRACT_TEXT_FIELDS
    leaked_case_count = 0
    for case in cases:
        generic_text = _normalize_text(_join_fields(case, generic_fields))
        contract_values = [
            _normalize_text(str(case.get(field, "")))
            for field in contract_fields
            if str(case.get(field, "")).strip()
        ]
        if any(contract_value in generic_text for contract_value in contract_values):
            leaked_case_count += 1
    leakage_rate = leaked_case_count / len(cases) if cases else 0.0
    return {
        "contract_rule_in_generic_fields": leaked_case_count > 0,
        "leakage_rate": leakage_rate,
        "leaked_case_count": leaked_case_count,
    }


def run_benchmark_integrity_audit(
    *,
    cases: list[dict[str, Any]],
    scores: list[float],
    config: BenchmarkIntegrityConfig,
    generic_text_fields: list[str],
    contract_text_fields: list[str],
    label_field: str = "label",
) -> BenchmarkIntegrityReport:
    if len(cases) != len(scores):
        raise ValueError(
            f"Case/score count mismatch: cases={len(cases)}, scores={len(scores)}"
        )
    normalized_scores = [float(score) for score in scores]
    labeled_cases = [
        {**case, "label": case.get(label_field)}
        for case in cases
    ]
    warnings: list[str] = []
    if not cases:
        warnings.append("missing_cases")
    if not any(
        any(str(case.get(field, "")).strip() for field in generic_text_fields)
        for case in cases
    ):
        warnings.append("missing_generic_text_fields")
    if not any(
        any(str(case.get(field, "")).strip() for field in contract_text_fields)
        for case in cases
    ):
        warnings.append("missing_contract_text_fields")
    if not any(case.get(label_field) is not None for case in cases):
        warnings.append("missing_label_field")

    collapse = score_collapse_check(normalized_scores, config)
    independence = compute_generator_independence(
        cases,
        generic_text_fields=generic_text_fields,
        contract_text_fields=contract_text_fields,
        high_overlap_threshold=config.token_overlap_warning_threshold,
        fail_overlap_threshold=config.token_overlap_fail_threshold,
        mean_overlap_threshold=config.generator_independence_mean_overlap_threshold,
    )
    sensitivity = threshold_sensitivity(
        cases,
        normalized_scores,
        config.threshold_primary,
        config.threshold_delta,
    )
    leakage = detect_contract_leakage(
        cases,
        generic_text_fields=generic_text_fields,
        contract_text_fields=contract_text_fields,
    )
    budget = (
        sum(score >= config.threshold_primary for score in normalized_scores)
        / len(normalized_scores)
        if normalized_scores
        else 0.0
    )
    shuffled = shuffled_label_selectivity_test(
        labeled_cases,
        normalized_scores,
        config.shuffled_label_trials,
        budget,
        config.shuffled_label_seed,
    )
    shuffled_delta = shuffled["selectivity_delta_vs_shuffled"]
    beats_shuffled = (
        bool(shuffled_delta >= config.shuffled_delta_minimum)
        if isinstance(shuffled_delta, (int, float))
        else None
    )
    if shuffled["true_tpr_at_budget"] is None:
        warnings.append("shuffled_label_test_unavailable")
    warnings.append("selectivity_delta_vs_random_unavailable")

    hard_issues: list[str] = []
    if (
        "score_collapse_detected" in config.hard_conditions
        and collapse["score_collapse_detected"]
    ):
        hard_issues.append("score_collapse_detected")
    if (
        "generator_independence" in config.hard_conditions
        and not independence["generator_independence"]
    ):
        hard_issues.append("generator_independence_failed")
    if (
        "leakage_rate" in config.hard_conditions
        and leakage["leakage_rate"] > config.leakage_rate_maximum
    ):
        hard_issues.append("leakage_rate_exceeded")
    if (
        "beats_shuffled_labels" in config.hard_conditions
        and beats_shuffled is False
    ):
        hard_issues.append("does_not_beat_shuffled_labels")

    result_sensitive = (
        sensitivity["threshold_sensitivity_delta"]
        > config.threshold_flip_soft_threshold
    )
    if (
        "result_sensitive_to_threshold" in config.soft_conditions
        and result_sensitive
    ):
        warnings.append("result_sensitive_to_threshold")
    if (
        "high_overlap_case_count" in config.soft_conditions
        and independence["high_overlap_case_count"] > 0
    ):
        warnings.append("high_overlap_cases_detected")
    warnings = sorted(set(warnings))

    payload = {
        "score_entropy": collapse["score_entropy"],
        "score_variance": collapse["score_variance"],
        "score_collapse_detected": collapse["score_collapse_detected"],
        "max_score_bin_fraction": collapse["max_score_bin_fraction"],
        "token_overlap_mean": independence["token_overlap_mean"],
        "token_overlap_max": independence["token_overlap_max"],
        "high_overlap_case_count": independence["high_overlap_case_count"],
        "generator_independence": independence["generator_independence"],
        "threshold_primary": config.threshold_primary,
        "threshold_delta": config.threshold_delta,
        "threshold_lower": sensitivity["lower_threshold"],
        "threshold_upper": sensitivity["upper_threshold"],
        "lower_threshold_flip_rate": sensitivity["lower_flip_rate"],
        "upper_threshold_flip_rate": sensitivity["upper_flip_rate"],
        "threshold_sensitivity_delta": sensitivity["threshold_sensitivity_delta"],
        "result_sensitive_to_threshold": result_sensitive,
        "contract_rule_in_generic_fields": leakage["contract_rule_in_generic_fields"],
        "leakage_rate": leakage["leakage_rate"],
        "true_tpr_at_budget": shuffled["true_tpr_at_budget"],
        "mean_shuffled_tpr_at_budget": shuffled["mean_shuffled_tpr_at_budget"],
        "selectivity_delta_vs_shuffled": shuffled_delta,
        "beats_shuffled_labels": beats_shuffled,
        "shuffled_label_trials": config.shuffled_label_trials,
        "selectivity_delta_vs_random": None,
        "integrity_passed": not hard_issues,
        "hard_issue_count": len(hard_issues),
        "soft_issue_count": len(warnings),
        "integrity_issues": hard_issues,
        "integrity_warnings": warnings,
    }
    return BenchmarkIntegrityReport.model_validate(
        {
            **payload,
            "integrity_hash": stable_json_hash(payload),
        }
    )


def write_integrity_audit_outputs(
    report: BenchmarkIntegrityReport,
    out_dir: str | Path,
) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "integrity_report.json"
    markdown_path = target / "integrity_report.md"
    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(report.to_markdown() + "\n", encoding="utf-8")
    return json_path, markdown_path


def _max_score_bin_fraction(scores: list[float], n_bins: int) -> float:
    if not scores or n_bins <= 0:
        return 0.0
    counts = [0] * n_bins
    for score in scores:
        unit_score = min(max(float(score), 0.0), 1.0)
        counts[min(int(unit_score * n_bins), n_bins - 1)] += 1
    return max(counts) / len(scores)


def _decision_flip_rate(primary: list[bool], comparison: list[bool]) -> float:
    if not primary:
        return 0.0
    return (
        sum(left != right for left, right in zip(primary, comparison, strict=True))
        / len(primary)
    )


def _join_fields(case: dict[str, Any], fields: list[str]) -> str:
    return " ".join(
        str(case.get(field, ""))
        for field in fields
        if case.get(field) is not None
    )


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _is_positive_label(label: Any) -> bool:
    if isinstance(label, bool):
        return label
    return str(label).strip().lower() in POSITIVE_LABELS


def _budget_count(budget: float | int, case_count: int) -> int:
    if isinstance(budget, float) and budget <= 1.0:
        return min(case_count, max(0, math.ceil(budget * case_count)))
    return min(case_count, max(0, int(budget)))


def _case_identifier(case: dict[str, Any], index: int) -> str:
    return str(case.get("sample_id") or case.get("case_id") or f"case_{index:09d}")


def _format_optional(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)

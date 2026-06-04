from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import stable_json_hash


class V10ReportabilityConfig(BaseModel):
    schema_version: str
    registered_before_experiment: bool = False
    score_entropy_min: float
    max_score_bin_fraction_max: float
    mid_risk_range: tuple[float, float]
    mid_risk_min_fraction: float
    near_boundary_range: tuple[float, float]
    near_boundary_min_fraction: float
    token_overlap_mean_max: float
    leakage_rate_max: float
    require_positive_random_selectivity: bool
    require_positive_shuffled_selectivity: bool
    require_bootstrap_ci: bool
    require_zero_hard_integrity_issues: bool
    require_score_band_occupancy: bool
    min_score_band_occupancy: dict[str, float]
    evidence_level_target: int
    level_5_requires_human_or_live_validation: bool
    notes: str = ""


class V10ReportabilityReport(BaseModel):
    reportability_passed: bool
    failed_criteria: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    score_entropy: float | None
    max_score_bin_fraction: float | None
    mid_risk_fraction: float | None
    near_boundary_fraction: float | None
    token_overlap_mean: float | None
    leakage_rate: float | None
    selectivity_delta_vs_random: float | None
    selectivity_delta_vs_shuffled: float | None
    bootstrap_ci_present: bool
    hard_integrity_issue_count: int | None
    score_band_occupancy: dict[str, float] = Field(default_factory=dict)
    evidence_level_allowed: int
    level_5_allowed: bool
    reportability_hash: str

    def to_markdown(self) -> str:
        status = "PASS" if self.reportability_passed else "FAIL"
        lines = [
            "# HELIX v10 Reportability Gate",
            "",
            "## Executive Summary",
            "",
            f"- reportability status: `{status}`",
            f"- evidence_level_allowed: `{self.evidence_level_allowed}`",
            f"- level_5_allowed: `{str(self.level_5_allowed).lower()}`",
            f"- reportability_hash: `{self.reportability_hash}`",
            "",
            "This gate does not generate a benchmark and does not prove v10 passes. "
            "It defines executable criteria for future v10 outputs.",
            "",
            "## Criteria Table",
            "",
            "| Criterion | Observed value | Result |",
            "|---|---:|---|",
        ]
        lines.extend(
            [
                _criterion_row(
                    "score entropy",
                    self.score_entropy,
                    "score_entropy_below_or_equal_minimum",
                    self.failed_criteria,
                ),
                _criterion_row(
                    "maximum score-bin fraction",
                    self.max_score_bin_fraction,
                    "max_score_bin_fraction_at_or_above_maximum",
                    self.failed_criteria,
                ),
                _criterion_row(
                    "mid-risk fraction",
                    self.mid_risk_fraction,
                    "mid_risk_fraction_below_minimum",
                    self.failed_criteria,
                ),
                _criterion_row(
                    "near-boundary fraction",
                    self.near_boundary_fraction,
                    "near_boundary_fraction_below_minimum",
                    self.failed_criteria,
                ),
                _criterion_row(
                    "token-overlap mean",
                    self.token_overlap_mean,
                    "token_overlap_mean_at_or_above_maximum",
                    self.failed_criteria,
                ),
                _criterion_row(
                    "leakage rate",
                    self.leakage_rate,
                    "leakage_rate_at_or_above_maximum",
                    self.failed_criteria,
                ),
                _criterion_row(
                    "selectivity delta vs random",
                    self.selectivity_delta_vs_random,
                    "non_positive_selectivity_delta_vs_random",
                    self.failed_criteria,
                ),
                _criterion_row(
                    "selectivity delta vs shuffled",
                    self.selectivity_delta_vs_shuffled,
                    "non_positive_selectivity_delta_vs_shuffled",
                    self.failed_criteria,
                ),
                _criterion_row(
                    "hard integrity issue count",
                    self.hard_integrity_issue_count,
                    "hard_integrity_issues_present",
                    self.failed_criteria,
                ),
                f"| Bootstrap CI present | `{str(self.bootstrap_ci_present).lower()}` | "
                f"`{'FAIL' if 'missing_bootstrap_ci' in self.failed_criteria else 'PASS'}` |",
            ]
        )
        lines.extend(
            [
                "",
                "## Score Distribution Requirements",
                "",
            ]
        )
        if self.score_band_occupancy:
            lines.extend(
                f"- `{band}`: `{occupancy:.6f}`"
                for band, occupancy in self.score_band_occupancy.items()
            )
        else:
            lines.append("- Score-band occupancy unavailable.")
        lines.extend(
            [
                "",
                "## Integrity Requirements",
                "",
                f"- hard_integrity_issue_count: `{_format_value(self.hard_integrity_issue_count)}`",
                f"- token_overlap_mean: `{_format_value(self.token_overlap_mean)}`",
                f"- leakage_rate: `{_format_value(self.leakage_rate)}`",
                "",
                "## Bootstrap CI Requirements",
                "",
                f"- bootstrap_ci_present: `{str(self.bootstrap_ci_present).lower()}`",
                "",
                "## Evidence-Level Decision",
                "",
                f"- evidence_level_allowed: `{self.evidence_level_allowed}`",
                f"- level_5_allowed: `{str(self.level_5_allowed).lower()}`",
                "- Level 5 remains reserved for human, external, or live validation.",
                "",
                "## Failed Criteria",
                "",
            ]
        )
        if self.failed_criteria:
            lines.extend(f"- `{criterion}`" for criterion in self.failed_criteria)
        else:
            lines.append("- None.")
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        lines.extend(
            [
                "",
                "## What This Supports",
                "",
                "- Future v10 outputs can be prevented from receiving Level-4 treatment "
                "unless both generic integrity and v10-specific reportability criteria pass.",
                "- Missing calibration, distribution, selectivity, or bootstrap evidence "
                "fails closed.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- This does not generate a benchmark.",
                "- This does not prove v10 passes.",
                "- This does not prove external validity or production safety.",
                "- Level 5 remains reserved for human, external, or live validation.",
            ]
        )
        return "\n".join(lines)


def load_v10_reportability_config(path: str | Path) -> V10ReportabilityConfig:
    return V10ReportabilityConfig.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def compute_score_bin_occupancy(
    scores: list[float],
    score_bands: list[str] | dict[str, float],
) -> dict[str, float]:
    bands = _parse_score_bands(score_bands)
    normalized_scores = _validate_scores(scores)
    if not normalized_scores:
        return {label: 0.0 for label, _, _ in bands}
    counts = {label: 0 for label, _, _ in bands}
    for score in normalized_scores:
        matched = False
        for index, (label, lower, upper) in enumerate(bands):
            is_final = index == len(bands) - 1
            if lower <= score < upper or (is_final and score == upper):
                counts[label] += 1
                matched = True
                break
        if not matched:
            raise ValueError(f"Score {score} is not covered by configured score bands")
    return {
        label: counts[label] / len(normalized_scores)
        for label, _, _ in bands
    }


def compute_mid_risk_fraction(
    scores: list[float],
    mid_risk_range: tuple[float, float] | list[float],
) -> float:
    return _fraction_in_range(scores, mid_risk_range)


def compute_near_boundary_fraction(
    scores: list[float],
    near_boundary_range: tuple[float, float] | list[float],
) -> float:
    return _fraction_in_range(scores, near_boundary_range)


def compute_max_score_bin_fraction(
    scores: list[float],
    score_bands: list[str] | dict[str, float],
) -> float:
    occupancy = compute_score_bin_occupancy(scores, score_bands)
    return max(occupancy.values(), default=0.0)


def evaluate_v10_reportability(
    *,
    integrity_report: dict[str, Any],
    benchmark_summary: dict[str, Any] | None,
    bootstrap_ci: dict[str, Any] | None,
    config: V10ReportabilityConfig,
) -> V10ReportabilityReport:
    failed: list[str] = []
    warnings = [str(value) for value in integrity_report.get("integrity_warnings") or []]
    summary = benchmark_summary or {}
    scores, score_warning = _extract_scores(summary)
    if score_warning:
        warnings.append(score_warning)

    score_entropy = _optional_float(integrity_report.get("score_entropy"))
    token_overlap_mean = _optional_fraction(
        integrity_report.get("token_overlap_mean")
    )
    leakage_rate = _optional_fraction(integrity_report.get("leakage_rate"))
    selectivity_random = _optional_float(
        integrity_report.get("selectivity_delta_vs_random")
    )
    selectivity_shuffled = _optional_float(
        integrity_report.get("selectivity_delta_vs_shuffled")
    )
    hard_issue_count = _optional_int(integrity_report.get("hard_issue_count"))

    score_bands = list(config.min_score_band_occupancy)
    occupancy = _extract_occupancy(summary, score_bands, scores, warnings)
    mid_risk_fraction = _summary_or_computed_fraction(
        summary,
        "mid_risk_fraction",
        scores,
        config.mid_risk_range,
    )
    near_boundary_fraction = _summary_or_computed_fraction(
        summary,
        "near_boundary_fraction",
        scores,
        config.near_boundary_range,
    )
    max_score_bin_fraction = _summary_or_computed_max_bin(
        summary,
        integrity_report,
        scores,
        score_bands,
    )
    bootstrap_present = bool(bootstrap_ci)

    _require_metric(
        failed,
        score_entropy,
        missing_code="missing_score_entropy",
        failure_code="score_entropy_below_or_equal_minimum",
        passes=lambda value: value > config.score_entropy_min,
    )
    _require_metric(
        failed,
        max_score_bin_fraction,
        missing_code="missing_max_score_bin_fraction",
        failure_code="max_score_bin_fraction_at_or_above_maximum",
        passes=lambda value: value < config.max_score_bin_fraction_max,
    )
    _require_metric(
        failed,
        mid_risk_fraction,
        missing_code="missing_mid_risk_fraction",
        failure_code="mid_risk_fraction_below_minimum",
        passes=lambda value: value >= config.mid_risk_min_fraction,
    )
    _require_metric(
        failed,
        near_boundary_fraction,
        missing_code="missing_near_boundary_fraction",
        failure_code="near_boundary_fraction_below_minimum",
        passes=lambda value: value >= config.near_boundary_min_fraction,
    )
    _require_metric(
        failed,
        token_overlap_mean,
        missing_code="missing_token_overlap_mean",
        failure_code="token_overlap_mean_at_or_above_maximum",
        passes=lambda value: value < config.token_overlap_mean_max,
    )
    _require_metric(
        failed,
        leakage_rate,
        missing_code="missing_leakage_rate",
        failure_code="leakage_rate_at_or_above_maximum",
        passes=lambda value: value < config.leakage_rate_max,
    )
    if config.require_positive_random_selectivity:
        _require_metric(
            failed,
            selectivity_random,
            missing_code="missing_selectivity_delta_vs_random",
            failure_code="non_positive_selectivity_delta_vs_random",
            passes=lambda value: value > 0.0,
        )
    if config.require_positive_shuffled_selectivity:
        _require_metric(
            failed,
            selectivity_shuffled,
            missing_code="missing_selectivity_delta_vs_shuffled",
            failure_code="non_positive_selectivity_delta_vs_shuffled",
            passes=lambda value: value > 0.0,
        )
    if config.require_bootstrap_ci and not bootstrap_present:
        failed.append("missing_bootstrap_ci")
    if integrity_report.get("integrity_passed") is not True:
        failed.append("generic_integrity_audit_failed")
    if config.require_zero_hard_integrity_issues:
        if hard_issue_count is None:
            failed.append("missing_hard_integrity_issue_count")
        elif hard_issue_count > 0:
            failed.append("hard_integrity_issues_present")
    if config.require_score_band_occupancy:
        if not occupancy:
            failed.append("missing_score_band_occupancy")
        else:
            for band, minimum in config.min_score_band_occupancy.items():
                if band not in occupancy:
                    failed.append(f"missing_score_band_occupancy:{band}")
                elif occupancy[band] < minimum:
                    failed.append(f"score_band_occupancy_below_minimum:{band}")

    failed = sorted(set(failed))
    warnings = sorted(set(warnings))
    passed = not failed
    evidence_level = (
        min(config.evidence_level_target, 4)
        if passed
        else min(config.evidence_level_target, 3)
    )
    payload = {
        "reportability_passed": passed,
        "failed_criteria": failed,
        "warnings": warnings,
        "score_entropy": score_entropy,
        "max_score_bin_fraction": max_score_bin_fraction,
        "mid_risk_fraction": mid_risk_fraction,
        "near_boundary_fraction": near_boundary_fraction,
        "token_overlap_mean": token_overlap_mean,
        "leakage_rate": leakage_rate,
        "selectivity_delta_vs_random": selectivity_random,
        "selectivity_delta_vs_shuffled": selectivity_shuffled,
        "bootstrap_ci_present": bootstrap_present,
        "hard_integrity_issue_count": hard_issue_count,
        "score_band_occupancy": occupancy,
        "evidence_level_allowed": evidence_level,
        "level_5_allowed": False,
    }
    return V10ReportabilityReport.model_validate(
        {**payload, "reportability_hash": stable_json_hash(payload)}
    )


def write_v10_reportability_outputs(
    report: V10ReportabilityReport,
    out_dir: str | Path,
) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "v10_reportability_report.json"
    markdown_path = target / "v10_reportability_report.md"
    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(report.to_markdown() + "\n", encoding="utf-8")
    return json_path, markdown_path


def _parse_score_bands(
    score_bands: list[str] | dict[str, float],
) -> list[tuple[str, float, float]]:
    labels = list(score_bands)
    if not labels:
        raise ValueError("At least one score band is required")
    bands: list[tuple[str, float, float]] = []
    for label in labels:
        try:
            lower_text, upper_text = str(label).split("-", maxsplit=1)
            lower = float(lower_text)
            upper = float(upper_text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid score band label: {label!r}") from exc
        if not 0.0 <= lower < upper <= 1.0:
            raise ValueError(f"Invalid score band bounds: {label!r}")
        bands.append((str(label), lower, upper))
    bands.sort(key=lambda item: item[1])
    for left, right in zip(bands, bands[1:], strict=False):
        if left[2] != right[1]:
            raise ValueError(
                f"Score bands must be contiguous: {left[0]!r}, {right[0]!r}"
            )
    return bands


def _validate_scores(scores: list[float]) -> list[float]:
    values = [float(score) for score in scores]
    if any(not math.isfinite(score) or not 0.0 <= score <= 1.0 for score in values):
        raise ValueError("Scores must be finite values in [0, 1]")
    return values


def _fraction_in_range(
    scores: list[float],
    value_range: tuple[float, float] | list[float],
) -> float:
    values = _validate_scores(scores)
    if len(value_range) != 2:
        raise ValueError("Score range must contain exactly two values")
    lower, upper = float(value_range[0]), float(value_range[1])
    if not 0.0 <= lower <= upper <= 1.0:
        raise ValueError("Score range must satisfy 0 <= lower <= upper <= 1")
    if not values:
        return 0.0
    return sum(lower <= score <= upper for score in values) / len(values)


def _extract_scores(
    summary: dict[str, Any],
) -> tuple[list[float] | None, str | None]:
    for key in ("scores", "violation_probabilities", "score_values"):
        value = summary.get(key)
        if value is None:
            continue
        if not isinstance(value, list):
            return None, f"invalid_benchmark_summary_{key}"
        try:
            return _validate_scores(value), None
        except (TypeError, ValueError):
            return None, f"invalid_benchmark_summary_{key}"
    return None, "missing_benchmark_summary_scores"


def _extract_occupancy(
    summary: dict[str, Any],
    score_bands: list[str],
    scores: list[float] | None,
    warnings: list[str],
) -> dict[str, float]:
    if scores is not None:
        return compute_score_bin_occupancy(scores, score_bands)
    direct = summary.get("score_band_occupancy")
    if direct is not None:
        if not isinstance(direct, dict):
            warnings.append("invalid_score_band_occupancy")
            return {}
        try:
            occupancy = {
                str(key): float(value)
                for key, value in sorted(direct.items())
            }
        except (TypeError, ValueError):
            warnings.append("invalid_score_band_occupancy")
            return {}
        if (
            set(occupancy) != set(score_bands)
            or any(
                not math.isfinite(value) or not 0.0 <= value <= 1.0
                for value in occupancy.values()
            )
            or not math.isclose(sum(occupancy.values()), 1.0, abs_tol=1e-6)
        ):
            warnings.append("invalid_score_band_occupancy")
            return {}
        return occupancy
    return {}


def _summary_or_computed_fraction(
    summary: dict[str, Any],
    key: str,
    scores: list[float] | None,
    value_range: tuple[float, float],
) -> float | None:
    if scores is not None:
        return _fraction_in_range(scores, value_range)
    return _optional_fraction(summary.get(key))


def _summary_or_computed_max_bin(
    summary: dict[str, Any],
    integrity_report: dict[str, Any],
    scores: list[float] | None,
    score_bands: list[str],
) -> float | None:
    if scores is not None:
        return compute_max_score_bin_fraction(scores, score_bands)
    direct = _optional_fraction(summary.get("max_score_bin_fraction"))
    if direct is not None:
        return direct
    return _optional_fraction(integrity_report.get("max_score_bin_fraction"))


def _require_metric(
    failed: list[str],
    value: float | int | None,
    *,
    missing_code: str,
    failure_code: str,
    passes: Callable[[float | int], bool],
) -> None:
    if value is None:
        failed.append(missing_code)
    elif not passes(value):
        failed.append(failure_code)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _optional_fraction(value: Any) -> float | None:
    result = _optional_float(value)
    if result is None or not 0.0 <= result <= 1.0:
        return None
    return result


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0 or not numeric.is_integer():
        return None
    return int(numeric)


def _criterion_row(
    name: str,
    value: float | int | None,
    failure_code: str,
    failures: list[str],
) -> str:
    failed = value is None or failure_code in failures
    return f"| {name} | `{_format_value(value)}` | `{'FAIL' if failed else 'PASS'}` |"


def _format_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)

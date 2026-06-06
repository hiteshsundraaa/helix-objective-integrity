from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, hash_text, stable_json_hash
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_judgment_normalization import (
    V10NormalizedJudgment,
    V10NormalizationSummary,
)


class V10BenchmarkRunnerConfig(BaseModel):
    schema_version: str
    registered_before_real_judgment_runs: bool
    block_threshold: float
    warn_threshold: float
    degrade_threshold: float
    quarantine_threshold: float
    high_risk_threshold: float
    valid_normalization_statuses: list[str]
    reject_normalization_statuses: list[str]
    positive_labels: list[str]
    safe_labels: list[str]
    ambiguous_labels: list[str]
    high_risk_decisions: list[str]
    accepted_high_risk_citation_methods: list[str]
    receipt_hash_algorithm: str
    notes: str = ""


class V10BenchmarkReceipt(BaseModel):
    receipt_id: str
    case_id: str
    case_hash: str
    judgment_hash: str
    decision: str
    violation_probability: float
    label: str
    benchmark_verdict: Literal[
        "true_positive",
        "false_positive",
        "true_negative",
        "false_negative",
        "ambiguous_escalated",
        "ambiguous_allowed",
        "ambiguous_blocked",
    ]
    high_risk_citation_valid: bool
    config_hash: str
    normalization_manifest_hash: str | None = None
    receipt_hash: str


class V10BenchmarkSummary(BaseModel):
    schema_version: str
    case_count: int
    normalized_judgment_count: int
    valid_judgment_count: int
    invalid_judgment_count: int
    matched_case_count: int
    missing_judgment_case_count: int
    extra_judgment_case_count: int
    block_threshold: float
    high_risk_threshold: float
    true_positive_count: int
    false_positive_count: int
    true_negative_count: int
    false_negative_count: int
    ambiguous_count: int
    tpr: float
    fpr: float
    precision: float
    recall: float
    unsafe_false_safe_rate: float
    safe_false_interruption_rate: float
    exact_or_normalized_citation_rate_high_risk: float
    high_risk_count: int
    high_risk_invalid_citation_count: int
    score_entropy: float
    max_score_bin_fraction: float
    binary_score_fraction: float
    score_band_occupancy: dict[str, int]
    family_metrics: dict[str, dict[str, Any]]
    domain_metrics: dict[str, dict[str, Any]]
    decision_counts: dict[str, int]
    label_counts: dict[str, int]
    receipt_count: int
    receipt_validation_issue_count: int
    status: Literal["complete", "needs_work", "failed"]
    failed_targets: list[str]
    warnings: list[str]
    benchmark_hash: str

    def to_markdown(self) -> str:
        lines = [
            "# HELIX v10 Benchmark Runner Report",
            "",
            "## Executive Summary",
            "",
            f"- status: `{self.status}`",
            f"- case_count: `{self.case_count}`",
            f"- matched_case_count: `{self.matched_case_count}`",
            f"- missing_judgment_case_count: `{self.missing_judgment_case_count}`",
            f"- receipt_count: `{self.receipt_count}`",
            f"- benchmark_hash: `{self.benchmark_hash}`",
            "",
            "This is a fixture/demo benchmark runner artifact. No live model APIs were called, "
            "and no final v10 reportability claim is made.",
            "",
            "## Input Coverage",
            "",
            f"- normalized_judgment_count: `{self.normalized_judgment_count}`",
            f"- valid_judgment_count: `{self.valid_judgment_count}`",
            f"- invalid_judgment_count: `{self.invalid_judgment_count}`",
            f"- extra_judgment_case_count: `{self.extra_judgment_case_count}`",
            "",
            "## Metric Summary",
            "",
            f"- tpr: `{self.tpr:.6f}`",
            f"- fpr: `{self.fpr:.6f}`",
            f"- precision: `{self.precision:.6f}`",
            f"- recall: `{self.recall:.6f}`",
            f"- unsafe_false_safe_rate: `{self.unsafe_false_safe_rate:.6f}`",
            f"- safe_false_interruption_rate: `{self.safe_false_interruption_rate:.6f}`",
            "",
            "## Family Metrics",
            "",
        ]
        lines.extend(_metrics_table(self.family_metrics))
        lines.extend(["", "## Domain Metrics", ""])
        lines.extend(_metrics_table(self.domain_metrics))
        lines.extend(
            [
                "",
                "## Citation Validation",
                "",
                f"- high_risk_count: `{self.high_risk_count}`",
                f"- high_risk_invalid_citation_count: `{self.high_risk_invalid_citation_count}`",
                f"- exact_or_normalized_citation_rate_high_risk: `{self.exact_or_normalized_citation_rate_high_risk:.6f}`",
                "",
                "## Receipt Validation",
                "",
                f"- receipt_count: `{self.receipt_count}`",
                f"- receipt_validation_issue_count: `{self.receipt_validation_issue_count}`",
                "",
                "## Failure Cases",
                "",
            ]
        )
        if self.false_positive_count or self.false_negative_count or self.high_risk_invalid_citation_count:
            lines.append("- See `v10_failure_cases.jsonl` for false positives, false negatives, and citation failures.")
        else:
            lines.append("- None in matched positive/safe cases.")
        lines.extend(
            [
                "",
                "## What This Supports",
                "",
                "- This supports running v10 metrics over valid normalized judgments.",
                "- This supports refusing malformed or score-collapsed normalization summaries by default.",
                "- This supports hash-linked benchmark-evaluation receipts for matched cases.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- This does not call live model APIs.",
                "- This does not collect real provider judgments unless supplied externally.",
                "- This does not prove final v10 reportability.",
                "- This does not include bootstrap confidence intervals yet.",
                "- Benchmark receipts here are evaluation receipts, not runtime authorization receipts.",
                "",
                "## Limitations",
                "",
                "- Fixture/demo runs are not final v10 evidence.",
                "- Partial case coverage is reported and is not hidden.",
                "- Metrics are computed only over matched valid normalized judgments.",
                "- Reportability remains gated by the separate preregistered v10 reportability gate.",
            ]
        )
        if self.failed_targets:
            lines.extend(["", "## Failed Targets", ""])
            lines.extend(f"- `{target}`" for target in self.failed_targets)
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_benchmark_config(path: str | Path) -> V10BenchmarkRunnerConfig:
    return V10BenchmarkRunnerConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_v10_cases(path: str | Path) -> list[V10Case]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"V10 cases file does not exist: {target}. "
            "Run examples/generate_v10_calibrated_cases.py first."
        )
    return [
        V10Case.model_validate_json(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_normalized_judgments(path: str | Path) -> list[V10NormalizedJudgment]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Normalized v10 judgment file does not exist: {target}")
    return [
        V10NormalizedJudgment.model_validate_json(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_normalization_summary(path: str | Path) -> V10NormalizationSummary:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"V10 normalization summary does not exist: {target}")
    return V10NormalizationSummary.model_validate_json(target.read_text(encoding="utf-8"))


def validate_normalization_status(
    summary: V10NormalizationSummary,
    config: V10BenchmarkRunnerConfig,
) -> list[str]:
    issues: list[str] = []
    if summary.status in set(config.reject_normalization_statuses):
        issues.append(f"normalization_status_rejected:{summary.status}")
    if summary.status not in set(config.valid_normalization_statuses):
        issues.append(f"normalization_status_not_valid:{summary.status}")
    if summary.invalid_count > 0:
        issues.append("normalization_invalid_judgments_present")
    if summary.valid_count == 0:
        issues.append("normalization_no_valid_judgments")
    return issues


def compute_v10_benchmark_metrics(
    cases: list[V10Case],
    normalized_judgments: list[V10NormalizedJudgment],
    config: V10BenchmarkRunnerConfig,
    *,
    normalization_summary: V10NormalizationSummary | None = None,
    receipt_count: int = 0,
    receipt_validation_issue_count: int = 0,
) -> V10BenchmarkSummary:
    cases_by_id = {case.case_id: case for case in cases}
    valid_judgments = [
        judgment
        for judgment in normalized_judgments
        if judgment.normalization_status == "valid"
        and judgment.violation_probability is not None
    ]
    invalid_judgment_count = len(normalized_judgments) - len(valid_judgments)
    seen_case_ids: set[str] = set()
    duplicate_case_ids: set[str] = set()
    matched: list[tuple[V10Case, V10NormalizedJudgment, str, bool, bool]] = []
    extra_judgment_case_count = 0

    for judgment in valid_judgments:
        if judgment.case_id in seen_case_ids:
            duplicate_case_ids.add(judgment.case_id)
        seen_case_ids.add(judgment.case_id)
        case = cases_by_id.get(judgment.case_id)
        if case is None:
            extra_judgment_case_count += 1
            continue
        high_risk_prediction = _is_high_risk_prediction(judgment, config)
        citation_valid = _high_risk_citation_valid(judgment, config)
        verdict = _benchmark_verdict(case.label, high_risk_prediction, judgment, config)
        matched.append((case, judgment, verdict, high_risk_prediction, citation_valid))

    matched_case_ids = {case.case_id for case, *_ in matched}
    missing_judgment_case_count = len(cases_by_id) - len(matched_case_ids)

    verdict_counts = Counter(verdict for _, _, verdict, _, _ in matched)
    decision_counts = Counter(judgment.decision for _, judgment, _, _, _ in matched)
    label_counts = Counter(case.label for case, *_ in matched)
    high_risk_rows = [
        (case, judgment, citation_valid)
        for case, judgment, _, _, citation_valid in matched
        if judgment.decision in set(config.high_risk_decisions)
    ]
    high_risk_count = len(high_risk_rows)
    high_risk_invalid_citation_count = sum(
        not citation_valid for _, _, citation_valid in high_risk_rows
    )
    citation_rate = _safe_divide(
        high_risk_count - high_risk_invalid_citation_count,
        high_risk_count,
    )

    positive_total = sum(
        1 for case, *_ in matched if case.label in set(config.positive_labels)
    )
    safe_total = sum(1 for case, *_ in matched if case.label in set(config.safe_labels))
    true_positive_count = verdict_counts["true_positive"]
    false_positive_count = verdict_counts["false_positive"]
    true_negative_count = verdict_counts["true_negative"]
    false_negative_count = verdict_counts["false_negative"]
    ambiguous_count = sum(
        1 for case, *_ in matched if case.label in set(config.ambiguous_labels)
    )

    tpr = _safe_divide(true_positive_count, positive_total)
    fpr = _safe_divide(false_positive_count, safe_total)
    precision = _safe_divide(
        true_positive_count,
        true_positive_count + false_positive_count,
    )
    unsafe_false_safe_rate = _safe_divide(false_negative_count, positive_total)
    safe_false_interruption_rate = _safe_divide(false_positive_count, safe_total)

    if normalization_summary is not None:
        score_entropy = normalization_summary.score_entropy
        max_score_bin_fraction = normalization_summary.max_score_bin_fraction
        binary_score_fraction = normalization_summary.binary_score_fraction
        score_band_occupancy = normalization_summary.score_band_occupancy
    else:
        scores = [judgment.violation_probability for _, judgment, *_ in matched]
        score_band_occupancy = _score_band_occupancy(scores)
        max_score_bin_fraction = _safe_divide(
            max(score_band_occupancy.values()) if score_band_occupancy else 0,
            len(scores),
        )
        score_entropy = 0.0
        binary_score_fraction = _safe_divide(
            sum(score in {0.0, 1.0} for score in scores),
            len(scores),
        )

    failed_targets: list[str] = []
    warnings: list[str] = []
    if invalid_judgment_count > 0:
        failed_targets.append("invalid_normalized_judgments_present")
    if extra_judgment_case_count > 0:
        failed_targets.append("extra_judgments_present")
    if duplicate_case_ids:
        failed_targets.append("duplicate_judgment_case_ids_present")
    if high_risk_invalid_citation_count > 0:
        failed_targets.append("high_risk_invalid_citations_present")
    if receipt_validation_issue_count > 0:
        failed_targets.append("receipt_validation_issues_present")
    if receipt_count and receipt_count != len(matched):
        failed_targets.append("receipt_count_mismatch")
    if missing_judgment_case_count > 0:
        warnings.append("partial_case_coverage")

    if failed_targets:
        status: Literal["complete", "needs_work", "failed"] = "failed"
    elif warnings:
        status = "needs_work"
    else:
        status = "complete"

    payload = {
        "schema_version": "v10_benchmark_runner_summary_v1",
        "case_count": len(cases),
        "normalized_judgment_count": len(normalized_judgments),
        "valid_judgment_count": len(valid_judgments),
        "invalid_judgment_count": invalid_judgment_count,
        "matched_case_count": len(matched),
        "missing_judgment_case_count": missing_judgment_case_count,
        "extra_judgment_case_count": extra_judgment_case_count,
        "block_threshold": config.block_threshold,
        "high_risk_threshold": config.high_risk_threshold,
        "true_positive_count": true_positive_count,
        "false_positive_count": false_positive_count,
        "true_negative_count": true_negative_count,
        "false_negative_count": false_negative_count,
        "ambiguous_count": ambiguous_count,
        "tpr": tpr,
        "fpr": fpr,
        "precision": precision,
        "recall": tpr,
        "unsafe_false_safe_rate": unsafe_false_safe_rate,
        "safe_false_interruption_rate": safe_false_interruption_rate,
        "exact_or_normalized_citation_rate_high_risk": citation_rate,
        "high_risk_count": high_risk_count,
        "high_risk_invalid_citation_count": high_risk_invalid_citation_count,
        "score_entropy": score_entropy,
        "max_score_bin_fraction": max_score_bin_fraction,
        "binary_score_fraction": binary_score_fraction,
        "score_band_occupancy": score_band_occupancy,
        "family_metrics": _group_metrics(matched, key_name="family", config=config),
        "domain_metrics": _group_metrics(matched, key_name="domain", config=config),
        "decision_counts": dict(sorted(decision_counts.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "receipt_count": receipt_count,
        "receipt_validation_issue_count": receipt_validation_issue_count,
        "status": status,
        "failed_targets": failed_targets,
        "warnings": warnings,
    }
    return V10BenchmarkSummary(**payload, benchmark_hash=stable_json_hash(payload))


def build_v10_benchmark_receipts(
    cases: list[V10Case],
    normalized_judgments: list[V10NormalizedJudgment],
    config: V10BenchmarkRunnerConfig,
    *,
    config_hash: str,
    normalization_manifest_hash: str | None = None,
) -> list[V10BenchmarkReceipt]:
    cases_by_id = {case.case_id: case for case in cases}
    receipts: list[V10BenchmarkReceipt] = []
    for judgment in normalized_judgments:
        if judgment.normalization_status != "valid" or judgment.violation_probability is None:
            continue
        case = cases_by_id.get(judgment.case_id)
        if case is None:
            continue
        high_risk_prediction = _is_high_risk_prediction(judgment, config)
        verdict = _benchmark_verdict(case.label, high_risk_prediction, judgment, config)
        citation_valid = _high_risk_citation_valid(judgment, config)
        case_hash = _case_hash(case)
        judgment_hash = _judgment_hash(judgment)
        receipt_id = f"v10_benchmark_receipt:{case.case_id}"
        receipt_hash = _receipt_hash(
            case_id=case.case_id,
            case_hash=case_hash,
            judgment_hash=judgment_hash,
            decision=judgment.decision,
            violation_probability=judgment.violation_probability,
            label=case.label,
            benchmark_verdict=verdict,
            high_risk_citation_valid=citation_valid,
            config_hash=config_hash,
            normalization_manifest_hash=normalization_manifest_hash,
        )
        receipts.append(
            V10BenchmarkReceipt(
                receipt_id=receipt_id,
                case_id=case.case_id,
                case_hash=case_hash,
                judgment_hash=judgment_hash,
                decision=judgment.decision,
                violation_probability=judgment.violation_probability,
                label=case.label,
                benchmark_verdict=verdict,
                high_risk_citation_valid=citation_valid,
                config_hash=config_hash,
                normalization_manifest_hash=normalization_manifest_hash,
                receipt_hash=receipt_hash,
            )
        )
    return receipts


def validate_v10_benchmark_receipts(
    receipts: list[V10BenchmarkReceipt],
    *,
    expected_count: int | None = None,
) -> list[str]:
    issues: list[str] = []
    if expected_count is not None and len(receipts) != expected_count:
        issues.append("receipt_count_mismatch")
    if expected_count and not receipts:
        issues.append("missing_receipt")
    seen_hashes: set[str] = set()
    for receipt in receipts:
        expected_hash = _receipt_hash(
            case_id=receipt.case_id,
            case_hash=receipt.case_hash,
            judgment_hash=receipt.judgment_hash,
            decision=receipt.decision,
            violation_probability=receipt.violation_probability,
            label=receipt.label,
            benchmark_verdict=receipt.benchmark_verdict,
            high_risk_citation_valid=receipt.high_risk_citation_valid,
            config_hash=receipt.config_hash,
            normalization_manifest_hash=receipt.normalization_manifest_hash,
        )
        if receipt.receipt_hash != expected_hash:
            issues.append("receipt_hash_mismatch")
        if receipt.receipt_hash in seen_hashes:
            issues.append("duplicate_receipt_hash")
        seen_hashes.add(receipt.receipt_hash)
    return sorted(set(issues))


def write_v10_benchmark_outputs(
    *,
    summary: V10BenchmarkSummary,
    receipts: list[V10BenchmarkReceipt],
    cases: list[V10Case],
    normalized_judgments: list[V10NormalizedJudgment],
    config_path: str | Path,
    input_cases_path: str | Path,
    normalized_judgments_path: str | Path,
    normalization_summary_path: str | Path,
    normalization_manifest_path: str | Path | None,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[Path, Path, Path, Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    receipts_path = target / "v10_benchmark_receipts.jsonl"
    summary_path = target / "v10_benchmark_summary.json"
    manifest_path = target / "v10_benchmark_manifest.json"
    report_path = target / "v10_benchmark_report.md"
    failure_cases_path = target / "v10_failure_cases.jsonl"

    receipts_path.write_text(
        "\n".join(
            json.dumps(receipt.model_dump(mode="json"), sort_keys=True)
            for receipt in receipts
        )
        + ("\n" if receipts else ""),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")
    _write_failure_cases(
        failure_cases_path,
        cases=cases,
        normalized_judgments=normalized_judgments,
        config=load_v10_benchmark_config(config_path),
    )
    manifest = _benchmark_manifest(
        summary=summary,
        config_path=Path(config_path),
        input_cases_path=Path(input_cases_path),
        normalized_judgments_path=Path(normalized_judgments_path),
        normalization_summary_path=Path(normalization_summary_path),
        normalization_manifest_path=Path(normalization_manifest_path)
        if normalization_manifest_path
        else None,
        generated_at=generated_at,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipts_path, summary_path, manifest_path, report_path, failure_cases_path


def _metrics_table(metrics: dict[str, dict[str, Any]]) -> list[str]:
    if not metrics:
        return ["- No matched cases."]
    lines = [
        "| group | count | tpr | fpr | mean_violation_probability | high_risk_rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key, row in sorted(metrics.items()):
        lines.append(
            f"| `{key}` | `{row['count']}` | `{_fmt(row['tpr'])}` | `{_fmt(row['fpr'])}` | "
            f"`{_fmt(row['mean_violation_probability'])}` | `{_fmt(row['high_risk_rate'])}` |"
        )
    return lines


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _is_high_risk_prediction(
    judgment: V10NormalizedJudgment,
    config: V10BenchmarkRunnerConfig,
) -> bool:
    score = judgment.violation_probability or 0.0
    return score >= config.block_threshold or judgment.decision in set(config.high_risk_decisions)


def _high_risk_citation_valid(
    judgment: V10NormalizedJudgment,
    config: V10BenchmarkRunnerConfig,
) -> bool:
    if judgment.decision not in set(config.high_risk_decisions):
        return True
    return bool(judgment.cited_contract_phrase) and judgment.citation_verification_method in set(
        config.accepted_high_risk_citation_methods
    )


def _benchmark_verdict(
    label: str,
    high_risk_prediction: bool,
    judgment: V10NormalizedJudgment,
    config: V10BenchmarkRunnerConfig,
) -> str:
    if label in set(config.positive_labels):
        return "true_positive" if high_risk_prediction else "false_negative"
    if label in set(config.safe_labels):
        return "false_positive" if high_risk_prediction else "true_negative"
    if judgment.decision == "ESCALATE_FOR_APPROVAL":
        return "ambiguous_escalated"
    if high_risk_prediction:
        return "ambiguous_blocked"
    return "ambiguous_allowed"


def _group_metrics(
    matched: list[tuple[V10Case, V10NormalizedJudgment, str, bool, bool]],
    *,
    key_name: Literal["family", "domain"],
    config: V10BenchmarkRunnerConfig,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[tuple[V10Case, V10NormalizedJudgment, str, bool, bool]]] = defaultdict(list)
    for row in matched:
        case = row[0]
        grouped[getattr(case, key_name)].append(row)
    result: dict[str, dict[str, Any]] = {}
    for key, rows in grouped.items():
        positive_total = sum(1 for case, *_ in rows if case.label in set(config.positive_labels))
        safe_total = sum(1 for case, *_ in rows if case.label in set(config.safe_labels))
        true_positive_count = sum(1 for _, _, verdict, _, _ in rows if verdict == "true_positive")
        false_positive_count = sum(1 for _, _, verdict, _, _ in rows if verdict == "false_positive")
        scores = [judgment.violation_probability or 0.0 for _, judgment, *_ in rows]
        high_risk_count = sum(1 for *_, high_risk_prediction, _ in rows if high_risk_prediction)
        result[key] = {
            "count": len(rows),
            "tpr": _safe_divide(true_positive_count, positive_total) if positive_total else None,
            "fpr": _safe_divide(false_positive_count, safe_total) if safe_total else None,
            "mean_violation_probability": sum(scores) / len(scores) if scores else None,
            "high_risk_rate": _safe_divide(high_risk_count, len(rows)),
        }
    return result


def _safe_divide(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def _score_band_occupancy(scores: list[float]) -> dict[str, int]:
    occupancy = {f"{index / 10:.2f}-{(index + 1) / 10:.2f}": 0 for index in range(10)}
    for score in scores:
        index = min(int(score * 10), 9)
        occupancy[f"{index / 10:.2f}-{(index + 1) / 10:.2f}"] += 1
    return occupancy


def _case_hash(case: V10Case) -> str:
    return stable_json_hash(
        {
            "case_id": case.case_id,
            "family": case.family,
            "domain": case.domain,
            "label": case.label,
            "active_contract_rule_id": case.active_contract_rule_id,
            "active_contract_rule_summary": case.active_contract_rule_summary,
            "proposed_action": case.proposed_action,
            "proposed_arguments": case.proposed_arguments,
        }
    )


def _judgment_hash(judgment: V10NormalizedJudgment) -> str:
    return stable_json_hash(
        {
            "case_id": judgment.case_id,
            "decision": judgment.decision,
            "violation_probability": judgment.violation_probability,
            "cited_contract_phrase": judgment.cited_contract_phrase,
            "citation_verification_method": judgment.citation_verification_method,
            "reason_codes": sorted(judgment.reason_codes),
            "raw_judgment_hash": judgment.raw_judgment_hash,
        }
    )


def _receipt_hash(
    *,
    case_id: str,
    case_hash: str,
    judgment_hash: str,
    decision: str,
    violation_probability: float,
    label: str,
    benchmark_verdict: str,
    high_risk_citation_valid: bool,
    config_hash: str,
    normalization_manifest_hash: str | None,
) -> str:
    # Independent verification depends on this preimage order.
    return hash_text(
        "|".join(
            [
                case_id,
                case_hash,
                judgment_hash,
                decision,
                _canonical_float(violation_probability),
                label,
                benchmark_verdict,
                str(high_risk_citation_valid).lower(),
                config_hash,
                normalization_manifest_hash or "",
            ]
        )
    )


def _canonical_float(value: float) -> str:
    return f"{value:.12g}"


def _benchmark_manifest(
    *,
    summary: V10BenchmarkSummary,
    config_path: Path,
    input_cases_path: Path,
    normalized_judgments_path: Path,
    normalization_summary_path: Path,
    normalization_manifest_path: Path | None,
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_benchmark_runner_v1",
        "benchmark_config_path": str(config_path),
        "benchmark_config_hash": hash_file(config_path),
        "input_cases_path": str(input_cases_path),
        "input_cases_hash": hash_file(input_cases_path),
        "normalized_judgments_path": str(normalized_judgments_path),
        "normalized_judgments_hash": hash_file(normalized_judgments_path),
        "normalization_summary_path": str(normalization_summary_path),
        "normalization_summary_hash": hash_file(normalization_summary_path),
        "normalization_manifest_path": str(normalization_manifest_path)
        if normalization_manifest_path
        else None,
        "normalization_manifest_hash": hash_file(normalization_manifest_path)
        if normalization_manifest_path
        else None,
        "case_count": summary.case_count,
        "matched_case_count": summary.matched_case_count,
        "missing_judgment_case_count": summary.missing_judgment_case_count,
        "receipt_count": summary.receipt_count,
        "benchmark_hash": summary.benchmark_hash,
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Fixture/demo runs do not create final v10 reportability claims.",
            "No live model APIs were called.",
            "Benchmark receipts are evaluation receipts, not runtime authorization receipts.",
            "Bootstrap confidence intervals are not computed in this patch.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}


def _write_failure_cases(
    path: Path,
    *,
    cases: list[V10Case],
    normalized_judgments: list[V10NormalizedJudgment],
    config: V10BenchmarkRunnerConfig,
) -> None:
    cases_by_id = {case.case_id: case for case in cases}
    rows: list[dict[str, Any]] = []
    for judgment in normalized_judgments:
        if judgment.normalization_status != "valid" or judgment.violation_probability is None:
            continue
        case = cases_by_id.get(judgment.case_id)
        if case is None:
            continue
        high_risk_prediction = _is_high_risk_prediction(judgment, config)
        verdict = _benchmark_verdict(case.label, high_risk_prediction, judgment, config)
        citation_valid = _high_risk_citation_valid(judgment, config)
        if verdict not in {"false_positive", "false_negative"} and citation_valid:
            continue
        rows.append(
            {
                "case_id": case.case_id,
                "label": case.label,
                "family": case.family,
                "domain": case.domain,
                "decision": judgment.decision,
                "violation_probability": judgment.violation_probability,
                "benchmark_verdict": verdict,
                "high_risk_citation_valid": citation_valid,
            }
        )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )

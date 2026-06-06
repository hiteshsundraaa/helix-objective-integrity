from __future__ import annotations

from datetime import UTC, datetime
import json
import math
import random
from pathlib import Path
from statistics import pstdev
from typing import Any

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.integrity_audit import (
    BenchmarkIntegrityReport,
    load_integrity_config,
    run_benchmark_integrity_audit,
)
from helix.benchmark.v10_benchmark_runner import V10BenchmarkReceipt, V10BenchmarkSummary
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_reportability import (
    V10ReportabilityReport,
    evaluate_v10_reportability,
    load_v10_reportability_config,
)


class V10DiagnosticsConfig(BaseModel):
    schema_version: str
    registered_before_real_judgment_runs: bool
    bootstrap_seed: int
    bootstrap_resamples: int
    confidence_level: float
    metrics_for_ci: list[str]
    minimum_cases_for_stable_ci: int
    fixture_mode_allowed: bool
    fixture_mode_must_not_claim_reportability: bool
    selectivity_baseline_seed: int
    selectivity_baseline_trials: int
    selectivity_budget: float
    positive_labels_for_selectivity: list[str]
    selectivity_score_field: str
    require_selectivity_baselines_for_reportability: bool
    notes: str = ""


class V10BootstrapMetricCI(BaseModel):
    metric_name: str
    point_estimate: float | None
    lower: float | None
    upper: float | None
    confidence_level: float
    resamples: int
    valid_resample_count: int
    warning: str | None = None


class V10SelectivityBaselineSummary(BaseModel):
    true_tpr_at_budget: float | None
    mean_random_tpr_at_budget: float | None
    random_tpr_std_at_budget: float | None
    selectivity_delta_vs_random: float | None
    mean_shuffled_tpr_at_budget: float | None
    shuffled_tpr_std_at_budget: float | None
    selectivity_delta_vs_shuffled: float | None
    selectivity_baseline_trials: int
    selectivity_budget: float
    selectivity_positive_label_count: int
    selectivity_selected_count: int
    selectivity_status: str
    selectivity_warnings: list[str] = Field(default_factory=list)


class V10DiagnosticsSummary(BaseModel):
    schema_version: str
    benchmark_run_path: str
    bootstrap_ci_path: str
    integrity_report_path: str
    reportability_report_path: str
    fixture_mode: bool
    case_count: int
    matched_case_count: int
    bootstrap_resamples: int
    ci_metrics: dict[str, V10BootstrapMetricCI]
    selectivity_baselines: V10SelectivityBaselineSummary
    integrity_passed: bool | None
    reportability_passed: bool | None
    evidence_level_allowed: int | None
    diagnostics_status: str
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    diagnostics_hash: str

    def to_markdown(self) -> str:
        ci_limitation = (
            "- Bootstrap CIs are unstable under small samples."
            if self.matched_case_count < 30
            else "- Bootstrap CIs are diagnostic for fixture/demo runs."
        )
        reportability_limitation = (
            "- Mechanical reportability pass is blocked from final claims in fixture mode."
            if self.reportability_passed
            else "- Reportability failure is preserved when diagnostic criteria are not met."
        )
        lines = [
            "# HELIX v10 Diagnostics Report",
            "",
            "## Executive Summary",
            "",
            f"- diagnostics_status: `{self.diagnostics_status}`",
            f"- fixture_mode: `{str(self.fixture_mode).lower()}`",
            f"- matched_case_count: `{self.matched_case_count}`",
            f"- integrity_passed: `{self.integrity_passed}`",
            f"- reportability_passed: `{self.reportability_passed}`",
            f"- evidence_level_allowed: `{self.evidence_level_allowed}`",
            f"- diagnostics_hash: `{self.diagnostics_hash}`",
            "",
            "This is fixture/demo diagnostics only. No live model APIs were called, "
            "and no final v10 reportability claim is made.",
            "",
            "## Bootstrap Confidence Intervals",
            "",
            "| metric | point | lower | upper | valid resamples | warning |",
            "|---|---:|---:|---:|---:|---|",
        ]
        for metric in self.ci_metrics.values():
            lines.append(
                f"| `{metric.metric_name}` | `{_fmt(metric.point_estimate)}` | "
                f"`{_fmt(metric.lower)}` | `{_fmt(metric.upper)}` | "
                f"`{metric.valid_resample_count}` | `{metric.warning or ''}` |"
            )
        lines.extend(
            [
                "",
                "## Selectivity Baselines",
                "",
                "Selectivity baselines are computed over matched benchmark receipts. "
                "For fixture runs, selectivity estimates are diagnostic only and may be unstable. "
                "If no positive labels are present, selectivity is unavailable and reportability must fail.",
                "",
                f"- budget: `{self.selectivity_baselines.selectivity_budget:.6f}`",
                f"- selected count: `{self.selectivity_baselines.selectivity_selected_count}`",
                f"- positive label count: `{self.selectivity_baselines.selectivity_positive_label_count}`",
                f"- true TPR at budget: `{_fmt(self.selectivity_baselines.true_tpr_at_budget)}`",
                f"- mean random TPR: `{_fmt(self.selectivity_baselines.mean_random_tpr_at_budget)}`",
                f"- selectivity delta vs random: `{_fmt(self.selectivity_baselines.selectivity_delta_vs_random)}`",
                f"- mean shuffled TPR: `{_fmt(self.selectivity_baselines.mean_shuffled_tpr_at_budget)}`",
                f"- selectivity delta vs shuffled: `{_fmt(self.selectivity_baselines.selectivity_delta_vs_shuffled)}`",
                f"- trials: `{self.selectivity_baselines.selectivity_baseline_trials}`",
                f"- status: `{self.selectivity_baselines.selectivity_status}`",
                f"- warnings: `{self.selectivity_baselines.selectivity_warnings}`",
                "",
                "## Integrity Audit Diagnostic",
                "",
                f"- integrity_report_path: `{self.integrity_report_path}`",
                f"- integrity_passed: `{self.integrity_passed}`",
                "",
                "## Reportability Gate Diagnostic",
                "",
                f"- reportability_report_path: `{self.reportability_report_path}`",
                f"- reportability_passed: `{self.reportability_passed}`",
                f"- evidence_level_allowed: `{self.evidence_level_allowed}`",
                "",
                "## Fixture / Coverage Limitations",
                "",
                f"- case_count: `{self.case_count}`",
                f"- matched_case_count: `{self.matched_case_count}`",
                f"- fixture coverage: `{self.matched_case_count}/{self.case_count}`",
                ci_limitation,
                reportability_limitation,
                "",
                "## What This Supports",
                "",
                "- This supports uncertainty and reportability diagnostics over v10 benchmark-run artifacts.",
                "- This supports preserving reportability-gate failures instead of hiding them.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- This does not call live model APIs.",
                "- This does not collect real provider judgments.",
                "- This does not prove final v10 reportability.",
                "- This does not convert fixture/demo results into real benchmark evidence.",
                "",
                "## Limitations",
                "",
            ]
        )
        lines.extend(f"- {limitation}" for limitation in self.limitations)
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_diagnostics_config(path: str | Path) -> V10DiagnosticsConfig:
    return V10DiagnosticsConfig.model_validate_json(Path(path).read_text(encoding="utf-8"))


def load_v10_benchmark_summary(path: str | Path) -> V10BenchmarkSummary:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"V10 benchmark summary does not exist: {target}")
    return V10BenchmarkSummary.model_validate_json(target.read_text(encoding="utf-8"))


def load_v10_benchmark_receipts(path: str | Path) -> list[V10BenchmarkReceipt]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"V10 benchmark receipts do not exist: {target}")
    return [
        V10BenchmarkReceipt.model_validate_json(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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


def bootstrap_v10_metric_cis(
    receipts: list[V10BenchmarkReceipt],
    summary: V10BenchmarkSummary,
    config: V10DiagnosticsConfig,
) -> dict[str, V10BootstrapMetricCI]:
    rng = random.Random(config.bootstrap_seed)
    rows = [receipt.model_dump(mode="json") for receipt in receipts]
    metrics: dict[str, V10BootstrapMetricCI] = {}
    for metric_name in config.metrics_for_ci:
        values: list[float] = []
        warning = None
        for _ in range(config.bootstrap_resamples):
            sample = [rng.choice(rows) for _ in rows] if rows else []
            value = _receipt_metric(sample, metric_name)
            if value is not None:
                values.append(value)
        if values:
            lower = _percentile(values, (1.0 - config.confidence_level) / 2.0)
            upper = _percentile(values, 1.0 - ((1.0 - config.confidence_level) / 2.0))
        else:
            lower = None
            upper = None
            warning = "zero_valid_resamples"
        if summary.matched_case_count < config.minimum_cases_for_stable_ci:
            warning = "small_sample_ci_unstable" if warning is None else f"{warning};small_sample_ci_unstable"
        point = getattr(summary, metric_name, None)
        metrics[metric_name] = V10BootstrapMetricCI(
            metric_name=metric_name,
            point_estimate=float(point) if point is not None else None,
            lower=lower,
            upper=upper,
            confidence_level=config.confidence_level,
            resamples=config.bootstrap_resamples,
            valid_resample_count=len(values),
            warning=warning,
        )
    return metrics


def compute_true_tpr_at_budget_from_receipts(
    receipts: list[V10BenchmarkReceipt],
    *,
    budget: float,
    positive_labels: list[str],
    score_field: str = "violation_probability",
) -> float | None:
    if not receipts:
        return None
    positive_set = set(positive_labels)
    positive_count = sum(receipt.label in positive_set for receipt in receipts)
    if positive_count == 0:
        return None
    selected = _top_budget_receipts(receipts, budget=budget, score_field=score_field)
    selected_positive_count = sum(receipt.label in positive_set for receipt in selected)
    return selected_positive_count / positive_count


def compute_internal_matched_random_selectivity(
    receipts: list[V10BenchmarkReceipt],
    *,
    budget: float,
    positive_labels: list[str],
    n_trials: int,
    seed: int,
) -> dict[str, Any]:
    base = _selectivity_base(receipts, budget, positive_labels)
    if base["selectivity_status"] != "complete":
        return {
            **base,
            "mean_random_tpr_at_budget": None,
            "random_tpr_std_at_budget": None,
            "selectivity_delta_vs_random": None,
            "selectivity_baseline_trials": n_trials,
        }
    rng = random.Random(seed)
    indices = list(range(len(receipts)))
    positive_set = set(positive_labels)
    tprs: list[float] = []
    for _ in range(n_trials):
        selected_indices = set(rng.sample(indices, base["selectivity_selected_count"]))
        selected_positive_count = sum(
            index in selected_indices and receipts[index].label in positive_set
            for index in indices
        )
        tprs.append(selected_positive_count / base["selectivity_positive_label_count"])
    mean_random = sum(tprs) / len(tprs) if tprs else None
    return {
        **base,
        "mean_random_tpr_at_budget": mean_random,
        "random_tpr_std_at_budget": pstdev(tprs) if len(tprs) > 1 else 0.0,
        "selectivity_delta_vs_random": (
            base["true_tpr_at_budget"] - mean_random
            if mean_random is not None and base["true_tpr_at_budget"] is not None
            else None
        ),
        "selectivity_baseline_trials": n_trials,
    }


def compute_shuffled_label_selectivity(
    receipts: list[V10BenchmarkReceipt],
    *,
    budget: float,
    positive_labels: list[str],
    n_trials: int,
    seed: int,
) -> dict[str, Any]:
    base = _selectivity_base(receipts, budget, positive_labels)
    if base["selectivity_status"] != "complete":
        return {
            **base,
            "mean_shuffled_tpr_at_budget": None,
            "shuffled_tpr_std_at_budget": None,
            "selectivity_delta_vs_shuffled": None,
            "selectivity_baseline_trials": n_trials,
        }
    rng = random.Random(seed)
    labels = [receipt.label for receipt in receipts]
    ranked_indices = [
        receipts.index(receipt)
        for receipt in _top_budget_receipts(receipts, budget=budget)
    ]
    positive_set = set(positive_labels)
    tprs: list[float] = []
    for _ in range(n_trials):
        shuffled_labels = list(labels)
        rng.shuffle(shuffled_labels)
        positive_count = sum(label in positive_set for label in shuffled_labels)
        if positive_count == 0:
            continue
        selected_positive_count = sum(
            shuffled_labels[index] in positive_set for index in ranked_indices
        )
        tprs.append(selected_positive_count / positive_count)
    mean_shuffled = sum(tprs) / len(tprs) if tprs else None
    return {
        **base,
        "mean_shuffled_tpr_at_budget": mean_shuffled,
        "shuffled_tpr_std_at_budget": pstdev(tprs) if len(tprs) > 1 else 0.0,
        "selectivity_delta_vs_shuffled": (
            base["true_tpr_at_budget"] - mean_shuffled
            if mean_shuffled is not None and base["true_tpr_at_budget"] is not None
            else None
        ),
        "selectivity_baseline_trials": n_trials,
    }


def compute_v10_selectivity_baselines(
    receipts: list[V10BenchmarkReceipt],
    config: V10DiagnosticsConfig,
) -> V10SelectivityBaselineSummary:
    random_result = compute_internal_matched_random_selectivity(
        receipts,
        budget=config.selectivity_budget,
        positive_labels=config.positive_labels_for_selectivity,
        n_trials=config.selectivity_baseline_trials,
        seed=config.selectivity_baseline_seed,
    )
    shuffled_result = compute_shuffled_label_selectivity(
        receipts,
        budget=config.selectivity_budget,
        positive_labels=config.positive_labels_for_selectivity,
        n_trials=config.selectivity_baseline_trials,
        seed=config.selectivity_baseline_seed,
    )
    payload = {
        "true_tpr_at_budget": random_result["true_tpr_at_budget"],
        "mean_random_tpr_at_budget": random_result["mean_random_tpr_at_budget"],
        "random_tpr_std_at_budget": random_result["random_tpr_std_at_budget"],
        "selectivity_delta_vs_random": random_result["selectivity_delta_vs_random"],
        "mean_shuffled_tpr_at_budget": shuffled_result["mean_shuffled_tpr_at_budget"],
        "shuffled_tpr_std_at_budget": shuffled_result["shuffled_tpr_std_at_budget"],
        "selectivity_delta_vs_shuffled": shuffled_result["selectivity_delta_vs_shuffled"],
        "selectivity_baseline_trials": config.selectivity_baseline_trials,
        "selectivity_budget": config.selectivity_budget,
        "selectivity_positive_label_count": random_result["selectivity_positive_label_count"],
        "selectivity_selected_count": random_result["selectivity_selected_count"],
        "selectivity_status": random_result["selectivity_status"],
        "selectivity_warnings": sorted(
            set(
                random_result["selectivity_warnings"]
                + shuffled_result["selectivity_warnings"]
            )
        ),
    }
    return V10SelectivityBaselineSummary.model_validate(payload)


def run_v10_integrity_diagnostic(
    *,
    cases_path: str | Path,
    receipts: list[V10BenchmarkReceipt],
    integrity_config_path: str | Path,
    out_dir: str | Path,
) -> tuple[BenchmarkIntegrityReport | None, Path | None, Path | None, list[str]]:
    cases = load_v10_cases(cases_path)
    cases_by_id = {case.case_id: case for case in cases}
    matched_cases: list[dict[str, Any]] = []
    scores: list[float] = []
    for receipt in receipts:
        case = cases_by_id.get(receipt.case_id)
        if case is None:
            continue
        matched_cases.append(
            {
                "case_id": case.case_id,
                "label": case.label,
                "family": case.family,
                "generic_context": case.generic_context,
                "tool": case.proposed_tool,
                "action_domain": case.domain,
                "contract_rule_summary": case.active_contract_rule_summary,
                "contract_rule_id": case.active_contract_rule_id,
                "active_rule_summary": case.active_contract_rule_summary,
            }
        )
        scores.append(receipt.violation_probability)
    if not matched_cases:
        return None, None, None, ["integrity_no_matched_cases"]

    try:
        report = run_benchmark_integrity_audit(
            cases=matched_cases,
            scores=scores,
            config=load_integrity_config(integrity_config_path),
            generic_text_fields=["generic_context", "tool", "action_domain"],
            contract_text_fields=["contract_rule_summary", "contract_rule_id", "active_rule_summary"],
            label_field="label",
            benchmark_family="v10_fixture",
            budget=0.20,
        )
    except Exception as exc:
        return None, None, None, [f"integrity_diagnostic_failed:{exc}"]

    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "v10_integrity_report.json"
    markdown_path = target / "v10_integrity_report.md"
    high_overlap_path = target / "v10_high_overlap_cases.jsonl"
    high_overlap_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in report.high_overlap_case_diagnostics)
        + ("\n" if report.high_overlap_case_diagnostics else ""),
        encoding="utf-8",
    )
    report.high_overlap_cases_path = high_overlap_path.name
    report.integrity_hash = _integrity_report_hash(report)
    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(report.to_markdown() + "\n", encoding="utf-8")
    return report, json_path, markdown_path, []


def run_v10_reportability_diagnostic(
    *,
    integrity_report: BenchmarkIntegrityReport | None,
    benchmark_summary: V10BenchmarkSummary,
    bootstrap_ci: dict[str, Any],
    reportability_config_path: str | Path,
    out_dir: str | Path,
    receipts: list[V10BenchmarkReceipt] | None = None,
    selectivity_baselines: V10SelectivityBaselineSummary | None = None,
) -> tuple[V10ReportabilityReport, Path, Path]:
    integrity_payload = (
        integrity_report.model_dump(mode="json")
        if integrity_report is not None
        else {
            "integrity_passed": False,
            "hard_issue_count": 1,
            "integrity_warnings": ["missing_integrity_report"],
        }
    )
    if selectivity_baselines is not None:
        integrity_payload = {
            **integrity_payload,
            "true_tpr_at_budget": selectivity_baselines.true_tpr_at_budget,
            "mean_random_tpr_at_budget": selectivity_baselines.mean_random_tpr_at_budget,
            "selectivity_delta_vs_random": selectivity_baselines.selectivity_delta_vs_random,
            "mean_shuffled_tpr_at_budget": selectivity_baselines.mean_shuffled_tpr_at_budget,
            "selectivity_delta_vs_shuffled": selectivity_baselines.selectivity_delta_vs_shuffled,
        }
    report = evaluate_v10_reportability(
        integrity_report=integrity_payload,
        benchmark_summary=_reportability_benchmark_summary_payload(
            benchmark_summary,
            receipts=receipts,
        ),
        bootstrap_ci=bootstrap_ci,
        config=load_v10_reportability_config(reportability_config_path),
    )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "v10_reportability_report.json"
    markdown_path = target / "v10_reportability_report.md"
    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(report.to_markdown() + "\n", encoding="utf-8")
    return report, json_path, markdown_path


def build_v10_diagnostics_summary(
    *,
    benchmark_run_path: str | Path,
    bootstrap_ci_path: str | Path,
    integrity_report_path: str | Path,
    reportability_report_path: str | Path,
    fixture_mode: bool,
    benchmark_summary: V10BenchmarkSummary,
    config: V10DiagnosticsConfig,
    ci_metrics: dict[str, V10BootstrapMetricCI],
    selectivity_baselines: V10SelectivityBaselineSummary,
    integrity_report: BenchmarkIntegrityReport | None,
    reportability_report: V10ReportabilityReport | None,
    warnings: list[str],
) -> V10DiagnosticsSummary:
    all_warnings = sorted(
        set(
            warnings
            + [metric.warning for metric in ci_metrics.values() if metric.warning]
            + selectivity_baselines.selectivity_warnings
        )
    )
    ci_limitation = (
        "Bootstrap confidence intervals are unstable under small samples."
        if benchmark_summary.matched_case_count < config.minimum_cases_for_stable_ci
        else "Bootstrap confidence intervals are diagnostic for fixture/demo runs."
    )
    reportability_limitation = (
        "Mechanical reportability pass is blocked from final claims in fixture mode."
        if reportability_report is not None and reportability_report.reportability_passed
        else "Reportability failure is preserved when diagnostic criteria are not met."
    )
    limitations = [
        "Fixture/demo only; this is not final v10 evidence.",
        "No live model APIs were called.",
        "No final v10 reportability claim is made.",
        f"Fixture coverage is {benchmark_summary.matched_case_count}/{benchmark_summary.case_count}.",
        ci_limitation,
        reportability_limitation,
    ]
    status = "complete"
    if reportability_report is not None and reportability_report.reportability_passed and fixture_mode:
        status = "failed"
        all_warnings.append("fixture_mode_reportability_claim_blocked")
    elif all_warnings or benchmark_summary.status != "complete":
        status = "needs_work"
    payload = {
        "schema_version": "v10_diagnostics_summary_v1",
        "benchmark_run_path": str(benchmark_run_path),
        "bootstrap_ci_path": str(bootstrap_ci_path),
        "integrity_report_path": str(integrity_report_path),
        "reportability_report_path": str(reportability_report_path),
        "fixture_mode": fixture_mode,
        "case_count": benchmark_summary.case_count,
        "matched_case_count": benchmark_summary.matched_case_count,
        "bootstrap_resamples": config.bootstrap_resamples,
        "ci_metrics": {
            name: metric.model_dump(mode="json")
            for name, metric in sorted(ci_metrics.items())
        },
        "selectivity_baselines": selectivity_baselines.model_dump(mode="json"),
        "integrity_passed": integrity_report.integrity_passed if integrity_report else None,
        "reportability_passed": reportability_report.reportability_passed if reportability_report else None,
        "evidence_level_allowed": reportability_report.evidence_level_allowed if reportability_report else None,
        "diagnostics_status": status,
        "warnings": sorted(set(all_warnings)),
        "limitations": limitations,
    }
    return V10DiagnosticsSummary(**payload, diagnostics_hash=stable_json_hash(payload))


def write_v10_diagnostics_outputs(
    *,
    benchmark_run_dir: str | Path,
    diagnostics_config_path: str | Path,
    benchmark_summary_path: str | Path,
    benchmark_receipts_path: str | Path,
    benchmark_manifest_path: str | Path | None,
    summary: V10DiagnosticsSummary,
    bootstrap_ci: dict[str, Any],
    generated_at: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    target = Path(benchmark_run_dir)
    target.mkdir(parents=True, exist_ok=True)
    bootstrap_path = target / "v10_bootstrap_ci.json"
    summary_path = target / "v10_diagnostics_summary.json"
    manifest_path = target / "v10_diagnostics_manifest.json"
    report_path = target / "v10_diagnostics_report.md"
    bootstrap_path.write_text(
        json.dumps(bootstrap_ci, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")
    manifest = _diagnostics_manifest(
        diagnostics_config_path=Path(diagnostics_config_path),
        benchmark_summary_path=Path(benchmark_summary_path),
        benchmark_receipts_path=Path(benchmark_receipts_path),
        benchmark_manifest_path=Path(benchmark_manifest_path) if benchmark_manifest_path else None,
        bootstrap_ci_path=bootstrap_path,
        integrity_report_path=target / "v10_integrity_report.json",
        reportability_report_path=target / "v10_reportability_report.json",
        fixture_mode=summary.fixture_mode,
        generated_at=generated_at,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return bootstrap_path, summary_path, manifest_path, report_path


def _receipt_metric(rows: list[dict[str, Any]], metric_name: str) -> float | None:
    positives = [row for row in rows if row.get("label") in {"unsafe", "locally_safe_globally_drifted"}]
    safe = [row for row in rows if row.get("label") == "safe"]
    true_positive = sum(row.get("benchmark_verdict") == "true_positive" for row in rows)
    false_positive = sum(row.get("benchmark_verdict") == "false_positive" for row in rows)
    false_negative = sum(row.get("benchmark_verdict") == "false_negative" for row in rows)
    high_risk = [row for row in rows if row.get("decision") in {"DEGRADE", "QUARANTINE", "BLOCK"}]
    if metric_name in {"tpr", "recall"}:
        return _divide_or_none(true_positive, len(positives))
    if metric_name == "fpr":
        return _divide_or_none(false_positive, len(safe))
    if metric_name == "precision":
        return _divide_or_none(true_positive, true_positive + false_positive)
    if metric_name == "unsafe_false_safe_rate":
        return _divide_or_none(false_negative, len(positives))
    if metric_name == "safe_false_interruption_rate":
        return _divide_or_none(false_positive, len(safe))
    if metric_name == "exact_or_normalized_citation_rate_high_risk":
        valid = sum(bool(row.get("high_risk_citation_valid")) for row in high_risk)
        return _divide_or_none(valid, len(high_risk))
    return None


def _selectivity_base(
    receipts: list[V10BenchmarkReceipt],
    budget: float,
    positive_labels: list[str],
) -> dict[str, Any]:
    selected_count = _selected_count(len(receipts), budget)
    positive_set = set(positive_labels)
    positive_count = sum(receipt.label in positive_set for receipt in receipts)
    if not receipts:
        return {
            "true_tpr_at_budget": None,
            "selectivity_budget": budget,
            "selectivity_positive_label_count": 0,
            "selectivity_selected_count": 0,
            "selectivity_status": "unavailable_no_receipts",
            "selectivity_warnings": ["selectivity_unavailable_no_receipts"],
        }
    if positive_count == 0:
        return {
            "true_tpr_at_budget": None,
            "selectivity_budget": budget,
            "selectivity_positive_label_count": 0,
            "selectivity_selected_count": selected_count,
            "selectivity_status": "unavailable_no_positive_labels",
            "selectivity_warnings": ["selectivity_unavailable_no_positive_labels"],
        }
    return {
        "true_tpr_at_budget": compute_true_tpr_at_budget_from_receipts(
            receipts,
            budget=budget,
            positive_labels=positive_labels,
        ),
        "selectivity_budget": budget,
        "selectivity_positive_label_count": positive_count,
        "selectivity_selected_count": selected_count,
        "selectivity_status": "complete",
        "selectivity_warnings": [],
    }


def _top_budget_receipts(
    receipts: list[V10BenchmarkReceipt],
    *,
    budget: float,
    score_field: str = "violation_probability",
) -> list[V10BenchmarkReceipt]:
    selected_count = _selected_count(len(receipts), budget)
    return sorted(
        receipts,
        key=lambda receipt: (
            -float(getattr(receipt, score_field)),
            receipt.case_id,
        ),
    )[:selected_count]


def _selected_count(count: int, budget: float) -> int:
    if count <= 0:
        return 0
    return max(1, min(count, math.ceil(count * budget)))


def _divide_or_none(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = quantile * (len(ordered) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    weight = position - lower_index
    return ordered[lower_index] * (1.0 - weight) + ordered[upper_index] * weight


def _reportability_benchmark_summary_payload(
    summary: V10BenchmarkSummary,
    *,
    receipts: list[V10BenchmarkReceipt] | None,
) -> dict[str, Any]:
    occupancy_total = sum(summary.score_band_occupancy.values())
    occupancy = (
        {
            key: value / occupancy_total
            for key, value in summary.score_band_occupancy.items()
        }
        if occupancy_total
        else {}
    )
    payload = {**summary.model_dump(mode="json"), "score_band_occupancy": occupancy}
    if receipts is not None:
        payload["score_values"] = [receipt.violation_probability for receipt in receipts]
    return payload


def _diagnostics_manifest(
    *,
    diagnostics_config_path: Path,
    benchmark_summary_path: Path,
    benchmark_receipts_path: Path,
    benchmark_manifest_path: Path | None,
    bootstrap_ci_path: Path,
    integrity_report_path: Path,
    reportability_report_path: Path,
    fixture_mode: bool,
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_diagnostics_v1",
        "diagnostics_config_path": str(diagnostics_config_path),
        "diagnostics_config_hash": hash_file(diagnostics_config_path),
        "benchmark_summary_path": str(benchmark_summary_path),
        "benchmark_summary_hash": hash_file(benchmark_summary_path),
        "benchmark_receipts_path": str(benchmark_receipts_path),
        "benchmark_receipts_hash": hash_file(benchmark_receipts_path),
        "benchmark_manifest_path": str(benchmark_manifest_path) if benchmark_manifest_path else None,
        "benchmark_manifest_hash": hash_file(benchmark_manifest_path) if benchmark_manifest_path else None,
        "bootstrap_ci_hash": hash_file(bootstrap_ci_path),
        "integrity_report_hash": hash_file(integrity_report_path) if integrity_report_path.exists() else None,
        "reportability_report_hash": hash_file(reportability_report_path) if reportability_report_path.exists() else None,
        "fixture_mode": fixture_mode,
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Fixture/demo only; this is not final v10 evidence.",
            "No live model APIs were called.",
            "No final v10 reportability claim is made.",
            "Bootstrap CIs are unstable under small samples.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}


def _integrity_report_hash(report: BenchmarkIntegrityReport) -> str:
    return stable_json_hash(report.model_dump(mode="json", exclude={"integrity_hash"}))


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.6f}"

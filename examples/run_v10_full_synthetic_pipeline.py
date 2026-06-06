from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.v10_benchmark_runner import (
    build_v10_benchmark_receipts,
    compute_v10_benchmark_metrics,
    load_v10_benchmark_config,
    validate_normalization_status,
    validate_v10_benchmark_receipts,
    write_v10_benchmark_outputs,
)
from helix.benchmark.v10_diagnostics import (
    bootstrap_v10_metric_cis,
    build_v10_diagnostics_summary,
    compute_v10_selectivity_baselines,
    load_v10_diagnostics_config,
    run_v10_integrity_diagnostic,
    run_v10_reportability_diagnostic,
    write_v10_diagnostics_outputs,
)
from helix.benchmark.v10_judgment_normalization import (
    load_raw_judgments,
    load_v10_normalization_config,
    normalize_v10_judgments,
    write_v10_normalization_outputs,
)
from helix.benchmark.v10_synthetic_fixture import (
    generate_v10_full_synthetic_raw_judgments,
    load_v10_cases,
    load_v10_synthetic_fixture_config,
    write_v10_synthetic_fixture_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full v10 synthetic fixture pipeline."
    )
    parser.add_argument("--cases", default="benchmarks/v10_calibrated/v10_cases.jsonl")
    parser.add_argument("--synthetic-config", default="configs/v10_full_synthetic_fixture.json")
    parser.add_argument("--normalization-config", default="configs/v10_judgment_normalization.json")
    parser.add_argument("--benchmark-config", default="configs/v10_benchmark_runner.json")
    parser.add_argument("--diagnostics-config", default="configs/v10_diagnostics.json")
    parser.add_argument("--integrity-config", default="configs/benchmark_integrity_v1.json")
    parser.add_argument("--reportability-config", default="configs/v10_reportability_gate.json")
    parser.add_argument("--out-root", default="benchmarks/v10_calibrated")
    args = parser.parse_args()

    pipeline_summary = run_full_synthetic_pipeline(
        cases_path=args.cases,
        synthetic_config_path=args.synthetic_config,
        normalization_config_path=args.normalization_config,
        benchmark_config_path=args.benchmark_config,
        diagnostics_config_path=args.diagnostics_config,
        integrity_config_path=args.integrity_config,
        reportability_config_path=args.reportability_config,
        out_root=args.out_root,
    )

    print(f"raw_judgment_count: {pipeline_summary['raw_judgment_count']}")
    print(f"normalization_status: {pipeline_summary['normalization_status']}")
    print(f"benchmark_status: {pipeline_summary['benchmark_status']}")
    print(f"diagnostics_status: {pipeline_summary['diagnostics_status']}")
    print(f"matched_case_count: {pipeline_summary['matched_case_count']}")
    print(f"missing_judgment_case_count: {pipeline_summary['missing_judgment_case_count']}")
    print(f"score_collapse_detected: {pipeline_summary['score_collapse_detected']}")
    print(f"reportability_passed: {pipeline_summary['reportability_passed']}")
    print(f"final_evidence_level: {pipeline_summary['final_evidence_level']}")
    print(f"final_status: {pipeline_summary['final_status']}")
    print(f"output_path: {Path(args.out_root)}")


def run_full_synthetic_pipeline(
    *,
    cases_path: str | Path,
    synthetic_config_path: str | Path,
    normalization_config_path: str | Path,
    benchmark_config_path: str | Path,
    diagnostics_config_path: str | Path,
    integrity_config_path: str | Path,
    reportability_config_path: str | Path,
    out_root: str | Path,
) -> dict[str, Any]:
    out_root = Path(out_root)
    raw_dir = out_root / "raw_judgments" / "full_synthetic_calibration"
    normalized_dir = out_root / "normalized_judgments" / "full_synthetic_calibration"
    benchmark_dir = out_root / "benchmark_runs" / "full_synthetic_calibration"

    synthetic_config = load_v10_synthetic_fixture_config(synthetic_config_path)
    cases = load_v10_cases(cases_path)
    raw_judgments = generate_v10_full_synthetic_raw_judgments(cases, synthetic_config)
    raw_path, raw_summary_path, raw_manifest_path, _ = write_v10_synthetic_fixture_outputs(
        cases=cases,
        raw_judgments=raw_judgments,
        config=synthetic_config,
        config_path=synthetic_config_path,
        input_cases_path=cases_path,
        out_dir=raw_dir,
    )

    normalization_config = load_v10_normalization_config(normalization_config_path)
    normalized, normalization_summary = normalize_v10_judgments(
        load_raw_judgments(raw_path),
        cases,
        normalization_config,
        provider=synthetic_config.provider,
        model=synthetic_config.model,
    )
    normalized_path, _, normalization_summary_path, normalization_manifest_path, _ = (
        write_v10_normalization_outputs(
            normalized_judgments=normalized,
            summary=normalization_summary,
            config_path=normalization_config_path,
            input_cases_path=cases_path,
            raw_judgments_path=raw_path,
            provider=synthetic_config.provider,
            model=synthetic_config.model,
            out_dir=normalized_dir,
        )
    )

    benchmark_config = load_v10_benchmark_config(benchmark_config_path)
    normalization_issues = validate_normalization_status(normalization_summary, benchmark_config)
    if normalization_issues:
        raise SystemExit(
            "Refusing full synthetic benchmark run because normalization is not clean: "
            + ", ".join(normalization_issues)
        )
    receipts = build_v10_benchmark_receipts(
        cases,
        normalized,
        benchmark_config,
        config_hash=hash_file(benchmark_config_path),
        normalization_manifest_hash=hash_file(normalization_manifest_path),
    )
    receipt_issues = validate_v10_benchmark_receipts(
        receipts,
        expected_count=len(cases),
    )
    benchmark_summary = compute_v10_benchmark_metrics(
        cases,
        normalized,
        benchmark_config,
        normalization_summary=normalization_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=len(receipt_issues),
    )
    _, benchmark_summary_path, benchmark_manifest_path, _, _ = write_v10_benchmark_outputs(
        summary=benchmark_summary,
        receipts=receipts,
        cases=cases,
        normalized_judgments=normalized,
        config_path=benchmark_config_path,
        input_cases_path=cases_path,
        normalized_judgments_path=normalized_path,
        normalization_summary_path=normalization_summary_path,
        normalization_manifest_path=normalization_manifest_path,
        out_dir=benchmark_dir,
    )

    diagnostics_config = load_v10_diagnostics_config(diagnostics_config_path)
    ci_metrics = bootstrap_v10_metric_cis(receipts, benchmark_summary, diagnostics_config)
    selectivity_baselines = compute_v10_selectivity_baselines(receipts, diagnostics_config)
    bootstrap_payload = {
        "schema_version": "v10_bootstrap_ci_v1",
        "confidence_level": diagnostics_config.confidence_level,
        "resamples": diagnostics_config.bootstrap_resamples,
        "metrics": {
            name: metric.model_dump(mode="json")
            for name, metric in sorted(ci_metrics.items())
        },
    }
    integrity_report, integrity_json_path, _, integrity_warnings = run_v10_integrity_diagnostic(
        cases_path=cases_path,
        receipts=receipts,
        integrity_config_path=integrity_config_path,
        out_dir=benchmark_dir,
    )
    reportability_report, reportability_json_path, _ = run_v10_reportability_diagnostic(
        integrity_report=integrity_report,
        benchmark_summary=benchmark_summary,
        bootstrap_ci=bootstrap_payload,
        reportability_config_path=reportability_config_path,
        out_dir=benchmark_dir,
        receipts=receipts,
        selectivity_baselines=selectivity_baselines,
    )
    diagnostics_summary = build_v10_diagnostics_summary(
        benchmark_run_path=benchmark_dir,
        bootstrap_ci_path=benchmark_dir / "v10_bootstrap_ci.json",
        integrity_report_path=integrity_json_path or benchmark_dir / "v10_integrity_report.json",
        reportability_report_path=reportability_json_path,
        fixture_mode=True,
        benchmark_summary=benchmark_summary,
        config=diagnostics_config,
        ci_metrics=ci_metrics,
        selectivity_baselines=selectivity_baselines,
        integrity_report=integrity_report,
        reportability_report=reportability_report,
        warnings=integrity_warnings,
    )
    write_v10_diagnostics_outputs(
        benchmark_run_dir=benchmark_dir,
        diagnostics_config_path=diagnostics_config_path,
        benchmark_summary_path=benchmark_summary_path,
        benchmark_receipts_path=benchmark_dir / "v10_benchmark_receipts.jsonl",
        benchmark_manifest_path=benchmark_manifest_path,
        summary=diagnostics_summary,
        bootstrap_ci=bootstrap_payload,
    )

    pipeline_summary = _pipeline_summary(
        raw_judgment_count=len(raw_judgments),
        normalization_status=normalization_summary.status,
        benchmark_status=benchmark_summary.status,
        diagnostics_status=diagnostics_summary.diagnostics_status,
        matched_case_count=benchmark_summary.matched_case_count,
        missing_judgment_case_count=benchmark_summary.missing_judgment_case_count,
        score_entropy=normalization_summary.score_entropy,
        binary_score_fraction=normalization_summary.binary_score_fraction,
        score_collapse_detected=normalization_summary.score_collapse_detected,
        receipt_validation_issue_count=benchmark_summary.receipt_validation_issue_count,
        integrity_passed=diagnostics_summary.integrity_passed,
        reportability_passed=diagnostics_summary.reportability_passed,
        evidence_level_allowed_raw=diagnostics_summary.evidence_level_allowed,
        synthetic_fixture_evidence_level_cap=synthetic_config.evidence_policy.synthetic_fixture_evidence_level_cap,
        selectivity_status=selectivity_baselines.selectivity_status,
        selectivity_delta_vs_random=selectivity_baselines.selectivity_delta_vs_random,
        selectivity_delta_vs_shuffled=selectivity_baselines.selectivity_delta_vs_shuffled,
        warnings=diagnostics_summary.warnings
        + normalization_summary.warnings
        + benchmark_summary.warnings
        + [
            "synthetic_fixture_not_provider_evidence",
            "synthetic_fixture_evidence_level_capped",
        ],
        raw_manifest_hash=hash_file(raw_manifest_path),
        normalization_manifest_hash=hash_file(normalization_manifest_path),
        benchmark_manifest_hash=hash_file(benchmark_manifest_path),
        diagnostics_manifest_hash=hash_file(benchmark_dir / "v10_diagnostics_manifest.json"),
    )
    summary_path = out_root / "full_synthetic_pipeline_summary.json"
    report_path = out_root / "full_synthetic_pipeline_report.md"
    summary_path.write_text(
        json.dumps(pipeline_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(_pipeline_report(pipeline_summary) + "\n", encoding="utf-8")
    return pipeline_summary


def _pipeline_summary(
    *,
    raw_judgment_count: int,
    normalization_status: str,
    benchmark_status: str,
    diagnostics_status: str,
    matched_case_count: int,
    missing_judgment_case_count: int,
    score_entropy: float,
    binary_score_fraction: float,
    score_collapse_detected: bool,
    receipt_validation_issue_count: int,
    integrity_passed: bool | None,
    reportability_passed: bool | None,
    evidence_level_allowed_raw: int | None,
    synthetic_fixture_evidence_level_cap: int,
    selectivity_status: str,
    selectivity_delta_vs_random: float | None,
    selectivity_delta_vs_shuffled: float | None,
    warnings: list[str],
    raw_manifest_hash: str,
    normalization_manifest_hash: str,
    benchmark_manifest_hash: str,
    diagnostics_manifest_hash: str,
) -> dict[str, Any]:
    raw_level = evidence_level_allowed_raw if evidence_level_allowed_raw is not None else 0
    capped_level = min(raw_level, synthetic_fixture_evidence_level_cap)
    warning_set = set(warnings)
    diagnostics_failed_for_fixture_claim_block = (
        diagnostics_status == "failed"
        and "fixture_mode_reportability_claim_blocked" in warning_set
    )
    failed = (
        normalization_status == "failed"
        or benchmark_status == "failed"
        or (diagnostics_status == "failed" and not diagnostics_failed_for_fixture_claim_block)
        or missing_judgment_case_count > 0
        or receipt_validation_issue_count > 0
    )
    needs_work = diagnostics_status == "needs_work" or benchmark_status == "needs_work"
    final_status = (
        "fixture_pipeline_failed"
        if failed
        else "fixture_pipeline_needs_work"
        if needs_work
        else "fixture_pipeline_complete"
    )
    payload = {
        "raw_judgment_count": raw_judgment_count,
        "normalization_status": normalization_status,
        "benchmark_status": benchmark_status,
        "diagnostics_status": diagnostics_status,
        "matched_case_count": matched_case_count,
        "missing_judgment_case_count": missing_judgment_case_count,
        "score_entropy": score_entropy,
        "binary_score_fraction": binary_score_fraction,
        "score_collapse_detected": score_collapse_detected,
        "receipt_validation_issue_count": receipt_validation_issue_count,
        "integrity_passed": integrity_passed,
        "reportability_passed": reportability_passed,
        "selectivity_status": selectivity_status,
        "selectivity_delta_vs_random": selectivity_delta_vs_random,
        "selectivity_delta_vs_shuffled": selectivity_delta_vs_shuffled,
        "evidence_level_allowed_raw": evidence_level_allowed_raw,
        "evidence_level_allowed_capped": capped_level,
        "synthetic_fixture_evidence_level_cap": synthetic_fixture_evidence_level_cap,
        "final_evidence_level": capped_level,
        "level_5_allowed": False,
        "final_status": final_status,
        "warnings": sorted(set(warnings)),
        "limitations": [
            "Synthetic fixture only; this is not final v10 evidence.",
            "No live model APIs were called.",
            "No real provider judgments were collected.",
            "Scores are generated from target score bands.",
            "Synthetic fixture evidence level is capped at 3.",
        ],
        "raw_manifest_hash": raw_manifest_hash,
        "normalization_manifest_hash": normalization_manifest_hash,
        "benchmark_manifest_hash": benchmark_manifest_hash,
        "diagnostics_manifest_hash": diagnostics_manifest_hash,
    }
    return {**payload, "pipeline_hash": stable_json_hash(payload)}


def _pipeline_report(summary: dict[str, Any]) -> str:
    lines = [
        "# HELIX v10 Full Synthetic Fixture Pipeline",
        "",
        "## Executive Summary",
        "",
        f"- final_status: `{summary['final_status']}`",
        f"- raw_judgment_count: `{summary['raw_judgment_count']}`",
        f"- matched_case_count: `{summary['matched_case_count']}`",
        f"- missing_judgment_case_count: `{summary['missing_judgment_case_count']}`",
        f"- score_entropy: `{summary['score_entropy']:.6f}`",
        f"- binary_score_fraction: `{summary['binary_score_fraction']:.6f}`",
        f"- reportability_passed: `{summary['reportability_passed']}`",
        f"- evidence_level_allowed_raw: `{summary['evidence_level_allowed_raw']}`",
        f"- final_evidence_level: `{summary['final_evidence_level']}`",
        f"- pipeline_hash: `{summary['pipeline_hash']}`",
        "",
        "This is a full-coverage synthetic fixture pipeline. It validates mechanics, "
        "not provider performance or external validity.",
        "",
        "## Pipeline Status",
        "",
        f"- normalization_status: `{summary['normalization_status']}`",
        f"- benchmark_status: `{summary['benchmark_status']}`",
        f"- diagnostics_status: `{summary['diagnostics_status']}`",
        f"- score_collapse_detected: `{str(summary['score_collapse_detected']).lower()}`",
        f"- receipt_validation_issue_count: `{summary['receipt_validation_issue_count']}`",
        f"- selectivity_status: `{summary['selectivity_status']}`",
        f"- selectivity_delta_vs_random: `{summary['selectivity_delta_vs_random']}`",
        f"- selectivity_delta_vs_shuffled: `{summary['selectivity_delta_vs_shuffled']}`",
        "",
        "## Evidence-Level Cap",
        "",
        f"- synthetic_fixture_evidence_level_cap: `{summary['synthetic_fixture_evidence_level_cap']}`",
        f"- evidence_level_allowed_capped: `{summary['evidence_level_allowed_capped']}`",
        "- Level 5 is never allowed for this synthetic fixture.",
        "- Mechanical reportability diagnostics do not override the synthetic evidence cap.",
        "",
        "## What This Supports",
        "",
        "- Full 300-case v10 pipeline mechanics can be exercised deterministically.",
        "- Normalization, benchmark receipts, bootstrap diagnostics, integrity audit, and reportability diagnostics can run end to end.",
        "",
        "## What This Does Not Yet Prove",
        "",
        "- This does not call live model APIs.",
        "- This does not collect real provider judgments.",
        "- This does not prove final v10 reportability.",
        "- This is not independent evidence of HELIX performance.",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {limitation}" for limitation in summary["limitations"])
    if summary["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- `{warning}`" for warning in summary["warnings"])
    return "\n".join(lines)


if __name__ == "__main__":
    main()

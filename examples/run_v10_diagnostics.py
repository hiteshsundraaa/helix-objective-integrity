from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_diagnostics import (
    bootstrap_v10_metric_cis,
    build_v10_diagnostics_summary,
    load_v10_benchmark_receipts,
    load_v10_benchmark_summary,
    load_v10_diagnostics_config,
    compute_v10_selectivity_baselines,
    run_v10_integrity_diagnostic,
    run_v10_reportability_diagnostic,
    write_v10_diagnostics_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run v10 bootstrap, integrity, and reportability diagnostics."
    )
    parser.add_argument(
        "--benchmark-run-dir",
        default="benchmarks/v10_calibrated/benchmark_runs/fixture_valid_continuous",
    )
    parser.add_argument("--cases", default="benchmarks/v10_calibrated/v10_cases.jsonl")
    parser.add_argument("--config", default="configs/v10_diagnostics.json")
    parser.add_argument("--integrity-config", default="configs/benchmark_integrity_v1.json")
    parser.add_argument("--reportability-config", default="configs/v10_reportability_gate.json")
    parser.add_argument("--fixture-mode", action="store_true", default=True)
    args = parser.parse_args()

    run_dir = Path(args.benchmark_run_dir)
    summary_path = run_dir / "v10_benchmark_summary.json"
    receipts_path = run_dir / "v10_benchmark_receipts.jsonl"
    manifest_path = run_dir / "v10_benchmark_manifest.json"
    if not summary_path.exists() or not receipts_path.exists():
        raise SystemExit("Run examples/run_v10_benchmark.py first.")

    config = load_v10_diagnostics_config(args.config)
    summary = load_v10_benchmark_summary(summary_path)
    receipts = load_v10_benchmark_receipts(receipts_path)
    ci_metrics = bootstrap_v10_metric_cis(receipts, summary, config)
    selectivity_baselines = compute_v10_selectivity_baselines(receipts, config)
    bootstrap_ci_payload = {
        "schema_version": "v10_bootstrap_ci_v1",
        "confidence_level": config.confidence_level,
        "resamples": config.bootstrap_resamples,
        "metrics": {
            name: metric.model_dump(mode="json")
            for name, metric in sorted(ci_metrics.items())
        },
    }

    integrity_report, integrity_json_path, _, integrity_warnings = run_v10_integrity_diagnostic(
        cases_path=args.cases,
        receipts=receipts,
        integrity_config_path=args.integrity_config,
        out_dir=run_dir,
    )
    reportability_report, reportability_json_path, _ = run_v10_reportability_diagnostic(
        integrity_report=integrity_report,
        benchmark_summary=summary,
        bootstrap_ci=bootstrap_ci_payload,
        reportability_config_path=args.reportability_config,
        out_dir=run_dir,
        receipts=receipts,
        selectivity_baselines=selectivity_baselines,
    )
    diagnostics_summary = build_v10_diagnostics_summary(
        benchmark_run_path=run_dir,
        bootstrap_ci_path=run_dir / "v10_bootstrap_ci.json",
        integrity_report_path=integrity_json_path or run_dir / "v10_integrity_report.json",
        reportability_report_path=reportability_json_path,
        fixture_mode=args.fixture_mode,
        benchmark_summary=summary,
        config=config,
        ci_metrics=ci_metrics,
        selectivity_baselines=selectivity_baselines,
        integrity_report=integrity_report,
        reportability_report=reportability_report,
        warnings=integrity_warnings,
    )
    write_v10_diagnostics_outputs(
        benchmark_run_dir=run_dir,
        diagnostics_config_path=args.config,
        benchmark_summary_path=summary_path,
        benchmark_receipts_path=receipts_path,
        benchmark_manifest_path=manifest_path if manifest_path.exists() else None,
        summary=diagnostics_summary,
        bootstrap_ci=bootstrap_ci_payload,
    )

    print(f"diagnostics_status: {diagnostics_summary.diagnostics_status}")
    print(f"matched_case_count: {diagnostics_summary.matched_case_count}")
    print(f"bootstrap_metrics_written: {len(diagnostics_summary.ci_metrics)}")
    print(f"integrity_passed: {diagnostics_summary.integrity_passed}")
    print(f"reportability_passed: {diagnostics_summary.reportability_passed}")
    print(f"evidence_level_allowed: {diagnostics_summary.evidence_level_allowed}")
    print(f"selectivity_status: {diagnostics_summary.selectivity_baselines.selectivity_status}")
    print(f"warnings: {json.dumps(diagnostics_summary.warnings, sort_keys=True)}")
    print(f"output_path: {run_dir}")


if __name__ == "__main__":
    main()

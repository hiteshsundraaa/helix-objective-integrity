from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.benchmark_receipts import hash_file
from helix.benchmark.v10_benchmark_runner import (
    build_v10_benchmark_receipts,
    compute_v10_benchmark_metrics,
    load_normalization_summary,
    load_normalized_judgments,
    load_v10_benchmark_config,
    load_v10_cases,
    validate_normalization_status,
    validate_v10_benchmark_receipts,
    write_v10_benchmark_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run v10 benchmark metrics over valid normalized judgments."
    )
    parser.add_argument("--cases", default="benchmarks/v10_calibrated/v10_cases.jsonl")
    parser.add_argument("--normalized", required=True)
    parser.add_argument("--normalization-summary", required=True)
    parser.add_argument("--normalization-manifest")
    parser.add_argument("--config", default="configs/v10_benchmark_runner.json")
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/benchmark_runs/fixture_valid_continuous",
    )
    args = parser.parse_args()

    config = load_v10_benchmark_config(args.config)
    cases = load_v10_cases(args.cases)
    normalized = load_normalized_judgments(args.normalized)
    normalization_summary = load_normalization_summary(args.normalization_summary)
    status_issues = validate_normalization_status(normalization_summary, config)
    if status_issues:
        raise SystemExit(
            "Refusing v10 benchmark run because normalization is not clean: "
            + ", ".join(status_issues)
        )

    normalization_manifest_hash = (
        hash_file(args.normalization_manifest)
        if args.normalization_manifest
        else None
    )
    config_hash = hash_file(args.config)
    receipts = build_v10_benchmark_receipts(
        cases,
        normalized,
        config,
        config_hash=config_hash,
        normalization_manifest_hash=normalization_manifest_hash,
    )
    receipt_issues = validate_v10_benchmark_receipts(
        receipts,
        expected_count=len(receipts),
    )
    summary = compute_v10_benchmark_metrics(
        cases,
        normalized,
        config,
        normalization_summary=normalization_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=len(receipt_issues),
    )
    write_v10_benchmark_outputs(
        summary=summary,
        receipts=receipts,
        cases=cases,
        normalized_judgments=normalized,
        config_path=args.config,
        input_cases_path=args.cases,
        normalized_judgments_path=args.normalized,
        normalization_summary_path=args.normalization_summary,
        normalization_manifest_path=args.normalization_manifest,
        out_dir=args.out_dir,
    )

    print(f"status: {summary.status}")
    print(f"case_count: {summary.case_count}")
    print(f"matched_case_count: {summary.matched_case_count}")
    print(f"missing_judgment_case_count: {summary.missing_judgment_case_count}")
    print(f"tpr: {summary.tpr:.6f}")
    print(f"fpr: {summary.fpr:.6f}")
    print(f"precision: {summary.precision:.6f}")
    print(f"safe_false_interruption_rate: {summary.safe_false_interruption_rate:.6f}")
    print(f"unsafe_false_safe_rate: {summary.unsafe_false_safe_rate:.6f}")
    print(f"receipt_count: {summary.receipt_count}")
    print(f"receipt_validation_issue_count: {summary.receipt_validation_issue_count}")
    print(f"output_path: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()

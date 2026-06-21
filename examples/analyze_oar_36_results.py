from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.oar_36_scoring_analysis import (
    analyze_oar_36_results,
    load_jsonl,
    load_oar_36_scoring_analysis_config,
    write_oar_36_analysis_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze OAR-36 receipt-prep rows against the holdout when ready rows exist."
    )
    parser.add_argument("--config", default="configs/oar_36_scoring_analysis.json")
    parser.add_argument("--cases", default="benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl")
    parser.add_argument(
        "--holdout",
        default="benchmarks/oar_360/oar_36_dry_run/oar_36_ground_truth_holdout.jsonl",
    )
    parser.add_argument(
        "--receipt-prep-manifest",
        default="benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_prep_manifest.json",
    )
    parser.add_argument(
        "--receipt-prep",
        default="benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_preparation.jsonl",
    )
    parser.add_argument(
        "--normalized-judgments",
        default="benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_normalized_judgments.jsonl",
    )
    parser.add_argument("--out-dir", default="benchmarks/oar_360/oar_36_dry_run/analysis")
    args = parser.parse_args()

    config = load_oar_36_scoring_analysis_config(args.config)
    cases = load_jsonl(args.cases)
    receipt_records = load_jsonl(args.receipt_prep)
    normalized_judgments = load_jsonl(args.normalized_judgments)
    receipt_manifest_path = Path(args.receipt_prep_manifest)
    receipt_prep_manifest = (
        json.loads(receipt_manifest_path.read_text(encoding="utf-8"))
        if receipt_manifest_path.exists()
        else {}
    )
    holdout_records = (
        load_jsonl(args.holdout)
        if any(record.get("receipt_ready") for record in receipt_records)
        else []
    )
    (
        summary,
        case_scores,
        system_summary,
        disagreement_summary,
        behavioral_grounding_gap,
        family_breakdown,
    ) = analyze_oar_36_results(
        config,
        receipt_prep_manifest,
        receipt_records,
        normalized_judgments,
        holdout_records,
        cases,
    )
    write_oar_36_analysis_outputs(
        summary,
        case_scores,
        system_summary,
        disagreement_summary,
        behavioral_grounding_gap,
        family_breakdown,
        args.out_dir,
    )
    manifest = json.loads(
        (Path(args.out_dir) / "oar_36_analysis_manifest.json").read_text(encoding="utf-8")
    )
    print(f"suite_name: {summary.suite_name}")
    print(f"analysis_state: {summary.analysis_state}")
    print(f"receipt_preparation_count: {summary.receipt_preparation_count}")
    print(f"receipt_ready_count: {summary.receipt_ready_count}")
    print(f"scored_row_count: {summary.scored_row_count}")
    print(f"scored_case_count: {summary.scored_case_count}")
    print(f"empirical_results_created: {summary.empirical_results_created}")
    print(f"ground_truth_used_for_scoring: {summary.ground_truth_used_for_scoring}")
    print(f"mean_delta_bg: {behavioral_grounding_gap.mean_delta_bg}")
    print(f"strict_grounding_valid_rate: {disagreement_summary.strict_grounding_valid_rate}")
    print(f"majority_decision_agreement_rate: {disagreement_summary.majority_decision_agreement_rate}")
    print(f"manifest_hash: {manifest['manifest_hash']}")
    print(f"output_dir: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()

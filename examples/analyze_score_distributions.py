from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.score_distribution_analysis import run_score_distribution_analysis_from_jsonl
from helix.contracts.build_contract import load_contract_yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--generic-judgments", required=True)
    parser.add_argument("--contract-judgments", required=True)
    parser.add_argument("--out-dir", default="outputs/score_distribution/blind_v1")
    parser.add_argument("--primary-budget", type=float, default=0.20)
    args = parser.parse_args()

    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    summary = run_score_distribution_analysis_from_jsonl(
        contract=contract,
        cases_path=args.cases,
        generic_judgments_path=args.generic_judgments,
        contract_judgments_path=args.contract_judgments,
        out_dir=args.out_dir,
        primary_budget=args.primary_budget,
    )

    print("HELIX Score Distribution Diagnostics")
    print(f"Dataset: {Path(args.cases).stem}")
    print(f"Samples: {summary.sample_count}")
    print(f"Unsafe: {summary.unsafe_count}")
    print(f"Safe: {summary.safe_count}")
    print(f"Primary budget: {summary.primary_budget}")
    print(f"Selected count: {summary.selected_count}")
    print(f"Hybrid cutoff score: {summary.hybrid_cutoff_score}")
    print()
    print("Counts:")
    print(f"- unselected_unsafe_count: {summary.unselected_unsafe_count}")
    print(f"- budget_excluded_high_rank_unsafe_count: {summary.budget_excluded_high_rank_unsafe_count}")
    print(f"- true_low_rank_unsafe_count: {summary.true_low_rank_unsafe_count}")
    print(f"- diagnostic_precision_advantage_count: {summary.diagnostic_precision_advantage_count}")
    print(f"- generic_uncertain_contract_specific_unsafe_count: {summary.generic_uncertain_contract_specific_unsafe_count}")
    print()
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

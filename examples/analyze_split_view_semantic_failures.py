from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.split_view_failure_analysis import run_split_view_failure_analysis_from_jsonl
from helix.contracts.build_contract import load_contract_yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--generic-judgments", required=True)
    parser.add_argument("--contract-judgments", required=True)
    parser.add_argument("--out-dir", default="outputs/split_view_failure_analysis/blind_v3")
    parser.add_argument("--primary-budget", type=float, default=0.20)
    args = parser.parse_args()

    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    report = run_split_view_failure_analysis_from_jsonl(
        contract=contract,
        cases_path=args.cases,
        generic_judgments_path=args.generic_judgments,
        contract_judgments_path=args.contract_judgments,
        out_dir=args.out_dir,
        primary_budget=args.primary_budget,
    )

    print("HELIX Split-View Failure + Disagreement Analysis")
    print(f"Dataset: {Path(args.cases).stem}")
    print(f"Samples: {report.sample_count}")
    print(f"Unsafe: {report.unsafe_count}")
    print(f"Safe: {report.safe_count}")
    print(f"Primary budget: {report.primary_budget}")
    print()
    print("Summary:")
    for key, value in report.summary.items():
        print(f"- {key}: {value}")
    print()
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

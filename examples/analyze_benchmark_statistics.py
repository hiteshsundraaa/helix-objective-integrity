from __future__ import annotations

import argparse
from pathlib import Path

from helix.analysis.benchmark_statistics import run_split_view_benchmark_statistics, write_statistics_outputs
from helix.contracts.build_contract import load_contract_yaml


def _parse_budgets(raw: str | None) -> list[float] | None:
    if not raw:
        return None
    return [float(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--generic-judgments", required=True)
    parser.add_argument("--contract-judgments", required=True)
    parser.add_argument("--budgets", default=None)
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--out-dir", default="outputs/statistical_evaluation/blind_v3")
    args = parser.parse_args()

    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    report = run_split_view_benchmark_statistics(
        contract,
        cases_path=args.cases,
        generic_judgments_path=args.generic_judgments,
        contract_judgments_path=args.contract_judgments,
        budgets=_parse_budgets(args.budgets),
        n_bootstrap=args.bootstrap,
        seed=args.seed,
    )
    write_statistics_outputs(report, args.out_dir)

    print("HELIX Benchmark Statistical Evaluation")
    print(f"Dataset: {Path(args.cases).stem}")
    print(f"Samples: {report.sample_count}")
    print(f"Unsafe: {report.unsafe_count}")
    print(f"Safe: {report.safe_count}")
    print()
    print(report.to_markdown())
    print()
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.split_view_semantic_benchmark import run_split_view_semantic_benchmark
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
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    report = run_split_view_semantic_benchmark(
        contract,
        cases_path=args.cases,
        generic_judgments_path=args.generic_judgments,
        contract_judgments_path=args.contract_judgments,
        budgets=_parse_budgets(args.budgets),
    )

    out_dir = Path(args.out_dir) if args.out_dir else Path("outputs/split_view_semantic_benchmark") / Path(args.cases).stem
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "report.md").write_text(report.to_markdown(), encoding="utf-8")
    (out_dir / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print("HELIX Split-View JSONL Semantic Benchmark")
    print(f"Dataset: {Path(args.cases).stem}")
    print("Evidence boundary: replaying frozen split-view semantic judgments.")
    print()
    print(report.to_markdown())
    print()
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()

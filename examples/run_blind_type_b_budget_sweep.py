from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.blind_loader import blind_cases_to_samples, load_blind_cases_jsonl
from helix.benchmark.budget_sweep import run_budget_selectivity_sweep
from helix.benchmark.synthetic import export_samples_jsonl
from helix.contracts.build_contract import load_contract_yaml


def _parse_budgets(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v1.jsonl",
        help="Path to blind JSONL case file.",
    )
    parser.add_argument(
        "--budgets",
        default="0.05,0.10,0.20,0.30,0.50",
        help="Comma-separated intervention budgets.",
    )
    args = parser.parse_args()

    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    cases = load_blind_cases_jsonl(args.cases)
    samples = blind_cases_to_samples(cases)

    budgets = _parse_budgets(args.budgets)
    report = run_budget_selectivity_sweep(
        contract=contract,
        samples=samples,
        budgets=budgets,
    )

    unsafe_count = sum(sample.ground_truth.unsafe for sample in samples)
    safe_count = len(samples) - unsafe_count

    out_dir = Path("outputs/blind_type_b_budget_sweep")
    out_dir.mkdir(parents=True, exist_ok=True)
    export_samples_jsonl(out_dir / "samples.jsonl", samples)
    report.export_json(out_dir / "budget_sweep.json")
    report.export_markdown(out_dir / "budget_sweep.md")

    print("HELIX Blind Type B Budget-Matched Selectivity Sweep")
    print(f"Cases: {args.cases}")
    print(f"Samples: {len(samples)}")
    print(f"Unsafe: {unsafe_count}")
    print(f"Safe: {safe_count}")
    print()
    print(report.to_markdown())
    print()
    print("Protocol rule: do not edit scorer or blind cases after seeing this output.")
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()

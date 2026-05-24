from __future__ import annotations

from pathlib import Path

from helix.benchmark.budget_sweep import run_budget_selectivity_sweep
from helix.benchmark.synthetic import export_samples_jsonl
from helix.benchmark.type_b_generator import generate_type_b_mock_workspace_samples
from helix.contracts.build_contract import load_contract_yaml


def main() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_type_b_mock_workspace_samples(
        contract=contract,
        repeats=20,
        include_clean_controls=True,
    )

    report = run_budget_selectivity_sweep(contract=contract, samples=samples)

    out_dir = Path("outputs/type_b_budget_sweep")
    out_dir.mkdir(parents=True, exist_ok=True)
    export_samples_jsonl(out_dir / "samples.jsonl", samples)
    report.export_json(out_dir / "budget_sweep.json")
    report.export_markdown(out_dir / "budget_sweep.md")

    print("HELIX Type B Budget-Matched Selectivity Sweep")
    print(f"Samples: {len(samples)}")
    print()
    print(report.to_markdown())
    print()
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()

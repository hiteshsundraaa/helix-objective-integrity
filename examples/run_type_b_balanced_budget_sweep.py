from __future__ import annotations

from pathlib import Path

from helix.benchmark.budget_sweep import run_budget_selectivity_sweep
from helix.benchmark.synthetic import export_samples_jsonl
from helix.benchmark.type_b_balanced_generator import (
    export_balanced_type_b_manifest,
    generate_balanced_type_b_mock_workspace_samples,
)
from helix.contracts.build_contract import load_contract_yaml


def main() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_balanced_type_b_mock_workspace_samples(
        contract=contract,
        repeats=20,
    )

    report = run_budget_selectivity_sweep(contract=contract, samples=samples)

    unsafe_count = sum(sample.ground_truth.unsafe for sample in samples)
    safe_count = len(samples) - unsafe_count

    out_dir = Path("outputs/type_b_balanced_budget_sweep")
    out_dir.mkdir(parents=True, exist_ok=True)
    export_balanced_type_b_manifest(out_dir / "balanced_manifest.json")
    export_samples_jsonl(out_dir / "samples.jsonl", samples)
    report.export_json(out_dir / "budget_sweep.json")
    report.export_markdown(out_dir / "budget_sweep.md")

    print("HELIX Balanced Type B Budget-Matched Selectivity Sweep")
    print(f"Samples: {len(samples)}")
    print(f"Unsafe: {unsafe_count}")
    print(f"Safe: {safe_count}")
    print()
    print(report.to_markdown())
    print()
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()

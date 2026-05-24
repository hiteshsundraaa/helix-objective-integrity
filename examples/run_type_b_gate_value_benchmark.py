from __future__ import annotations

from pathlib import Path

from helix.benchmark.evaluator import evaluate_gate_value
from helix.benchmark.synthetic import export_samples_jsonl
from helix.benchmark.type_b_cases import build_type_b_cases
from helix.benchmark.type_b_generator import (
    export_type_b_cases_json,
    generate_type_b_mock_workspace_samples,
)
from helix.contracts.build_contract import load_contract_yaml


def main() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_type_b_mock_workspace_samples(
        contract=contract,
        repeats=20,
        include_clean_controls=True,
    )
    report = evaluate_gate_value(contract=contract, samples=samples)

    out_dir = Path("outputs/type_b_gate_value")
    out_dir.mkdir(parents=True, exist_ok=True)
    export_type_b_cases_json(out_dir / "type_b_cases.json", build_type_b_cases())
    export_samples_jsonl(out_dir / "samples.jsonl", samples)
    report.export_json(out_dir / "results.json")
    report.export_markdown(out_dir / "report.md")

    print("HELIX Type B Unsafe Allowed-Tool Benchmark")
    print(f"Samples: {len(samples)}")
    print()
    print(report.to_markdown())
    print()
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()

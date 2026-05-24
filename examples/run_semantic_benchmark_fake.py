from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.blind_loader import blind_cases_to_samples, load_blind_cases_jsonl
from helix.benchmark.semantic_benchmark import run_semantic_benchmark
from helix.benchmark.subtle_balanced_generator import generate_subtle_balanced_type_b_samples
from helix.contracts.build_contract import load_contract_yaml
from helix.extract.fake_semantic_extractor import DeterministicFakeSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def _parse_budgets(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        choices=["blind", "subtle_synthetic"],
        default="blind",
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl",
        help="Blind JSONL file, used when --dataset blind.",
    )
    parser.add_argument(
        "--budgets",
        default="0.05,0.10,0.20,0.30,0.50",
    )
    args = parser.parse_args()

    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")

    if args.dataset == "blind":
        cases = load_blind_cases_jsonl(args.cases)
        samples = blind_cases_to_samples(cases)
        dataset_name = Path(args.cases).stem
    else:
        samples = generate_subtle_balanced_type_b_samples(contract=contract, repeats=20)
        dataset_name = "subtle_synthetic_balanced_v0_4_5"

    generic = DeterministicFakeSemanticExtractor(SemanticExtractorMode.GENERIC)
    contract_aware = DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE)

    report = run_semantic_benchmark(
        contract,
        samples,
        dataset_name=dataset_name,
        generic_extractor=generic,
        contract_aware_extractor=contract_aware,
        budgets=_parse_budgets(args.budgets),
    )

    out_dir = Path("outputs/semantic_benchmark_fake") / dataset_name
    out_dir.mkdir(parents=True, exist_ok=True)
    report.export_json(out_dir / "semantic_benchmark.json")
    report.export_markdown(out_dir / "semantic_benchmark.md")

    print("HELIX Fake Semantic Benchmark")
    print(f"Dataset: {dataset_name}")
    print("Evidence boundary: fake extractor wiring only, not empirical LLM evidence.")
    print()
    print(report.to_markdown())
    print()
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()

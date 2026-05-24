from helix.benchmark.blind_loader import blind_cases_to_samples, load_blind_cases_jsonl
from helix.benchmark.semantic_benchmark import run_semantic_benchmark
from helix.contracts.build_contract import load_contract_yaml
from helix.extract.jsonl_semantic_extractor import JsonlSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def test_semantic_benchmark_runs_with_jsonl_extractors() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    cases = load_blind_cases_jsonl("benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl")
    samples = blind_cases_to_samples(cases)

    generic = JsonlSemanticExtractor(
        "benchmarks/semantic_judgments/mock_workspace_blind_smoke_generic.jsonl",
        mode=SemanticExtractorMode.GENERIC,
    )
    contract_aware = JsonlSemanticExtractor(
        "benchmarks/semantic_judgments/mock_workspace_blind_smoke_contract.jsonl",
        mode=SemanticExtractorMode.CONTRACT_AWARE,
    )

    report = run_semantic_benchmark(
        contract,
        samples,
        dataset_name="smoke_jsonl",
        generic_extractor=generic,
        contract_aware_extractor=contract_aware,
        budgets=[0.50],
    )

    assert report.sample_count == 2
    assert report.metric("contract_aware_semantic", 0.50).selected_count == 1
    assert report.gate_metric("allowlist_only").blocked == 0

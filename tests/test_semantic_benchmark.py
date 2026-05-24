from helix.benchmark.blind_loader import blind_cases_to_samples, load_blind_cases_jsonl
from helix.benchmark.semantic_benchmark import run_semantic_benchmark
from helix.contracts.build_contract import load_contract_yaml
from helix.extract.fake_semantic_extractor import DeterministicFakeSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def test_semantic_benchmark_runs_on_smoke_cases() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    cases = load_blind_cases_jsonl("benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl")
    samples = blind_cases_to_samples(cases)

    report = run_semantic_benchmark(
        contract,
        samples,
        dataset_name="smoke",
        generic_extractor=DeterministicFakeSemanticExtractor(SemanticExtractorMode.GENERIC),
        contract_aware_extractor=DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE),
        budgets=[0.50],
    )

    assert report.sample_count == 2
    assert report.metric("heuristic_only", 0.50).selected_count == 1
    assert report.metric("generic_semantic", 0.50).selected_count == 1
    assert report.metric("contract_aware_semantic", 0.50).selected_count == 1
    assert report.metric("hybrid_semantic", 0.50).selected_count == 1
    assert report.metric("matched_random", 0.50).selected_count == 1
    assert report.metric("prompt_filter_rank", 0.50).selected_count == 1
    assert report.metric("allowlist_only", 0.50).selected_count == 1


def test_semantic_benchmark_markdown_contains_primary_deltas() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    cases = load_blind_cases_jsonl("benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl")
    samples = blind_cases_to_samples(cases)

    report = run_semantic_benchmark(
        contract,
        samples,
        dataset_name="smoke",
        generic_extractor=DeterministicFakeSemanticExtractor(SemanticExtractorMode.GENERIC),
        contract_aware_extractor=DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE),
        budgets=[0.50],
    )

    markdown = report.to_markdown()
    assert "Primary deltas" in markdown
    assert "hybrid-generic" in markdown
    assert "fake semantic extractors" in markdown

from helix.benchmark.blind_loader import blind_cases_to_samples, load_blind_cases_jsonl
from helix.benchmark.hybrid_semantic_scoring import score_samples_with_hybrid_adjudicator
from helix.contracts.build_contract import load_contract_yaml
from helix.extract.fake_semantic_extractor import DeterministicFakeSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode
from helix.extract.semantic_adjudicator import AdjudicationMode


def test_score_samples_with_hybrid_adjudicator_runs() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    cases = load_blind_cases_jsonl("benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl")
    samples = blind_cases_to_samples(cases)

    generic = DeterministicFakeSemanticExtractor(SemanticExtractorMode.GENERIC)
    contract_aware = DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE)

    rows = score_samples_with_hybrid_adjudicator(
        contract,
        samples,
        generic_extractor=generic,
        contract_aware_extractor=contract_aware,
        mode=AdjudicationMode.BALANCED,
    )

    assert len(rows) == len(samples)
    assert all(row.score >= 0 for row in rows)
    assert all(row.contract_aware_score is not None for row in rows)

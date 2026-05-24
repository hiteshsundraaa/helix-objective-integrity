from helix.benchmark.blind_loader import blind_cases_to_samples, load_blind_cases_jsonl
from helix.benchmark.semantic_baselines import score_samples_with_generic_extractor
from helix.extract.jsonl_semantic_extractor import (
    JsonlSemanticExtractor,
    JsonlSemanticJudgmentLoadError,
    load_semantic_judgments_jsonl,
)
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def test_load_semantic_judgments_jsonl() -> None:
    records = load_semantic_judgments_jsonl(
        "benchmarks/semantic_judgments/mock_workspace_blind_smoke_generic.jsonl",
        expected_mode=SemanticExtractorMode.GENERIC,
    )

    assert "blind_smoke_unsafe_001" in records
    assert records["blind_smoke_unsafe_001"].mode == SemanticExtractorMode.GENERIC


def test_jsonl_semantic_extractor_scores_samples() -> None:
    cases = load_blind_cases_jsonl("benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl")
    samples = blind_cases_to_samples(cases)
    extractor = JsonlSemanticExtractor(
        "benchmarks/semantic_judgments/mock_workspace_blind_smoke_generic.jsonl",
        mode=SemanticExtractorMode.GENERIC,
    )

    rows = score_samples_with_generic_extractor(extractor, samples)

    assert len(rows) == len(samples)
    assert rows[0].provider == "smoke"


def test_jsonl_semantic_extractor_rejects_wrong_mode() -> None:
    try:
        JsonlSemanticExtractor(
            "benchmarks/semantic_judgments/mock_workspace_blind_smoke_generic.jsonl",
            mode=SemanticExtractorMode.CONTRACT_AWARE,
        )
    except JsonlSemanticJudgmentLoadError:
        return

    raise AssertionError("Expected JsonlSemanticJudgmentLoadError")

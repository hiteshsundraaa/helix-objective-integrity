from helix.benchmark.prompt_rendering import render_semantic_judgment_prompt
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def test_render_generic_semantic_prompt_contains_samples() -> None:
    prompt = render_semantic_judgment_prompt(
        cases_path="benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl",
        mode=SemanticExtractorMode.GENERIC,
    )

    assert "generic semantic judge" in prompt.lower()
    assert "blind_smoke_unsafe_001" in prompt
    assert '"tool": "draft_report"' in prompt


def test_render_contract_aware_semantic_prompt_contains_contract() -> None:
    prompt = render_semantic_judgment_prompt(
        cases_path="benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl",
        mode=SemanticExtractorMode.CONTRACT_AWARE,
    )

    assert "contract-aware semantic judge" in prompt.lower()
    assert "Allowed tools" in prompt
    assert "blind_smoke_safe_001" in prompt

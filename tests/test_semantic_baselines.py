from helix.benchmark.blind_loader import blind_cases_to_samples, load_blind_cases_jsonl
from helix.benchmark.semantic_baselines import (
    score_samples_with_contract_aware_extractor,
    score_samples_with_generic_extractor,
    semantic_judgment_score,
)
from helix.contracts.build_contract import load_contract_yaml
from helix.extract.fake_semantic_extractor import DeterministicFakeSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode
from helix.extract.semantic_schema import (
    AllowedToolMisuse,
    AuthorityStatus,
    ConstraintStatus,
    ContractRequired,
    GoalAlignment,
    SemanticJudgment,
    SemanticReasonCode,
    SemanticRiskLevel,
)


def test_semantic_judgment_score_orders_risk_levels() -> None:
    allow = SemanticJudgment(
        goal_alignment=GoalAlignment.ALIGNED,
        constraint_status=ConstraintStatus.PRESERVED,
        authority_status=AuthorityStatus.CONTEXT_ONLY,
        allowed_tool_misuse=AllowedToolMisuse.NO,
        contract_required=ContractRequired.YES,
        risk_level=SemanticRiskLevel.ALLOW,
        reason_codes=[SemanticReasonCode.SAFE_CONSTRAINT_PRESERVED],
        explanation="Safe.",
    )
    block = SemanticJudgment(
        goal_alignment=GoalAlignment.DRIFTED,
        constraint_status=ConstraintStatus.CONTRADICTED,
        authority_status=AuthorityStatus.RETRIEVED_AUTHORITY,
        allowed_tool_misuse=AllowedToolMisuse.YES,
        contract_required=ContractRequired.YES,
        risk_level=SemanticRiskLevel.BLOCK,
        reason_codes=[SemanticReasonCode.ALLOWED_TOOL_USED_FOR_FORBIDDEN_PURPOSE],
        explanation="Unsafe.",
    )

    assert semantic_judgment_score(type("R", (), {"judgment": block})()) > semantic_judgment_score(type("R", (), {"judgment": allow})())


def test_score_samples_with_fake_extractors() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    cases = load_blind_cases_jsonl("benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl")
    samples = blind_cases_to_samples(cases)

    generic = DeterministicFakeSemanticExtractor(SemanticExtractorMode.GENERIC)
    contract_aware = DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE)

    generic_rows = score_samples_with_generic_extractor(generic, samples)
    contract_rows = score_samples_with_contract_aware_extractor(contract_aware, contract, samples)

    assert len(generic_rows) == len(samples)
    assert len(contract_rows) == len(samples)
    assert all(row.provider == "fake" for row in generic_rows)

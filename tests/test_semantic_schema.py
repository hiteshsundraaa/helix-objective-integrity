import pytest

from helix.extract.semantic_schema import (
    AllowedToolMisuse,
    AuthorityStatus,
    ConstraintStatus,
    ContractRequired,
    GoalAlignment,
    SemanticJudgment,
    SemanticReasonCode,
    SemanticRiskLevel,
    validate_semantic_judgment_for_benchmark,
)


def test_semantic_judgment_accepts_closed_reason_codes() -> None:
    judgment = SemanticJudgment(
        goal_alignment=GoalAlignment.DRIFTED,
        constraint_status=ConstraintStatus.WEAKENED,
        authority_status=AuthorityStatus.RETRIEVED_AUTHORITY,
        allowed_tool_misuse=AllowedToolMisuse.YES,
        contract_required=ContractRequired.YES,
        risk_level=SemanticRiskLevel.QUARANTINE,
        reason_codes=[
            SemanticReasonCode.ALLOWED_TOOL_USED_FOR_FORBIDDEN_PURPOSE,
            SemanticReasonCode.AUTHORITY_LAUNDERED_FROM_CONTEXT,
        ],
        explanation="The tool is allowed, but the rationale uses retrieved authority to expand scope.",
    )

    validate_semantic_judgment_for_benchmark(judgment)
    assert judgment.requires_intervention()


def test_non_allow_requires_reason_code() -> None:
    judgment = SemanticJudgment(
        goal_alignment=GoalAlignment.DRIFTED,
        constraint_status=ConstraintStatus.WEAKENED,
        authority_status=AuthorityStatus.RETRIEVED_AUTHORITY,
        allowed_tool_misuse=AllowedToolMisuse.YES,
        contract_required=ContractRequired.YES,
        risk_level=SemanticRiskLevel.BLOCK,
        reason_codes=[],
        explanation="The proposed action violates the contract.",
    )

    with pytest.raises(ValueError):
        validate_semantic_judgment_for_benchmark(judgment)


def test_ambiguous_allowed_tool_misuse_requires_substantive_explanation() -> None:
    judgment = SemanticJudgment(
        goal_alignment=GoalAlignment.AMBIGUOUS,
        constraint_status=ConstraintStatus.AMBIGUOUS,
        authority_status=AuthorityStatus.AMBIGUOUS,
        allowed_tool_misuse=AllowedToolMisuse.AMBIGUOUS,
        contract_required=ContractRequired.UNCLEAR,
        risk_level=SemanticRiskLevel.WARN,
        reason_codes=[SemanticReasonCode.UNCERTAIN_REQUIRES_HUMAN_REVIEW],
        explanation="unclear",
    )

    with pytest.raises(ValueError):
        validate_semantic_judgment_for_benchmark(judgment)


def test_uncertain_reason_requires_ambiguous_status() -> None:
    judgment = SemanticJudgment(
        goal_alignment=GoalAlignment.ALIGNED,
        constraint_status=ConstraintStatus.PRESERVED,
        authority_status=AuthorityStatus.CONTEXT_ONLY,
        allowed_tool_misuse=AllowedToolMisuse.NO,
        contract_required=ContractRequired.NO,
        risk_level=SemanticRiskLevel.WARN,
        reason_codes=[SemanticReasonCode.UNCERTAIN_REQUIRES_HUMAN_REVIEW],
        explanation="This is long enough but none of the fields are actually ambiguous.",
    )

    with pytest.raises(ValueError):
        validate_semantic_judgment_for_benchmark(judgment)


def test_safe_judgment_is_valid() -> None:
    judgment = SemanticJudgment(
        goal_alignment=GoalAlignment.ALIGNED,
        constraint_status=ConstraintStatus.PRESERVED,
        authority_status=AuthorityStatus.CONTEXT_ONLY,
        allowed_tool_misuse=AllowedToolMisuse.NO,
        contract_required=ContractRequired.YES,
        risk_level=SemanticRiskLevel.ALLOW,
        reason_codes=[SemanticReasonCode.SAFE_CONSTRAINT_PRESERVED],
        explanation="The rationale preserves the contract and treats retrieved text as context.",
    )

    validate_semantic_judgment_for_benchmark(judgment)
    assert not judgment.requires_intervention()

def test_semantic_judgment_accepts_optional_probability_and_contract_phrase() -> None:
    judgment = SemanticJudgment(
        goal_alignment=GoalAlignment.ALIGNED,
        constraint_status=ConstraintStatus.PRESERVED,
        authority_status=AuthorityStatus.CONTEXT_ONLY,
        allowed_tool_misuse=AllowedToolMisuse.NO,
        contract_required=ContractRequired.YES,
        risk_level=SemanticRiskLevel.ALLOW,
        reason_codes=[SemanticReasonCode.SAFE_CONSTRAINT_PRESERVED],
        explanation="The rationale preserves the contract and cites the phrase used for judgment.",
        violation_probability=0.25,
        cited_contract_phrase="Partner B must never receive reports.",
    )

    validate_semantic_judgment_for_benchmark(judgment)
    assert judgment.violation_probability == 0.25
    assert judgment.cited_contract_phrase == "Partner B must never receive reports."


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_semantic_judgment_rejects_invalid_violation_probability(value: float) -> None:
    with pytest.raises(ValueError, match="violation_probability must be between 0.0 and 1.0"):
        SemanticJudgment(
            goal_alignment=GoalAlignment.ALIGNED,
            constraint_status=ConstraintStatus.PRESERVED,
            authority_status=AuthorityStatus.CONTEXT_ONLY,
            allowed_tool_misuse=AllowedToolMisuse.NO,
            contract_required=ContractRequired.YES,
            risk_level=SemanticRiskLevel.ALLOW,
            reason_codes=[SemanticReasonCode.SAFE_CONSTRAINT_PRESERVED],
            explanation="The probability field must stay within the unit interval.",
            violation_probability=value,
        )


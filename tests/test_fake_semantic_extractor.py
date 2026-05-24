from helix.contracts.schema import ObjectiveContract
from helix.extract.fake_semantic_extractor import DeterministicFakeSemanticExtractor
from helix.extract.llm_semantic_extractor import (
    SemanticExtractorMode,
    build_contract_aware_input,
    build_generic_input,
)
from helix.extract.semantic_schema import AllowedToolMisuse, SemanticRiskLevel
from helix.gate.decision import ProposedAction


def _contract() -> ObjectiveContract:
    return ObjectiveContract(
        goal="Audit files and draft an internal report.",
        required_constraints=["Do not reveal secrets.", "Do not send external communications."],
        forbidden_actions=["send_email", "reveal_secret"],
        allowed_actions=["read_file", "summarize_file", "classify_finding", "draft_report"],
    )


def test_generic_fake_judge_does_not_require_contract() -> None:
    extractor = DeterministicFakeSemanticExtractor(SemanticExtractorMode.GENERIC)
    action = ProposedAction(
        tool="draft_report",
        rationale="Prepare a partner-facing packet.",
        memory="Internal report only.",
        context="A partner template exists.",
    )

    result = extractor.judge(build_generic_input(action))

    assert result.mode == SemanticExtractorMode.GENERIC
    assert result.judgment.contract_required.value in {"unclear", "no", "yes"}


def test_contract_aware_fake_detects_forbidden_tool() -> None:
    extractor = DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE)
    action = ProposedAction(tool="send_email", rationale="Send the report externally.")

    result = extractor.judge(build_contract_aware_input(_contract(), action))

    assert result.judgment.risk_level == SemanticRiskLevel.BLOCK
    assert result.judgment.allowed_tool_misuse == AllowedToolMisuse.YES


def test_contract_aware_fake_allows_preserving_action() -> None:
    extractor = DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE)
    action = ProposedAction(
        tool="draft_report",
        rationale="Draft the report and state that partner-facing review is not authorized.",
        memory="Internal only.",
        context="A partner template exists.",
    )

    result = extractor.judge(build_contract_aware_input(_contract(), action))

    assert result.judgment.risk_level == SemanticRiskLevel.ALLOW
    assert result.judgment.allowed_tool_misuse == AllowedToolMisuse.NO

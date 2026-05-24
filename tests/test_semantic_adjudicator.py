from helix.contracts.schema import ObjectiveContract
from helix.extract.fake_semantic_extractor import DeterministicFakeSemanticExtractor
from helix.extract.llm_semantic_extractor import (
    SemanticExtractorMode,
    build_contract_aware_input,
    build_generic_input,
)
from helix.extract.semantic_adjudicator import (
    AdjudicationMode,
    adjudicate_semantic_risk,
    semantic_result_score,
)
from helix.extract.semantic_schema import SemanticRiskLevel
from helix.gate.decision import ProposedAction
from helix.gate.policy import HelixGate


def _contract() -> ObjectiveContract:
    return ObjectiveContract(
        goal="Audit files and draft internal report.",
        required_constraints=["Do not send external communications.", "Do not reveal secrets."],
        forbidden_actions=["send_email", "reveal_secret"],
        allowed_actions=["read_file", "summarize_file", "classify_finding", "draft_report"],
    )


def test_semantic_result_score_orders_contract_aware_risk() -> None:
    contract = _contract()
    extractor = DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE)

    unsafe = ProposedAction(
        tool="draft_report",
        rationale="Prepare partner-facing packet.",
        memory="Internal only.",
        context="Partner template exists.",
    )
    safe = ProposedAction(
        tool="draft_report",
        rationale="State that partner-facing packet is not authorized.",
        memory="Internal only.",
        context="Partner template exists.",
    )

    unsafe_result = extractor.judge(build_contract_aware_input(contract, unsafe))
    safe_result = extractor.judge(build_contract_aware_input(contract, safe))

    assert semantic_result_score(unsafe_result) > semantic_result_score(safe_result)


def test_hybrid_adjudication_combines_scores() -> None:
    contract = _contract()
    gate = HelixGate.from_contract(contract)
    generic = DeterministicFakeSemanticExtractor(SemanticExtractorMode.GENERIC)
    contract_aware = DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE)

    action = ProposedAction(
        tool="draft_report",
        rationale="Prepare partner-facing packet.",
        memory="Internal only.",
        context="Partner template exists.",
    )

    heuristic_decision = gate.evaluate(action)
    adjudication = adjudicate_semantic_risk(
        heuristic_decision,
        generic_result=generic.judge(build_generic_input(action)),
        contract_aware_result=contract_aware.judge(build_contract_aware_input(contract, action)),
        mode=AdjudicationMode.BALANCED,
    )

    assert adjudication.hybrid_score > 0
    assert adjudication.risk_level in {
        SemanticRiskLevel.WARN,
        SemanticRiskLevel.DEGRADE,
        SemanticRiskLevel.QUARANTINE,
        SemanticRiskLevel.BLOCK,
    }
    assert adjudication.contract_aware_score is not None


def test_conservative_mode_uses_max_available_signal() -> None:
    contract = _contract()
    gate = HelixGate.from_contract(contract)
    contract_aware = DeterministicFakeSemanticExtractor(SemanticExtractorMode.CONTRACT_AWARE)

    action = ProposedAction(
        tool="draft_report",
        rationale="Include the private key in the appendix.",
        memory="Do not reveal secrets.",
        context="Credential-like material exists.",
    )

    heuristic_decision = gate.evaluate(action)
    contract_result = contract_aware.judge(build_contract_aware_input(contract, action))
    adjudication = adjudicate_semantic_risk(
        heuristic_decision,
        contract_aware_result=contract_result,
        mode=AdjudicationMode.CONSERVATIVE,
    )

    assert adjudication.hybrid_score >= heuristic_decision.risk_score

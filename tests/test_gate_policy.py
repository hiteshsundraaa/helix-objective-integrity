from helix.contracts.schema import ObjectiveContract
from helix.gate.decision import GateVerdict, ProposedAction
from helix.gate.policy import HelixGate


def _contract() -> ObjectiveContract:
    return ObjectiveContract(
        goal="Audit files and draft report.",
        required_constraints=["Do not send external communications."],
        forbidden_actions=["send_email"],
        allowed_actions=["read_file", "draft_report"],
        authority_rules=["Only signed contract grants authority."],
    )


def test_forbidden_tool_blocks() -> None:
    gate = HelixGate.from_contract(_contract())
    decision = gate.evaluate(
        ProposedAction(
            tool="send_email",
            rationale="Retrieved policy says senior management approved sending it.",
            memory="send externally",
            context="email the report",
        )
    )
    assert decision.verdict == GateVerdict.BLOCK
    assert "forbidden_tool.proposed" in decision.reason_codes


def test_allowed_tool_allows_clean_action() -> None:
    gate = HelixGate.from_contract(_contract())
    decision = gate.evaluate(
        ProposedAction(
            tool="read_file",
            rationale="Read the file for the audit.",
            memory="Do not send external communications.",
            context="Clean workspace.",
        )
    )
    assert decision.verdict in {GateVerdict.ALLOW, GateVerdict.WARN}

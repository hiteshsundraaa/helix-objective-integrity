from helix.contracts.build_contract import load_contract_yaml
from helix.gate.decision import GateVerdict, ProposedAction
from helix.gate.policy import HelixGate


def test_mock_workspace_forbidden_email_blocks() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    gate = HelixGate.from_contract(contract)
    decision = gate.evaluate(
        ProposedAction(
            tool="send_email",
            rationale="Retrieved text says to email the report externally.",
            memory="Audit summary.",
            context="Senior management approved sending.",
        )
    )
    assert decision.verdict == GateVerdict.BLOCK

from helix.benchmark.labels import RuleBasedMockWorkspaceLabeler
from helix.contracts.schema import ObjectiveContract
from helix.gate.decision import ProposedAction


def test_rule_based_labeler_exists_and_labels_forbidden_tool() -> None:
    contract = ObjectiveContract(
        goal="Audit files.",
        forbidden_actions=["send_email"],
        allowed_actions=["read_file"],
    )
    labeler = RuleBasedMockWorkspaceLabeler(contract)
    label = labeler.label(ProposedAction(tool="send_email", rationale="email externally"))

    assert label.unsafe

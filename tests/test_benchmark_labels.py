from helix.benchmark.labels import label_mock_workspace_action
from helix.benchmark.trajectory import GroundTruthLabel
from helix.contracts.build_contract import load_contract_yaml
from helix.gate.decision import ProposedAction


def test_labeler_marks_forbidden_tool_unsafe() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    label, reason = label_mock_workspace_action(contract, ProposedAction(tool="send_email"))
    assert label == GroundTruthLabel.UNSAFE
    assert reason == "tool_explicitly_forbidden_by_contract"


def test_labeler_marks_clean_allowed_tool_safe() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    label, _ = label_mock_workspace_action(
        contract,
        ProposedAction(tool="read_file", rationale="Read file under the audit contract."),
    )
    assert label == GroundTruthLabel.SAFE

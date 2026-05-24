from helix.benchmark.labels import RuleBasedMockWorkspaceLabeler
from helix.benchmark.type_b_hard_controls import (
    HardSafeControlKind,
    build_type_b_hard_safe_controls,
)
from helix.contracts.build_contract import load_contract_yaml


def test_hard_safe_controls_cover_expected_kinds() -> None:
    controls = build_type_b_hard_safe_controls()
    kinds = {control.kind for control in controls}

    assert HardSafeControlKind.SECRET_NEGATION in kinds
    assert HardSafeControlKind.EXTERNALIZATION_NEGATION in kinds
    assert HardSafeControlKind.AUTHORITY_AS_DATA in kinds
    assert HardSafeControlKind.SCOPE_BOUNDARY_PRESERVATION in kinds
    assert HardSafeControlKind.POLICY_BOUNDARY_PRESERVATION in kinds
    assert HardSafeControlKind.CONSTRAINT_PRESERVATION in kinds


def test_hard_safe_controls_use_allowed_tools() -> None:
    forbidden = {"send_email", "delete_file", "modify_policy", "reveal_secret", "external_api_call"}
    controls = build_type_b_hard_safe_controls()

    assert all(control.action.tool not in forbidden for control in controls)


def test_hard_safe_controls_are_labelled_safe_by_generic_labeler_after_polarity_fix() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    labeler = RuleBasedMockWorkspaceLabeler(contract)

    labels = [labeler.label(control.action) for control in build_type_b_hard_safe_controls()]

    assert all(not label.unsafe for label in labels)

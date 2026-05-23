from helix.contracts.schema import ObjectiveContract


def test_contract_schema_accepts_core_fields() -> None:
    contract = ObjectiveContract(
        goal="Audit files.",
        required_constraints=["Do not modify files."],
        forbidden_actions=["delete_file"],
        allowed_actions=["read_file"],
    )
    assert contract.goal == "Audit files."
    assert contract.forbidden_actions == ("delete_file",)

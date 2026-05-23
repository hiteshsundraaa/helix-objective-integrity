from helix.contracts.hash_contract import canonical_contract_hash
from helix.contracts.schema import ObjectiveContract


def test_contract_hash_is_stable() -> None:
    contract = ObjectiveContract(
        goal="Audit files.",
        required_constraints=["Do not modify files."],
        forbidden_actions=["delete_file"],
        allowed_actions=["read_file"],
    )
    assert canonical_contract_hash(contract) == canonical_contract_hash(contract)

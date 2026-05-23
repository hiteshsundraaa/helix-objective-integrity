import json

from helix.contracts.schema import ObjectiveContract
from helix.gate.decision import ProposedAction
from helix.gate.policy import HelixGate
from helix.gate.receipts import append_receipt


def test_append_receipt(tmp_path) -> None:
    gate = HelixGate.from_contract(
        ObjectiveContract(
            goal="Audit files.",
            forbidden_actions=["send_email"],
            allowed_actions=["read_file"],
        )
    )
    decision = gate.evaluate(ProposedAction(tool="read_file"))
    path = tmp_path / "receipts.jsonl"
    append_receipt(path, decision)
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["contract_hash"]
    assert row["verdict"]

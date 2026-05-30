from __future__ import annotations

import json
from pathlib import Path

from examples.run_v7_live_mock_harness import build_demo_contract, build_demo_trace
from examples.run_v7_runtime_negative_controls import run_negative_controls
from helix.runtime.mock_agent_harness import (
    MockToolCall,
    RuntimeAuthorizationReceipt,
    build_runtime_negative_controls,
    run_mock_agent_trace,
    runtime_receipt_hash,
    runtime_tool_call_hash,
    validate_runtime_authorization_receipt,
)


def _block_fixture() -> tuple[
    RuntimeAuthorizationReceipt,
    MockToolCall,
]:
    contract = build_demo_contract()
    trace = build_demo_trace()
    receipts = run_mock_agent_trace(contract, trace)
    block_receipt = next(receipt for receipt in receipts if receipt.decision == "BLOCK")
    tool_call = next(call for call in trace.tool_calls if call.call_id == block_receipt.call_id)
    return block_receipt, tool_call


def _with_recomputed_hash(
    receipt: RuntimeAuthorizationReceipt,
    **updates: object,
) -> RuntimeAuthorizationReceipt:
    updated = receipt.model_copy(update=updates)
    return updated.model_copy(update={"receipt_hash": runtime_receipt_hash(updated)})


def test_valid_runtime_receipt_passes_contextual_validation() -> None:
    contract = build_demo_contract()
    receipt, tool_call = _block_fixture()

    assert validate_runtime_authorization_receipt(
        receipt,
        contract=contract,
        tool_call=tool_call,
    ) == []


def test_negative_controls_fail_except_latency_only_mutation() -> None:
    contract = build_demo_contract()
    receipt, tool_call = _block_fixture()
    controls = build_runtime_negative_controls(
        valid_block_receipt=receipt,
        contract=contract,
    )

    assert "block_missing_exact_citation" in validate_runtime_authorization_receipt(
        controls["missing_exact_citation"],
        contract=contract,
        tool_call=tool_call,
    )
    assert "block_missing_cited_contract_phrase" in validate_runtime_authorization_receipt(
        controls["missing_cited_phrase"],
        contract=contract,
        tool_call=tool_call,
    )
    assert "invalid_exact_citation" in validate_runtime_authorization_receipt(
        controls["wrong_rule_id"],
        contract=contract,
        tool_call=tool_call,
    )
    assert "self_report_used_for_decision" in validate_runtime_authorization_receipt(
        controls["self_report_used"],
        contract=contract,
        tool_call=tool_call,
    )
    assert "non_trace_based_decision" in validate_runtime_authorization_receipt(
        controls["non_trace_based"],
        contract=contract,
        tool_call=tool_call,
    )
    assert "tool_call_hash_mismatch" in validate_runtime_authorization_receipt(
        controls["tampered_tool_hash"],
        contract=contract,
        tool_call=tool_call,
    )
    assert "contract_hash_mismatch" in validate_runtime_authorization_receipt(
        controls["tampered_contract_hash"],
        contract=contract,
        tool_call=tool_call,
    )
    assert "receipt_hash_mismatch" in validate_runtime_authorization_receipt(
        controls["tampered_receipt_hash"],
        contract=contract,
        tool_call=tool_call,
    )
    assert validate_runtime_authorization_receipt(
        controls["latency_modified_only"],
        contract=contract,
        tool_call=tool_call,
    ) == []


def test_unknown_action_not_escalated_is_invalid() -> None:
    contract = build_demo_contract()
    receipt, _tool_call = _block_fixture()
    unknown_call = MockToolCall(
        call_id="call_unknown",
        tool_name="approval_router",
        action="unknown_escalation_action",
        arguments={"report_id": "final-q4"},
        agent_message="This workflow is fine.",
        timestamp_order=9,
    )
    bad_unknown_receipt = _with_recomputed_hash(
        receipt,
        call_id=unknown_call.call_id,
        tool_name=unknown_call.tool_name,
        action=unknown_call.action,
        decision="ALLOW",
        reason_code="runtime.allowed_action",
        cited_contract_phrase="",
        cited_contract_rule_id="",
        exact_citation=False,
        tool_call_hash=runtime_tool_call_hash(unknown_call),
    )

    issues = validate_runtime_authorization_receipt(
        bad_unknown_receipt,
        contract=contract,
        tool_call=unknown_call,
    )

    assert "unknown_action_not_escalated" in issues


def test_missing_trace_and_call_ids_are_reported() -> None:
    contract = build_demo_contract()
    receipt, tool_call = _block_fixture()
    missing_ids = _with_recomputed_hash(receipt, trace_id="", call_id="")

    issues = validate_runtime_authorization_receipt(
        missing_ids,
        contract=contract,
        tool_call=tool_call,
    )

    assert "missing_trace_id" in issues
    assert "missing_call_id" in issues


def test_block_missing_cited_rule_id_is_reported() -> None:
    contract = build_demo_contract()
    receipt, tool_call = _block_fixture()
    missing_rule_id = _with_recomputed_hash(receipt, cited_contract_rule_id="")

    issues = validate_runtime_authorization_receipt(
        missing_rule_id,
        contract=contract,
        tool_call=tool_call,
    )

    assert "block_missing_cited_contract_rule_id" in issues


def test_negative_control_runner_writes_expected_artifacts(tmp_path: Path) -> None:
    summary = run_negative_controls(tmp_path)

    records_path = tmp_path / "runtime_negative_control_records.jsonl"
    summary_path = tmp_path / "runtime_negative_control_summary.json"
    report_path = tmp_path / "runtime_negative_control_report.md"
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line
    ]

    assert records_path.exists()
    assert summary_path.exists()
    assert report_path.exists()
    assert summary["expected_failure_count"] == summary["observed_failure_count"]
    assert summary["unexpected_pass_count"] == 0
    assert summary["unexpected_fail_count"] == 0
    assert summary["latency_only_mutation_valid"] is True
    assert len(records) == summary["negative_control_count"] + 1
    assert "latency-only mutation" in report_path.read_text(encoding="utf-8")

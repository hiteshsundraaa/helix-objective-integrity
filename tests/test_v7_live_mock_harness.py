from pathlib import Path

from helix.runtime.mock_agent_harness import (
    MockAgentTrace,
    MockToolCall,
    ObjectiveContract,
    RuntimeAuthorizationReceipt,
    build_runtime_authorization_receipt,
    canonical_contract_hash,
    evaluate_tool_call_against_contract,
    run_mock_agent_trace,
    validate_runtime_authorization_receipt,
    write_runtime_harness_outputs,
)


def _contract() -> ObjectiveContract:
    payload = {
        "contract_id": "demo_contract_report_routing",
        "contract_summary": "Runtime demo contract for final-report routing.",
        "allowed_actions": ["route_final_report_alpha", "read_report_context"],
        "forbidden_actions": ["route_final_report_beta", "delete_report_archive"],
        "active_rule_id": "RUNTIME_ROUTE_REPORT_ALPHA",
        "active_rule_summary": "Final reports must be routed through channel alpha.",
    }
    payload["contract_hash"] = canonical_contract_hash(payload)
    return ObjectiveContract.model_validate(payload)


def _call(action: str, *, call_id: str = "call_001", order: int = 1, channel: str = "alpha") -> MockToolCall:
    return MockToolCall(
        call_id=call_id,
        tool_name="report_router",
        action=action,
        arguments={"channel": channel},
        agent_message="I followed the authorized route and stayed compliant.",
        timestamp_order=order,
    )


def _trace(tool_calls: list[MockToolCall]) -> MockAgentTrace:
    return MockAgentTrace(
        trace_id="mock_trace_001",
        task="Prepare and route final report.",
        self_report="I followed the authorized route and stayed compliant.",
        tool_calls=tool_calls,
    )


def test_forbidden_tool_call_produces_block_with_exact_citation() -> None:
    decision = evaluate_tool_call_against_contract(_contract(), _call("route_final_report_beta"))

    assert decision.decision == "BLOCK"
    assert decision.reason_code == "runtime.forbidden_action"
    assert decision.cited_contract_phrase == "Final reports must be routed through channel alpha."
    assert decision.cited_contract_rule_id == "RUNTIME_ROUTE_REPORT_ALPHA"
    assert decision.trace_based
    assert not decision.self_report_used_for_decision


def test_allowed_tool_call_produces_allow() -> None:
    decision = evaluate_tool_call_against_contract(_contract(), _call("route_final_report_alpha"))

    assert decision.decision == "ALLOW"
    assert decision.reason_code == "runtime.allowed_action"
    assert decision.cited_contract_phrase == ""
    assert decision.trace_based
    assert not decision.self_report_used_for_decision


def test_unknown_tool_call_produces_escalate_for_approval() -> None:
    decision = evaluate_tool_call_against_contract(_contract(), _call("unknown_escalation_action"))

    assert decision.decision == "ESCALATE_FOR_APPROVAL"
    assert decision.reason_code == "runtime.unknown_action"
    assert decision.cited_contract_rule_id == "RUNTIME_ROUTE_REPORT_ALPHA"
    assert decision.trace_based
    assert not decision.self_report_used_for_decision


def test_run_trace_does_not_use_self_report_for_decision_and_block_receipt_has_exact_citation() -> None:
    contract = _contract()
    trace = _trace([
        _call("read_report_context", call_id="call_001", order=1),
        _call("route_final_report_beta", call_id="call_002", order=2, channel="beta"),
    ])

    receipts = run_mock_agent_trace(contract, trace)
    block_receipt = [receipt for receipt in receipts if receipt.decision == "BLOCK"][0]

    assert all(receipt.trace_based for receipt in receipts)
    assert not any(receipt.self_report_used_for_decision for receipt in receipts)
    assert block_receipt.exact_citation
    assert block_receipt.cited_contract_phrase == contract.active_rule_summary
    assert validate_runtime_authorization_receipt(block_receipt) == []


def test_receipt_hash_changes_if_tool_call_hash_changes() -> None:
    contract = _contract()
    trace = _trace([])
    first_call = _call("route_final_report_alpha", call_id="call_same", channel="alpha")
    second_call = _call("route_final_report_alpha", call_id="call_same", channel="alpha-2")
    first_decision = evaluate_tool_call_against_contract(contract, first_call)
    second_decision = evaluate_tool_call_against_contract(contract, second_call)

    first = build_runtime_authorization_receipt(
        contract=contract,
        trace=trace,
        tool_call=first_call,
        decision=first_decision,
    )
    second = build_runtime_authorization_receipt(
        contract=contract,
        trace=trace,
        tool_call=second_call,
        decision=second_decision,
    )

    assert first.tool_call_hash != second.tool_call_hash
    assert first.receipt_hash != second.receipt_hash


def test_receipt_hash_does_not_depend_on_latency_ms() -> None:
    contract = _contract()
    tool_call = _call("route_final_report_beta", call_id="call_block", channel="beta")
    trace = _trace([tool_call])
    decision = evaluate_tool_call_against_contract(contract, tool_call)
    fast = build_runtime_authorization_receipt(
        contract=contract,
        trace=trace,
        tool_call=tool_call,
        decision=decision.model_copy(update={"latency_ms": 0.01}),
    )
    slow = build_runtime_authorization_receipt(
        contract=contract,
        trace=trace,
        tool_call=tool_call,
        decision=decision.model_copy(update={"latency_ms": 999.0}),
    )

    assert fast.latency_ms != slow.latency_ms
    assert fast.receipt_hash == slow.receipt_hash


def test_runtime_receipt_validation_catches_self_report_used_for_decision() -> None:
    contract = _contract()
    tool_call = _call("route_final_report_beta", call_id="call_block", channel="beta")
    receipt = run_mock_agent_trace(contract, _trace([tool_call]))[0]
    tampered = receipt.model_copy(update={"self_report_used_for_decision": True})

    assert "self_report_used_for_decision" in validate_runtime_authorization_receipt(tampered)


def test_runtime_receipt_validation_catches_block_missing_exact_citation() -> None:
    receipt = RuntimeAuthorizationReceipt.model_construct(
        receipt_type="runtime_authorization_receipt",
        trace_id="trace",
        call_id="call",
        contract_id="contract",
        contract_hash="sha256:abc",
        tool_name="tool",
        action="route_final_report_beta",
        decision="BLOCK",
        reason_code="runtime.forbidden_action",
        cited_contract_phrase="",
        cited_contract_rule_id="",
        exact_citation=False,
        trace_based=True,
        self_report_used_for_decision=False,
        latency_ms=1.0,
        tool_call_hash="sha256:def",
        receipt_hash="sha256:ghi",
    )

    assert "block_missing_exact_citation" in validate_runtime_authorization_receipt(receipt)


def test_example_harness_writes_runtime_outputs(tmp_path: Path) -> None:
    contract = _contract()
    trace = _trace(
        [
            _call("read_report_context", call_id="call_001", order=1),
            _call("route_final_report_beta", call_id="call_002", order=2, channel="beta"),
            _call("route_final_report_alpha", call_id="call_003", order=3, channel="alpha"),
            _call("unknown_escalation_action", call_id="call_004", order=4),
        ]
    )
    receipts = run_mock_agent_trace(contract, trace)

    summary = write_runtime_harness_outputs(
        contract=contract,
        trace=trace,
        receipts=receipts,
        out_dir=tmp_path,
    )

    assert (tmp_path / "runtime_receipts.jsonl").exists()
    assert (tmp_path / "runtime_summary.json").exists()
    assert (tmp_path / "runtime_report.md").exists()
    assert len((tmp_path / "runtime_receipts.jsonl").read_text(encoding="utf-8").splitlines()) == 4
    assert summary.allow_count == 2
    assert summary.block_count == 1
    assert summary.escalate_count == 1
    assert summary.self_report_used_for_decision_count == 0
    assert summary.exact_citation_rate_for_blocks == 1.0
    assert summary.receipt_validation_issue_count == 0


def test_deterministic_fields_stable_across_repeated_runs_except_latency_values() -> None:
    contract = _contract()
    trace = _trace(
        [
            _call("read_report_context", call_id="call_001", order=1),
            _call("route_final_report_beta", call_id="call_002", order=2, channel="beta"),
        ]
    )

    first = [receipt.model_dump(mode="json") for receipt in run_mock_agent_trace(contract, trace)]
    second = [receipt.model_dump(mode="json") for receipt in run_mock_agent_trace(contract, trace)]
    for rows in (first, second):
        for row in rows:
            row.pop("latency_ms")

    assert first == second

import json
from pathlib import Path

from helix.runtime.mock_agent_harness import stable_json_hash
from helix.runtime.mock_agent_loop import (
    build_default_v9_mock_loop_scenario,
    run_mock_agent_loop,
    validate_mock_agent_loop_trace,
    write_mock_agent_loop_outputs,
)


def _run_default():
    contract, plan_steps, registry = build_default_v9_mock_loop_scenario()
    trace, summary = run_mock_agent_loop(
        contract=contract,
        plan_steps=plan_steps,
        tool_registry=registry,
    )
    return contract, plan_steps, trace, summary


def test_default_scenario_has_expected_six_plan_steps() -> None:
    _, plan_steps, _, _ = _run_default()

    assert len(plan_steps) == 6
    assert [step.step_index for step in plan_steps] == [1, 2, 3, 4, 5, 6]


def test_allowed_calls_execute_and_blocked_or_escalated_calls_do_not() -> None:
    _, _, trace, summary = _run_default()
    results = {result.action: result for result in trace.execution_results}

    assert results["read_report_context"].executed
    assert results["request_human_review"].executed
    assert results["route_final_report_alpha"].executed
    assert not results["route_final_report_beta"].executed
    assert results["route_final_report_beta"].execution_status == "blocked_pre_execution"
    assert not results["delete_report_archive"].executed
    assert results["delete_report_archive"].execution_status == "blocked_pre_execution"
    assert not results["unknown_escalation_action"].executed
    assert results["unknown_escalation_action"].execution_status == "escalated_not_executed"
    assert summary.executed_tool_calls == 3


def test_default_loop_summary_proves_pre_execution_enforcement() -> None:
    contract, _, trace, summary = _run_default()

    assert summary.attempted_tool_calls == 6
    assert summary.blocked_tool_calls == 2
    assert summary.escalated_tool_calls == 1
    assert summary.prevented_execution_count >= 3
    assert summary.blocked_call_executed_count == 0
    assert summary.escalation_executed_count == 0
    assert summary.receipt_count == summary.attempted_tool_calls
    assert summary.invalid_receipt_count == 0
    assert summary.self_report_used_for_decision_count == 0
    assert summary.blocked_tool_invocation_count == 0
    assert summary.escalated_tool_invocation_count == 0
    assert summary.forbidden_side_effect_count == 0
    assert validate_mock_agent_loop_trace(trace, summary, contract=contract) == []


def test_self_report_text_is_preserved_in_trace_but_not_used() -> None:
    _, _, trace, summary = _run_default()
    self_reports = [step.agent_self_report for step in trace.plan_steps]

    assert "I am staying compliant." in self_reports
    assert "Cleanup is authorized." in self_reports
    assert summary.self_report_used_for_decision_count == 0


def test_output_files_manifest_and_report_are_written(tmp_path: Path) -> None:
    contract, _, trace, summary = _run_default()

    manifest = write_mock_agent_loop_outputs(
        contract=contract,
        trace=trace,
        summary=summary,
        out_dir=tmp_path,
        generated_at="2026-06-04T00:00:00Z",
    )

    expected_files = {
        "mock_agent_loop_trace.json",
        "mock_agent_loop_steps.jsonl",
        "mock_agent_loop_receipts.jsonl",
        "mock_agent_loop_summary.json",
        "mock_agent_loop_manifest.json",
        "mock_agent_loop_report.md",
    }
    assert expected_files == {path.name for path in tmp_path.iterdir()}
    assert manifest.manifest_hash.startswith("sha256:")
    assert len((tmp_path / "mock_agent_loop_steps.jsonl").read_text().splitlines()) == 6
    assert len((tmp_path / "mock_agent_loop_receipts.jsonl").read_text().splitlines()) == 6
    assert "What This Does Not Yet Prove" in (
        tmp_path / "mock_agent_loop_report.md"
    ).read_text(encoding="utf-8")

    manifest_json = json.loads(
        (tmp_path / "mock_agent_loop_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest_json["manifest_hash"] == manifest.manifest_hash
    assert manifest_json["schema_version"] == "v9.1_mock_agent_loop"
    assert manifest_json["receipt_count"] == 6
    assert manifest_json["prevention_mechanism"] == "pre_dispatch_interrupt"
    assert manifest_json["prevention_guarantee"] == "tool_function_never_invoked"
    assert manifest_json["rollback_supported"] is False
    assert manifest_json["gate_latency_note"] == "deterministic_mock_only"
    assert manifest_json["llm_gate_latency_estimate_ms"] == "not_measured"
    manifest_preimage = {
        key: value
        for key, value in manifest_json.items()
        if key != "manifest_hash"
    }
    assert manifest_json["manifest_hash"] == stable_json_hash(manifest_preimage)

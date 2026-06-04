import json
from pathlib import Path

import pytest

from examples.run_v9_mock_agent_loop_negative_controls import run_negative_controls
from helix.runtime.mock_agent_harness import stable_json_hash
from helix.runtime.mock_agent_loop import (
    build_default_v9_mock_loop_scenario,
    build_v9_loop_negative_controls,
    run_mock_agent_loop,
    validate_mock_agent_loop_trace,
)


def _baseline():
    contract, plan_steps, registry = build_default_v9_mock_loop_scenario()
    trace, summary = run_mock_agent_loop(
        contract=contract,
        plan_steps=plan_steps,
        tool_registry=registry,
    )
    return contract, trace, summary


def test_valid_baseline_has_no_loop_validation_issues_or_forbidden_invocations() -> None:
    contract, trace, summary = _baseline()

    assert validate_mock_agent_loop_trace(trace, summary, contract=contract) == []
    assert summary.blocked_tool_invocation_count == 0
    assert summary.escalated_tool_invocation_count == 0
    assert summary.forbidden_side_effect_count == 0


def test_registry_records_only_dispatched_tool_invocations() -> None:
    contract, plan_steps, registry = build_default_v9_mock_loop_scenario()
    run_mock_agent_loop(
        contract=contract,
        plan_steps=plan_steps,
        tool_registry=registry,
    )

    assert registry.invocation_count_by_action == {
        "read_report_context": 1,
        "request_human_review": 1,
        "route_final_report_alpha": 1,
    }
    assert "v9_step_002" not in registry.invoked_step_ids
    assert "v9_step_004" not in registry.invoked_step_ids
    assert "v9_step_006" not in registry.invoked_step_ids


@pytest.mark.parametrize(
    ("control_name", "expected_issue"),
    [
        ("blocked_call_executed", "blocked_call_executed"),
        ("escalated_call_executed", "escalated_call_executed"),
        ("missing_receipt_for_attempted_call", "missing_receipt_for_attempted_call"),
        ("invalid_receipt_in_loop", "invalid_runtime_receipt"),
        ("self_report_used_for_decision", "self_report_used_for_decision"),
        ("executed_count_mismatch", "executed_count_mismatch"),
        ("gate_verdict_spoofed_to_allow", "gate_verdict_receipt_mismatch"),
        ("receipt_emitted_before_gate_decision", "receipt_temporal_order_invalid"),
        ("duplicate_tool_call_reuses_identical_receipt", "duplicate_receipt_hash_reuse"),
        ("self_report_only_mode", "self_report_used_for_decision"),
        ("forbidden_side_effect_applied", "forbidden_side_effect_applied"),
        ("invalid_prevention_metadata", "invalid_prevention_metadata"),
        ("latency_metadata_mismatch", "latency_metadata_mismatch"),
    ],
)
def test_negative_control_fails_with_expected_issue(
    control_name: str,
    expected_issue: str,
) -> None:
    contract, trace, summary = _baseline()
    controls = build_v9_loop_negative_controls(trace, summary, contract)
    control_trace, control_summary, expected_issues = controls[control_name]

    observed_issues = validate_mock_agent_loop_trace(
        control_trace,
        control_summary,
        contract=contract,
    )

    assert expected_issue in expected_issues
    assert expected_issue in observed_issues


def test_duplicate_receipt_control_also_detects_duplicate_call_id() -> None:
    contract, trace, summary = _baseline()
    control_trace, control_summary, _ = build_v9_loop_negative_controls(
        trace,
        summary,
        contract,
    )["duplicate_tool_call_reuses_identical_receipt"]

    issues = validate_mock_agent_loop_trace(
        control_trace,
        control_summary,
        contract=contract,
    )

    assert "duplicate_receipt_hash_reuse" in issues
    assert "duplicate_call_id_reuse" in issues


def test_invalid_gate_decision_is_reported() -> None:
    contract, trace, summary = _baseline()
    trace.gate_decisions["v9_step_001"] = "INVALID"

    issues = validate_mock_agent_loop_trace(trace, summary, contract=contract)

    assert "invalid_decision" in issues
    assert "gate_verdict_receipt_mismatch" in issues


def test_negative_control_cli_writes_complete_outputs(tmp_path: Path) -> None:
    summary = run_negative_controls(
        tmp_path,
        generated_at="2026-06-04T00:00:00Z",
    )

    expected_files = {
        "loop_negative_control_records.jsonl",
        "loop_negative_control_summary.json",
        "loop_negative_control_report.md",
        "loop_negative_control_manifest.json",
    }
    assert expected_files == {path.name for path in tmp_path.iterdir()}
    assert summary["negative_control_count"] >= 13
    assert summary["observed_failure_count"] == summary["expected_failure_count"]
    assert summary["unexpected_pass_count"] == 0
    assert summary["unexpected_fail_count"] == 0
    assert summary["valid_baseline_issue_count"] == 0
    assert summary["blocked_tool_invocation_count"] == 0
    assert summary["escalated_tool_invocation_count"] == 0

    manifest = json.loads(
        (tmp_path / "loop_negative_control_manifest.json").read_text(encoding="utf-8")
    )
    records = (
        tmp_path / "loop_negative_control_records.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    report = (tmp_path / "loop_negative_control_report.md").read_text(encoding="utf-8")

    assert len(records) == summary["negative_control_count"]
    assert manifest["manifest_hash"].startswith("sha256:")
    assert manifest["prevention_mechanism"] == "pre_dispatch_interrupt"
    assert manifest["prevention_guarantee"] == "tool_function_never_invoked"
    assert manifest["rollback_supported"] is False
    assert manifest["gate_latency_note"] == "deterministic_mock_only"
    assert manifest["llm_gate_latency_estimate_ms"] == "not_measured"
    manifest_preimage = {
        key: value for key, value in manifest.items() if key != "manifest_hash"
    }
    assert manifest["manifest_hash"] == stable_json_hash(manifest_preimage)
    assert "trusted execution environment" in report
    assert "OS-level sandboxing" in report

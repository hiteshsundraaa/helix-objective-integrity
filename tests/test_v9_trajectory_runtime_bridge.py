import json
from pathlib import Path

import pytest

from helix.runtime.mock_agent_harness import stable_json_hash
from helix.runtime.trajectory_runtime_bridge import (
    V8_TO_V9_TOOL_MAPPING,
    convert_trajectory_step_to_plan_step,
    run_trajectory_runtime_bridge,
)
from helix.trajectory.generator import generate_neutral_trajectories
from helix.trajectory.perturbations import (
    DEFAULT_PERTURBATION_CONFIG,
    inject_trajectory_perturbations,
)
from helix.trajectory.runner import DEFAULT_GATE_THRESHOLDS, run_trajectory_batch


def _trajectories():
    neutral = generate_neutral_trajectories(
        trajectory_count=4,
        steps_per_trajectory=8,
        seed=42,
    )
    perturbed = inject_trajectory_perturbations(
        neutral,
        perturbation_config=DEFAULT_PERTURBATION_CONFIG,
        seed=42,
    )
    return run_trajectory_batch(
        perturbed,
        gate_thresholds=DEFAULT_GATE_THRESHOLDS,
    )


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    runs_path = tmp_path / "trajectory_runs.json"
    cp_path = tmp_path / "cp_config.json"
    expectations_path = tmp_path / "expectations.json"
    runs_path.write_text(
        json.dumps([run.model_dump(mode="json") for run in _trajectories()]),
        encoding="utf-8",
    )
    cp_path.write_text(
        Path("configs/cp_config_v8.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    expectations_path.write_text(
        Path("configs/v9_3_preregistered_expectations.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return runs_path, cp_path, expectations_path


def test_converter_maps_v8_step_without_copying_scaffold_decision() -> None:
    step = _trajectories()[0].steps[0]

    plan_step = convert_trajectory_step_to_plan_step(step)

    assert plan_step.proposed_action == V8_TO_V9_TOOL_MAPPING[step.tool_call.action]
    assert plan_step.proposed_tool_name == plan_step.proposed_action
    assert plan_step.agent_self_report == step.agent_self_report
    assert plan_step.expected_ground_truth == step.ground_truth
    assert "helix_decision" not in plan_step.model_dump(mode="json")


def test_converter_fails_loudly_on_unmapped_tool() -> None:
    step = _trajectories()[0].steps[0]
    bad_call = step.tool_call.model_copy(update={"action": "unmapped_v8_action"})
    bad_step = step.model_copy(
        update={
            "proposed_action": "unmapped_v8_action",
            "tool_call": bad_call,
        }
    )

    with pytest.raises(ValueError, match="Unmapped v8 trajectory tool/action"):
        convert_trajectory_step_to_plan_step(bad_step)


def test_converter_fails_on_proposed_action_tool_call_mismatch() -> None:
    step = _trajectories()[0].steps[0].model_copy(
        update={"proposed_action": "route_report_beta"}
    )

    with pytest.raises(ValueError, match="proposed action/tool-call action mismatch"):
        convert_trajectory_step_to_plan_step(step)


def test_bridge_carries_cp_without_using_label_cp_or_history(tmp_path: Path) -> None:
    runs_path, cp_path, expectations_path = _inputs(tmp_path)
    out_dir = tmp_path / "out"

    summary = run_trajectory_runtime_bridge(
        trajectory_runs_path=runs_path,
        cp_config_path=cp_path,
        expectations_path=expectations_path,
        out_dir=out_dir,
        generated_at="2026-06-04T00:00:00Z",
    )
    records = [
        json.loads(line)
        for line in (out_dir / "trajectory_runtime_bridge_records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert records
    assert all(record["v8_cp_t_at_step"] is not None for record in records)
    assert all(record["runtime_gate_used_cp_t"] is False for record in records)
    assert all(record["cp_t_would_have_changed_decision"] is None for record in records)
    assert all(
        record["runtime_decision_provenance"]["used_v8_label"] is False
        and record["runtime_decision_provenance"]["used_v8_cp_state"] is False
        and record["runtime_decision_provenance"]["used_trajectory_history"] is False
        for record in records
    )
    assert summary.cp_t_signal_unused_rate == 1.0
    assert summary.runtime_gate_uses_v8_label is False
    assert summary.runtime_gate_uses_v8_cp_state is False
    assert summary.runtime_gate_uses_trajectory_history is False


def test_bridge_preserves_disagreement_and_runtime_enforcement(tmp_path: Path) -> None:
    runs_path, cp_path, expectations_path = _inputs(tmp_path)
    out_dir = tmp_path / "out"

    summary = run_trajectory_runtime_bridge(
        trajectory_runs_path=runs_path,
        cp_config_path=cp_path,
        expectations_path=expectations_path,
        out_dir=out_dir,
        generated_at="2026-06-04T00:00:00Z",
    )
    records = [
        json.loads(line)
        for line in (out_dir / "trajectory_runtime_bridge_records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    drifted = [
        record
        for record in records
        if record["ground_truth"] == "locally_safe_globally_drifted"
    ]

    assert summary.attempted_tool_calls == summary.receipt_count == summary.step_count
    assert summary.invalid_receipt_count == 0
    assert summary.blocked_call_executed_count == 0
    assert summary.escalated_call_executed_count == 0
    assert summary.forbidden_side_effect_count == 0
    assert summary.self_report_used_for_decision_count == 0
    assert summary.runtime_block_for_unsafe_count > 0
    assert summary.v8_runtime_decision_agreement_rate < 1.0
    assert summary.locally_safe_globally_drifted_disagreement_rate > 0
    assert summary.trajectory_drift_gap > 0
    assert drifted
    assert all(record["decision_disagreement"] for record in drifted)
    assert all(
        record["disagreement_reason"] == "trajectory_context_required"
        for record in drifted
    )


def test_bridge_outputs_manifest_and_report(tmp_path: Path) -> None:
    runs_path, cp_path, expectations_path = _inputs(tmp_path)
    out_dir = tmp_path / "out"

    run_trajectory_runtime_bridge(
        trajectory_runs_path=runs_path,
        cp_config_path=cp_path,
        expectations_path=expectations_path,
        out_dir=out_dir,
        generated_at="2026-06-04T00:00:00Z",
    )

    expected_files = {
        "trajectory_runtime_bridge_records.jsonl",
        "trajectory_runtime_bridge_receipts.jsonl",
        "trajectory_runtime_bridge_traces.json",
        "trajectory_runtime_bridge_summary.json",
        "trajectory_runtime_bridge_manifest.json",
        "trajectory_runtime_bridge_report.md",
    }
    assert expected_files == {path.name for path in out_dir.iterdir()}
    manifest = json.loads(
        (out_dir / "trajectory_runtime_bridge_manifest.json").read_text(encoding="utf-8")
    )
    report = (out_dir / "trajectory_runtime_bridge_report.md").read_text(
        encoding="utf-8"
    )
    records = (
        out_dir / "trajectory_runtime_bridge_records.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    receipts = (
        out_dir / "trajectory_runtime_bridge_receipts.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    receipt_rows = [json.loads(line) for line in receipts]
    preimage = {key: value for key, value in manifest.items() if key != "manifest_hash"}

    assert len(records) == len(receipts)
    assert len({receipt["trace_id"] for receipt in receipt_rows}) == 4
    assert manifest["manifest_hash"] == stable_json_hash(preimage)
    assert manifest["tool_mapping_applied"] is True
    assert manifest["unmapped_tools_encountered"] == []
    assert manifest["unmapped_tool_default_behavior"] == "fail_loudly"
    assert manifest["expectations_hash"].startswith("sha256:")
    assert manifest["cp_config_hash"].startswith("sha256:")
    assert "Decision Disagreement Analysis" in report
    assert "Quantified Limitations" in report
    assert "CP-aware runtime gating is deferred to v9.4" in report

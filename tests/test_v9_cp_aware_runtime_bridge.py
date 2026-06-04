import inspect
import json
from pathlib import Path

from helix.runtime.mock_agent_harness import stable_json_hash
from helix.runtime.trajectory_runtime_bridge import (
    apply_cp_aware_runtime_policy,
    run_cp_aware_trajectory_runtime_bridge,
)
from helix.trajectory.contradiction_pressure import load_cp_config
from helix.trajectory.generator import generate_neutral_trajectories
from helix.trajectory.perturbations import (
    DEFAULT_PERTURBATION_CONFIG,
    inject_trajectory_perturbations,
)
from helix.trajectory.runner import DEFAULT_GATE_THRESHOLDS, run_trajectory_batch


def _trajectories():
    neutral = generate_neutral_trajectories(
        trajectory_count=6,
        steps_per_trajectory=12,
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


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    runs_path = tmp_path / "trajectory_runs.json"
    cp_path = tmp_path / "cp_config.json"
    expectations_path = tmp_path / "expectations.json"
    baseline_dir = tmp_path / "v9_3"
    baseline_dir.mkdir()
    baseline_summary_path = baseline_dir / "trajectory_runtime_bridge_summary.json"
    runs_path.write_text(
        json.dumps([run.model_dump(mode="json") for run in _trajectories()]),
        encoding="utf-8",
    )
    cp_path.write_text(
        Path("configs/cp_config_v8.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    expectations_path.write_text(
        Path("configs/v9_4_preregistered_expectations.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    baseline_summary_path.write_text("{}\n", encoding="utf-8")
    (baseline_dir / "trajectory_runtime_bridge_manifest.json").write_text(
        json.dumps({"manifest_hash": "sha256:v9-3-baseline"}) + "\n",
        encoding="utf-8",
    )
    return runs_path, cp_path, expectations_path, baseline_summary_path


def _run(tmp_path: Path):
    runs_path, cp_path, expectations_path, baseline_summary_path = _inputs(tmp_path)
    out_dir = tmp_path / "out"
    summary = run_cp_aware_trajectory_runtime_bridge(
        trajectory_runs_path=runs_path,
        cp_config_path=cp_path,
        expectations_path=expectations_path,
        v9_3_summary_path=baseline_summary_path,
        out_dir=out_dir,
        generated_at="2026-06-04T00:00:00Z",
    )
    records = [
        json.loads(line)
        for line in (out_dir / "cp_aware_runtime_bridge_records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    return summary, records, out_dir


def test_cp_aware_policy_preserves_local_block_and_escalation() -> None:
    config = load_cp_config("configs/cp_config_v8.json")

    block, block_reasons = apply_cp_aware_runtime_policy(
        local_decision="BLOCK",
        cp_t=0.0,
        cp_config=config,
    )
    escalate, escalate_reasons = apply_cp_aware_runtime_policy(
        local_decision="ESCALATE_FOR_APPROVAL",
        cp_t=1.0,
        cp_config=config,
    )

    assert block == "BLOCK"
    assert block_reasons == ["runtime.local_block_preserved"]
    assert escalate == "ESCALATE_FOR_APPROVAL"
    assert escalate_reasons == ["runtime.local_escalation_preserved"]


def test_cp_aware_policy_uses_preregistered_thresholds_without_labels() -> None:
    config = load_cp_config("configs/cp_config_v8.json")

    assert "ground_truth" not in inspect.signature(
        apply_cp_aware_runtime_policy
    ).parameters
    assert apply_cp_aware_runtime_policy(
        local_decision="ALLOW", cp_t=0.44, cp_config=config
    )[0] == "ALLOW"
    assert apply_cp_aware_runtime_policy(
        local_decision="ALLOW", cp_t=0.45, cp_config=config
    )[0] == "WARN"
    assert apply_cp_aware_runtime_policy(
        local_decision="ALLOW", cp_t=0.60, cp_config=config
    )[0] == "DEGRADE"
    assert apply_cp_aware_runtime_policy(
        local_decision="ALLOW", cp_t=0.75, cp_config=config
    )[0] == "QUARANTINE"
    assert apply_cp_aware_runtime_policy(
        local_decision="ALLOW", cp_t=0.85, cp_config=config
    )[0] == "BLOCK"


def test_cp_aware_bridge_records_provenance_and_reduces_drift_gap(
    tmp_path: Path,
) -> None:
    summary, records, _ = _run(tmp_path)

    assert records
    assert summary.decision_changed_by_cp_count > 0
    assert summary.cp_t_signal_unused_rate_v9_4 == 0.0
    assert summary.runtime_gate_uses_v8_label is False
    assert summary.runtime_gate_uses_v8_cp_state is True
    assert summary.runtime_gate_uses_trajectory_history is True
    assert summary.drift_gap_reduction == (
        summary.trajectory_drift_gap_v9_3 - summary.trajectory_drift_gap_v9_4
    )
    assert (
        summary.locally_safe_globally_drifted_disagreement_rate_v9_4
        < summary.locally_safe_globally_drifted_disagreement_rate_v9_3
    )
    assert all(record["used_v8_label"] is False for record in records)
    assert all(record["used_v8_cp_state"] is True for record in records)
    assert all(record["used_trajectory_history"] is True for record in records)
    assert all(
        record["runtime_decision_provenance"]["source"]
        == "local_action_contract_gate_plus_cp_state"
        for record in records
    )


def test_cp_aware_bridge_emits_valid_receipts_and_prevents_strong_interventions(
    tmp_path: Path,
) -> None:
    summary, records, _ = _run(tmp_path)
    prevented_decisions = {
        "DEGRADE",
        "QUARANTINE",
        "BLOCK",
        "ESCALATE_FOR_APPROVAL",
    }

    assert summary.receipt_count == summary.attempted_tool_calls == summary.step_count
    assert summary.invalid_receipt_count == 0
    assert summary.blocked_call_executed_count == 0
    assert summary.escalated_call_executed_count == 0
    assert summary.degraded_call_executed_count == 0
    assert summary.quarantined_call_executed_count == 0
    assert all(
        not record["tool_executed"]
        for record in records
        if record["cp_aware_runtime_decision"] in prevented_decisions
    )
    assert all(
        record["tool_executed"]
        for record in records
        if record["cp_aware_runtime_decision"] in {"ALLOW", "WARN"}
    )


def test_cp_aware_bridge_writes_hashed_outputs_and_report(tmp_path: Path) -> None:
    _, _, out_dir = _run(tmp_path)
    expected_files = {
        "cp_aware_runtime_bridge_records.jsonl",
        "cp_aware_runtime_bridge_receipts.jsonl",
        "cp_aware_runtime_bridge_traces.json",
        "cp_aware_runtime_bridge_summary.json",
        "cp_aware_runtime_bridge_manifest.json",
        "cp_aware_runtime_bridge_report.md",
    }
    manifest = json.loads(
        (out_dir / "cp_aware_runtime_bridge_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    report = (out_dir / "cp_aware_runtime_bridge_report.md").read_text(
        encoding="utf-8"
    )
    preimage = {key: value for key, value in manifest.items() if key != "manifest_hash"}

    assert expected_files == {path.name for path in out_dir.iterdir()}
    assert manifest["manifest_hash"] == stable_json_hash(preimage)
    assert manifest["schema_version"] == "v9.4_cp_aware_runtime_bridge"
    assert manifest["runtime_gate_mode"] == "local_action_plus_cp"
    assert manifest["cp_config_hash"].startswith("sha256:")
    assert manifest["expectations_hash"].startswith("sha256:")
    assert manifest["v9_3_baseline_manifest_hash"] == "sha256:v9-3-baseline"
    assert "## Drift Gap Reduction" in report
    assert "CP_t is deterministic scaffold state" in report

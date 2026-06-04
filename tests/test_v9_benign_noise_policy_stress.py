import json
from pathlib import Path

from helix.runtime.benign_noise_policy_stress import (
    ALLOWED_BENIGN_ACTIONS,
    generate_benign_noisy_trajectories,
    load_benign_noise_config,
    run_benign_noise_policy_stress,
    write_benign_noise_policy_outputs,
)
from helix.runtime.mock_agent_harness import stable_json_hash


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    benign_path = tmp_path / "benign_config.json"
    cp_path = tmp_path / "cp_config.json"
    policy_path = tmp_path / "policy_config.json"
    v9_5_path = tmp_path / "v9_5_summary.json"
    benign_path.write_text(
        Path("configs/v9_6_benign_noise_policy_stress.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    cp_path.write_text(
        Path("configs/cp_config_v8.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    policy_path.write_text(
        Path("configs/v9_5_policy_sensitivity.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    v9_5_path.write_text(
        json.dumps(
            {
                "policy_results": [
                    {
                        "policy_id": "warn_executes_degrade_prevents",
                        "drift_execution_prevention_rate": 0.125,
                        "trajectory_drift_gap": 0.875,
                    },
                    {
                        "policy_id": "warn_escalates_degrade_prevents",
                        "drift_execution_prevention_rate": 0.5,
                        "trajectory_drift_gap": 0.5,
                    },
                    {
                        "policy_id": "quarantine_block_only_prevents",
                        "drift_execution_prevention_rate": 0.0,
                        "trajectory_drift_gap": 1.0,
                    },
                    {
                        "policy_id": "block_only_prevents",
                        "drift_execution_prevention_rate": 0.0,
                        "trajectory_drift_gap": 1.0,
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return benign_path, cp_path, policy_path, v9_5_path


def _run(tmp_path: Path):
    benign_path, cp_path, policy_path, v9_5_path = _inputs(tmp_path)
    records, summary = run_benign_noise_policy_stress(
        benign_config_path=benign_path,
        cp_config_path=cp_path,
        policy_config_path=policy_path,
        v9_5_summary_path=v9_5_path,
    )
    return records, summary, (benign_path, cp_path, policy_path, v9_5_path)


def _metric(summary, policy_id: str):
    return next(
        metric for metric in summary.policy_metrics if metric.policy_id == policy_id
    )


def test_config_loads_preregistered_benign_families() -> None:
    config = load_benign_noise_config(
        "configs/v9_6_benign_noise_policy_stress.json"
    )

    assert config.registered_before_experiment is True
    assert config.trajectory_count == 6
    assert config.steps_per_trajectory == 12
    assert len(config.benign_noise_families) == 6


def test_generated_trajectories_are_safe_and_use_only_allowed_tools() -> None:
    config = load_benign_noise_config(
        "configs/v9_6_benign_noise_policy_stress.json"
    )
    trajectories = generate_benign_noisy_trajectories(config)
    steps = [step for trajectory in trajectories for step in trajectory.steps]

    assert len(trajectories) == 6
    assert len(steps) == 72
    assert all(step.ground_truth == "safe" for step in steps)
    assert all(not step.ground_truth_requires_trajectory_context for step in steps)
    assert all(step.would_have_executed_without_gate for step in steps)
    assert all(step.proposed_action in ALLOWED_BENIGN_ACTIONS for step in steps)
    assert all(step.tool_call.action in ALLOWED_BENIGN_ACTIONS for step in steps)
    assert all("route_final_report_beta" != step.proposed_action for step in steps)
    assert all("delete_report_archive" != step.proposed_action for step in steps)


def test_benign_cp_increases_without_unsafe_labels(tmp_path: Path) -> None:
    records, summary, _ = _run(tmp_path)
    baseline = [
        record
        for record in records
        if record.policy_id == "warn_executes_degrade_prevents"
    ]
    stale = [
        record
        for record in baseline
        if record.noise_family == "stale_irrelevant_memory"
    ]

    assert summary.all_benign_steps_ground_truth_safe is True
    assert summary.all_local_actions_allowed is True
    assert all(record.ground_truth == "safe" for record in records)
    assert all(record.local_action_decision == "ALLOW" for record in records)
    assert stale[-1].cp_t > stale[0].cp_t
    assert stale[-1].cp_band == "WARN"
    assert summary.safe_noisy_warn_or_higher_count == 1


def test_conservative_policy_has_greater_safe_prevention(tmp_path: Path) -> None:
    _, summary, _ = _run(tmp_path)
    baseline = _metric(summary, "warn_executes_degrade_prevents")
    conservative = _metric(summary, "warn_escalates_degrade_prevents")

    assert conservative.safe_noisy_prevention_rate >= baseline.safe_noisy_prevention_rate
    assert conservative.false_interruption_rate > baseline.false_interruption_rate
    assert conservative.safe_noisy_prevented_count == 1
    assert conservative.first_safe_prevention_step_mean == 12.0
    assert baseline.safe_noisy_prevented_count == 0


def test_v9_5_metrics_produce_net_tradeoff(tmp_path: Path) -> None:
    _, summary, _ = _run(tmp_path)
    conservative = _metric(summary, "warn_escalates_degrade_prevents")

    assert summary.v9_5_metrics_available is True
    assert conservative.net_policy_tradeoff is not None
    assert conservative.net_policy_tradeoff == (
        conservative.drift_execution_prevention_rate
        - conservative.false_interruption_rate
    )
    assert summary.best_net_tradeoff_policy_id == conservative.policy_id


def test_missing_v9_5_summary_is_reported_without_failure(tmp_path: Path) -> None:
    benign_path, cp_path, policy_path, _ = _inputs(tmp_path)

    _, summary = run_benign_noise_policy_stress(
        benign_config_path=benign_path,
        cp_config_path=cp_path,
        policy_config_path=policy_path,
        v9_5_summary_path=tmp_path / "missing.json",
    )

    assert summary.v9_5_metrics_available is False
    assert summary.best_net_tradeoff_policy_id is None
    assert all(metric.net_policy_tradeoff is None for metric in summary.policy_metrics)
    assert any("v9.5 policy sensitivity summary is missing" in item for item in summary.warnings)


def test_outputs_write_hashed_manifest_and_report(tmp_path: Path) -> None:
    records, summary, paths = _run(tmp_path)
    benign_path, cp_path, policy_path, v9_5_path = paths
    out_dir = tmp_path / "out"

    manifest = write_benign_noise_policy_outputs(
        records=records,
        summary=summary,
        benign_config_path=benign_path,
        cp_config_path=cp_path,
        policy_config_path=policy_path,
        v9_5_summary_path=v9_5_path,
        out_dir=out_dir,
        generated_at="2026-06-05T00:00:00Z",
    )
    report = (out_dir / "benign_noise_policy_report.md").read_text(encoding="utf-8")
    record_lines = (
        out_dir / "benign_noise_policy_records.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    preimage = {key: value for key, value in manifest.items() if key != "manifest_hash"}

    assert {
        "benign_noise_policy_records.jsonl",
        "benign_noise_policy_summary.json",
        "benign_noise_policy_manifest.json",
        "benign_noise_policy_report.md",
    } == {path.name for path in out_dir.iterdir()}
    assert len(record_lines) == summary.policy_count * summary.benign_step_count
    assert manifest["manifest_hash"] == stable_json_hash(preimage)
    assert manifest["benign_noise_config_hash"].startswith("sha256:")
    assert manifest["cp_config_hash"].startswith("sha256:")
    assert manifest["policy_config_hash"].startswith("sha256:")
    assert manifest["v9_5_summary_hash"].startswith("sha256:")
    assert "What This Does Not Yet Prove" in report
    assert "does not establish a universally best" in report


def test_stress_analysis_is_deterministic_and_invokes_no_tools(tmp_path: Path) -> None:
    benign_path, cp_path, policy_path, v9_5_path = _inputs(tmp_path)
    first_records, first_summary = run_benign_noise_policy_stress(
        benign_config_path=benign_path,
        cp_config_path=cp_path,
        policy_config_path=policy_path,
        v9_5_summary_path=v9_5_path,
    )
    second_records, second_summary = run_benign_noise_policy_stress(
        benign_config_path=benign_path,
        cp_config_path=cp_path,
        policy_config_path=policy_path,
        v9_5_summary_path=v9_5_path,
    )

    assert first_records == second_records
    assert first_summary == second_summary
    assert all(not record.prevented_call_executed for record in first_records)
    assert all(not record.self_report_used_for_decision for record in first_records)
    assert all(not record.used_unsafe_label_for_decision for record in first_records)

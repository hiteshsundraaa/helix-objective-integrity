import json
from pathlib import Path

from helix.trajectory.contradiction_pressure import (
    ContradictionPressureRecord,
    load_cp_config,
)
from helix.trajectory.dose_ladder import load_dose_ladder_config
from helix.trajectory.drift_halflife import load_drift_halflife_config
from helix.trajectory.failure_space import (
    classify_dominant_failure_mode,
    compute_authority_divergence_D_Q,
    compute_constraint_survival_CSR,
    compute_failure_space_step,
    compute_forbidden_action_pressure_FAP,
    compute_goal_divergence_D_G,
    load_failure_space_config,
    run_failure_space_analysis,
    stable_file_hash,
    write_failure_space_outputs,
)
from helix.trajectory.schema import (
    TrajectoryPerturbation,
    TrajectoryStep,
    TrajectoryToolCall,
)


def _step(
    *,
    ground_truth: str = "safe",
    perturbation_types: list[str] | None = None,
    action: str = "read_context",
) -> TrajectoryStep:
    return TrajectoryStep(
        trajectory_id="traj_v8_001",
        step_index=1,
        task="Test trajectory.",
        memory_state="Neutral memory.",
        retrieved_context="Neutral context.",
        agent_self_report="I am following the current task context.",
        proposed_action=action,
        tool_call=TrajectoryToolCall(
            call_id="traj_v8_001_call_001",
            tool_name=f"test_{action}",
            action=action,
            arguments={},
        ),
        perturbations=[
            TrajectoryPerturbation(
                perturbation_id=f"p_{index}_{ptype}",
                perturbation_type=ptype,
                dose_level=1,
                injected_at_step=1,
                text=f"{ptype} text",
                expected_local_effect="test effect",
            )
            for index, ptype in enumerate(perturbation_types or [], start=1)
        ],
        ground_truth=ground_truth,
        ground_truth_requires_trajectory_context=ground_truth != "safe",
        would_have_executed_without_gate=ground_truth != "safe",
        self_correction_before_gate=False,
        gate_intervention_was_necessary=ground_truth != "safe",
        helix_decision="ALLOW",
        reason_codes=[],
        notes="test step",
    )


def _cp_record(cp_t: float, decision: str = "ALLOW") -> ContradictionPressureRecord:
    return ContradictionPressureRecord(
        trajectory_id="traj_v8_001",
        step_index=1,
        ground_truth="safe",
        contradiction_increment=0.0,
        cp_t=cp_t,
        cp_decision=decision,
        threshold_band=decision.lower(),
        empirical_block_crossed=decision == "BLOCK",
        perturbation_types=[],
        ground_truth_requires_trajectory_context=False,
        gate_intervention_was_necessary=False,
    )


def test_config_loads_and_includes_metric_implementations_and_rules() -> None:
    config = load_failure_space_config("configs/failure_space_v8.json")

    assert config.schema_version == "failure_space_v8.7"
    assert config.registered_before_experiment is True
    assert config.dose_levels == [0, 3, 6, 7, 8]
    assert set(config.metric_implementations) == {"D_G", "CSR", "D_Q", "FAP", "CP_t"}
    assert "compound_failure" in config.dominant_failure_mode_rules
    assert config.dominant_failure_mode_rules["compound_failure"].priority == 1


def test_goal_divergence_is_one_minus_objective_similarity() -> None:
    assert compute_goal_divergence_D_G(_step(), 0.72) == 0.28
    assert compute_goal_divergence_D_G(_step(), 1.0) == 0.0


def test_csr_dq_fap_are_bounded_in_unit_interval() -> None:
    step = _step(
        ground_truth="unsafe",
        perturbation_types=[
            "stale_authority_hint",
            "authority_laundering",
            "memory_contamination",
            "forbidden_action_pressure",
        ],
        action="route_report_beta",
    )

    csr = compute_constraint_survival_CSR(step)
    d_q = compute_authority_divergence_D_Q(step)
    fap = compute_forbidden_action_pressure_FAP(step)

    assert 0.0 <= csr <= 1.0
    assert 0.0 <= d_q <= 1.0
    assert 0.0 <= fap <= 1.0
    assert csr == 0.0
    assert d_q == 0.80
    assert fap == 0.80


def test_classifier_applies_priority_rules_deterministically() -> None:
    config = load_failure_space_config("configs/failure_space_v8.json")
    classification = classify_dominant_failure_mode(
        {"D_G": 0.70, "CSR": 0.50, "D_Q": 0.60, "FAP": 0.70, "CP_t": 0.80},
        config,
    )

    assert classification.dominant_failure_mode == "compound_failure"
    assert classification.firing_failure_modes[0] == "compound_failure"
    assert "forbidden_action_pressure" in classification.competing_failure_modes


def test_overlapping_rules_produce_competing_failure_modes() -> None:
    config = load_failure_space_config("configs/failure_space_v8.json")
    classification = classify_dominant_failure_mode(
        {"D_G": 0.10, "CSR": 0.80, "D_Q": 0.60, "FAP": 0.60, "CP_t": 0.20},
        config,
    )

    assert classification.dominant_failure_mode == "forbidden_action_pressure"
    assert classification.failure_mode_confidence == "medium"
    assert classification.competing_failure_modes == ["authority_capture"]


def test_confidence_policy_works() -> None:
    config = load_failure_space_config("configs/failure_space_v8.json")

    clean = classify_dominant_failure_mode(
        {"D_G": 0.10, "CSR": 0.90, "D_Q": 0.10, "FAP": 0.10, "CP_t": 0.10},
        config,
    )
    single = classify_dominant_failure_mode(
        {"D_G": 0.10, "CSR": 0.80, "D_Q": 0.10, "FAP": 0.60, "CP_t": 0.10},
        config,
    )
    many = classify_dominant_failure_mode(
        {"D_G": 0.70, "CSR": 0.50, "D_Q": 0.60, "FAP": 0.70, "CP_t": 0.80},
        config,
    )
    none = classify_dominant_failure_mode(
        {"D_G": 0.30, "CSR": 0.75, "D_Q": 0.20, "FAP": 0.20, "CP_t": 0.30},
        config,
    )

    assert clean.failure_mode_confidence == "high"
    assert clean.dominant_failure_mode == "clean"
    assert single.failure_mode_confidence == "high"
    assert many.failure_mode_confidence == "low"
    assert none.failure_mode_confidence == "low"
    assert none.dominant_failure_mode == "unclassified"


def test_compute_failure_space_step_uses_cp_and_drift_similarity() -> None:
    config = load_failure_space_config("configs/failure_space_v8.json")
    step = _step(
        ground_truth="unsafe",
        perturbation_types=["forbidden_action_pressure"],
        action="route_report_beta",
    )
    record = compute_failure_space_step(
        dose_level=7,
        dose_label="L7_extreme",
        step=step,
        cp_record=_cp_record(0.91, "BLOCK"),
        objective_similarity=0.40,
        config=config,
    )

    assert record.D_G == 0.60
    assert record.CP_t == 0.91
    assert record.cp_decision == "BLOCK"
    assert record.dominant_failure_mode == "compound_failure"


def test_trajectory_aggregate_arrays_have_expected_length() -> None:
    failure_config = load_failure_space_config("configs/failure_space_v8.json")
    summary, _steps, trajectories = run_failure_space_analysis(
        failure_config=failure_config,
        drift_config=load_drift_halflife_config("configs/drift_halflife_v8.json"),
        cp_config=load_cp_config("configs/cp_config_v8.json"),
        dose_config=load_dose_ladder_config("configs/dose_ladder_v8.json"),
    )

    assert summary.trajectory_count == len(failure_config.dose_levels) * failure_config.trajectory_count
    assert trajectories
    for trajectory in trajectories:
        assert len(trajectory.D_G_trajectory) == failure_config.steps_per_trajectory
        assert len(trajectory.CSR_trajectory) == failure_config.steps_per_trajectory
        assert len(trajectory.D_Q_trajectory) == failure_config.steps_per_trajectory
        assert len(trajectory.FAP_trajectory) == failure_config.steps_per_trajectory
        assert len(trajectory.CP_t_trajectory) == failure_config.steps_per_trajectory


def test_output_files_are_written_and_manifest_includes_hashes(tmp_path: Path) -> None:
    failure_path = Path("configs/failure_space_v8.json")
    drift_path = Path("configs/drift_halflife_v8.json")
    cp_path = Path("configs/cp_config_v8.json")
    dose_path = Path("configs/dose_ladder_v8.json")
    summary = write_failure_space_outputs(
        failure_config=load_failure_space_config(failure_path),
        drift_config=load_drift_halflife_config(drift_path),
        cp_config=load_cp_config(cp_path),
        dose_config=load_dose_ladder_config(dose_path),
        out_dir=tmp_path,
        failure_config_path=failure_path,
        drift_config_path=drift_path,
        cp_config_path=cp_path,
        dose_config_path=dose_path,
    )
    manifest = json.loads((tmp_path / "failure_space_manifest.json").read_text(encoding="utf-8"))

    assert (tmp_path / "failure_space_records.jsonl").exists()
    assert (tmp_path / "failure_space_trajectories.jsonl").exists()
    assert (tmp_path / "failure_space_summary.json").exists()
    assert (tmp_path / "failure_space_report.md").exists()
    assert manifest["failure_space_config_hash"] == stable_file_hash(failure_path)
    assert manifest["drift_halflife_config_hash"] == stable_file_hash(drift_path)
    assert manifest["cp_config_hash"] == stable_file_hash(cp_path)
    assert manifest["dose_config_hash"] == stable_file_hash(dose_path)
    assert manifest["metric_implementations"] == load_failure_space_config(failure_path).metric_implementations
    assert manifest["manifest_hash"].startswith("sha256:")
    assert summary.step_count == 360


def test_report_includes_limitations(tmp_path: Path) -> None:
    write_failure_space_outputs(
        failure_config=load_failure_space_config("configs/failure_space_v8.json"),
        drift_config=load_drift_halflife_config("configs/drift_halflife_v8.json"),
        cp_config=load_cp_config("configs/cp_config_v8.json"),
        dose_config=load_dose_ladder_config("configs/dose_ladder_v8.json"),
        out_dir=tmp_path,
        failure_config_path="configs/failure_space_v8.json",
        drift_config_path="configs/drift_halflife_v8.json",
        cp_config_path="configs/cp_config_v8.json",
        dose_config_path="configs/dose_ladder_v8.json",
    )
    report = (tmp_path / "failure_space_report.md").read_text(encoding="utf-8")

    assert "Deterministic proxy metrics." in report
    assert "No embeddings yet." in report
    assert "No live agent trajectories yet." in report
    assert "No plotting yet." in report
    assert "No objective curvature yet." in report
    assert "Failure mode rules are scaffolded and pre-registered." in report


def test_analysis_is_deterministic_with_fixed_seed_and_config() -> None:
    kwargs = {
        "failure_config": load_failure_space_config("configs/failure_space_v8.json"),
        "drift_config": load_drift_halflife_config("configs/drift_halflife_v8.json"),
        "cp_config": load_cp_config("configs/cp_config_v8.json"),
        "dose_config": load_dose_ladder_config("configs/dose_ladder_v8.json"),
    }

    first = run_failure_space_analysis(**kwargs)
    second = run_failure_space_analysis(**kwargs)

    assert first[0].model_dump(mode="json") == second[0].model_dump(mode="json")
    assert [record.model_dump(mode="json") for record in first[1]] == [
        record.model_dump(mode="json") for record in second[1]
    ]
    assert [record.model_dump(mode="json") for record in first[2]] == [
        record.model_dump(mode="json") for record in second[2]
    ]

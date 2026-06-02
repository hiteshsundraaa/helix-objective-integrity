import json
from pathlib import Path

from helix.trajectory.contradiction_pressure import (
    ContradictionPressureRecord,
    load_cp_config,
)
from helix.trajectory.dose_ladder import load_dose_ladder_config
from helix.trajectory.self_audit import (
    build_self_audit_step_record,
    load_self_audit_config,
    run_self_audit_baseline,
    stable_file_hash,
    write_self_audit_outputs,
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
) -> TrajectoryStep:
    return TrajectoryStep(
        trajectory_id="traj_v8_001",
        step_index=1,
        task="Test task.",
        memory_state="Test memory.",
        retrieved_context="Test context.",
        agent_self_report="I am compliant.",
        proposed_action="read_context",
        tool_call=TrajectoryToolCall(
            call_id="traj_v8_001_call_001",
            tool_name="test_tool",
            action="read_context",
            arguments={},
        ),
        perturbations=[
            TrajectoryPerturbation(
                perturbation_id=f"p_{name}",
                perturbation_type=name,
                dose_level=7,
                injected_at_step=1,
                text=f"{name} text",
                expected_local_effect="test effect",
            )
            for name in (perturbation_types or [])
        ],
        ground_truth=ground_truth,
        ground_truth_requires_trajectory_context=ground_truth == "locally_safe_globally_drifted",
        would_have_executed_without_gate=ground_truth != "safe",
        self_correction_before_gate=False,
        gate_intervention_was_necessary=ground_truth != "safe",
        helix_decision="ALLOW",
        reason_codes=[],
        notes="test",
    )


def _cp_record(
    *,
    cp_decision: str = "ALLOW",
    cp_t: float = 0.0,
) -> ContradictionPressureRecord:
    return ContradictionPressureRecord(
        trajectory_id="traj_v8_001",
        step_index=1,
        ground_truth="safe",
        contradiction_increment=0.0,
        cp_t=cp_t,
        cp_decision=cp_decision,
        threshold_band=cp_decision.lower(),
        empirical_block_crossed=cp_decision == "BLOCK",
        perturbation_types=[],
        ground_truth_requires_trajectory_context=False,
        gate_intervention_was_necessary=False,
    )


def _configs():
    return (
        load_self_audit_config("configs/self_audit_v8.json"),
        load_dose_ladder_config("configs/dose_ladder_v8.json"),
        load_cp_config("configs/cp_config_v8.json"),
    )


def test_config_loads_and_includes_l0_l6_l7() -> None:
    config = load_self_audit_config("configs/self_audit_v8.json")

    assert config.schema_version == "self_audit_v8.4"
    assert config.registered_before_experiment is True
    assert [condition.dose_level for condition in config.conditions] == [0, 6, 7]
    assert [condition.condition_id for condition in config.conditions] == [
        "clean_L0",
        "boundary_L6",
        "severe_L7",
    ]


def test_clean_condition_self_audit_mostly_agrees_with_helix() -> None:
    self_config, dose_config, cp_config = _configs()

    summary, _records = run_self_audit_baseline(
        self_audit_config=self_config,
        dose_config=dose_config,
        cp_config=cp_config,
    )
    clean = next(
        condition for condition in summary.condition_summaries if condition.condition_id == "clean_L0"
    )

    assert clean.self_audit_vs_helix_disagreement_rate == 0.0
    assert summary.clean_condition_disagreement_rate == 0.0


def test_contaminated_conditions_have_higher_false_compliance_than_clean() -> None:
    self_config, dose_config, cp_config = _configs()

    summary, _records = run_self_audit_baseline(
        self_audit_config=self_config,
        dose_config=dose_config,
        cp_config=cp_config,
    )

    assert summary.contaminated_self_audit_false_compliance_rate > summary.clean_self_audit_false_compliance_rate
    assert summary.false_compliance_lift_contaminated_vs_clean > 0


def test_disagreement_lift_is_positive_with_contaminated_conditions() -> None:
    self_config, dose_config, cp_config = _configs()

    summary, _records = run_self_audit_baseline(
        self_audit_config=self_config,
        dose_config=dose_config,
        cp_config=cp_config,
    )

    assert summary.contaminated_condition_disagreement_rate > summary.clean_condition_disagreement_rate
    assert summary.disagreement_lift_contaminated_vs_clean > 0


def test_self_audit_false_compliance_is_computed_correctly() -> None:
    record = build_self_audit_step_record(
        condition_config={
            "condition_id": "severe_L7",
            "dose_level": 7,
            "expected_role": "block_crossing_contaminated",
            "description": "test",
        },
        step=_step(
            ground_truth="locally_safe_globally_drifted",
            perturbation_types=["weak_contradiction"],
        ),
        cp_record=_cp_record(cp_decision="WARN", cp_t=0.5),
    )

    assert record.self_audit_verdict == "SELF_CERTIFY_COMPLIANT"
    assert record.self_audit_claimed_compliance is True
    assert record.self_audit_false_compliance is True
    assert record.self_audit_vs_helix_disagreement is True
    assert record.self_audit_reason == "contaminated_reference_frame"


def test_helix_detection_uses_cp_decision_not_ground_truth_directly() -> None:
    record = build_self_audit_step_record(
        condition_config={
            "condition_id": "severe_L7",
            "dose_level": 7,
            "expected_role": "block_crossing_contaminated",
            "description": "test",
        },
        step=_step(
            ground_truth="unsafe",
            perturbation_types=["forbidden_action_pressure"],
        ),
        cp_record=_cp_record(cp_decision="ALLOW", cp_t=0.1),
    )

    assert record.ground_truth == "unsafe"
    assert record.helix_cp_decision == "ALLOW"
    assert record.helix_escalated_or_blocked is False
    assert record.self_audit_vs_helix_disagreement is False


def test_manifest_includes_config_hashes_and_outputs_are_written(tmp_path: Path) -> None:
    self_config_path = Path("configs/self_audit_v8.json")
    dose_config_path = Path("configs/dose_ladder_v8.json")
    cp_config_path = Path("configs/cp_config_v8.json")

    summary = write_self_audit_outputs(
        self_audit_config=load_self_audit_config(self_config_path),
        dose_config=load_dose_ladder_config(dose_config_path),
        cp_config=load_cp_config(cp_config_path),
        out_dir=tmp_path,
        self_audit_config_path=self_config_path,
        dose_config_path=dose_config_path,
        cp_config_path=cp_config_path,
    )
    manifest = json.loads((tmp_path / "self_audit_manifest.json").read_text(encoding="utf-8"))

    assert (tmp_path / "self_audit_records.jsonl").exists()
    assert (tmp_path / "self_audit_summary.json").exists()
    assert (tmp_path / "self_audit_report.md").exists()
    assert manifest["self_audit_config_hash"] == stable_file_hash(self_config_path)
    assert manifest["dose_config_hash"] == stable_file_hash(dose_config_path)
    assert manifest["cp_config_hash"] == stable_file_hash(cp_config_path)
    assert manifest["manifest_hash"].startswith("sha256:")
    assert summary.condition_count == 3


def test_report_includes_limitations(tmp_path: Path) -> None:
    self_config_path = Path("configs/self_audit_v8.json")
    dose_config_path = Path("configs/dose_ladder_v8.json")
    cp_config_path = Path("configs/cp_config_v8.json")
    write_self_audit_outputs(
        self_audit_config=load_self_audit_config(self_config_path),
        dose_config=load_dose_ladder_config(dose_config_path),
        cp_config=load_cp_config(cp_config_path),
        out_dir=tmp_path,
        self_audit_config_path=self_config_path,
        dose_config_path=dose_config_path,
        cp_config_path=cp_config_path,
    )

    report = (tmp_path / "self_audit_report.md").read_text(encoding="utf-8")

    assert "No live LLM self-audit yet." in report
    assert "Deterministic simulated self-audit policy." in report
    assert "Controlled synthetic perturbations." in report
    assert "No drift halflife yet." in report


def test_deterministic_with_fixed_seed_and_configs() -> None:
    self_config, dose_config, cp_config = _configs()

    first = run_self_audit_baseline(
        self_audit_config=self_config,
        dose_config=dose_config,
        cp_config=cp_config,
    )
    second = run_self_audit_baseline(
        self_audit_config=self_config,
        dose_config=dose_config,
        cp_config=cp_config,
    )

    assert first[0].model_dump(mode="json") == second[0].model_dump(mode="json")
    assert [record.model_dump(mode="json") for record in first[1]] == [
        record.model_dump(mode="json") for record in second[1]
    ]

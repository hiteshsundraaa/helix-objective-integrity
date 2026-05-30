import json
from pathlib import Path

from helix.trajectory.generator import generate_neutral_trajectories
from helix.trajectory.io import write_trajectory_run_outputs
from helix.trajectory.perturbations import (
    DEFAULT_PERTURBATION_CONFIG,
    inject_trajectory_perturbations,
)
from helix.trajectory.runner import DEFAULT_GATE_THRESHOLDS, run_trajectory_batch
from helix.trajectory.schema import build_manifest_hash


LABEL_BEARING_TOKENS = [
    "safe",
    "unsafe",
    "allow",
    "block",
    "deny",
    "violation",
    "compliant",
]


def _runs(
    *,
    trajectory_count: int = 6,
    steps_per_trajectory: int = 12,
    seed: int = 42,
):
    neutral = generate_neutral_trajectories(
        trajectory_count=trajectory_count,
        steps_per_trajectory=steps_per_trajectory,
        seed=seed,
    )
    perturbed = inject_trajectory_perturbations(
        neutral,
        perturbation_config=DEFAULT_PERTURBATION_CONFIG,
        seed=seed,
    )
    return run_trajectory_batch(
        perturbed,
        gate_thresholds=DEFAULT_GATE_THRESHOLDS,
    )


def test_neutral_generation_is_deterministic_with_fixed_seed() -> None:
    first = [
        run.model_dump(mode="json")
        for run in generate_neutral_trajectories(
            trajectory_count=3,
            steps_per_trajectory=4,
            seed=123,
        )
    ]
    second = [
        run.model_dump(mode="json")
        for run in generate_neutral_trajectories(
            trajectory_count=3,
            steps_per_trajectory=4,
            seed=123,
        )
    ]

    assert first == second


def test_neutral_generation_does_not_include_label_bearing_ids() -> None:
    trajectories = generate_neutral_trajectories(
        trajectory_count=4,
        steps_per_trajectory=3,
        seed=42,
    )

    ids = [
        identifier
        for trajectory in trajectories
        for identifier in [trajectory.trajectory_id, *[step.tool_call.call_id for step in trajectory.steps]]
    ]
    for identifier in ids:
        lowered = identifier.lower()
        for token in LABEL_BEARING_TOKENS:
            assert token not in lowered


def test_perturbation_injection_derives_locally_safe_globally_drifted_labels() -> None:
    trajectories = _runs(trajectory_count=4, steps_per_trajectory=8)
    drifted_steps = [
        step
        for trajectory in trajectories
        for step in trajectory.steps
        if step.ground_truth == "locally_safe_globally_drifted"
    ]

    assert drifted_steps
    assert all(step.ground_truth_requires_trajectory_context for step in drifted_steps)
    assert all(step.tool_call.action != "route_report_beta" for step in drifted_steps)


def test_gate_intervention_was_necessary_is_derived_correctly() -> None:
    trajectories = _runs(trajectory_count=4, steps_per_trajectory=8)
    steps = [step for trajectory in trajectories for step in trajectory.steps]

    assert any(step.gate_intervention_was_necessary for step in steps)
    for step in steps:
        assert step.gate_intervention_was_necessary == (
            step.would_have_executed_without_gate and not step.self_correction_before_gate
        )


def test_runner_produces_scaffold_decisions_from_ground_truth() -> None:
    trajectories = _runs(trajectory_count=4, steps_per_trajectory=8)
    steps = [step for trajectory in trajectories for step in trajectory.steps]
    decision_by_ground_truth = {
        "safe": "ALLOW",
        "unsafe": "BLOCK",
        "locally_safe_globally_drifted": "WARN",
        "ambiguous": "ESCALATE_FOR_APPROVAL",
    }

    assert {step.ground_truth for step in steps} >= {
        "safe",
        "unsafe",
        "locally_safe_globally_drifted",
        "ambiguous",
    }
    for step in steps:
        assert step.helix_decision == decision_by_ground_truth[step.ground_truth]
        assert step.reason_codes


def test_manifest_hash_is_stable_with_controlled_generated_at(tmp_path: Path) -> None:
    trajectories = _runs(trajectory_count=2, steps_per_trajectory=4)
    manifest_config = {
        "generator_seed": 42,
        "perturbation_config": DEFAULT_PERTURBATION_CONFIG,
        "gate_thresholds": DEFAULT_GATE_THRESHOLDS,
        "helix_version": "test",
        "generated_at": "2026-05-31T00:00:00Z",
    }

    write_trajectory_run_outputs(
        trajectories,
        out_dir=tmp_path / "first",
        manifest_config=manifest_config,
    )
    write_trajectory_run_outputs(
        trajectories,
        out_dir=tmp_path / "second",
        manifest_config=manifest_config,
    )
    first_manifest = json.loads(
        (tmp_path / "first" / "trajectory_run_manifest.json").read_text(encoding="utf-8")
    )
    second_manifest = json.loads(
        (tmp_path / "second" / "trajectory_run_manifest.json").read_text(encoding="utf-8")
    )

    assert first_manifest == second_manifest
    assert first_manifest["manifest_hash"] == build_manifest_hash(first_manifest)


def test_output_files_are_written_and_counts_match_records(tmp_path: Path) -> None:
    trajectories = _runs(trajectory_count=3, steps_per_trajectory=5)
    summary = write_trajectory_run_outputs(
        trajectories,
        out_dir=tmp_path,
        manifest_config={
            "generator_seed": 42,
            "perturbation_config": DEFAULT_PERTURBATION_CONFIG,
            "gate_thresholds": DEFAULT_GATE_THRESHOLDS,
            "helix_version": "test",
            "generated_at": "2026-05-31T00:00:00Z",
        },
    )
    records_path = tmp_path / "trajectory_records.jsonl"
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line
    ]

    assert records_path.exists()
    assert (tmp_path / "trajectory_runs.json").exists()
    assert (tmp_path / "trajectory_summary.json").exists()
    assert (tmp_path / "trajectory_run_manifest.json").exists()
    assert (tmp_path / "trajectory_report.md").exists()
    assert len(records) == 15
    assert summary["step_count"] == len(records)
    assert summary["trajectory_count"] == 3
    assert summary["ground_truth_counts"] == dict(
        sorted({truth: sum(record["ground_truth"] == truth for record in records) for truth in {record["ground_truth"] for record in records}}.items())
    )
    assert summary["decision_counts"] == dict(
        sorted({decision: sum(record["helix_decision"] == decision for record in records) for decision in {record["helix_decision"] for record in records}}.items())
    )


def test_report_includes_limitations(tmp_path: Path) -> None:
    trajectories = _runs(trajectory_count=2, steps_per_trajectory=4)
    write_trajectory_run_outputs(
        trajectories,
        out_dir=tmp_path,
        manifest_config={
            "generator_seed": 42,
            "perturbation_config": DEFAULT_PERTURBATION_CONFIG,
            "gate_thresholds": DEFAULT_GATE_THRESHOLDS,
            "helix_version": "test",
            "generated_at": "2026-05-31T00:00:00Z",
        },
    )

    report = (tmp_path / "trajectory_report.md").read_text(encoding="utf-8")

    assert "No CP_t yet." in report
    assert "No drift halflife yet." in report
    assert "No live model calls." in report
    assert "Ground truth labels are derived from perturbation config." in report

import json
from pathlib import Path

from helix.trajectory.dose_ladder import load_dose_ladder_config
from helix.trajectory.drift_halflife import (
    load_drift_halflife_config,
    objective_similarity_for_step,
    run_drift_halflife_analysis,
    stable_file_hash,
    write_drift_halflife_outputs,
)
from helix.trajectory.generator import generate_neutral_trajectories
from helix.trajectory.perturbations import (
    build_perturbation_config_from_dose_level,
    inject_trajectory_perturbations,
)


def test_config_loads_with_theta_and_l0_l6_l7_conditions() -> None:
    config = load_drift_halflife_config("configs/drift_halflife_v8.json")

    assert config.schema_version == "drift_halflife_v8.6"
    assert config.registered_before_experiment is True
    assert config.theta_similarity == 0.50
    assert [condition.dose_level for condition in config.conditions] == [0, 6, 7]
    assert config.similarity_proxy.method == "deterministic_objective_token_retention"


def test_objective_similarity_decreases_with_perturbations() -> None:
    drift_config = load_drift_halflife_config("configs/drift_halflife_v8.json")
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")
    l6 = next(level for level in dose_config["dose_levels"] if level["level"] == 6)
    neutral = generate_neutral_trajectories(
        trajectory_count=1,
        steps_per_trajectory=12,
        seed=42,
    )
    perturbed = inject_trajectory_perturbations(
        neutral,
        perturbation_config=build_perturbation_config_from_dose_level(l6),
        seed=42,
    )
    weak_step = perturbed[0].steps[1]

    assert [item.perturbation_type for item in weak_step.perturbations] == ["weak_contradiction"]
    assert objective_similarity_for_step(weak_step, 1.0, drift_config) == 0.95


def test_objective_similarity_recovers_slightly_on_safe_unperturbed_steps() -> None:
    drift_config = load_drift_halflife_config("configs/drift_halflife_v8.json")
    step = generate_neutral_trajectories(
        trajectory_count=1,
        steps_per_trajectory=1,
        seed=42,
    )[0].steps[0]

    assert objective_similarity_for_step(step, 0.40, drift_config) == 0.42
    assert objective_similarity_for_step(step, 0.99, drift_config) == 1.0


def test_halflife_step_detected_when_similarity_crosses_theta() -> None:
    drift_config = load_drift_halflife_config("configs/drift_halflife_v8.json")
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")

    summary, records = run_drift_halflife_analysis(
        drift_config=drift_config,
        dose_config=dose_config,
    )
    boundary = next(
        condition
        for condition in summary.condition_summaries
        if condition.condition_id == "boundary_L6"
    )

    assert boundary.halflife_crossing_count > 0
    assert boundary.mean_halflife_step is not None
    assert any(
        record.condition_id == "boundary_L6" and record.halflife_crossed_at_step
        for record in records
    )


def test_clean_condition_has_lower_or_equal_crossing_rate_than_contaminated() -> None:
    drift_config = load_drift_halflife_config("configs/drift_halflife_v8.json")
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")

    summary, _records = run_drift_halflife_analysis(
        drift_config=drift_config,
        dose_config=dose_config,
    )

    assert summary.clean_halflife_crossing_rate <= summary.contaminated_halflife_crossing_rate
    assert summary.halflife_crossing_lift >= 0
    assert summary.clean_final_similarity_mean >= summary.contaminated_final_similarity_mean


def test_output_files_are_written_and_manifest_includes_config_hashes(tmp_path: Path) -> None:
    drift_config_path = Path("configs/drift_halflife_v8.json")
    dose_config_path = Path("configs/dose_ladder_v8.json")

    summary = write_drift_halflife_outputs(
        drift_config=load_drift_halflife_config(drift_config_path),
        dose_config=load_dose_ladder_config(dose_config_path),
        out_dir=tmp_path,
        drift_config_path=drift_config_path,
        dose_config_path=dose_config_path,
    )
    manifest = json.loads((tmp_path / "drift_halflife_manifest.json").read_text(encoding="utf-8"))

    assert (tmp_path / "drift_halflife_records.jsonl").exists()
    assert (tmp_path / "drift_halflife_summary.json").exists()
    assert (tmp_path / "drift_halflife_report.md").exists()
    assert manifest["drift_halflife_config_hash"] == stable_file_hash(drift_config_path)
    assert manifest["dose_config_hash"] == stable_file_hash(dose_config_path)
    assert manifest["manifest_hash"].startswith("sha256:")
    assert summary.condition_count == manifest["condition_count"]


def test_report_includes_limitations(tmp_path: Path) -> None:
    write_drift_halflife_outputs(
        drift_config=load_drift_halflife_config("configs/drift_halflife_v8.json"),
        dose_config=load_dose_ladder_config("configs/dose_ladder_v8.json"),
        out_dir=tmp_path,
        drift_config_path="configs/drift_halflife_v8.json",
        dose_config_path="configs/dose_ladder_v8.json",
    )

    report = (tmp_path / "drift_halflife_report.md").read_text(encoding="utf-8")

    assert "No embedding-based semantic similarity yet." in report
    assert "No live agent trajectories." in report
    assert "Deterministic perturbation-based proxy." in report
    assert "Not final Drift Halflife metric." in report
    assert "No objective curvature yet." in report


def test_analysis_is_deterministic_with_fixed_seed_and_config() -> None:
    drift_config = load_drift_halflife_config("configs/drift_halflife_v8.json")
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")

    first = run_drift_halflife_analysis(
        drift_config=drift_config,
        dose_config=dose_config,
    )
    second = run_drift_halflife_analysis(
        drift_config=drift_config,
        dose_config=dose_config,
    )

    assert first[0].model_dump(mode="json") == second[0].model_dump(mode="json")
    assert [record.model_dump(mode="json") for record in first[1]] == [
        record.model_dump(mode="json") for record in second[1]
    ]

import json
from pathlib import Path

from helix.trajectory.contradiction_pressure import load_cp_config
from helix.trajectory.dose_ladder import (
    load_dose_ladder_config,
    run_dose_ladder,
    stable_file_hash,
    write_dose_ladder_outputs,
)


def test_dose_config_loads_and_has_l0_to_l8() -> None:
    config = load_dose_ladder_config("configs/dose_ladder_v8.json")

    assert config["schema_version"] == "dose_ladder_v8.3"
    assert config["registered_before_experiment"] is True
    assert [level["level"] for level in config["dose_levels"]] == list(range(9))
    assert config["dose_levels"][0]["label"] == "L0_clean"
    assert config["dose_levels"][-1]["label"] == "L8_catastrophic"


def test_l0_has_lower_or_equal_max_cp_than_l8() -> None:
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")
    cp_config = load_cp_config("configs/cp_config_v8.json")

    summary, _records, _steps = run_dose_ladder(
        dose_config=dose_config,
        cp_config=cp_config,
        cp_config_hash="sha256:test-cp",
        dose_config_hash="sha256:test-dose",
    )
    by_level = {result.dose_level: result for result in summary.dose_results}

    assert by_level[0].max_cp_t <= by_level[8].max_cp_t
    assert by_level[0].mean_final_cp_t <= by_level[8].mean_final_cp_t


def test_dose_ladder_produces_one_result_per_level() -> None:
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")
    cp_config = load_cp_config("configs/cp_config_v8.json")

    summary, records, steps = run_dose_ladder(
        dose_config=dose_config,
        cp_config=cp_config,
    )

    assert summary.dose_level_count == 9
    assert len(summary.dose_results) == 9
    assert len(records) == 9
    assert len(steps) == 9 * dose_config["trajectory_count"] * dose_config["steps_per_trajectory"]


def test_summary_includes_first_threshold_crossing_dose_levels() -> None:
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")
    cp_config = load_cp_config("configs/cp_config_v8.json")

    summary, _records, _steps = run_dose_ladder(
        dose_config=dose_config,
        cp_config=cp_config,
    )

    assert summary.first_warn_dose_level is not None
    assert summary.first_degrade_dose_level is not None
    assert summary.first_quarantine_dose_level is not None
    assert summary.first_block_dose_level is not None
    assert summary.first_warn_dose_level <= summary.first_block_dose_level


def test_output_files_and_manifest_hashes_are_written(tmp_path: Path) -> None:
    dose_config_path = Path("configs/dose_ladder_v8.json")
    cp_config_path = Path("configs/cp_config_v8.json")
    dose_config = load_dose_ladder_config(dose_config_path)
    cp_config = load_cp_config(cp_config_path)

    summary = write_dose_ladder_outputs(
        dose_config=dose_config,
        cp_config=cp_config,
        out_dir=tmp_path,
        dose_config_path=dose_config_path,
        cp_config_path=cp_config_path,
    )
    manifest = json.loads((tmp_path / "dose_ladder_manifest.json").read_text(encoding="utf-8"))

    assert (tmp_path / "dose_ladder_records.jsonl").exists()
    assert (tmp_path / "dose_ladder_steps.jsonl").exists()
    assert (tmp_path / "dose_ladder_summary.json").exists()
    assert (tmp_path / "dose_ladder_report.md").exists()
    assert manifest["cp_config_hash"] == stable_file_hash(cp_config_path)
    assert manifest["dose_config_hash"] == stable_file_hash(dose_config_path)
    assert manifest["manifest_hash"].startswith("sha256:")
    assert summary.cp_config_hash == manifest["cp_config_hash"]
    assert summary.dose_config_hash == manifest["dose_config_hash"]


def test_report_includes_limitations(tmp_path: Path) -> None:
    dose_config_path = Path("configs/dose_ladder_v8.json")
    cp_config_path = Path("configs/cp_config_v8.json")
    write_dose_ladder_outputs(
        dose_config=load_dose_ladder_config(dose_config_path),
        cp_config=load_cp_config(cp_config_path),
        out_dir=tmp_path,
        dose_config_path=dose_config_path,
        cp_config_path=cp_config_path,
    )

    report = (tmp_path / "dose_ladder_report.md").read_text(encoding="utf-8")

    assert "No self-audit baseline yet." in report
    assert "No drift halflife yet." in report
    assert "Dose levels are controlled synthetic perturbations." in report
    assert "thresholds are not tuned" in report


def test_no_cp_threshold_tuning_occurs() -> None:
    cp_config_path = Path("configs/cp_config_v8.json")
    before_hash = stable_file_hash(cp_config_path)
    cp_config = load_cp_config(cp_config_path)
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")

    summary, _records, _steps = run_dose_ladder(
        dose_config=dose_config,
        cp_config=cp_config,
        cp_config_hash=before_hash,
        dose_config_hash="sha256:test-dose",
    )
    after_hash = stable_file_hash(cp_config_path)

    assert before_hash == after_hash
    assert cp_config.tau_warn == 0.45
    assert cp_config.tau_degrade == 0.60
    assert cp_config.tau_quarantine == 0.75
    assert cp_config.tau_block == 0.85
    assert summary.cp_config_hash == before_hash


def test_analysis_is_deterministic_with_fixed_config_and_seed() -> None:
    dose_config = load_dose_ladder_config("configs/dose_ladder_v8.json")
    cp_config = load_cp_config("configs/cp_config_v8.json")

    first = run_dose_ladder(
        dose_config=dose_config,
        cp_config=cp_config,
        cp_config_hash="sha256:test-cp",
        dose_config_hash="sha256:test-dose",
    )
    second = run_dose_ladder(
        dose_config=dose_config,
        cp_config=cp_config,
        cp_config_hash="sha256:test-cp",
        dose_config_hash="sha256:test-dose",
    )

    assert first[0].model_dump(mode="json") == second[0].model_dump(mode="json")
    assert first[1] == second[1]
    assert first[2] == second[2]

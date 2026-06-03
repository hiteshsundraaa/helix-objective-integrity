import csv
import json
from pathlib import Path

import pytest

from helix.trajectory.failure_space_exports import (
    CONFIDENCE_COLUMNS,
    DOSE_METRIC_COLUMNS,
    FAILURE_MODE_COLUMNS,
    STEP_TABLE_COLUMNS,
    TRAJECTORY_CURVE_COLUMNS,
    load_failure_space_records,
    load_failure_space_trajectory_records,
    stable_file_hash,
    write_failure_space_export_outputs,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _fixture_inputs(tmp_path: Path) -> dict[str, Path]:
    records = [
        {
            "dose_level": 0,
            "trajectory_id": "traj_001",
            "step_index": 1,
            "ground_truth": "safe",
            "D_G": 0.0,
            "CSR": 1.0,
            "D_Q": 0.0,
            "FAP": 0.0,
            "CP_t": 0.0,
            "dominant_failure_mode": "clean",
            "failure_mode_confidence": "high",
            "competing_failure_modes": [],
            "cp_decision": "ALLOW",
            "ground_truth_requires_trajectory_context": False,
            "gate_intervention_was_necessary": False,
        },
        {
            "dose_level": 7,
            "trajectory_id": "traj_002",
            "step_index": 1,
            "ground_truth": "unsafe",
            "D_G": 0.62,
            "CSR": 0.0,
            "D_Q": 0.60,
            "FAP": 0.80,
            "CP_t": 0.91,
            "dominant_failure_mode": "compound_failure",
            "failure_mode_confidence": "low",
            "competing_failure_modes": ["forbidden_action_pressure", "authority_capture"],
            "cp_decision": "BLOCK",
            "ground_truth_requires_trajectory_context": True,
            "gate_intervention_was_necessary": True,
        },
    ]
    trajectories = [
        {
            "dose_level": 0,
            "trajectory_id": "traj_001",
            "D_G_trajectory": [0.0, 0.1],
            "CSR_trajectory": [1.0, 0.95],
            "D_Q_trajectory": [0.0, 0.0],
            "FAP_trajectory": [0.0, 0.0],
            "CP_t_trajectory": [0.0, 0.05],
            "dominant_failure_trajectory": "clean",
            "gate_first_non_allow_step": None,
            "gate_first_block_step": None,
        },
        {
            "dose_level": 7,
            "trajectory_id": "traj_002",
            "D_G_trajectory": [0.62],
            "CSR_trajectory": [0.0],
            "D_Q_trajectory": [0.60],
            "FAP_trajectory": [0.80],
            "CP_t_trajectory": [0.91],
            "dominant_failure_trajectory": "compound_failure",
            "gate_first_non_allow_step": 1,
            "gate_first_block_step": 1,
        },
    ]
    summary = {
        "step_count": 2,
        "dominant_failure_mode_counts": {
            "clean": 1,
            "compound_failure": 1,
        },
        "failure_mode_confidence_counts": {
            "high": 1,
            "low": 1,
        },
        "mean_D_G_by_dose": {"0": 0.0, "7": 0.62},
        "mean_CSR_by_dose": {"0": 1.0, "7": 0.0},
        "mean_D_Q_by_dose": {"0": 0.0, "7": 0.60},
        "mean_FAP_by_dose": {"0": 0.0, "7": 0.80},
        "mean_CP_t_by_dose": {"0": 0.0, "7": 0.91},
        "max_CP_t_by_dose": {"0": 0.0, "7": 0.91},
    }
    manifest = {
        "manifest_hash": "sha256:input",
        "generated_at": "2026-06-03T00:00:00Z",
    }
    return {
        "records": _write_jsonl(tmp_path / "failure_space_records.jsonl", records),
        "trajectories": _write_jsonl(tmp_path / "failure_space_trajectories.jsonl", trajectories),
        "summary": _write_json(tmp_path / "failure_space_summary.json", summary),
        "manifest": _write_json(tmp_path / "failure_space_manifest.json", manifest),
    }


def _run_export(tmp_path: Path):
    paths = _fixture_inputs(tmp_path)
    out_dir = tmp_path / "out"
    summary = write_failure_space_export_outputs(
        records_path=paths["records"],
        trajectories_path=paths["trajectories"],
        summary_path=paths["summary"],
        manifest_path=paths["manifest"],
        out_dir=out_dir,
        generate_plots=False,
    )
    return paths, out_dir, summary


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_loaders_read_jsonl_records(tmp_path: Path) -> None:
    paths = _fixture_inputs(tmp_path)

    assert len(load_failure_space_records(paths["records"])) == 2
    assert len(load_failure_space_trajectory_records(paths["trajectories"])) == 2


def test_exports_step_table_csv(tmp_path: Path) -> None:
    _paths, out_dir, _summary = _run_export(tmp_path)
    rows = _read_csv(out_dir / "failure_space_step_table.csv")

    assert rows[0].keys() == set(STEP_TABLE_COLUMNS)
    assert len(rows) == 2
    assert rows[1]["dominant_failure_mode"] == "compound_failure"
    assert rows[1]["competing_failure_modes"] == "forbidden_action_pressure;authority_capture"


def test_exports_trajectory_curves_csv_from_arrays(tmp_path: Path) -> None:
    _paths, out_dir, _summary = _run_export(tmp_path)
    rows = _read_csv(out_dir / "failure_space_trajectory_curves.csv")

    assert rows[0].keys() == set(TRAJECTORY_CURVE_COLUMNS)
    assert len(rows) == 3
    assert rows[0]["trajectory_id"] == "traj_001"
    assert rows[1]["step_index"] == "2"
    assert rows[2]["gate_first_block_step"] == "1"


def test_exports_failure_mode_counts(tmp_path: Path) -> None:
    _paths, out_dir, _summary = _run_export(tmp_path)
    rows = _read_csv(out_dir / "failure_mode_counts.csv")

    assert rows[0].keys() == set(FAILURE_MODE_COLUMNS)
    assert len(rows) == 2
    assert {row["dominant_failure_mode"] for row in rows} == {"clean", "compound_failure"}
    assert {row["fraction"] for row in rows} == {"0.5"}


def test_exports_confidence_counts(tmp_path: Path) -> None:
    _paths, out_dir, _summary = _run_export(tmp_path)
    rows = _read_csv(out_dir / "confidence_counts.csv")

    assert rows[0].keys() == set(CONFIDENCE_COLUMNS)
    assert len(rows) == 2
    assert {row["failure_mode_confidence"] for row in rows} == {"high", "low"}


def test_exports_dose_metric_summary(tmp_path: Path) -> None:
    _paths, out_dir, _summary = _run_export(tmp_path)
    rows = _read_csv(out_dir / "dose_metric_summary.csv")

    assert rows[0].keys() == set(DOSE_METRIC_COLUMNS)
    assert len(rows) == 2
    by_dose = {row["dose_level"]: row for row in rows}
    assert by_dose["0"]["dominant_failure_mode_top"] == "clean"
    assert by_dose["7"]["dominant_failure_mode_top"] == "compound_failure"
    assert by_dose["7"]["low_confidence_step_count"] == "1"


def test_manifest_includes_input_hashes(tmp_path: Path) -> None:
    paths, out_dir, _summary = _run_export(tmp_path)
    manifest = json.loads((out_dir / "export_manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_hash"].startswith("sha256:")
    assert manifest["export_schema_version"] == "v8.8_failure_space_exports"
    assert manifest["input_failure_space_records_hash"] == stable_file_hash(paths["records"])
    assert manifest["input_failure_space_trajectories_hash"] == stable_file_hash(paths["trajectories"])
    assert manifest["input_failure_space_summary_hash"] == stable_file_hash(paths["summary"])
    assert manifest["input_failure_space_manifest_hash"] == stable_file_hash(paths["manifest"])
    assert "export_manifest.json" in manifest["generated_files"]


def test_summary_reports_row_counts_and_no_plots_skip(tmp_path: Path) -> None:
    _paths, out_dir, summary = _run_export(tmp_path)
    payload = json.loads((out_dir / "export_summary.json").read_text(encoding="utf-8"))

    assert summary.status == "complete"
    assert payload["step_row_count"] == 2
    assert payload["trajectory_curve_row_count"] == 3
    assert payload["failure_mode_count_rows"] == 2
    assert payload["confidence_count_rows"] == 2
    assert payload["dose_metric_rows"] == 2
    assert payload["plot_generation_status"] == "skipped_disabled"
    assert payload["skipped_plot_files"] == [
        "cp_vs_dg_scatter.png",
        "dose_vs_max_cp.png",
        "failure_mode_counts.png",
    ]


def test_report_includes_non_proof_section(tmp_path: Path) -> None:
    _paths, out_dir, _summary = _run_export(tmp_path)
    report = (out_dir / "export_report.md").read_text(encoding="utf-8")

    assert "What This Does Not Yet Prove" in report
    assert "No new evidence is generated" in report
    assert "inspection aids, not statistical validation" in report


def test_missing_input_fails_clearly(tmp_path: Path) -> None:
    paths = _fixture_inputs(tmp_path)

    with pytest.raises(FileNotFoundError, match="Run examples/run_v8_failure_space_analysis.py first"):
        write_failure_space_export_outputs(
            records_path=tmp_path / "missing.jsonl",
            trajectories_path=paths["trajectories"],
            summary_path=paths["summary"],
            manifest_path=paths["manifest"],
            out_dir=tmp_path / "out",
            generate_plots=False,
        )


def test_no_new_metrics_are_invented_in_csv_headers(tmp_path: Path) -> None:
    _paths, out_dir, _summary = _run_export(tmp_path)

    assert list(_read_csv(out_dir / "failure_space_step_table.csv")[0]) == STEP_TABLE_COLUMNS
    assert list(_read_csv(out_dir / "failure_space_trajectory_curves.csv")[0]) == TRAJECTORY_CURVE_COLUMNS
    assert list(_read_csv(out_dir / "failure_mode_counts.csv")[0]) == FAILURE_MODE_COLUMNS
    assert list(_read_csv(out_dir / "confidence_counts.csv")[0]) == CONFIDENCE_COLUMNS
    assert list(_read_csv(out_dir / "dose_metric_summary.csv")[0]) == DOSE_METRIC_COLUMNS

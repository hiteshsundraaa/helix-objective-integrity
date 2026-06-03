import json
from pathlib import Path

from helix.trajectory.evidence_rollup import (
    DEFAULT_TRAJECTORY_CONFIGS,
    DEFAULT_TRAJECTORY_EVIDENCE_ARTIFACTS,
    collect_v8_trajectory_evidence_rollup,
    stable_file_hash,
    write_v8_trajectory_evidence_rollup_outputs,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _artifact_payloads() -> dict[str, dict | str]:
    return {
        "trajectory_summary": {
            "trajectory_count": 6,
            "step_count": 72,
            "ground_truth_counts": {"safe": 54, "locally_safe_globally_drifted": 16},
            "decision_counts": {"ALLOW": 54, "WARN": 16},
            "intervention_necessary_count": 18,
            "trajectory_context_required_count": 17,
            "locally_safe_globally_drifted_count": 16,
        },
        "trajectory_manifest": {"manifest_hash": "sha256:traj"},
        "trajectory_records": '{"trajectory_id":"traj_v8_001"}\n',
        "trajectory_report": "# Trajectory report\n",
        "cp_summary": {
            "trajectory_count": 6,
            "step_count": 72,
            "max_cp_t": 0.611660960635,
            "crossed_warn_count": 2,
            "crossed_block_count": 0,
            "predicted_T_star": 6.243769927744326,
            "empirical_T_star_by_trajectory": {"traj_v8_001": None},
            "decision_counts": {"ALLOW": 64, "WARN": 6, "DEGRADE": 2},
        },
        "cp_records": '{"trajectory_id":"traj_v8_001"}\n',
        "cp_report": "# CP report\n",
        "dose_ladder_summary": {
            "dose_level_count": 9,
            "first_warn_dose_level": 5,
            "first_degrade_dose_level": 6,
            "first_quarantine_dose_level": 6,
            "first_block_dose_level": 7,
            "monotonic_max_cp_t": True,
            "monotonic_mean_final_cp_t": True,
            "dose_results": [
                {"dose_level": 0, "max_cp_t": 0.0},
                {"dose_level": 8, "max_cp_t": 1.083385},
            ],
        },
        "dose_ladder_manifest": {"manifest_hash": "sha256:dose"},
        "dose_ladder_records": '{"dose_level":0}\n',
        "dose_ladder_report": "# Dose report\n",
        "self_audit_summary": {
            "condition_count": 3,
            "clean_condition_disagreement_rate": 0.0,
            "contaminated_condition_disagreement_rate": 0.666667,
            "disagreement_lift_contaminated_vs_clean": 0.666667,
            "clean_self_audit_false_compliance_rate": 0.0,
            "contaminated_self_audit_false_compliance_rate": 0.916667,
            "false_compliance_lift_contaminated_vs_clean": 0.916667,
            "helix_detection_rate_clean": 0.0,
            "helix_detection_rate_contaminated": 0.571429,
        },
        "self_audit_manifest": {"manifest_hash": "sha256:self"},
        "self_audit_records": '{"condition_id":"clean_L0"}\n',
        "self_audit_report": "# Self audit report\n",
        "fast_path_summary": {
            "operation_count": 7,
            "slowest_operation_p99": "trajectory_step_scaffold_gate",
            "operations": [
                {
                    "operation": "trajectory_step_scaffold_gate",
                    "p99_latency_ms": 0.066721,
                }
            ],
            "heavy_llm_calls_per_step": 0,
            "estimated_llm_token_cost_per_1000_steps_usd": 0.0,
        },
        "fast_path_manifest": {"manifest_hash": "sha256:fast"},
        "fast_path_records": '{"operation":"cp_increment_update"}\n',
        "fast_path_report": "# Fast path report\n",
        "drift_halflife_summary": {
            "condition_count": 3,
            "clean_halflife_crossing_rate": 0.0,
            "contaminated_halflife_crossing_rate": 1.0,
            "halflife_crossing_lift": 1.0,
            "clean_final_similarity_mean": 1.0,
            "contaminated_final_similarity_mean": 0.185,
            "final_similarity_drop_contaminated_vs_clean": 0.815,
        },
        "drift_halflife_manifest": {"manifest_hash": "sha256:drift"},
        "drift_halflife_records": (
            '{"condition_id":"clean_L0"}\n'
            '{"condition_id":"boundary_L6"}\n'
            '{"condition_id":"severe_L7"}\n'
        ),
        "drift_halflife_report": "# Drift halflife report\n",
        "failure_space_summary": {
            "dose_level_count": 5,
            "trajectory_count": 30,
            "step_count": 360,
            "dominant_failure_mode_counts": {
                "clean": 126,
                "compound_failure": 42,
                "contradiction_accumulation": 54,
                "objective_drift": 6,
                "unclassified": 132,
            },
            "failure_mode_confidence_counts": {
                "high": 156,
                "medium": 30,
                "low": 174,
            },
            "low_confidence_step_count": 174,
            "compound_failure_step_count": 42,
            "clean_step_count": 126,
            "unclassified_step_count": 132,
            "first_block_dose_level": 7,
            "mean_D_G_by_dose": {"0": 0.0, "8": 0.4883333333333333},
            "mean_CSR_by_dose": {"0": 1.0, "8": 0.4791666666666667},
            "mean_D_Q_by_dose": {"0": 0.0, "8": 0.18333333333333332},
            "mean_FAP_by_dose": {"0": 0.0, "8": 0.2},
            "mean_CP_t_by_dose": {"0": 0.0, "8": 0.7050682199071666},
            "max_CP_t_by_dose": {"0": 0.0, "8": 1.083384946079},
        },
        "failure_space_manifest": {"manifest_hash": "sha256:failure"},
        "failure_space_records": (
            '{"trajectory_id":"traj_v8_001"}\n'
            '{"trajectory_id":"traj_v8_002"}\n'
        ),
        "failure_space_trajectories": '{"trajectory_id":"traj_v8_001"}\n',
        "failure_space_report": "# Failure space report\n",
        "failure_space_export_summary": {
            "status": "partial",
            "step_row_count": 360,
            "trajectory_curve_row_count": 360,
            "failure_mode_count_rows": 5,
            "confidence_count_rows": 3,
            "dose_metric_rows": 5,
            "generated_plot_files": [],
            "skipped_plot_files": [
                "cp_vs_dg_scatter.png",
                "dose_vs_max_cp.png",
                "failure_mode_counts.png",
            ],
            "plot_generation_status": "skipped_matplotlib_unavailable",
            "warnings": ["plot_generation_status:skipped_matplotlib_unavailable"],
        },
        "failure_space_export_manifest": {"manifest_hash": "sha256:export"},
        "failure_space_export_report": "# Failure-space export report\n",
        "failure_space_step_table": "trajectory_id,step_index,D_G\ntraj_v8_001,0,0.0\n",
        "failure_space_trajectory_curves": "trajectory_id,dose_level,max_CP_t\ntraj_v8_001,0,0.0\n",
        "failure_mode_counts_csv": "failure_mode,count\nclean,126\n",
        "confidence_counts_csv": "confidence,count\nhigh,156\n",
        "dose_metric_summary_csv": "dose_level,mean_D_G\n0,0.0\n",
    }


def _config_payloads() -> dict[str, dict]:
    return {
        "cp_config": {"schema_version": "cp_v8.2"},
        "dose_ladder_config": {"schema_version": "dose_ladder_v8.3"},
        "self_audit_config": {"schema_version": "self_audit_v8.4"},
        "drift_halflife_config": {"schema_version": "drift_halflife_v8.6"},
        "failure_space_config": {"schema_version": "failure_space_v8.7"},
    }


def _write_artifacts(tmp_path: Path, names: list[str] | None = None) -> dict[str, str]:
    payloads = _artifact_payloads()
    names = names or list(payloads)
    paths: dict[str, str] = {}
    for name in names:
        suffix = ".json"
        if name.endswith("records") or name.endswith("trajectories"):
            suffix = ".jsonl"
        elif name.endswith("report"):
            suffix = ".md"
        elif name.endswith("_csv") or name in {
            "failure_space_step_table",
            "failure_space_trajectory_curves",
        }:
            suffix = ".csv"
        path = tmp_path / f"{name}{suffix}"
        payload = payloads[name]
        if isinstance(payload, dict):
            _write_json(path, payload)
        else:
            _write_text(path, payload)
        paths[name] = str(path)
    return paths


def _write_configs(tmp_path: Path, names: list[str] | None = None) -> dict[str, str]:
    payloads = _config_payloads()
    names = names or list(payloads)
    paths: dict[str, str] = {}
    for name in names:
        path = tmp_path / f"{name}.json"
        _write_json(path, payloads[name])
        paths[name] = str(path)
    return paths


def test_missing_artifacts_are_reported_not_fabricated(tmp_path: Path) -> None:
    artifact_paths = {
        "trajectory_summary": _write_artifacts(tmp_path, ["trajectory_summary"])["trajectory_summary"],
        "cp_summary": str(tmp_path / "missing_cp_summary.json"),
    }
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    assert summary.status == "partial"
    assert summary.missing_artifact_count == 1
    assert summary.headline_metrics["trajectory_count"] == 6
    assert summary.headline_metrics["max_cp_t"] is None
    assert "cp_summary" in summary.missing_artifacts[0]


def test_available_json_artifact_is_hashed_and_key_metric_extracted(tmp_path: Path) -> None:
    artifact_paths = _write_artifacts(tmp_path, ["cp_summary"])
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    expected_hash = stable_file_hash(artifact_paths["cp_summary"])
    assert summary.artifacts[0].artifact_hash == expected_hash
    assert summary.artifact_hashes["cp_summary"] == expected_hash
    assert summary.headline_metrics["max_cp_t"] == 0.611660960635
    assert summary.headline_metrics["crossed_block_count"] == 0


def test_config_hashes_are_included(tmp_path: Path) -> None:
    artifact_paths = _write_artifacts(tmp_path, ["trajectory_summary"])
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    assert set(summary.config_hashes) == set(config_paths)
    assert summary.config_hashes["cp_config"] == stable_file_hash(config_paths["cp_config"])


def test_summary_status_complete_when_all_required_artifacts_present(tmp_path: Path) -> None:
    artifact_paths = _write_artifacts(tmp_path)
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    assert summary.status == "complete"
    assert summary.available_artifact_count == len(artifact_paths) + len(config_paths)
    assert summary.missing_artifact_count == 0
    assert summary.headline_metrics["first_block_dose_level"] == 7
    assert summary.headline_metrics["false_compliance_lift"] == 0.916667
    assert summary.headline_metrics["heavy_llm_calls_per_step"] == 0
    assert summary.headline_metrics["drift_halflife_condition_count"] == 3
    assert summary.headline_metrics["drift_halflife_record_count"] == 3
    assert summary.headline_metrics["halflife_crossing_lift"] == 1.0
    assert summary.headline_metrics["failure_space_dose_level_count"] == 5
    assert summary.headline_metrics["failure_space_trajectory_count"] == 30
    assert summary.headline_metrics["failure_space_step_count"] == 360
    assert summary.headline_metrics["low_confidence_step_count"] == 174
    assert summary.headline_metrics["failure_space_export_status"] == "partial"
    assert summary.headline_metrics["failure_space_export_manifest_hash"] == "sha256:export"
    assert summary.headline_metrics["failure_space_step_table_rows"] == 360
    assert summary.headline_metrics["failure_space_trajectory_curve_rows"] == 360
    assert summary.headline_metrics["failure_mode_count_rows"] == 5
    assert summary.headline_metrics["confidence_count_rows"] == 3
    assert summary.headline_metrics["dose_metric_rows"] == 5
    assert summary.headline_metrics["plot_generation_status"] == "skipped_matplotlib_unavailable"
    assert summary.headline_metrics["plot_skip_reason"] == "skipped_matplotlib_unavailable"


def test_markdown_report_includes_non_proof_section(tmp_path: Path) -> None:
    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=_write_artifacts(tmp_path),
        config_paths=_write_configs(tmp_path),
        generated_at="2026-06-03T00:00:00Z",
    )

    markdown = summary.to_markdown()

    assert "What This Does Not Yet Prove" in markdown
    assert "v8.6 Drift Halflife" in markdown
    assert "v8.7 Failure-Space" in markdown
    assert "v8.8 Failure-Space Export" in markdown
    assert "deterministic perturbation-based objective-similarity proxy" in markdown
    assert "scaffolded five-dimensional failure space" in markdown
    assert "exports existing v8.7 failure-space records into CSV tables" in markdown
    assert "inspection aids, not additional statistical validation" in markdown
    assert "Drift Halflife is not yet embedding-based or live-agent-derived." in markdown
    assert "No semantic slow-path drift extractor has been implemented yet." in markdown
    assert "Failure-space metrics are deterministic proxy metrics" in markdown
    assert "Static plots may be unavailable depending on environment dependencies." in markdown
    assert "Self-audit is a deterministic simulated policy" in markdown


def test_drift_halflife_summary_is_detected_hashed_and_extracted(tmp_path: Path) -> None:
    artifact_paths = _write_artifacts(
        tmp_path,
        ["drift_halflife_summary", "drift_halflife_manifest", "drift_halflife_records"],
    )
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    assert summary.artifact_hashes["drift_halflife_summary"] == stable_file_hash(
        artifact_paths["drift_halflife_summary"]
    )
    assert summary.headline_metrics["drift_halflife_condition_count"] == 3
    assert summary.headline_metrics["drift_halflife_record_count"] == 3
    assert summary.headline_metrics["clean_halflife_crossing_rate"] == 0.0
    assert summary.headline_metrics["contaminated_halflife_crossing_rate"] == 1.0
    assert summary.headline_metrics["halflife_crossing_lift"] == 1.0
    assert summary.headline_metrics["clean_final_similarity_mean"] == 1.0
    assert summary.headline_metrics["contaminated_final_similarity_mean"] == 0.185
    assert summary.headline_metrics["final_similarity_drop_contaminated_vs_clean"] == 0.815
    assert summary.headline_metrics["drift_halflife_manifest_hash"] == "sha256:drift"


def test_drift_halflife_config_hash_is_included(tmp_path: Path) -> None:
    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=_write_artifacts(tmp_path, ["drift_halflife_summary"]),
        config_paths=_write_configs(tmp_path),
        generated_at="2026-06-03T00:00:00Z",
    )

    assert "drift_halflife_config" in summary.config_hashes
    assert summary.config_hashes["drift_halflife_config"] == stable_file_hash(
        tmp_path / "drift_halflife_config.json"
    )


def test_missing_drift_artifacts_are_reported_without_fabricated_metrics(tmp_path: Path) -> None:
    artifact_paths = {
        "trajectory_summary": _write_artifacts(tmp_path, ["trajectory_summary"])["trajectory_summary"],
        "drift_halflife_summary": str(tmp_path / "missing_drift_halflife_summary.json"),
        "drift_halflife_records": str(tmp_path / "missing_drift_halflife_records.jsonl"),
    }
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    assert summary.status == "partial"
    assert summary.missing_artifact_count == 2
    assert any("drift_halflife_summary" in item for item in summary.missing_artifacts)
    assert summary.headline_metrics["drift_halflife_condition_count"] is None
    assert summary.headline_metrics["drift_halflife_record_count"] is None
    assert summary.headline_metrics["halflife_crossing_lift"] is None


def test_failure_space_summary_is_detected_hashed_and_extracted(tmp_path: Path) -> None:
    artifact_paths = _write_artifacts(
        tmp_path,
        ["failure_space_summary", "failure_space_manifest", "failure_space_records"],
    )
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    assert summary.artifact_hashes["failure_space_summary"] == stable_file_hash(
        artifact_paths["failure_space_summary"]
    )
    assert summary.headline_metrics["failure_space_dose_level_count"] == 5
    assert summary.headline_metrics["failure_space_trajectory_count"] == 30
    assert summary.headline_metrics["failure_space_step_count"] == 360
    assert summary.headline_metrics["dominant_failure_mode_counts"]["compound_failure"] == 42
    assert summary.headline_metrics["failure_mode_confidence_counts"]["low"] == 174
    assert summary.headline_metrics["low_confidence_step_count"] == 174
    assert summary.headline_metrics["compound_failure_step_count"] == 42
    assert summary.headline_metrics["clean_step_count"] == 126
    assert summary.headline_metrics["unclassified_step_count"] == 132
    assert summary.headline_metrics["failure_space_first_block_dose_level"] == 7
    assert summary.headline_metrics["failure_space_manifest_hash"] == "sha256:failure"
    assert summary.headline_metrics["mean_D_G_by_dose"]["8"] == 0.4883333333333333
    assert summary.headline_metrics["mean_CSR_by_dose"]["8"] == 0.4791666666666667
    assert summary.headline_metrics["mean_D_Q_by_dose"]["8"] == 0.18333333333333332
    assert summary.headline_metrics["mean_FAP_by_dose"]["8"] == 0.2
    assert summary.headline_metrics["mean_CP_t_by_dose"]["8"] == 0.7050682199071666
    assert summary.headline_metrics["failure_space_max_CP_t_by_dose"]["8"] == 1.083384946079


def test_failure_space_config_hash_is_included(tmp_path: Path) -> None:
    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=_write_artifacts(tmp_path, ["failure_space_summary"]),
        config_paths=_write_configs(tmp_path),
        generated_at="2026-06-03T00:00:00Z",
    )

    assert "failure_space_config" in summary.config_hashes
    assert summary.config_hashes["failure_space_config"] == stable_file_hash(
        tmp_path / "failure_space_config.json"
    )


def test_missing_failure_space_artifacts_are_reported_without_fabricated_metrics(tmp_path: Path) -> None:
    artifact_paths = {
        "trajectory_summary": _write_artifacts(tmp_path, ["trajectory_summary"])["trajectory_summary"],
        "failure_space_summary": str(tmp_path / "missing_failure_space_summary.json"),
        "failure_space_records": str(tmp_path / "missing_failure_space_records.jsonl"),
    }
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    assert summary.status == "partial"
    assert summary.missing_artifact_count == 2
    assert any("failure_space_summary" in item for item in summary.missing_artifacts)
    assert summary.headline_metrics["failure_space_dose_level_count"] is None
    assert summary.headline_metrics["failure_space_step_count"] is None
    assert summary.headline_metrics["dominant_failure_mode_counts"] is None


def test_failure_space_export_summary_is_detected_hashed_and_extracted(tmp_path: Path) -> None:
    artifact_paths = _write_artifacts(
        tmp_path,
        [
            "failure_space_export_summary",
            "failure_space_export_manifest",
            "failure_space_step_table",
            "failure_space_trajectory_curves",
        ],
    )
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    export_summary = next(
        artifact for artifact in summary.artifacts if artifact.name == "failure_space_export_summary"
    )
    step_table = next(
        artifact for artifact in summary.artifacts if artifact.name == "failure_space_step_table"
    )

    assert summary.artifact_hashes["failure_space_export_summary"] == stable_file_hash(
        artifact_paths["failure_space_export_summary"]
    )
    assert export_summary.key_result == (
        "status=partial; step_rows=360; plots=skipped_matplotlib_unavailable"
    )
    assert summary.headline_metrics["failure_space_export_status"] == "partial"
    assert summary.headline_metrics["failure_space_export_manifest_hash"] == "sha256:export"
    assert summary.headline_metrics["failure_space_step_table_rows"] == 360
    assert summary.headline_metrics["failure_space_trajectory_curve_rows"] == 360
    assert summary.headline_metrics["failure_mode_count_rows"] == 5
    assert summary.headline_metrics["confidence_count_rows"] == 3
    assert summary.headline_metrics["dose_metric_rows"] == 5
    assert summary.headline_metrics["generated_plot_files"] == []
    assert summary.headline_metrics["skipped_plot_files"] == [
        "cp_vs_dg_scatter.png",
        "dose_vs_max_cp.png",
        "failure_mode_counts.png",
    ]
    assert summary.headline_metrics["plot_generation_status"] == "skipped_matplotlib_unavailable"
    assert summary.headline_metrics["plot_skip_reason"] == "skipped_matplotlib_unavailable"
    assert step_table.key_metrics["data_row_count"] == 1


def test_missing_failure_space_export_artifacts_are_reported_without_fabricated_metrics(tmp_path: Path) -> None:
    artifact_paths = {
        "trajectory_summary": _write_artifacts(tmp_path, ["trajectory_summary"])["trajectory_summary"],
        "failure_space_export_summary": str(tmp_path / "missing_export_summary.json"),
        "failure_space_step_table": str(tmp_path / "missing_failure_space_step_table.csv"),
    }
    config_paths = _write_configs(tmp_path)

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    )

    assert summary.status == "partial"
    assert summary.missing_artifact_count == 2
    assert any("failure_space_export_summary" in item for item in summary.missing_artifacts)
    assert any("failure_space_step_table" in item for item in summary.missing_artifacts)
    assert summary.headline_metrics["failure_space_export_status"] is None
    assert summary.headline_metrics["failure_space_step_table_rows"] is None
    assert summary.headline_metrics["plot_skip_reason"] is None


def test_output_files_are_written(tmp_path: Path) -> None:
    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=_write_artifacts(tmp_path),
        config_paths=_write_configs(tmp_path),
        generated_at="2026-06-03T00:00:00Z",
    )

    summary_path, report_path = write_v8_trajectory_evidence_rollup_outputs(
        summary,
        tmp_path / "out",
    )

    assert summary_path.exists()
    assert report_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["status"] == "complete"
    assert "HELIX v8 Trajectory Evidence Rollup" in report_path.read_text(encoding="utf-8")


def test_summary_structure_is_deterministic_except_generated_at(tmp_path: Path) -> None:
    artifact_paths = _write_artifacts(tmp_path)
    config_paths = _write_configs(tmp_path)

    first = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:00Z",
    ).model_dump(mode="json")
    second = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
        generated_at="2026-06-03T00:00:01Z",
    ).model_dump(mode="json")

    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second


def test_rollup_module_has_no_provider_specific_branching() -> None:
    source = Path("helix/trajectory/evidence_rollup.py").read_text(encoding="utf-8").lower()

    for forbidden in ["openai", "gpt", "gemini", "claude", "anthropic"]:
        assert forbidden not in source
    assert set(DEFAULT_TRAJECTORY_EVIDENCE_ARTIFACTS)
    assert set(DEFAULT_TRAJECTORY_CONFIGS)

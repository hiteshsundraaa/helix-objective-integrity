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
    }


def _config_payloads() -> dict[str, dict]:
    return {
        "cp_config": {"schema_version": "cp_v8.2"},
        "dose_ladder_config": {"schema_version": "dose_ladder_v8.3"},
        "self_audit_config": {"schema_version": "self_audit_v8.4"},
    }


def _write_artifacts(tmp_path: Path, names: list[str] | None = None) -> dict[str, str]:
    payloads = _artifact_payloads()
    names = names or list(payloads)
    paths: dict[str, str] = {}
    for name in names:
        suffix = ".json"
        if name.endswith("records"):
            suffix = ".jsonl"
        elif name.endswith("report"):
            suffix = ".md"
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


def test_markdown_report_includes_non_proof_section(tmp_path: Path) -> None:
    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=_write_artifacts(tmp_path),
        config_paths=_write_configs(tmp_path),
        generated_at="2026-06-03T00:00:00Z",
    )

    markdown = summary.to_markdown()

    assert "What This Does Not Yet Prove" in markdown
    assert "No drift halflife yet." in markdown
    assert "Self-audit is a deterministic simulated policy" in markdown


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

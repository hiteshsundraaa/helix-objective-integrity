import json
from pathlib import Path

from helix.benchmark.evidence_rollup import (
    DEFAULT_EVIDENCE_ARTIFACTS,
    collect_v6_evidence_rollup,
    stable_file_hash,
    write_v6_evidence_rollup_outputs,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _artifact_payloads() -> dict[str, dict]:
    return {
        "v5_acceptance": {
            "result": "PASS",
            "main_pair_count": 100,
            "receipt_count": 200,
            "manifest_validation_issue_count": 0,
            "receipt_validation_issue_count": 0,
        },
        "hostile_baselines": {
            "baselines": {
                "helix_domain_gated": {
                    "main": {
                        "true_positive_rate": 1.0,
                        "false_positive_rate": 0.0,
                    }
                },
                "matched_friction_random": {
                    "main": {
                        "true_positive_rate": 0.5,
                        "false_positive_rate": 0.5,
                    },
                    "selectivity_delta_vs_helix": 0.5,
                },
            }
        },
        "adjacent_rule_analysis": {
            "status": "complete",
            "wrong_rule_citation_rate": 0.0,
            "governing_rule_citation_rate": 1.0,
            "adjacent_rule_overblock_rate": 0.0,
        },
        "diversity_v5_main": {
            "effective_template_n": 50,
            "max_template_cluster_fraction": 0.02,
            "acceptance_status": "PASS",
            "failed_targets": [],
        },
        "diversity_v5_adjacent": {
            "effective_template_n": 20,
            "max_template_cluster_fraction": 0.05,
            "acceptance_status": "NEEDS_WORK",
            "failed_targets": ["effective_template_n"],
        },
        "asymmetric_trace_analysis": {
            "asymmetric_detection_gain": 1.0,
            "trace_based_detection_rate": 1.0,
            "self_report_detection_rate": 0.0,
        },
        "threshold_sensitivity": {
            "sweep_point_count": 6,
            "helix_beats_matched_random_fraction": 0.8333333333333334,
            "mean_selectivity_delta_vs_matched_random": 0.375,
        },
        "paraphrase_analysis": {
            "status": "complete",
            "main_tpr": 1.0,
            "main_fpr": 0.0,
            "exact_citation_rate": 1.0,
            "invalid_citation_rate": 0.0,
        },
        "multi_provider_replay": {
            "provider_count": 2,
            "complete_provider_count": 2,
            "providers_meeting_clean_targets": ["google_flash"],
            "providers_failing_clean_targets": ["degraded_control"],
        },
        "trace_noise_analysis": {
            "status": "complete",
            "main_tpr": 1.0,
            "main_fpr": 0.0,
            "stale_rule_citation_rate": 0.0,
            "active_rule_citation_rate": 1.0,
        },
    }


def _write_artifacts(tmp_path: Path, names: list[str] | None = None) -> dict[str, str]:
    payloads = _artifact_payloads()
    names = names or list(payloads)
    paths: dict[str, str] = {}
    for name in names:
        path = tmp_path / f"{name}.json"
        _write_json(path, payloads[name])
        paths[name] = str(path)
    return paths


def test_missing_artifacts_are_reported_not_fabricated(tmp_path: Path) -> None:
    available = _write_artifacts(tmp_path, ["v5_acceptance"])
    artifact_paths = {
        "v5_acceptance": available["v5_acceptance"],
        "hostile_baselines": str(tmp_path / "missing.json"),
    }

    summary = collect_v6_evidence_rollup(
        artifact_paths=artifact_paths,
        generated_at="2026-05-30T00:00:00Z",
    )

    assert summary.status == "partial"
    assert summary.available_artifact_count == 1
    assert summary.missing_artifact_count == 1
    assert summary.headline_metrics["v5_acceptance_result"] == "PASS"
    assert summary.headline_metrics["hostile_helix_tpr"] is None
    assert summary.artifacts[1].status == "missing"
    assert "hostile_baselines" in summary.missing_artifacts[0]


def test_available_json_artifact_is_hashed_and_metric_extracted(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path, ["v5_acceptance"])

    summary = collect_v6_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-30T00:00:00Z",
    )

    expected_hash = stable_file_hash(paths["v5_acceptance"])
    artifact = summary.artifacts[0]
    assert artifact.status == "available"
    assert artifact.artifact_hash == expected_hash
    assert summary.artifact_hashes["v5_acceptance"] == expected_hash
    assert summary.headline_metrics["v5_pairs"] == 100
    assert summary.headline_metrics["v5_receipt_count"] == 200


def test_summary_status_complete_when_all_required_artifacts_present(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)

    summary = collect_v6_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-30T00:00:00Z",
    )

    assert summary.status == "complete"
    assert summary.artifact_count == len(paths)
    assert summary.available_artifact_count == len(paths)
    assert summary.missing_artifact_count == 0
    assert summary.missing_artifacts == []
    assert summary.headline_metrics["paraphrase_exact_citation_rate"] == 1.0
    assert summary.headline_metrics["multi_provider_failed_targets"] == ["degraded_control"]
    assert summary.headline_metrics["trace_noise_active_rule_citation_rate"] == 1.0


def test_markdown_report_includes_non_proof_section(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    summary = collect_v6_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-30T00:00:00Z",
    )

    markdown = summary.to_markdown()

    assert "What This Does Not Yet Prove" in markdown
    assert "No live production agent integration yet." in markdown
    assert "production-proven" in markdown


def test_output_files_are_written(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    summary = collect_v6_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-30T00:00:00Z",
    )

    summary_path, report_path = write_v6_evidence_rollup_outputs(summary, tmp_path / "out")

    assert summary_path.exists()
    assert report_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["status"] == "complete"
    assert "HELIX v6 Controlled Evidence Rollup" in report_path.read_text(encoding="utf-8")


def test_summary_structure_is_deterministic_except_generated_at(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)

    first = collect_v6_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-30T00:00:00Z",
    ).model_dump(mode="json")
    second = collect_v6_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-30T00:00:01Z",
    ).model_dump(mode="json")

    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second


def test_rollup_module_has_no_provider_specific_branching() -> None:
    source = Path("helix/benchmark/evidence_rollup.py").read_text(encoding="utf-8").lower()

    for forbidden in ["openai", "gpt", "gemini", "claude", "anthropic"]:
        assert forbidden not in source
    assert set(DEFAULT_EVIDENCE_ARTIFACTS)

import json
from pathlib import Path

from helix.benchmark.evidence_levels import (
    assign_evidence_level,
    collect_benchmark_evidence_levels,
    write_benchmark_evidence_levels_outputs,
)


def _integrity(passed: bool) -> dict:
    return {
        "integrity_passed": passed,
        "integrity_hash": "sha256:integrity",
        "integrity_issues": [] if passed else ["score_collapse_detected"],
        "integrity_warnings": ["high_overlap_cases_detected"],
        "score_collapse_detected": not passed,
        "token_overlap_mean": 0.16,
        "selectivity_delta_vs_shuffled": 0.4,
        "selectivity_delta_vs_random": 0.5,
    }


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_failed_integrity_audit_caps_level_at_three() -> None:
    record = assign_evidence_level(
        protocol_name="failed_protocol",
        protocol_completed=True,
        receipts_or_manifest_validated=True,
        hostile_or_degraded_controls_passed=True,
        integrity_report=_integrity(False),
    )

    assert record.evidence_level == 3
    assert record.integrity_audit_status == "failed"
    assert record.integrity_hard_issues == ["score_collapse_detected"]


def test_passed_integrity_audit_gives_level_four() -> None:
    record = assign_evidence_level(
        protocol_name="passed_protocol",
        protocol_completed=True,
        receipts_or_manifest_validated=True,
        hostile_or_degraded_controls_passed=True,
        integrity_report=_integrity(True),
    )

    assert record.evidence_level == 4
    assert record.integrity_audit_status == "passed"


def test_missing_integrity_audit_caps_level_at_three_and_no_level_five() -> None:
    record = assign_evidence_level(
        protocol_name="missing_protocol",
        protocol_completed=True,
        receipts_or_manifest_validated=True,
        hostile_or_degraded_controls_passed=True,
        integrity_report=None,
    )

    assert record.evidence_level == 3
    assert record.evidence_level < 5
    assert record.integrity_audit_status == "missing"


def test_default_rollup_preserves_v6_failed_integrity_audit(tmp_path: Path) -> None:
    paths = {
        "v5_acceptance": _write_json(
            tmp_path / "v5.json",
            {
                "result": "PASS",
                "case_count": 2,
                "receipt_count": 2,
                "receipt_validation_issue_count": 0,
                "manifest_validation_issue_count": 0,
            },
        ),
        "v5_manifest": _write_json(tmp_path / "v5_manifest.json", {"manifest_hash": "x"}),
        "v5_hostile_baselines": _write_json(tmp_path / "hostile.json", {"status": "complete"}),
        "v6_paraphrase": _write_json(
            tmp_path / "paraphrase.json",
            {"status": "complete", "main_tpr": 1.0, "main_fpr": 0.0},
        ),
        "v6_multi_provider": _write_json(
            tmp_path / "multi.json",
            {
                "provider_count": 2,
                "providers_meeting_clean_targets": ["clean"],
                "providers_failing_clean_targets": ["degraded_control"],
            },
        ),
        "v6_paraphrase_integrity": _write_json(
            tmp_path / "integrity.json",
            _integrity(False),
        ),
        "v8_trajectory_rollup": _write_json(
            tmp_path / "v8.json",
            {"status": "complete", "missing_artifact_count": 0, "config_hashes": {"x": "y"}},
        ),
        "v9_mock_loop": _write_json(
            tmp_path / "v9.json",
            {"receipt_count": 2, "attempted_tool_calls": 2, "invalid_receipt_count": 0},
        ),
        "v9_mock_loop_manifest": _write_json(
            tmp_path / "v9_manifest.json",
            {"manifest_hash": "x"},
        ),
    }

    summary = collect_benchmark_evidence_levels(paths)
    v6 = next(
        record
        for record in summary.records
        if record.protocol_name == "v6_paraphrase_google_flash"
    )

    assert summary.protocol_count == 5
    assert summary.max_assigned_level < 5
    assert v6.evidence_level == 3
    assert v6.integrity_hard_issues == ["score_collapse_detected"]
    assert v6.integrity_metrics["selectivity_delta_vs_random"] == 0.5


def test_markdown_preserves_failed_audit_issues_and_outputs_are_written(
    tmp_path: Path,
) -> None:
    summary = collect_benchmark_evidence_levels(
        {
            "v6_paraphrase": _write_json(
                tmp_path / "paraphrase.json",
                {"status": "complete"},
            ),
            "v6_paraphrase_integrity": _write_json(
                tmp_path / "integrity.json",
                _integrity(False),
            ),
        }
    )

    json_path, markdown_path = write_benchmark_evidence_levels_outputs(
        summary,
        tmp_path / "out",
    )
    markdown = markdown_path.read_text(encoding="utf-8")

    assert json_path.exists()
    assert "score_collapse_detected" in markdown
    assert "high_overlap_cases_detected" in markdown
    assert "v6_paraphrase_google_flash" in markdown
    assert "No protocol is assigned Level 5" in markdown

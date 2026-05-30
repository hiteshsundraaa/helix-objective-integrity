import json
from pathlib import Path

from helix.runtime.runtime_evidence_rollup import (
    DEFAULT_RUNTIME_EVIDENCE_ARTIFACTS,
    collect_v7_runtime_evidence_rollup,
    stable_file_hash,
    write_v7_runtime_evidence_rollup_outputs,
)


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _artifact_payloads() -> dict[str, str | dict]:
    return {
        "runtime_summary": {
            "receipt_count": 4,
            "allow_count": 2,
            "block_count": 1,
            "escalate_count": 1,
            "self_report_used_for_decision_count": 0,
            "receipt_validation_issue_count": 0,
            "exact_citation_rate_for_blocks": 1.0,
            "mean_latency_ms": 0.02,
            "max_latency_ms": 0.05,
        },
        "runtime_receipts": (
            '{"call_id":"call_001"}\n'
            '{"call_id":"call_002"}\n'
            '{"call_id":"call_003"}\n'
            '{"call_id":"call_004"}\n'
        ),
        "runtime_report": "# Runtime report\n",
        "negative_control_summary": {
            "negative_control_count": 9,
            "expected_failure_count": 8,
            "observed_failure_count": 8,
            "unexpected_pass_count": 0,
            "unexpected_fail_count": 0,
            "latency_only_mutation_valid": True,
            "issue_counts_by_code": {
                "receipt_hash_mismatch": 1,
                "tool_call_hash_mismatch": 1,
            },
        },
        "negative_control_records": (
            '{"control_name":"valid_block_receipt"}\n'
            '{"control_name":"tampered_receipt_hash"}\n'
        ),
        "negative_control_report": "# Negative control report\n",
    }


def _write_artifacts(tmp_path: Path, names: list[str] | None = None) -> dict[str, str]:
    payloads = _artifact_payloads()
    names = names or list(payloads)
    paths: dict[str, str] = {}
    for name in names:
        suffix = ".json"
        if name.endswith("records") or name.endswith("receipts"):
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


def test_missing_artifacts_are_reported_not_fabricated(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path, ["runtime_summary"])
    artifact_paths = {
        "runtime_summary": paths["runtime_summary"],
        "negative_control_summary": str(tmp_path / "missing.json"),
    }

    summary = collect_v7_runtime_evidence_rollup(
        artifact_paths=artifact_paths,
        generated_at="2026-05-31T00:00:00Z",
    )

    assert summary.status == "partial"
    assert summary.available_artifact_count == 1
    assert summary.missing_artifact_count == 1
    assert summary.headline_metrics["runtime_receipt_count"] == 4
    assert summary.headline_metrics["negative_control_count"] is None
    assert summary.artifacts[1].status == "missing"
    assert "negative_control_summary" in summary.missing_artifacts[0]


def test_available_json_artifact_is_hashed_and_metric_extracted(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path, ["runtime_summary"])

    summary = collect_v7_runtime_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-31T00:00:00Z",
    )

    expected_hash = stable_file_hash(paths["runtime_summary"])
    artifact = summary.artifacts[0]
    assert artifact.status == "available"
    assert artifact.artifact_hash == expected_hash
    assert summary.artifact_hashes["runtime_summary"] == expected_hash
    assert summary.headline_metrics["allow_count"] == 2
    assert summary.headline_metrics["block_count"] == 1
    assert summary.headline_metrics["receipt_validation_issue_count"] == 0


def test_summary_status_complete_when_all_required_artifacts_present(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)

    summary = collect_v7_runtime_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-31T00:00:00Z",
    )

    assert summary.status == "complete"
    assert summary.artifact_count == len(paths)
    assert summary.available_artifact_count == len(paths)
    assert summary.missing_artifact_count == 0
    assert summary.missing_artifacts == []
    assert summary.headline_metrics["runtime_receipt_count"] == 4
    assert summary.headline_metrics["negative_control_count"] == 9
    assert summary.headline_metrics["latency_only_mutation_valid"] is True


def test_markdown_report_includes_non_proof_section(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    summary = collect_v7_runtime_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-31T00:00:00Z",
    )

    markdown = summary.to_markdown()

    assert "What This Does Not Yet Prove" in markdown
    assert "No live LLM agent loop yet." in markdown
    assert "No production proxy or broker yet." in markdown


def test_output_files_are_written(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)
    summary = collect_v7_runtime_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-31T00:00:00Z",
    )

    summary_path, report_path = write_v7_runtime_evidence_rollup_outputs(
        summary,
        tmp_path / "out",
    )

    assert summary_path.exists()
    assert report_path.exists()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["status"] == "complete"
    assert "HELIX v7 Runtime Evidence Rollup" in report_path.read_text(encoding="utf-8")


def test_summary_structure_is_deterministic_except_generated_at(tmp_path: Path) -> None:
    paths = _write_artifacts(tmp_path)

    first = collect_v7_runtime_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-31T00:00:00Z",
    ).model_dump(mode="json")
    second = collect_v7_runtime_evidence_rollup(
        artifact_paths=paths,
        generated_at="2026-05-31T00:00:01Z",
    ).model_dump(mode="json")

    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second


def test_rollup_module_has_no_provider_specific_branching() -> None:
    source = Path("helix/runtime/runtime_evidence_rollup.py").read_text(encoding="utf-8").lower()

    for forbidden in ["openai", "gpt", "gemini", "claude", "anthropic"]:
        assert forbidden not in source
    assert set(DEFAULT_RUNTIME_EVIDENCE_ARTIFACTS)

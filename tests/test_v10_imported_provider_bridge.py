import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from helix.benchmark.benchmark_receipts import stable_json_hash
from helix.benchmark.v10_imported_provider_bridge import (
    _bridge_summary,
    filter_cases_to_imported_case_ids,
    load_raw_import_validation_summary,
    load_v10_cases,
    load_v10_imported_provider_bridge_config,
    validate_provider_run_is_manual_import,
    write_imported_provider_bridge_outputs,
)
from helix.benchmark.v10_judgment_normalization import load_raw_judgments


BRIDGE_CONFIG_PATH = Path("configs/v10_imported_provider_pipeline_bridge.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")


def test_v10_imported_provider_bridge_config_loads() -> None:
    config = load_v10_imported_provider_bridge_config(BRIDGE_CONFIG_PATH)

    assert config.schema_version == "v10_imported_provider_pipeline_bridge_v1"
    assert config.manual_import_bridge
    assert config.evidence_policy.manual_import_bridge_evidence_level_cap == 3
    assert not config.evidence_policy.level_4_allowed
    assert not config.evidence_policy.level_5_allowed
    assert not config.allow_network_calls
    assert not config.allow_provider_sdk_imports
    assert not config.allow_api_keys


def test_v10_imported_provider_bridge_missing_provider_run_fails_clearly(tmp_path: Path) -> None:
    config = load_v10_imported_provider_bridge_config(BRIDGE_CONFIG_PATH)

    with pytest.raises(FileNotFoundError, match="Run examples/import_v10_provider_raw_outputs.py first"):
        write_imported_provider_bridge_outputs(
            provider_run_dir=tmp_path / "missing",
            cases_path=CASES_PATH,
            config=config,
            config_path=BRIDGE_CONFIG_PATH,
        )


def test_v10_imported_provider_bridge_missing_summary_fails() -> None:
    assert validate_provider_run_is_manual_import(Path("missing_dir")) == [
        "missing_raw_import_validation_summary"
    ]


def test_v10_imported_provider_bridge_rejects_incomplete_validation(tmp_path: Path) -> None:
    run_dir = _write_valid_manual_import(tmp_path)
    _mutate_summary(run_dir, {"validation_status": "needs_work"})

    assert "raw_import_validation_not_complete" in validate_provider_run_is_manual_import(run_dir)


def test_v10_imported_provider_bridge_rejects_unwritten_parsed_jsonl(tmp_path: Path) -> None:
    run_dir = _write_valid_manual_import(tmp_path)
    _mutate_summary(run_dir, {"parsed_raw_judgments_written": False})

    assert "parsed_raw_judgments_not_written" in validate_provider_run_is_manual_import(run_dir)


def test_v10_imported_provider_bridge_rejects_api_key_observed(tmp_path: Path) -> None:
    run_dir = _write_valid_manual_import(tmp_path)
    _mutate_summary(run_dir, {"api_key_observed": True})

    assert "raw_import_api_key_observed" in validate_provider_run_is_manual_import(run_dir)


def test_v10_imported_provider_bridge_reads_parsed_judgments_and_filters_cases(tmp_path: Path) -> None:
    run_dir = _write_valid_manual_import(tmp_path, case_count=5)
    config = load_v10_imported_provider_bridge_config(BRIDGE_CONFIG_PATH)

    raw_judgments = load_raw_judgments(run_dir / "parsed_raw_judgments.jsonl")
    filtered = filter_cases_to_imported_case_ids(load_v10_cases(CASES_PATH), raw_judgments)

    assert len(filtered) == 5
    assert {case.case_id for case in filtered} == {
        raw.payload["case_id"] for raw in raw_judgments
    }

    paths = write_imported_provider_bridge_outputs(
        provider_run_dir=run_dir,
        cases_path=CASES_PATH,
        config=config,
        config_path=BRIDGE_CONFIG_PATH,
        out_subdir="imported_pipeline_bridge",
        generated_at="2026-06-09T00:00:00Z",
    )

    assert paths["parsed_raw_judgments"].exists()
    assert paths["filtered_cases"].exists()
    assert paths["normalized_output_dir"].exists()
    assert paths["benchmark_output_dir"].exists()
    assert paths["diagnostics_output_dir"].exists()
    assert paths["reportability_output_path"].exists()
    assert (paths["normalized_output_dir"] / "v10_normalization_summary.json").exists()
    assert (paths["benchmark_output_dir"] / "v10_benchmark_summary.json").exists()
    assert (paths["diagnostics_output_dir"] / "v10_diagnostics_summary.json").exists()
    assert (paths["bridge_dir"] / "reportability" / "v10_reportability_report.json").exists()
    assert len(paths["filtered_cases"].read_text(encoding="utf-8").splitlines()) == 5


def test_v10_imported_provider_bridge_summary_caps_evidence_and_blocks_levels(tmp_path: Path) -> None:
    run_dir = _write_valid_manual_import(tmp_path, case_count=6)
    config = load_v10_imported_provider_bridge_config(BRIDGE_CONFIG_PATH)

    paths = write_imported_provider_bridge_outputs(
        provider_run_dir=run_dir,
        cases_path=CASES_PATH,
        config=config,
        config_path=BRIDGE_CONFIG_PATH,
        out_subdir="imported_pipeline_bridge",
        generated_at="2026-06-09T00:00:00Z",
    )
    summary = json.loads(paths["bridge_summary"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["bridge_manifest"].read_text(encoding="utf-8"))

    assert summary["manual_import_bridge"] is True
    assert summary["no_api_calls_made"] is True
    assert summary["provider_sdk_imported"] is False
    assert summary["api_key_observed"] is False
    assert summary["raw_judgment_count"] == 6
    assert summary["normalized_judgment_count"] == 6
    assert summary["benchmark_receipt_count"] == 6
    assert summary["matched_case_count"] == 6
    assert summary["missing_judgment_case_count"] == 0
    assert summary["final_evidence_level"] <= 3
    assert summary["level_4_allowed"] is False
    assert summary["level_5_allowed"] is False
    assert manifest["case_filtering_policy"]["source_case_count"] > 6
    assert manifest["case_filtering_policy"]["filtered_case_count"] == 6
    assert manifest["case_filtering_policy"]["source_cases_modified"] is False


def test_v10_imported_provider_bridge_warning_when_mechanical_pass_is_capped(tmp_path: Path) -> None:
    run_dir = _write_valid_manual_import(tmp_path, case_count=1)
    config = load_v10_imported_provider_bridge_config(BRIDGE_CONFIG_PATH)
    raw_summary = load_raw_import_validation_summary(run_dir)

    summary = _bridge_summary(
        provider_run_dir=run_dir,
        bridge_dir=run_dir / "bridge",
        raw_import_summary=raw_summary,
        raw_import_summary_path=run_dir / "raw_import_validation_summary.json",
        parsed_path=run_dir / "parsed_raw_judgments.jsonl",
        normalization_summary=SimpleNamespace(
            status="complete",
            invalid_count=0,
            normalized_count=1,
        ),
        benchmark_summary=SimpleNamespace(
            status="complete",
            matched_case_count=1,
            missing_judgment_case_count=0,
        ),
        receipts=[object()],
        diagnostics_summary=SimpleNamespace(diagnostics_status="complete"),
        reportability_report=SimpleNamespace(
            reportability_passed=True,
            evidence_level_allowed=4,
        ),
        config=config,
        diagnostics_paths={"reportability_json": run_dir / "reportability.json"},
    )

    assert summary.final_evidence_level == 3
    assert "mechanical_reportability_passed_but_manual_import_cap_applied" in summary.warnings
    assert not summary.level_4_allowed
    assert not summary.level_5_allowed


def test_v10_imported_provider_bridge_report_contains_limits(tmp_path: Path) -> None:
    run_dir = _write_valid_manual_import(tmp_path, case_count=4)
    config = load_v10_imported_provider_bridge_config(BRIDGE_CONFIG_PATH)

    paths = write_imported_provider_bridge_outputs(
        provider_run_dir=run_dir,
        cases_path=CASES_PATH,
        config=config,
        config_path=BRIDGE_CONFIG_PATH,
        out_subdir="imported_pipeline_bridge",
        generated_at="2026-06-09T00:00:00Z",
    )
    report = paths["bridge_report"].read_text(encoding="utf-8")

    assert "What This Does Not Yet Prove" in report
    assert "No API calls were made" in report
    assert "Imported files were externally saved raw outputs" in report
    assert "existing v10 pipeline" in report.lower()
    assert "manual import, not locked live API execution" in report
    assert "Level 4 false" in report
    assert "Level 5 false" in report


def _write_valid_manual_import(tmp_path: Path, *, case_count: int = 6) -> Path:
    cases = load_v10_cases(CASES_PATH)[:case_count]
    run_dir = tmp_path / "manual_import_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, case in enumerate(cases):
        rows.append(
            {
                "case_id": case.case_id,
                "decision": "WARN",
                "violation_probability": round(0.12 + (index * 0.07), 3),
                "cited_contract_phrase": "",
                "citation_verification_method": "unverified",
                "reason_codes": ["test.manual_import_fixture"],
                "uncertainty_reason": None,
            }
        )
    parsed_path = run_dir / "parsed_raw_judgments.jsonl"
    parsed_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    summary_payload = {
        "schema_version": "v10_provider_raw_import_validation_summary_v1",
        "run_id": "manual_import_test",
        "validator_only": True,
        "no_api_calls_made": True,
        "network_calls_attempted": 0,
        "provider_sdk_imported": False,
        "api_key_observed": False,
        "plan_path": "tests/fixtures/v10_provider_plan.json",
        "plan_hash": "sha256:test-plan",
        "import_dir": str(tmp_path / "external_import"),
        "output_provider_run_dir": str(run_dir),
        "expected_case_count": case_count,
        "imported_case_count": case_count,
        "parsed_raw_judgment_count": case_count,
        "missing_case_count": 0,
        "duplicate_case_count": 0,
        "unexpected_case_count": 0,
        "malformed_judgment_count": 0,
        "raw_file_count": 0,
        "batch_count": 1,
        "provider": "external_test_provider",
        "model": "external_test_model",
        "prompt_hashes_observed": ["sha256:test-prompt"],
        "provider_metadata_complete": True,
        "response_metadata_complete": True,
        "validation_status": "complete",
        "parsed_raw_judgments_written": True,
        "evidence_level_cap": 3,
        "level_4_allowed": False,
        "level_5_allowed": False,
        "warnings": [],
        "issues": [],
    }
    summary = {
        **summary_payload,
        "import_hash": stable_json_hash(summary_payload),
    }
    (run_dir / "raw_import_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "provider_run_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "test_manual_import_manifest_v1",
                "no_api_calls_made": True,
                "provider_sdk_imported": False,
                "api_key_observed": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "raw_file_hashes.json").write_text(
        json.dumps({"schema_version": "test_raw_hashes_v1", "batches": {}}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return run_dir


def _mutate_summary(run_dir: Path, updates: dict[str, object]) -> None:
    summary_path = run_dir / "raw_import_validation_summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload.update(updates)
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

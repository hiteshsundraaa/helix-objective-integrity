import json
from pathlib import Path

from helix.benchmark.v10_live_runner_design_gate import load_v10_live_runner_design_config
from helix.benchmark.v10_manual_pilot_runner import (
    V10ManualPilotInput,
    load_v10_manual_pilot_config,
    run_manual_pilot,
    stage_manual_raw_output_for_import,
    validate_manual_pilot_inputs,
)
from helix.benchmark.v10_provider_raw_import import load_provider_run_plan


CONFIG_PATH = Path("configs/v10_manual_one_provider_pilot.json")
PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")
LIVE_CONFIG_PATH = Path("configs/v10_live_provider_runner_design_gate.json")


def test_v10_manual_pilot_config_loads() -> None:
    config = load_v10_manual_pilot_config(CONFIG_PATH)

    assert config.schema_version == "v10_manual_one_provider_pilot_v1"
    assert config.manual_pilot_only
    assert config.execution_mode == "manual_import"
    assert config.evidence_level_cap == 3
    assert not config.level_4_allowed
    assert not config.level_5_allowed
    assert "manual_copy_paste" in config.collection_method_allowed_values


def test_unknown_provider_model_fails_before_staging(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "raw_output.jsonl")
    pilot_input = _input(tmp_path, raw, provider="unknown", model="model")
    config = _config_for_tmp(tmp_path)

    issues = validate_manual_pilot_inputs(
        pilot_input,
        config,
        load_v10_live_runner_design_config(LIVE_CONFIG_PATH),
    )

    assert "provider_model_not_allowed" in issues
    assert not (tmp_path / "imports" / pilot_input.run_id).exists()


def test_missing_raw_output_file_fails_clearly(tmp_path: Path) -> None:
    issues = validate_manual_pilot_inputs(
        _input(tmp_path, tmp_path / "missing.jsonl"),
        _config_for_tmp(tmp_path),
        load_v10_live_runner_design_config(LIVE_CONFIG_PATH),
    )

    assert "missing_raw_output_file" in issues


def test_invalid_collection_method_fails(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "raw_output.jsonl")
    issues = validate_manual_pilot_inputs(
        _input(tmp_path, raw, collection_method="automatic_api_call"),
        _config_for_tmp(tmp_path),
        load_v10_live_runner_design_config(LIVE_CONFIG_PATH),
    )

    assert "invalid_collection_method" in issues


def test_run_id_traversal_fails(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "raw_output.jsonl")
    issues = validate_manual_pilot_inputs(
        _input(tmp_path, raw, run_id="../escape"),
        _config_for_tmp(tmp_path),
        load_v10_live_runner_design_config(LIVE_CONFIG_PATH),
    )

    assert "invalid_run_id" in issues


def test_secret_looking_input_value_fails(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "raw_output.jsonl")
    issues = validate_manual_pilot_inputs(
        _input(tmp_path, raw, notes="api_key=should-not-be-here"),
        _config_for_tmp(tmp_path),
        load_v10_live_runner_design_config(LIVE_CONFIG_PATH),
    )

    assert "secret_like_input_value:notes" in issues


def test_staging_preserves_json_object_array_and_jsonl_raw_bytes(tmp_path: Path) -> None:
    plan = load_provider_run_plan(PLAN_PATH)
    config = _config_for_tmp(tmp_path)
    rows = _raw_rows(plan)
    payloads = {
        "object": json.dumps({"judgments": rows}, sort_keys=True).encode("utf-8"),
        "array": json.dumps(rows, sort_keys=True).encode("utf-8"),
        "jsonl": ("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n").encode("utf-8"),
    }

    for name, raw_bytes in payloads.items():
        raw = tmp_path / f"{name}.raw"
        raw.write_bytes(raw_bytes)
        staging = stage_manual_raw_output_for_import(
            _input(tmp_path, raw, run_id=f"stage_{name}"),
            config,
            plan,
            generated_at="2026-06-10T00:00:00Z",
        )

        assert Path(staging.raw_response_path).read_bytes() == raw_bytes
        assert Path(staging.raw_text_path).read_bytes() == raw_bytes
        assert staging.source_raw_output_hash == staging.staged_raw_response_hash


def test_request_manifest_has_plan_case_ids_and_prompt_hash(tmp_path: Path) -> None:
    plan = load_provider_run_plan(PLAN_PATH)
    raw = _write_raw_file(tmp_path, "raw_output.jsonl")
    staging = stage_manual_raw_output_for_import(
        _input(tmp_path, raw),
        _config_for_tmp(tmp_path),
        plan,
        generated_at="2026-06-10T00:00:00Z",
    )
    manifest = json.loads(Path(staging.request_manifest_path).read_text(encoding="utf-8"))

    assert manifest["case_ids"] == plan.sampled_case_ids
    assert manifest["prompt_hash"] == plan.prompt_hashes["contract_prompt"]
    assert manifest["collection_method"] == "manual_copy_paste"
    assert manifest["source_raw_output_hash"] == staging.source_raw_output_hash


def test_valid_manual_fixture_runs_import_bridge_and_assessment(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "raw_output.jsonl")

    summary, paths = run_manual_pilot(
        _input(tmp_path, raw),
        _config_for_tmp(tmp_path),
        generated_at="2026-06-10T00:00:00Z",
    )

    assert summary.import_validation_status == "complete"
    assert summary.bridge_status in {"complete", "needs_work"}
    assert summary.evidence_assessment_status == "complete"
    assert summary.final_evidence_level <= 3
    assert not summary.level_4_allowed
    assert not summary.level_5_allowed
    assert summary.receipt_count == load_provider_run_plan(PLAN_PATH).case_count
    assert summary.invalid_receipt_count == 0
    assert summary.receipt_chain_complete
    assert paths["manifest"].exists()
    assert paths["report"].exists()


def test_malformed_import_stops_after_import_validation(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "malformed.jsonl", malformed=True)

    summary, paths = run_manual_pilot(
        _input(tmp_path, raw, run_id="malformed_manual"),
        _config_for_tmp(tmp_path),
        generated_at="2026-06-10T00:00:00Z",
    )

    assert summary.import_validation_status == "needs_work"
    assert summary.bridge_status == "not_run"
    assert summary.evidence_assessment_status == "not_run"
    assert summary.status == "needs_work"
    assert any("malformed_judgment" in issue for issue in summary.blocking_issues)
    assert paths["manual_pilot_summary"].exists()


def test_missing_and_duplicate_cases_report_needs_work_honestly(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "partial.jsonl", missing_last=True, duplicate_first=True)

    summary, _ = run_manual_pilot(
        _input(tmp_path, raw, run_id="partial_manual"),
        _config_for_tmp(tmp_path),
        generated_at="2026-06-10T00:00:00Z",
    )

    assert summary.import_validation_status == "needs_work"
    assert summary.bridge_status == "not_run"
    assert any("missing" in issue for issue in summary.blocking_issues)
    assert any("duplicate" in issue for issue in summary.blocking_issues)


def test_score_collapse_fixture_remains_level_3_or_below(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "collapsed.jsonl", collapsed_scores=True)

    summary, _ = run_manual_pilot(
        _input(tmp_path, raw, run_id="collapsed_manual"),
        _config_for_tmp(tmp_path),
        generated_at="2026-06-10T00:00:00Z",
    )

    assert summary.final_evidence_level <= 3
    assert summary.score_collapse_detected is True
    assert "score_collapse_blocks_level_4" in summary.blocking_issues


def test_pilot_report_contains_limits(tmp_path: Path) -> None:
    raw = _write_raw_file(tmp_path, "raw_output.jsonl")

    summary, paths = run_manual_pilot(
        _input(tmp_path, raw, run_id="report_manual"),
        _config_for_tmp(tmp_path),
        generated_at="2026-06-10T00:00:00Z",
    )
    report = paths["report"].read_text(encoding="utf-8")

    assert summary.final_evidence_level <= 3
    assert "What This Does Not Prove" in report
    assert "One provider does not prove cross-provider consistency" in report
    assert "No live provider APIs are called" in report


def test_manual_pilot_module_uses_no_provider_sdks_or_secret_sources() -> None:
    source = Path("helix/benchmark/v10_manual_pilot_runner.py").read_text(encoding="utf-8")

    assert "import openai" not in source
    assert "import anthropic" not in source
    assert "import google" not in source
    assert "os.environ" not in source


def _config_for_tmp(tmp_path: Path):
    return load_v10_manual_pilot_config(CONFIG_PATH).model_copy(
        update={
            "provider_imports_root": str(tmp_path / "imports"),
            "provider_runs_root": str(tmp_path / "runs"),
        }
    )


def _input(
    tmp_path: Path,
    raw_output_file: Path,
    *,
    provider: str = "google",
    model: str = "gemini-flash-2.0",
    run_id: str = "manual_test",
    collection_method: str = "manual_copy_paste",
    notes: str | None = None,
) -> V10ManualPilotInput:
    return V10ManualPilotInput(
        provider=provider,
        model=model,
        run_id=run_id,
        raw_output_file=str(raw_output_file),
        collection_method=collection_method,
        plan_path=str(PLAN_PATH),
        output_root=str(tmp_path / "runs"),
        notes=notes,
    )


def _write_raw_file(
    tmp_path: Path,
    name: str,
    *,
    missing_last: bool = False,
    duplicate_first: bool = False,
    malformed: bool = False,
    collapsed_scores: bool = False,
) -> Path:
    path = tmp_path / name
    path.write_text(
        "\n".join(
            json.dumps(row, sort_keys=True)
            for row in _raw_rows(
                load_provider_run_plan(PLAN_PATH),
                missing_last=missing_last,
                duplicate_first=duplicate_first,
                malformed=malformed,
                collapsed_scores=collapsed_scores,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _raw_rows(
    plan,
    *,
    missing_last: bool = False,
    duplicate_first: bool = False,
    malformed: bool = False,
    collapsed_scores: bool = False,
) -> list[dict[str, object]]:
    case_ids = list(plan.sampled_case_ids)
    if missing_last:
        case_ids = case_ids[:-1]
    if duplicate_first:
        case_ids.append(case_ids[0])
    rows = []
    for index, case_id in enumerate(case_ids):
        row: dict[str, object] = {
            "case_id": case_id,
            "decision": "WARN",
            "violation_probability": 0.25 if collapsed_scores else round(0.08 + (index % 10) * 0.073, 3),
            "cited_contract_phrase": "",
            "citation_verification_method": "unverified",
            "reason_codes": ["test.manual_one_provider_fixture"],
            "uncertainty_reason": None,
        }
        if malformed and index == 0:
            row["decision"] = "MAYBE"
            row.pop("violation_probability")
        rows.append(row)
    return rows

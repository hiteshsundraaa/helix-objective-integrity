import json
from pathlib import Path

from helix.benchmark.v10_provider_raw_import import (
    discover_external_raw_files,
    load_provider_run_plan,
    load_v10_provider_raw_import_config,
    parse_raw_response_file,
    write_imported_provider_run_outputs,
)


CONFIG_PATH = Path("configs/v10_provider_raw_import_validator.json")
PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")


def test_v10_provider_raw_import_config_loads() -> None:
    config = load_v10_provider_raw_import_config(CONFIG_PATH)

    assert config.schema_version == "v10_provider_raw_import_validator_v1"
    assert config.validator_only
    assert not config.allow_network_calls
    assert not config.allow_provider_sdk_imports
    assert not config.allow_api_keys
    assert config.evidence_policy.manual_external_import_evidence_level_cap == 3
    assert not config.evidence_policy.level_4_allowed_without_locked_live_runner
    assert not config.evidence_policy.level_5_allowed


def test_v10_provider_raw_import_valid_import_completes(tmp_path: Path) -> None:
    import_dir = _write_import_fixture(tmp_path / "import")

    summary, paths = _run_import(tmp_path, import_dir)

    assert summary["validation_status"] == "complete"
    assert summary["expected_case_count"] == 30
    assert summary["imported_case_count"] == 30
    assert summary["missing_case_count"] == 0
    assert summary["duplicate_case_count"] == 0
    assert summary["unexpected_case_count"] == 0
    assert summary["malformed_judgment_count"] == 0
    assert summary["api_key_observed"] is False
    assert summary["parsed_raw_judgments_written"] is True
    assert summary["evidence_level_cap"] == 3
    assert summary["level_4_allowed"] is False
    assert summary["level_5_allowed"] is False
    assert paths["parsed_raw_judgments"].exists()


def test_v10_provider_raw_import_copies_raw_before_parsing(tmp_path: Path) -> None:
    import_dir = _write_import_fixture(tmp_path / "import")

    summary, paths = _run_import(tmp_path, import_dir)

    copied = paths["output_provider_run_dir"] / "external_raw" / "raw_response_batch_001.json"
    assert copied.exists()
    assert summary["parsed_raw_judgments_written"] is True
    parsed = parse_raw_response_file(copied)
    assert len(parsed["judgments"]) == 10


def test_v10_provider_raw_import_missing_case_needs_work(tmp_path: Path) -> None:
    plan = load_provider_run_plan(PLAN_PATH)
    omitted = plan.sampled_case_ids[-1]
    import_dir = _write_import_fixture(tmp_path / "import", omit_case_id=omitted)

    summary, _ = _run_import(tmp_path, import_dir)

    assert summary["validation_status"] == "needs_work"
    assert summary["missing_case_count"] == 1


def test_v10_provider_raw_import_duplicate_case_needs_work(tmp_path: Path) -> None:
    plan = load_provider_run_plan(PLAN_PATH)
    import_dir = _write_import_fixture(tmp_path / "import", duplicate_case_id=plan.sampled_case_ids[0])

    summary, _ = _run_import(tmp_path, import_dir)

    assert summary["validation_status"] == "needs_work"
    assert summary["duplicate_case_count"] == 1


def test_v10_provider_raw_import_unexpected_case_needs_work(tmp_path: Path) -> None:
    import_dir = _write_import_fixture(tmp_path / "import", unexpected_case_id="v10_case_not_in_plan")

    summary, _ = _run_import(tmp_path, import_dir)

    assert summary["validation_status"] == "needs_work"
    assert summary["unexpected_case_count"] == 1


def test_v10_provider_raw_import_malformed_judgment_needs_work(tmp_path: Path) -> None:
    plan = load_provider_run_plan(PLAN_PATH)
    import_dir = _write_import_fixture(
        tmp_path / "import",
        malformed_case_id=plan.sampled_case_ids[0],
    )

    summary, _ = _run_import(tmp_path, import_dir)

    assert summary["validation_status"] == "needs_work"
    assert summary["malformed_judgment_count"] == 1


def test_v10_provider_raw_import_secret_fails_and_does_not_write_parsed(tmp_path: Path) -> None:
    import_dir = _write_import_fixture(tmp_path / "import", secret_in_manifest=True)

    summary, paths = _run_import(tmp_path, import_dir)

    assert summary["validation_status"] == "failed"
    assert summary["api_key_observed"] is True
    assert summary["parsed_raw_judgments_written"] is False
    assert not paths["parsed_raw_judgments"].exists()


def test_v10_provider_raw_import_prompt_hash_mismatch_needs_work(tmp_path: Path) -> None:
    import_dir = _write_import_fixture(tmp_path / "import", prompt_hash="sha256:bad")

    summary, _ = _run_import(tmp_path, import_dir)

    assert summary["validation_status"] == "needs_work"
    assert any("prompt_hash_mismatch" in issue for issue in summary["issues"])


def test_v10_provider_raw_import_jsonl_response_format_accepted(tmp_path: Path) -> None:
    import_dir = _write_import_fixture(tmp_path / "import", response_format="jsonl")

    summary, paths = _run_import(tmp_path, import_dir)

    assert summary["validation_status"] == "complete"
    assert summary["parsed_raw_judgment_count"] == 30
    assert paths["parsed_raw_judgments"].exists()


def test_v10_provider_raw_import_report_contains_limits(tmp_path: Path) -> None:
    import_dir = _write_import_fixture(tmp_path / "import")

    _, paths = _run_import(tmp_path, import_dir)
    report = paths["raw_import_validation_report"].read_text(encoding="utf-8")

    assert "What This Does Not Yet Prove" in report
    assert "No API calls were made" in report
    assert "Manual import is not locked live-run evidence" in report
    assert "Level 4" in report
    assert "Level 5" in report


def test_v10_provider_raw_import_discovers_external_raw_preferentially(tmp_path: Path) -> None:
    import_dir = _write_import_fixture(tmp_path / "import")
    root_manifest = import_dir / "request_manifest_batch_999.json"
    root_manifest.write_text("{}", encoding="utf-8")

    records, warnings, source = discover_external_raw_files(import_dir)

    assert source == import_dir / "external_raw"
    assert len(records) == 3
    assert "root_and_external_raw_present_preferred_external_raw" in warnings


def _run_import(tmp_path: Path, import_dir: Path):
    config = load_v10_provider_raw_import_config(CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)
    paths = write_imported_provider_run_outputs(
        config=config,
        config_path=CONFIG_PATH,
        plan=plan,
        plan_path=PLAN_PATH,
        import_dir=import_dir,
        run_id="manual_import_test",
        out_root=tmp_path / "provider_runs",
        generated_at="2026-06-09T00:00:00Z",
    )
    summary = json.loads(paths["raw_import_validation_summary"].read_text(encoding="utf-8"))
    return summary, paths


def _write_import_fixture(
    import_dir: Path,
    *,
    omit_case_id: str | None = None,
    duplicate_case_id: str | None = None,
    unexpected_case_id: str | None = None,
    malformed_case_id: str | None = None,
    secret_in_manifest: bool = False,
    prompt_hash: str | None = None,
    response_format: str = "object",
) -> Path:
    plan = load_provider_run_plan(PLAN_PATH)
    raw_dir = import_dir / "external_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    case_ids = [case_id for case_id in plan.sampled_case_ids if case_id != omit_case_id]
    if unexpected_case_id:
        case_ids.append(unexpected_case_id)
    batches = [case_ids[index : index + 10] for index in range(0, len(case_ids), 10)]
    if duplicate_case_id:
        batches[0].append(duplicate_case_id)
    for batch_index, batch_case_ids in enumerate(batches, start=1):
        batch_id = f"batch_{batch_index:03d}"
        request = {
            "schema_version": "v10_external_provider_request_manifest_v1",
            "batch_id": batch_id,
            "provider": "external_fixture_provider",
            "model": "external-fixture-model",
            "model_version": "fixture-001",
            "prompt_mode": plan.prompt_mode,
            "prompt_hash": prompt_hash or plan.prompt_hashes["contract_prompt"],
            "case_ids": batch_case_ids,
            "request_timestamp": "2026-06-09T00:00:00Z",
            "response_timestamp": "2026-06-09T00:00:01Z",
            "settings": {
                "temperature": 0,
                "top_p": 1,
                "max_output_tokens": 8192,
            },
            "retry_attempt": 0,
            "retry_reason": None,
        }
        if secret_in_manifest and batch_index == 1:
            request["api_key"] = "should-not-be-here"
        judgments = [
            _judgment(case_id, malformed=(case_id == malformed_case_id))
            for case_id in batch_case_ids
        ]
        (raw_dir / f"request_manifest_{batch_id}.json").write_text(
            json.dumps(request, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if response_format == "jsonl":
            (raw_dir / f"raw_response_{batch_id}.json").write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in judgments) + "\n",
                encoding="utf-8",
            )
        elif response_format == "array":
            (raw_dir / f"raw_response_{batch_id}.json").write_text(
                json.dumps(judgments, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        else:
            response = {
                "schema_version": "v10_external_provider_response_v1",
                "batch_id": batch_id,
                "provider": "external_fixture_provider",
                "model": "external-fixture-model",
                "response_timestamp": "2026-06-09T00:00:01Z",
                "response_hash": "sha256:external-provider-hash-placeholder",
                "judgments": judgments,
            }
            (raw_dir / f"raw_response_{batch_id}.json").write_text(
                json.dumps(response, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        (raw_dir / f"raw_text_{batch_id}.txt").write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in judgments) + "\n",
            encoding="utf-8",
        )
    return import_dir


def _judgment(case_id: str, *, malformed: bool = False) -> dict[str, object]:
    row: dict[str, object] = {
        "case_id": case_id,
        "decision": "WARN",
        "violation_probability": 0.25,
        "cited_contract_phrase": "",
        "citation_verification_method": "unverified",
        "reason_codes": ["external_fixture"],
        "uncertainty_reason": None,
    }
    if malformed:
        row["decision"] = "MAYBE"
        row.pop("violation_probability")
    return row

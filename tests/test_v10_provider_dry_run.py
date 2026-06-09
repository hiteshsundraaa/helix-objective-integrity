import json
from pathlib import Path

from helix.benchmark.v10_provider_dry_run import (
    build_dry_run_batches,
    generate_fixture_response_for_batch,
    load_provider_run_plan,
    load_v10_cases,
    load_v10_provider_dry_run_config,
    parse_fixture_response_from_raw,
    preserve_raw_response,
    write_provider_dry_run_outputs,
)


CONFIG_PATH = Path("configs/v10_provider_dry_run_executor.json")
PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")


def test_v10_provider_dry_run_config_loads() -> None:
    config = load_v10_provider_dry_run_config(CONFIG_PATH)

    assert config.schema_version == "v10_provider_dry_run_executor_v1"
    assert config.registered_before_live_provider_execution
    assert config.dry_run_mode
    assert config.batch_size == 10
    assert not config.allow_network_calls
    assert not config.allow_provider_sdk_imports
    assert not config.allow_api_keys
    assert config.evidence_policy.dry_run_evidence_level_cap == 2
    assert not config.evidence_policy.level_5_allowed


def test_v10_provider_dry_run_batches_respect_batch_size() -> None:
    config = load_v10_provider_dry_run_config(CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)

    batches = build_dry_run_batches(plan, config)

    assert len(batches) == 3
    assert [len(batch.case_ids) for batch in batches] == [10, 10, 10]
    assert all(batch.dry_run for batch in batches)
    assert all(batch.request_hash.startswith("sha256:") for batch in batches)


def test_v10_provider_dry_run_preserves_raw_before_parse(tmp_path: Path) -> None:
    config = load_v10_provider_dry_run_config(CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)
    cases = load_v10_cases(CASES_PATH)
    cases_by_id = {case.case_id: case for case in cases}
    batch = build_dry_run_batches(plan, config)[0]
    response = generate_fixture_response_for_batch(batch, cases_by_id)

    preserved = preserve_raw_response(batch, response, tmp_path)
    response["judgments"] = []
    parsed = parse_fixture_response_from_raw(preserved.raw_response_path)

    assert Path(preserved.raw_response_path).exists()
    assert Path(preserved.raw_text_path).exists()
    assert len(parsed) == 10
    assert preserved.parsed_raw_judgment_count == 10
    assert preserved.parse_status == "complete"


def test_v10_provider_dry_run_fixture_response_shape() -> None:
    config = load_v10_provider_dry_run_config(CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)
    cases = load_v10_cases(CASES_PATH)
    cases_by_id = {case.case_id: case for case in cases}
    batch = build_dry_run_batches(plan, config)[0]

    response = generate_fixture_response_for_batch(batch, cases_by_id)

    assert response["dry_run"] is True
    assert response["provider"] == "dry_run_fixture"
    assert response["model"] == "fixture-response-generator"
    assert response["response_hash"].startswith("sha256:")
    assert len(response["judgments"]) == 10
    for row in response["judgments"]:
        assert row["provider"] == "dry_run_fixture"
        assert row["model"] == "fixture-response-generator"
        assert 0.0 < row["violation_probability"] < 1.0
        assert "dry_run_fixture" in row["reason_codes"]


def test_v10_provider_dry_run_outputs_are_written(tmp_path: Path) -> None:
    config = load_v10_provider_dry_run_config(CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)
    cases = load_v10_cases(CASES_PATH)

    paths = write_provider_dry_run_outputs(
        run_id="dry_run_test",
        plan=plan,
        plan_path=PLAN_PATH,
        cases=cases,
        config=config,
        config_path=CONFIG_PATH,
        out_root=tmp_path,
        generated_at="2026-06-09T00:00:00Z",
    )

    expected = {
        "provider_run_config",
        "provider_run_manifest",
        "prompt_hashes",
        "sampled_case_ids",
        "parsed_raw_judgments",
        "provider_dry_run_summary",
        "provider_dry_run_report",
        "retry_policy_dry_run_report",
    }
    assert expected.issubset(paths)
    for key in expected:
        assert paths[key].exists()
    assert len(list((paths["run_dir"] / "raw").glob("raw_response_*.json"))) == 3
    assert len(list((paths["run_dir"] / "raw").glob("request_manifest_*.json"))) == 3
    assert len(list((paths["run_dir"] / "raw").glob("raw_text_*.txt"))) == 3


def test_v10_provider_dry_run_summary_flags_no_api_or_secrets(tmp_path: Path) -> None:
    config = load_v10_provider_dry_run_config(CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)
    cases = load_v10_cases(CASES_PATH)

    paths = write_provider_dry_run_outputs(
        run_id="dry_run_test_flags",
        plan=plan,
        plan_path=PLAN_PATH,
        cases=cases,
        config=config,
        config_path=CONFIG_PATH,
        out_root=tmp_path,
        generated_at="2026-06-09T00:00:00Z",
    )
    summary = json.loads(paths["provider_dry_run_summary"].read_text(encoding="utf-8"))

    assert summary["dry_run"] is True
    assert summary["no_api_calls_made"] is True
    assert summary["network_calls_attempted"] == 0
    assert summary["provider_sdk_imported"] is False
    assert summary["api_key_observed"] is False
    assert summary["case_count"] == 30
    assert summary["batch_count"] == 3
    assert summary["raw_response_count"] == 3
    assert summary["parsed_raw_judgment_count"] == 30
    assert summary["evidence_level_cap"] == 2
    assert summary["level_5_allowed"] is False
    assert summary["status"] == "complete"


def test_v10_provider_dry_run_retry_policy_report_written(tmp_path: Path) -> None:
    config = load_v10_provider_dry_run_config(CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)
    cases = load_v10_cases(CASES_PATH)

    paths = write_provider_dry_run_outputs(
        run_id="dry_run_test_retry",
        plan=plan,
        plan_path=PLAN_PATH,
        cases=cases,
        config=config,
        config_path=CONFIG_PATH,
        out_root=tmp_path,
        generated_at="2026-06-09T00:00:00Z",
    )
    retry = json.loads(paths["retry_policy_dry_run_report"].read_text(encoding="utf-8"))

    assert retry["status"] == "complete"
    assert retry["missing_allowed_test_cases"] == []
    assert retry["no_real_retries_performed"] is True
    assert retry["retry_policy_hash"].startswith("sha256:")


def test_v10_provider_dry_run_report_states_limits(tmp_path: Path) -> None:
    config = load_v10_provider_dry_run_config(CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)
    cases = load_v10_cases(CASES_PATH)

    paths = write_provider_dry_run_outputs(
        run_id="dry_run_test_report",
        plan=plan,
        plan_path=PLAN_PATH,
        cases=cases,
        config=config,
        config_path=CONFIG_PATH,
        out_root=tmp_path,
        generated_at="2026-06-09T00:00:00Z",
    )
    report = paths["provider_dry_run_report"].read_text(encoding="utf-8")

    assert "What This Does Not Yet Prove" in report
    assert "No API calls were made" in report
    assert "no real provider judgments were collected" in report.lower()
    assert "Dry-run evidence is capped at Level 2" in report

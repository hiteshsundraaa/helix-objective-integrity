import json
from pathlib import Path

import pytest

from helix.benchmark.v10_provider_dry_run import (
    load_provider_run_plan,
    load_v10_cases as load_dry_run_cases,
    load_v10_provider_dry_run_config,
    write_provider_dry_run_outputs,
)
from helix.benchmark.v10_provider_dry_run_bridge import (
    load_provider_dry_run_summary,
    load_v10_provider_dry_run_bridge_config,
    validate_provider_run_is_dry_run,
    write_provider_dry_run_bridge_outputs,
)


BRIDGE_CONFIG_PATH = Path("configs/v10_provider_dry_run_pipeline_bridge.json")
DRY_RUN_CONFIG_PATH = Path("configs/v10_provider_dry_run_executor.json")
PLAN_PATH = Path("benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json")
CASES_PATH = Path("benchmarks/v10_calibrated/v10_cases.jsonl")


def test_v10_provider_dry_run_bridge_config_loads() -> None:
    config = load_v10_provider_dry_run_bridge_config(BRIDGE_CONFIG_PATH)

    assert config.schema_version == "v10_provider_dry_run_pipeline_bridge_v1"
    assert config.dry_run_bridge
    assert config.evidence_policy.dry_run_bridge_evidence_level_cap == 2
    assert not config.evidence_policy.level_4_allowed
    assert not config.evidence_policy.level_5_allowed
    assert not config.allow_network_calls
    assert not config.allow_provider_sdk_imports
    assert not config.allow_api_keys


def test_v10_provider_dry_run_bridge_missing_provider_run_fails_clearly(tmp_path: Path) -> None:
    config = load_v10_provider_dry_run_bridge_config(BRIDGE_CONFIG_PATH)

    with pytest.raises(FileNotFoundError, match="Run examples/run_v10_provider_dry_run.py first"):
        write_provider_dry_run_bridge_outputs(
            provider_run_dir=tmp_path / "missing",
            cases_path=CASES_PATH,
            config=config,
            config_path=BRIDGE_CONFIG_PATH,
        )


def test_v10_provider_dry_run_bridge_rejects_non_dry_run_summary(tmp_path: Path) -> None:
    run_dir = _write_valid_dry_run(tmp_path)
    _mutate_summary(run_dir, {"dry_run": False})

    assert "provider_run_not_dry_run" in validate_provider_run_is_dry_run(run_dir)


def test_v10_provider_dry_run_bridge_validates_no_api_calls_true(tmp_path: Path) -> None:
    run_dir = _write_valid_dry_run(tmp_path)
    _mutate_summary(run_dir, {"no_api_calls_made": False})

    assert "provider_run_api_calls_not_excluded" in validate_provider_run_is_dry_run(run_dir)


def test_v10_provider_dry_run_bridge_rejects_api_key_observed(tmp_path: Path) -> None:
    run_dir = _write_valid_dry_run(tmp_path)
    _mutate_summary(run_dir, {"api_key_observed": True})

    assert "provider_run_api_key_observed" in validate_provider_run_is_dry_run(run_dir)


def test_v10_provider_dry_run_bridge_rejects_provider_sdk_imported(tmp_path: Path) -> None:
    run_dir = _write_valid_dry_run(tmp_path)
    _mutate_summary(run_dir, {"provider_sdk_imported": True})

    assert "provider_run_provider_sdk_imported" in validate_provider_run_is_dry_run(run_dir)


def test_v10_provider_dry_run_bridge_reads_parsed_judgments_and_writes_pipeline(tmp_path: Path) -> None:
    run_dir = _write_valid_dry_run(tmp_path)
    config = load_v10_provider_dry_run_bridge_config(BRIDGE_CONFIG_PATH)

    paths = write_provider_dry_run_bridge_outputs(
        provider_run_dir=run_dir,
        cases_path=CASES_PATH,
        config=config,
        config_path=BRIDGE_CONFIG_PATH,
        out_subdir="pipeline_bridge",
        generated_at="2026-06-09T00:00:00Z",
    )

    assert paths["parsed_raw_judgments"].exists()
    assert paths["normalized_output_dir"].exists()
    assert paths["benchmark_output_dir"].exists()
    assert paths["diagnostics_output_dir"].exists()
    assert paths["reportability_output_path"].exists()
    assert (paths["normalized_output_dir"] / "v10_normalization_summary.json").exists()
    assert (paths["benchmark_output_dir"] / "v10_benchmark_summary.json").exists()
    assert (paths["diagnostics_output_dir"] / "v10_diagnostics_summary.json").exists()
    assert (paths["bridge_dir"] / "reportability" / "v10_reportability_report.json").exists()


def test_v10_provider_dry_run_bridge_summary_caps_evidence_and_blocks_levels(tmp_path: Path) -> None:
    run_dir = _write_valid_dry_run(tmp_path)
    config = load_v10_provider_dry_run_bridge_config(BRIDGE_CONFIG_PATH)

    paths = write_provider_dry_run_bridge_outputs(
        provider_run_dir=run_dir,
        cases_path=CASES_PATH,
        config=config,
        config_path=BRIDGE_CONFIG_PATH,
        out_subdir="pipeline_bridge",
        generated_at="2026-06-09T00:00:00Z",
    )
    summary = json.loads(paths["bridge_summary"].read_text(encoding="utf-8"))

    assert summary["dry_run_bridge"] is True
    assert summary["no_api_calls_made"] is True
    assert summary["provider_sdk_imported"] is False
    assert summary["api_key_observed"] is False
    assert summary["raw_judgment_count"] == 30
    assert summary["normalized_judgment_count"] == 30
    assert summary["benchmark_receipt_count"] == 30
    assert summary["matched_case_count"] == 30
    assert summary["missing_judgment_case_count"] == 0
    assert summary["final_evidence_level"] <= 2
    assert summary["level_4_allowed"] is False
    assert summary["level_5_allowed"] is False
    if summary["mechanical_reportability_passed"]:
        assert "mechanical_reportability_passed_but_dry_run_cap_applied" in summary["warnings"]


def test_v10_provider_dry_run_bridge_report_contains_limits(tmp_path: Path) -> None:
    run_dir = _write_valid_dry_run(tmp_path)
    config = load_v10_provider_dry_run_bridge_config(BRIDGE_CONFIG_PATH)

    paths = write_provider_dry_run_bridge_outputs(
        provider_run_dir=run_dir,
        cases_path=CASES_PATH,
        config=config,
        config_path=BRIDGE_CONFIG_PATH,
        out_subdir="pipeline_bridge",
        generated_at="2026-06-09T00:00:00Z",
    )
    report = paths["bridge_report"].read_text(encoding="utf-8")

    assert "What This Does Not Yet Prove" in report
    assert "No API calls were made" in report
    assert "No real provider judgments were collected" in report
    assert "existing v10 pipeline" in report.lower()
    assert "Level 4 false" in report
    assert "Level 5 false" in report


def _write_valid_dry_run(tmp_path: Path) -> Path:
    dry_config = load_v10_provider_dry_run_config(DRY_RUN_CONFIG_PATH)
    plan = load_provider_run_plan(PLAN_PATH)
    cases = load_dry_run_cases(CASES_PATH)
    paths = write_provider_dry_run_outputs(
        run_id="dry_run_test",
        plan=plan,
        plan_path=PLAN_PATH,
        cases=cases,
        config=dry_config,
        config_path=DRY_RUN_CONFIG_PATH,
        out_root=tmp_path,
        generated_at="2026-06-09T00:00:00Z",
    )
    return paths["run_dir"]


def _mutate_summary(run_dir: Path, updates: dict[str, object]) -> None:
    summary_path = run_dir / "provider_dry_run_summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload.update(updates)
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

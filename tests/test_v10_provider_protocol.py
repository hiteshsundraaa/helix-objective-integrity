import json
from pathlib import Path

import pytest

from helix.benchmark.v10_provider_protocol import (
    build_v10_full_case_list,
    build_v10_pilot_case_sample,
    build_v10_provider_run_plan,
    load_v10_cases,
    load_v10_provider_protocol_config,
    write_v10_provider_run_plan,
)


CONFIG_PATH = Path("configs/v10_provider_judgment_protocol.json")


def test_v10_provider_protocol_config_loads() -> None:
    config = load_v10_provider_protocol_config(CONFIG_PATH)

    assert config.schema_version == "v10_provider_judgment_protocol_v1"
    assert config.registered_before_provider_calls
    assert config.default_run_stage == "pilot"
    assert config.provider is None
    assert config.model is None
    assert not config.level_5_allowed


def test_v10_pilot_sample_has_30_cases_and_3_per_family() -> None:
    config = load_v10_provider_protocol_config(CONFIG_PATH)
    cases = load_v10_cases(config.cases_path)

    sample = build_v10_pilot_case_sample(cases, config)

    assert sample.stage == "pilot"
    assert sample.case_count == 30
    assert set(sample.family_counts.values()) == {3}
    assert len(sample.family_counts) == 10
    assert len(sample.sampled_case_ids) == 30


def test_v10_full_sample_has_all_300_cases() -> None:
    config = load_v10_provider_protocol_config(CONFIG_PATH)
    cases = load_v10_cases(config.cases_path)

    sample = build_v10_full_case_list(cases, config)

    assert sample.stage == "full"
    assert sample.case_count == 300
    assert len(sample.sampled_case_ids) == 300
    assert sample.sampled_case_ids == sorted(sample.sampled_case_ids)


def test_v10_pilot_sampling_is_deterministic() -> None:
    config = load_v10_provider_protocol_config(CONFIG_PATH)
    cases = load_v10_cases(config.cases_path)

    first = build_v10_pilot_case_sample(cases, config)
    second = build_v10_pilot_case_sample(cases, config)

    assert first == second
    assert first.deterministic_seed == 42


def test_v10_provider_run_plan_records_hashes_and_null_metadata() -> None:
    config = load_v10_provider_protocol_config(CONFIG_PATH)
    cases = load_v10_cases(config.cases_path)

    plan = build_v10_provider_run_plan(
        cases=cases,
        config=config,
        config_path=CONFIG_PATH,
        stage="pilot",
    )

    assert plan.case_count == 30
    assert plan.provider is None
    assert plan.model is None
    assert plan.no_api_calls_made
    assert not plan.level_5_allowed
    assert plan.prompt_hashes["contract_prompt"].startswith("sha256:")
    assert plan.prompt_hashes["prompt_rendering_manifest"].startswith("sha256:")
    assert plan.config_hashes["provider_protocol_config"].startswith("sha256:")
    assert plan.config_hashes["cases"].startswith("sha256:")
    assert "provider_or_model_not_filled_for_planning" in plan.warnings


def test_v10_provider_run_plan_outputs_are_written(tmp_path: Path) -> None:
    config = load_v10_provider_protocol_config(CONFIG_PATH)
    cases = load_v10_cases(config.cases_path)
    plan = build_v10_provider_run_plan(
        cases=cases,
        config=config,
        config_path=CONFIG_PATH,
        stage="pilot",
    )

    paths = write_v10_provider_run_plan(
        plan=plan,
        config_path=CONFIG_PATH,
        out_dir=tmp_path,
        generated_at="2026-06-07T00:00:00Z",
    )

    for path in paths.values():
        assert path.exists()
    sampled = json.loads(paths["sampled_case_ids"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    report = paths["report"].read_text(encoding="utf-8")
    assert sampled["case_count"] == 30
    assert manifest["manifest_hash"].startswith("sha256:")
    assert manifest["no_api_calls_made"] is True
    assert "No API calls were made" in report
    assert "Level 5 is not allowed" in report


def test_v10_full_provider_run_plan_outputs_300_case_plan() -> None:
    config = load_v10_provider_protocol_config(CONFIG_PATH)
    cases = load_v10_cases(config.cases_path)

    plan = build_v10_provider_run_plan(
        cases=cases,
        config=config,
        config_path=CONFIG_PATH,
        stage="full",
    )

    assert plan.stage == "full"
    assert plan.case_count == 300
    assert len(plan.sampled_case_ids) == 300
    assert "pilot_run_not_final_evidence" not in plan.warnings


def test_v10_provider_planning_missing_selected_prompt_fails_clearly(tmp_path: Path) -> None:
    config = load_v10_provider_protocol_config(CONFIG_PATH)
    cases = load_v10_cases(config.cases_path)
    broken = config.model_copy(
        update={"contract_prompt_path": str(tmp_path / "missing_contract_prompt.md")}
    )

    with pytest.raises(FileNotFoundError, match="Render v10 prompts before planning provider run"):
        build_v10_provider_run_plan(
            cases=cases,
            config=broken,
            config_path=CONFIG_PATH,
            stage="pilot",
        )

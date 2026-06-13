from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.oar_360_prompt_rendering import (
    build_ground_truth_holdout,
    build_prompt_pack,
    load_oar_360_cases,
    load_oar_360_prompt_rendering_config,
    summarize_prompt_rendering,
    validate_prompt_pack,
    validate_prompt_no_ground_truth,
    write_oar_360_prompt_outputs,
)


CONFIG_PATH = Path("configs/oar_360_prompt_rendering.json")
CASES_PATH = Path("benchmarks/oar_360/oar_360_cases.jsonl")
CASE_MANIFEST_PATH = Path("benchmarks/oar_360/oar_360_case_manifest.json")


def _fixture():
    config = load_oar_360_prompt_rendering_config(CONFIG_PATH)
    cases = load_oar_360_cases(CASES_PATH)
    prompts = build_prompt_pack(cases, config)
    holdout = build_ground_truth_holdout(cases, config)
    return config, cases, prompts, holdout


def test_config_loads() -> None:
    config = load_oar_360_prompt_rendering_config(CONFIG_PATH)

    assert config.schema_version == "oar_360_prompt_rendering_config_v1"
    assert config.suite_name == "OAR-360"
    assert "label" in config.withheld_fields
    assert "ALLOW" in config.allowed_decisions


def test_cases_prompts_and_holdout_counts() -> None:
    config, cases, prompts, holdout = _fixture()

    assert len(cases) == 360
    assert len(prompts) == 360
    assert len(holdout) == 360
    assert validate_prompt_pack(prompts, holdout, config, cases) == []


def test_prompts_do_not_include_ground_truth_or_answer_key_fields() -> None:
    _config, cases, prompts, _holdout = _fixture()
    cases_by_id = {case["case_id"]: case for case in cases}

    for prompt in prompts:
        text = prompt.prompt_text
        source_case = cases_by_id[prompt.case_id]
        assert "ground_truth" not in text
        assert "label" not in text
        assert "risk_band" not in text
        assert "expected_decision" not in text
        assert "expected_risk_interval" not in text
        assert "required_citation_phrases" not in text
        assert "case_hash" not in text
        assert validate_prompt_no_ground_truth(prompt, source_case) == []


def test_prompt_records_include_source_hashes_and_unique_case_ids() -> None:
    _config, _cases, prompts, holdout = _fixture()

    assert all(prompt.source_case_hash.startswith("sha256:") for prompt in prompts)
    assert all(prompt.prompt_hash.startswith("sha256:") for prompt in prompts)
    assert len({prompt.case_id for prompt in prompts}) == 360
    assert len({record.case_id for record in holdout}) == 360
    assert {prompt.case_id for prompt in prompts} == {record.case_id for record in holdout}


def test_holdout_contains_ground_truth_fields() -> None:
    _config, _cases, _prompts, holdout = _fixture()

    assert any(record.expected_decision == "BLOCK" for record in holdout)
    assert any(record.required_citation_phrases for record in holdout)
    assert all(record.case_hash.startswith("sha256:") for record in holdout)
    assert all(record.expected_risk_interval for record in holdout)


def test_outputs_write_provider_packs_manifest_and_report(tmp_path: Path) -> None:
    config, cases, prompts, holdout = _fixture()
    validation_issues = validate_prompt_pack(prompts, holdout, config, cases)
    summary = summarize_prompt_rendering(prompts, holdout, config, validation_issues)
    result = write_oar_360_prompt_outputs(
        prompts,
        holdout,
        summary,
        tmp_path,
        source_cases_path=CASES_PATH,
        source_case_manifest_path=CASE_MANIFEST_PATH,
        config=config,
    )
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    report = Path(result["report_path"]).read_text(encoding="utf-8")

    assert (tmp_path / "oar_360_prompt_pack.jsonl").exists()
    assert (tmp_path / "oar_360_prompt_manifest.json").exists()
    assert (tmp_path / "oar_360_prompt_rendering_report.md").exists()
    assert (tmp_path / "provider_prompt_packs" / "generic_oar360_prompt_pack.md").exists()
    assert (tmp_path / "provider_prompt_packs" / "google_oar360_prompt_pack.md").exists()
    assert (tmp_path / "provider_prompt_packs" / "anthropic_oar360_prompt_pack.md").exists()
    assert (tmp_path / "provider_prompt_packs" / "openai_oar360_prompt_pack.md").exists()
    assert (
        tmp_path
        / "ground_truth_holdout"
        / "oar_360_ground_truth_holdout.jsonl"
    ).exists()
    assert (
        tmp_path
        / "ground_truth_holdout"
        / "oar_360_ground_truth_holdout_manifest.json"
    ).exists()
    assert manifest["ground_truth_excluded"] is True
    assert manifest["no_provider_calls"] is True
    assert manifest["no_model_outputs"] is True
    assert manifest["semantic_equivalence_claim"] is True
    assert manifest["source_case_manifest_hash"].startswith("sha256:")
    assert "google_prompt_pack_hash" in manifest["provider_prompt_pack_hashes"]
    assert "no model outputs" in report
    assert "does not prove model correctness" in report


def test_prompt_rendering_is_deterministic_across_reruns(tmp_path: Path) -> None:
    config, cases, prompts, holdout = _fixture()
    validation_issues = validate_prompt_pack(prompts, holdout, config, cases)
    summary = summarize_prompt_rendering(prompts, holdout, config, validation_issues)
    first = write_oar_360_prompt_outputs(
        prompts,
        holdout,
        summary,
        tmp_path / "first",
        source_cases_path=CASES_PATH,
        source_case_manifest_path=CASE_MANIFEST_PATH,
        config=config,
    )
    second_prompts = build_prompt_pack(load_oar_360_cases(CASES_PATH), config)
    second_holdout = build_ground_truth_holdout(load_oar_360_cases(CASES_PATH), config)
    second_summary = summarize_prompt_rendering(
        second_prompts,
        second_holdout,
        config,
        validate_prompt_pack(second_prompts, second_holdout, config, cases),
    )
    second = write_oar_360_prompt_outputs(
        second_prompts,
        second_holdout,
        second_summary,
        tmp_path / "second",
        source_cases_path=CASES_PATH,
        source_case_manifest_path=CASE_MANIFEST_PATH,
        config=config,
    )

    assert first["prompt_pack_hash"] == second["prompt_pack_hash"]
    assert first["holdout_file_hash"] == second["holdout_file_hash"]
    assert first["manifest_hash"] == second["manifest_hash"]

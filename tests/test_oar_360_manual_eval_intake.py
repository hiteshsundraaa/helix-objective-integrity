from __future__ import annotations

import json
from pathlib import Path
import tempfile

from helix.benchmark.oar_360_manual_eval_intake import (
    build_expected_raw_output_filenames,
    build_oar_360_batch_plan,
    build_system_registry_template,
    load_case_manifest,
    load_cases,
    load_oar_360_manual_eval_intake_config,
    load_prompt_manifest,
    validate_manual_eval_readiness,
    write_oar_360_manual_eval_intake_outputs,
)


CONFIG_PATH = Path("configs/oar_360_manual_eval_intake.json")
CASES_PATH = Path("benchmarks/oar_360/oar_360_cases.jsonl")
CASE_MANIFEST_PATH = Path("benchmarks/oar_360/oar_360_case_manifest.json")
PROMPT_MANIFEST_PATH = Path("benchmarks/oar_360/prompts/oar_360_prompt_manifest.json")
PROMPT_ROOT = Path("benchmarks/oar_360/prompts")


def _fixture(tmp_path: Path | None = None):
    config = load_oar_360_manual_eval_intake_config(CONFIG_PATH)
    cases = load_cases(CASES_PATH)
    case_manifest = load_case_manifest(CASE_MANIFEST_PATH)
    prompt_manifest = load_prompt_manifest(PROMPT_MANIFEST_PATH)
    registry = build_system_registry_template(config)
    batches = build_oar_360_batch_plan(cases, config)
    expected = build_expected_raw_output_filenames(registry, batches, config)
    out_dir = tmp_path or Path(tempfile.mkdtemp(prefix="oar360_manual_eval_test_"))
    readiness = validate_manual_eval_readiness(
        CASES_PATH,
        CASE_MANIFEST_PATH,
        PROMPT_MANIFEST_PATH,
        PROMPT_ROOT,
        out_dir,
        cases,
        batches,
        registry,
        expected,
        config,
    )
    return config, cases, case_manifest, prompt_manifest, registry, batches, expected, readiness


def test_config_loads() -> None:
    config = load_oar_360_manual_eval_intake_config(CONFIG_PATH)

    assert config.suite_name == "OAR-360"
    assert config.no_provider_calls is True
    assert config.no_model_outputs is True
    assert config.evidence_level == 0


def test_batch_plan_shape() -> None:
    config, cases, *_rest = _fixture()
    batches = build_oar_360_batch_plan(cases, config)

    assert len(batches) == 22
    assert len([batch for batch in batches if batch.batch_type == "family"]) == 12
    assert len([batch for batch in batches if batch.batch_type == "mixed"]) == 6
    assert len([batch for batch in batches if batch.batch_type == "balanced"]) == 3
    assert len([batch for batch in batches if batch.batch_type == "full"]) == 1


def test_family_batches_cover_all_cases_once() -> None:
    _config, cases, _case_manifest, _prompt_manifest, _registry, batches, *_rest = _fixture()
    case_ids = {case["case_id"] for case in cases}
    family_batches = [batch for batch in batches if batch.batch_type == "family"]
    family_case_ids = [case_id for batch in family_batches for case_id in batch.case_ids]

    assert len(set(family_case_ids)) == 360
    assert set(family_case_ids) == case_ids
    assert all(batch.case_count == 30 for batch in family_batches)


def test_mixed_batches_cover_all_cases_once() -> None:
    _config, cases, _case_manifest, _prompt_manifest, _registry, batches, *_rest = _fixture()
    case_ids = {case["case_id"] for case in cases}
    mixed_batches = [batch for batch in batches if batch.batch_type == "mixed"]
    mixed_case_ids = [case_id for batch in mixed_batches for case_id in batch.case_ids]

    assert len(set(mixed_case_ids)) == 360
    assert set(mixed_case_ids) == case_ids
    assert all(batch.case_count == 60 for batch in mixed_batches)


def test_balanced_batches_cover_all_cases_once() -> None:
    _config, cases, _case_manifest, _prompt_manifest, _registry, batches, *_rest = _fixture()
    case_ids = {case["case_id"] for case in cases}
    balanced_batches = [batch for batch in batches if batch.batch_type == "balanced"]
    balanced_case_ids = [case_id for batch in balanced_batches for case_id in batch.case_ids]

    assert len(set(balanced_case_ids)) == 360
    assert set(balanced_case_ids) == case_ids
    assert all(batch.case_count == 120 for batch in balanced_batches)


def test_full_batch_has_all_cases() -> None:
    _config, cases, _case_manifest, _prompt_manifest, _registry, batches, *_rest = _fixture()
    full_batch = [batch for batch in batches if batch.batch_id == "full_oar_360"][0]

    assert full_batch.case_count == 360
    assert set(full_batch.case_ids) == {case["case_id"] for case in cases}


def test_system_registry_defaults() -> None:
    config, *_rest = _fixture()
    registry = build_system_registry_template(config)
    roles = [system["role"] for system in registry["systems"]]
    providers = {system["provider"] for system in registry["systems"]}

    assert len(registry["systems"]) == 3
    assert len(set(roles)) == 3
    assert providers == {"google", "anthropic", "openai"}
    assert registry["level_4_allowed"] is False
    assert registry["level_5_allowed"] is False


def test_expected_raw_output_filenames() -> None:
    _config, _cases, _case_manifest, _prompt_manifest, _registry, _batches, expected, *_rest = _fixture()
    paths = [record.relative_path for record in expected]

    assert len(expected) == 66
    assert all(record.expected_filename.endswith("_raw.jsonl") for record in expected)
    assert all(record.relative_path.startswith(f"raw_outputs/{record.provider}/") for record in expected)
    assert len(set(paths)) == len(paths)


def test_write_outputs_creates_required_files(tmp_path: Path) -> None:
    config, cases, case_manifest, prompt_manifest, registry, batches, expected, readiness = _fixture(tmp_path)
    summary = write_oar_360_manual_eval_intake_outputs(
        config,
        cases,
        case_manifest,
        prompt_manifest,
        batches,
        registry,
        expected,
        readiness,
        tmp_path,
    )

    assert summary.batch_count == 22
    assert (tmp_path / "oar_360_manual_eval_plan.json").exists()
    assert (tmp_path / "oar_360_system_registry_template.json").exists()
    assert (tmp_path / "oar_360_batch_plan.json").exists()
    assert (tmp_path / "oar_360_collection_instructions.md").exists()
    assert (tmp_path / "oar_360_expected_raw_output_filenames.json").exists()
    assert (tmp_path / "oar_360_intake_manifest.json").exists()
    assert (tmp_path / "oar_360_intake_report.md").exists()
    assert (tmp_path / "raw_outputs" / "README.md").exists()
    assert (tmp_path / "raw_outputs" / "google" / ".gitkeep").exists()
    assert (tmp_path / "raw_outputs" / "anthropic" / ".gitkeep").exists()
    assert (tmp_path / "raw_outputs" / "openai" / ".gitkeep").exists()


def test_manifest_flags(tmp_path: Path) -> None:
    config, cases, case_manifest, prompt_manifest, registry, batches, expected, readiness = _fixture(tmp_path)
    write_oar_360_manual_eval_intake_outputs(
        config,
        cases,
        case_manifest,
        prompt_manifest,
        batches,
        registry,
        expected,
        readiness,
        tmp_path,
    )
    manifest = json.loads((tmp_path / "oar_360_intake_manifest.json").read_text(encoding="utf-8"))

    assert manifest["no_provider_calls"] is True
    assert manifest["no_model_outputs"] is True
    assert manifest["ground_truth_not_exposed"] is True
    assert manifest["evidence_level"] == 0
    assert manifest["manual_result_evidence_cap"] == 3


def test_report_claim_boundaries(tmp_path: Path) -> None:
    config, cases, case_manifest, prompt_manifest, registry, batches, expected, readiness = _fixture(tmp_path)
    write_oar_360_manual_eval_intake_outputs(
        config,
        cases,
        case_manifest,
        prompt_manifest,
        batches,
        registry,
        expected,
        readiness,
        tmp_path,
    )
    report = (tmp_path / "oar_360_intake_report.md").read_text(encoding="utf-8")

    assert "does not prove model correctness" in report
    assert "No provider calls were made" in report
    assert "no model outputs were created" in report
    assert "Manual collection results will be capped at Level 3" in report
    assert "Do not edit malformed rows" in report
    assert "Majority vote is not truth" in report


def test_no_raw_outputs_created(tmp_path: Path) -> None:
    config, cases, case_manifest, prompt_manifest, registry, batches, expected, readiness = _fixture(tmp_path)
    write_oar_360_manual_eval_intake_outputs(
        config,
        cases,
        case_manifest,
        prompt_manifest,
        batches,
        registry,
        expected,
        readiness,
        tmp_path,
    )
    raw_files = sorted(path.relative_to(tmp_path / "raw_outputs") for path in (tmp_path / "raw_outputs").rglob("*") if path.is_file())

    assert raw_files == [
        Path("README.md"),
        Path("anthropic/.gitkeep"),
        Path("google/.gitkeep"),
        Path("openai/.gitkeep"),
    ]
    assert not list((tmp_path / "raw_outputs").rglob("*.jsonl"))

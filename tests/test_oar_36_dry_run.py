from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.oar_36_dry_run import (
    build_oar_36_expected_raw_output_filenames,
    build_oar_36_holdout,
    build_oar_36_prompt_pack,
    load_oar_36_dry_run_config,
    load_oar_360_cases,
    load_oar_360_holdout,
    load_oar_360_prompts,
    select_oar_36_cases,
    validate_oar_36_selection,
    write_oar_36_outputs,
)


CONFIG_PATH = Path("configs/oar_36_dry_run_config.json")
CASES_PATH = Path("benchmarks/oar_360/oar_360_cases.jsonl")
CASE_MANIFEST_PATH = Path("benchmarks/oar_360/oar_360_case_manifest.json")
PROMPTS_PATH = Path("benchmarks/oar_360/prompts/oar_360_prompt_pack.jsonl")
PROMPT_MANIFEST_PATH = Path("benchmarks/oar_360/prompts/oar_360_prompt_manifest.json")
HOLDOUT_PATH = Path("benchmarks/oar_360/prompts/ground_truth_holdout/oar_360_ground_truth_holdout.jsonl")
HOLDOUT_MANIFEST_PATH = Path("benchmarks/oar_360/prompts/ground_truth_holdout/oar_360_ground_truth_holdout_manifest.json")


def _fixture():
    config = load_oar_36_dry_run_config(CONFIG_PATH)
    cases = load_oar_360_cases(CASES_PATH)
    prompts = load_oar_360_prompts(PROMPTS_PATH)
    holdout = load_oar_360_holdout(HOLDOUT_PATH)
    selected = select_oar_36_cases(cases, config)
    selected_ids = [case["case_id"] for case in selected]
    dry_prompts = build_oar_36_prompt_pack(selected_ids, prompts, config)
    dry_holdout = build_oar_36_holdout(selected_ids, holdout, config)
    expected = build_oar_36_expected_raw_output_filenames(config)
    return config, selected, dry_prompts, dry_holdout, expected


def _count(records, key):
    counts = {}
    for record in records:
        counts[record[key]] = counts.get(record[key], 0) + 1
    return dict(sorted(counts.items()))


def _edge_count(records):
    tags = set()
    for record in records:
        tags.update(record["edge_case_tags"])
    return len(tags)


def test_config_loads() -> None:
    config = load_oar_36_dry_run_config(CONFIG_PATH)

    assert config.suite_name == "OAR-36"
    assert config.source_suite == "OAR-360"
    assert config.no_provider_calls is True
    assert config.no_model_outputs is True


def test_selection_shape_and_distributions() -> None:
    config, selected, _prompts, _holdout, _expected = _fixture()

    assert len(selected) == 36
    assert len(_count(selected, "family")) == 12
    assert all(count == 3 for count in _count(selected, "family").values())
    assert len(_count(selected, "label")) == 4
    assert len(_count(selected, "expected_decision")) == 6
    assert len(_count(selected, "risk_band")) == 6
    assert len(_count(selected, "domain")) == 10
    assert _edge_count(selected) >= 18
    assert validate_oar_36_selection(selected, [], [], config) == []


def test_prompt_and_holdout_records_match_selection_and_do_not_leak() -> None:
    config, selected, prompts, holdout, _expected = _fixture()
    selected_ids = {case["case_id"] for case in selected}

    assert len(prompts) == 36
    assert len(holdout) == 36
    assert {prompt["case_id"] for prompt in prompts} == selected_ids
    assert {record["case_id"] for record in holdout} == selected_ids
    for prompt in prompts:
        text = prompt["prompt_text"]
        assert "label" not in text
        assert "risk_band" not in text
        assert "expected_decision" not in text
        assert "expected_risk_interval" not in text
        assert "ground_truth" not in text
        assert prompt["source_oar360_prompt_hash"].startswith("sha256:")
    for record in holdout:
        assert "expected_decision" in record
        assert "required_citation_phrases" in record
    assert validate_oar_36_selection(selected, prompts, holdout, config) == []


def test_expected_raw_output_filenames_count() -> None:
    _config, _selected, _prompts, _holdout, expected = _fixture()

    assert len(expected) == 3
    assert all(record.expected_filename.endswith("_raw.jsonl") for record in expected)
    assert {record.provider for record in expected} == {"google", "anthropic", "openai"}


def test_write_outputs_and_manifests(tmp_path: Path) -> None:
    config, selected, prompts, holdout, expected = _fixture()
    summary = write_oar_36_outputs(
        config=config,
        selected_cases=selected,
        prompts=prompts,
        holdout=holdout,
        expected_raw_outputs=expected,
        source_case_file=CASES_PATH,
        source_case_manifest=json.loads(CASE_MANIFEST_PATH.read_text(encoding="utf-8")),
        source_prompt_pack=PROMPTS_PATH,
        source_prompt_manifest=json.loads(PROMPT_MANIFEST_PATH.read_text(encoding="utf-8")),
        source_holdout_file=HOLDOUT_PATH,
        source_holdout_manifest=json.loads(HOLDOUT_MANIFEST_PATH.read_text(encoding="utf-8")),
        out_dir=tmp_path,
    )

    assert summary.total_cases == 36
    assert (tmp_path / "oar_36_cases.jsonl").exists()
    assert (tmp_path / "oar_36_case_manifest.json").exists()
    assert (tmp_path / "oar_36_prompt_pack.jsonl").exists()
    assert (tmp_path / "oar_36_prompt_manifest.json").exists()
    assert (tmp_path / "oar_36_ground_truth_holdout.jsonl").exists()
    assert (tmp_path / "oar_36_ground_truth_holdout_manifest.json").exists()
    assert (tmp_path / "oar_36_manual_eval_plan.json").exists()
    assert (tmp_path / "oar_36_expected_raw_output_filenames.json").exists()
    assert (tmp_path / "oar_36_collection_instructions.md").exists()
    assert (tmp_path / "oar_36_report.md").exists()
    assert (tmp_path / "raw_outputs" / "README.md").exists()
    assert (tmp_path / "raw_outputs" / "google" / ".gitkeep").exists()
    assert (tmp_path / "raw_outputs" / "anthropic" / ".gitkeep").exists()
    assert (tmp_path / "raw_outputs" / "openai" / ".gitkeep").exists()

    case_manifest = json.loads((tmp_path / "oar_36_case_manifest.json").read_text(encoding="utf-8"))
    prompt_manifest = json.loads((tmp_path / "oar_36_prompt_manifest.json").read_text(encoding="utf-8"))
    holdout_manifest = json.loads((tmp_path / "oar_36_ground_truth_holdout_manifest.json").read_text(encoding="utf-8"))
    assert case_manifest["no_provider_calls"] is True
    assert case_manifest["no_model_outputs"] is True
    assert prompt_manifest["no_provider_calls"] is True
    assert prompt_manifest["no_model_outputs"] is True
    assert holdout_manifest["not_for_model_prompting"] is True


def test_report_claim_boundaries_and_raw_dirs(tmp_path: Path) -> None:
    config, selected, prompts, holdout, expected = _fixture()
    write_oar_36_outputs(
        config=config,
        selected_cases=selected,
        prompts=prompts,
        holdout=holdout,
        expected_raw_outputs=expected,
        source_case_file=CASES_PATH,
        source_case_manifest=json.loads(CASE_MANIFEST_PATH.read_text(encoding="utf-8")),
        source_prompt_pack=PROMPTS_PATH,
        source_prompt_manifest=json.loads(PROMPT_MANIFEST_PATH.read_text(encoding="utf-8")),
        source_holdout_file=HOLDOUT_PATH,
        source_holdout_manifest=json.loads(HOLDOUT_MANIFEST_PATH.read_text(encoding="utf-8")),
        out_dir=tmp_path,
    )
    report = (tmp_path / "oar_36_report.md").read_text(encoding="utf-8")
    raw_files = sorted(path.relative_to(tmp_path / "raw_outputs") for path in (tmp_path / "raw_outputs").rglob("*") if path.is_file())

    assert "no empirical results were created" in report
    assert "does not prove model correctness" in report
    assert "does not estimate full OAR-360 performance" in report
    assert raw_files == [
        Path("README.md"),
        Path("anthropic/.gitkeep"),
        Path("google/.gitkeep"),
        Path("openai/.gitkeep"),
    ]


def test_deterministic_rerun_same_selection_and_hashes(tmp_path: Path) -> None:
    config, selected, prompts, holdout, expected = _fixture()
    first = write_oar_36_outputs(
        config=config,
        selected_cases=selected,
        prompts=prompts,
        holdout=holdout,
        expected_raw_outputs=expected,
        source_case_file=CASES_PATH,
        source_case_manifest=json.loads(CASE_MANIFEST_PATH.read_text(encoding="utf-8")),
        source_prompt_pack=PROMPTS_PATH,
        source_prompt_manifest=json.loads(PROMPT_MANIFEST_PATH.read_text(encoding="utf-8")),
        source_holdout_file=HOLDOUT_PATH,
        source_holdout_manifest=json.loads(HOLDOUT_MANIFEST_PATH.read_text(encoding="utf-8")),
        out_dir=tmp_path / "first",
    )
    config2, selected2, prompts2, holdout2, expected2 = _fixture()
    second = write_oar_36_outputs(
        config=config2,
        selected_cases=selected2,
        prompts=prompts2,
        holdout=holdout2,
        expected_raw_outputs=expected2,
        source_case_file=CASES_PATH,
        source_case_manifest=json.loads(CASE_MANIFEST_PATH.read_text(encoding="utf-8")),
        source_prompt_pack=PROMPTS_PATH,
        source_prompt_manifest=json.loads(PROMPT_MANIFEST_PATH.read_text(encoding="utf-8")),
        source_holdout_file=HOLDOUT_PATH,
        source_holdout_manifest=json.loads(HOLDOUT_MANIFEST_PATH.read_text(encoding="utf-8")),
        out_dir=tmp_path / "second",
    )

    assert [case["case_id"] for case in selected] == [case["case_id"] for case in selected2]
    assert first.case_manifest_hash == second.case_manifest_hash
    assert first.prompt_manifest_hash == second.prompt_manifest_hash
    assert first.holdout_manifest_hash == second.holdout_manifest_hash

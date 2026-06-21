from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.oar_36_raw_receipt_prep import (
    build_oar_36_receipt_preparation,
    load_expected_raw_output_filenames,
    load_jsonl,
    load_oar_36_raw_receipt_prep_config,
    validate_raw_receipt_prep,
    write_oar_36_receipt_prep_outputs,
)


CONFIG_PATH = Path("configs/oar_36_raw_receipt_prep.json")
CASES_PATH = Path("benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl")
PROMPTS_PATH = Path("benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_pack.jsonl")
EXPECTED_FILES_PATH = Path("benchmarks/oar_360/oar_36_dry_run/oar_36_expected_raw_output_filenames.json")


def _fixture():
    config = load_oar_36_raw_receipt_prep_config(CONFIG_PATH)
    cases = load_jsonl(CASES_PATH)
    prompts = load_jsonl(PROMPTS_PATH)
    expected = load_expected_raw_output_filenames(EXPECTED_FILES_PATH)
    return config, cases, prompts, expected


def _valid_row(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "decision": "ALLOW",
        "violation_probability": 0.05,
        "cited_contract_phrase": "",
        "citation_verification_method": "missing",
        "reason_codes": ["safe.constraint_preserved"],
    }


def _write_raw(raw_root: Path, expected: dict, rows: list[str]) -> Path:
    relative = Path(expected["relative_path"])
    if relative.parts and relative.parts[0] == "raw_outputs":
        relative = Path(*relative.parts[1:])
    path = raw_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _run(raw_root: Path):
    config, cases, prompts, expected = _fixture()
    return validate_raw_receipt_prep(
        config=config,
        cases=cases,
        prompts=prompts,
        expected_files=expected,
        raw_output_root=raw_root,
    )


def test_config_loads() -> None:
    config = load_oar_36_raw_receipt_prep_config(CONFIG_PATH)

    assert config.suite_name == "OAR-36"
    assert config.no_provider_calls is True
    assert config.no_fake_outputs is True
    assert config.score_against_holdout is False


def test_awaiting_raw_outputs_state(tmp_path: Path) -> None:
    summary, _inventory, _lint, normalized, receipts = _run(tmp_path / "raw_outputs")

    assert summary.import_state == "awaiting_raw_outputs"
    assert summary.expected_file_count == 3
    assert summary.present_file_count == 0
    assert summary.normalized_judgment_count == 0
    assert summary.receipt_preparation_count == 0
    assert normalized == []
    assert receipts == []


def test_partial_valid_raw_file_creates_normalized_and_receipt_rows(tmp_path: Path) -> None:
    config, cases, _prompts, expected = _fixture()
    raw_root = tmp_path / "raw_outputs"
    _write_raw(
        raw_root,
        expected[0],
        [
            json.dumps(_valid_row(cases[0]["case_id"]), sort_keys=True),
            json.dumps(_valid_row(cases[1]["case_id"]), sort_keys=True),
        ],
    )

    summary, _inventory, _lint, normalized, receipts = _run(raw_root)

    assert summary.normalized_judgment_count == 2
    assert summary.receipt_preparation_count == 2
    assert summary.receipt_ready_count == 2
    assert all(record.evidence_level == 3 for record in receipts)
    assert summary.ground_truth_used is False
    assert all(record.normalized_judgment_hash.startswith("sha256:") for record in normalized)


def test_malformed_json_blocks_receipt(tmp_path: Path) -> None:
    _config, _cases, _prompts, expected = _fixture()
    raw_root = tmp_path / "raw_outputs"
    _write_raw(raw_root, expected[0], ['{"case_id": "oar360_case_0001"'])

    summary, _inventory, lint, normalized, receipts = _run(raw_root)

    assert summary.malformed_json_line_count == 1
    assert "malformed_json_line_count" in lint[0].issues
    assert normalized[0].parse_status == "malformed_json"
    assert receipts[0].receipt_ready is False


def test_missing_required_field_blocks_receipt(tmp_path: Path) -> None:
    _config, cases, _prompts, expected = _fixture()
    raw_root = tmp_path / "raw_outputs"
    row = _valid_row(cases[0]["case_id"])
    row.pop("reason_codes")
    _write_raw(raw_root, expected[0], [json.dumps(row)])

    summary, _inventory, _lint, normalized, receipts = _run(raw_root)

    assert summary.records_missing_required_fields == 1
    assert normalized[0].parse_status == "missing_required_fields"
    assert receipts[0].receipt_ready is False


def test_invalid_decision_or_score_blocks_receipt(tmp_path: Path) -> None:
    _config, cases, _prompts, expected = _fixture()
    raw_root = tmp_path / "raw_outputs"
    row = _valid_row(cases[0]["case_id"])
    row["decision"] = "INVALID"
    row["violation_probability"] = 1.5
    _write_raw(raw_root, expected[0], [json.dumps(row)])

    summary, _inventory, _lint, normalized, receipts = _run(raw_root)

    assert summary.invalid_decision_count == 1
    assert summary.invalid_score_count == 1
    assert normalized[0].parse_status == "invalid_fields"
    assert receipts[0].receipt_ready is False


def test_no_ground_truth_scoring(tmp_path: Path) -> None:
    summary, inventory, lint, normalized, receipts = _run(tmp_path / "raw_outputs")
    out_dir = tmp_path / "out"
    write_oar_36_receipt_prep_outputs(summary, inventory, lint, normalized, receipts, out_dir)
    manifest = json.loads((out_dir / "oar_36_receipt_prep_manifest.json").read_text(encoding="utf-8"))
    report = (out_dir / "oar_36_receipt_prep_report.md").read_text(encoding="utf-8")

    assert manifest["ground_truth_used"] is False
    assert manifest["score_against_holdout"] is False
    assert "no scoring against holdout occurred" in report


def test_receipt_material_hash_deterministic(tmp_path: Path) -> None:
    _config, cases, _prompts, expected = _fixture()
    raw_root = tmp_path / "raw_outputs"
    row = json.dumps(_valid_row(cases[0]["case_id"]), sort_keys=True)
    _write_raw(raw_root, expected[0], [row])

    first = _run(raw_root)
    second = _run(raw_root)

    assert first[3][0].normalized_judgment_hash == second[3][0].normalized_judgment_hash
    assert first[4][0].receipt_material_hash == second[4][0].receipt_material_hash


def test_outputs_written(tmp_path: Path) -> None:
    summary, inventory, lint, normalized, receipts = _run(tmp_path / "raw_outputs")
    out_dir = tmp_path / "out"
    write_oar_36_receipt_prep_outputs(summary, inventory, lint, normalized, receipts, out_dir)

    assert (out_dir / "oar_36_raw_import_status.json").exists()
    assert (out_dir / "oar_36_raw_file_inventory.json").exists()
    assert (out_dir / "oar_36_raw_schema_lint.json").exists()
    assert (out_dir / "oar_36_normalized_judgments.jsonl").exists()
    assert (out_dir / "oar_36_receipt_preparation.jsonl").exists()
    assert (out_dir / "oar_36_receipt_prep_manifest.json").exists()
    assert (out_dir / "oar_36_receipt_prep_report.md").exists()


def test_no_level_4_or_5_claim(tmp_path: Path) -> None:
    summary, inventory, lint, normalized, receipts = _run(tmp_path / "raw_outputs")
    out_dir = tmp_path / "out"
    write_oar_36_receipt_prep_outputs(summary, inventory, lint, normalized, receipts, out_dir)
    manifest = json.loads((out_dir / "oar_36_receipt_prep_manifest.json").read_text(encoding="utf-8"))
    report = (out_dir / "oar_36_receipt_prep_report.md").read_text(encoding="utf-8")

    assert manifest["level_4_allowed"] is False
    assert manifest["level_5_allowed"] is False
    assert "Level 4/5 not claimed" in report

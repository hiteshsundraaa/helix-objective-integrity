from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.oar_360_raw_import_validator import (
    load_cases,
    load_expected_raw_output_filenames,
    load_oar_360_raw_import_validator_config,
    validate_oar_360_raw_imports,
    write_oar_360_raw_import_validation_outputs,
)


CONFIG_PATH = Path("configs/oar_360_raw_import_validator.json")
EXPECTED_FILES_PATH = Path("benchmarks/oar_360/manual_eval/oar_360_expected_raw_output_filenames.json")
CASES_PATH = Path("benchmarks/oar_360/oar_360_cases.jsonl")


def _fixture():
    config = load_oar_360_raw_import_validator_config(CONFIG_PATH)
    expected_files = load_expected_raw_output_filenames(EXPECTED_FILES_PATH)
    cases = load_cases(CASES_PATH)
    return config, expected_files, cases


def _write_raw_file(raw_root: Path, expected: dict, rows: list[str]) -> Path:
    relative = Path(expected["relative_path"])
    if relative.parts and relative.parts[0] == "raw_outputs":
        relative = Path(*relative.parts[1:])
    path = raw_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _valid_row(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "decision": "ALLOW",
        "violation_probability": 0.05,
        "cited_contract_phrase": "",
        "citation_verification_method": "missing",
        "reason_codes": ["safe.constraint_preserved"],
    }


def test_config_loads() -> None:
    config = load_oar_360_raw_import_validator_config(CONFIG_PATH)

    assert config.no_provider_calls is True
    assert config.no_fake_outputs is True
    assert config.no_empirical_results is True
    assert config.ground_truth_use_allowed is False
    assert config.score_against_holdout is False


def test_awaiting_raw_outputs_state(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    raw_root.mkdir()

    summary, _inventory, _lint, _preview = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        raw_root,
    )

    assert summary.expected_file_count == 66
    assert summary.present_file_count == 0
    assert summary.missing_file_count == 66
    assert summary.import_state == "awaiting_raw_outputs"
    assert summary.no_empirical_results is True


def test_partial_valid_raw_output(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    row_one = json.dumps(_valid_row(cases[0]["case_id"]), sort_keys=True)
    row_two = json.dumps(_valid_row(cases[1]["case_id"]), sort_keys=True)
    _write_raw_file(raw_root, expected_files[0], [row_one, row_two])

    summary, _inventory, _lint, _preview = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        raw_root,
    )

    assert summary.present_file_count == 1
    assert summary.total_raw_lines == 2
    assert summary.parseable_json_line_count == 2
    assert summary.complete_required_field_record_count == 2
    assert summary.import_state == "partial_raw_outputs_present"


def test_malformed_json_detected(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    _write_raw_file(raw_root, expected_files[0], ['{"case_id": "oar360_case_0001"'])

    summary, _inventory, _lint, preview = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        raw_root,
    )

    assert summary.malformed_json_line_count > 0
    assert summary.import_state == "partial_with_schema_issues"
    assert preview[0].raw_line_hash.startswith("sha256:")


def test_missing_required_fields_detected(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    row = {"case_id": cases[0]["case_id"], "decision": "ALLOW", "violation_probability": 0.1}
    _write_raw_file(raw_root, expected_files[0], [json.dumps(row)])

    summary, _inventory, lint, _preview = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        raw_root,
    )

    assert lint[0].records_missing_required_fields > 0
    assert summary.complete_required_field_record_count < summary.total_raw_lines


def test_invalid_decision_and_score_detected(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    row = _valid_row(cases[0]["case_id"])
    row["decision"] = "INVALID"
    row["violation_probability"] = 1.5
    _write_raw_file(raw_root, expected_files[0], [json.dumps(row)])

    summary, _inventory, _lint, _preview = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        raw_root,
    )

    assert summary.invalid_decision_count > 0
    assert summary.invalid_score_count > 0


def test_unknown_and_duplicate_case_ids_detected(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    duplicate = _valid_row(cases[0]["case_id"])
    unknown = _valid_row("oar360_case_unknown")
    _write_raw_file(
        raw_root,
        expected_files[0],
        [
            json.dumps(duplicate),
            json.dumps(duplicate),
            json.dumps(unknown),
        ],
    )

    summary, _inventory, _lint, _preview = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        raw_root,
    )

    assert summary.unknown_case_id_count > 0
    assert summary.duplicate_case_id_count > 0


def test_outputs_written_without_raw_text_preview(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    _write_raw_file(raw_root, expected_files[0], [json.dumps(_valid_row(cases[0]["case_id"]))])
    summary, inventory, lint, preview = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        raw_root,
    )
    out_dir = tmp_path / "out"
    write_oar_360_raw_import_validation_outputs(summary, inventory, lint, preview, out_dir)

    assert (out_dir / "oar_360_raw_import_status.json").exists()
    assert (out_dir / "oar_360_raw_import_manifest.json").exists()
    assert (out_dir / "oar_360_raw_import_report.md").exists()
    assert (out_dir / "oar_360_raw_file_inventory.json").exists()
    assert (out_dir / "oar_360_raw_schema_lint.json").exists()
    preview_path = out_dir / "oar_360_raw_parse_preview.jsonl"
    assert preview_path.exists()
    preview_row = json.loads(preview_path.read_text(encoding="utf-8").splitlines()[0])
    assert "raw_line_hash" in preview_row
    assert "raw_line" not in preview_row
    report = (out_dir / "oar_360_raw_import_report.md").read_text(encoding="utf-8")
    assert "ground truth was not used" in report
    assert "does not prove model correctness" in report


def test_no_ground_truth_scoring(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    summary, inventory, lint, preview = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        raw_root,
    )
    out_dir = tmp_path / "out"
    write_oar_360_raw_import_validation_outputs(summary, inventory, lint, preview, out_dir)
    report = (out_dir / "oar_360_raw_import_report.md").read_text(encoding="utf-8")

    assert summary.ground_truth_used is False
    assert summary.score_against_holdout is False
    assert "outputs were not scored against holdout" in report


def test_no_fake_outputs_created(tmp_path: Path) -> None:
    config, expected_files, cases = _fixture()
    raw_root = tmp_path / "raw_outputs"
    raw_root.mkdir()

    validate_oar_360_raw_imports(config, expected_files, cases, raw_root)

    assert not list(raw_root.rglob("*.jsonl"))

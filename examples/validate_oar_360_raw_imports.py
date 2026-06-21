from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.oar_360_raw_import_validator import (
    OAR360RawImportSummary,
    load_cases,
    load_expected_raw_output_filenames,
    load_oar_360_raw_import_validator_config,
    sha256_file,
    validate_oar_360_raw_imports,
    write_oar_360_raw_import_validation_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate OAR-360 manually collected raw output imports."
    )
    parser.add_argument("--config", default="configs/oar_360_raw_import_validator.json")
    parser.add_argument(
        "--expected-files",
        default="benchmarks/oar_360/manual_eval/oar_360_expected_raw_output_filenames.json",
    )
    parser.add_argument("--cases", default="benchmarks/oar_360/oar_360_cases.jsonl")
    parser.add_argument(
        "--raw-output-root",
        default="benchmarks/oar_360/manual_eval/raw_outputs",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/oar_360/manual_eval/import_validation",
    )
    args = parser.parse_args()

    config = load_oar_360_raw_import_validator_config(args.config)
    expected_files = load_expected_raw_output_filenames(args.expected_files)
    cases = load_cases(args.cases)
    summary, inventory, lint_records, preview_records = validate_oar_360_raw_imports(
        config,
        expected_files,
        cases,
        Path(args.raw_output_root),
    )
    summary = OAR360RawImportSummary(
        **{
            **summary.to_dict(),
            "source_expected_filenames_hash": sha256_file(args.expected_files),
            "source_case_file_hash": sha256_file(args.cases),
        }
    )
    write_oar_360_raw_import_validation_outputs(
        summary,
        inventory,
        lint_records,
        preview_records,
        args.out_dir,
    )
    manifest = json.loads(
        (Path(args.out_dir) / "oar_360_raw_import_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    print(f"suite_name: {summary.suite_name}")
    print(f"import_state: {summary.import_state}")
    print(f"expected_file_count: {summary.expected_file_count}")
    print(f"present_file_count: {summary.present_file_count}")
    print(f"missing_file_count: {summary.missing_file_count}")
    print(f"total_raw_lines: {summary.total_raw_lines}")
    print(f"parseable_json_line_count: {summary.parseable_json_line_count}")
    print(f"malformed_json_line_count: {summary.malformed_json_line_count}")
    print(
        "complete_required_field_record_count: "
        f"{summary.complete_required_field_record_count}"
    )
    print(f"unknown_case_id_count: {summary.unknown_case_id_count}")
    print(f"duplicate_case_id_count: {summary.duplicate_case_id_count}")
    print(f"invalid_decision_count: {summary.invalid_decision_count}")
    print(f"invalid_score_count: {summary.invalid_score_count}")
    print(f"invalid_citation_method_count: {summary.invalid_citation_method_count}")
    print(f"no_provider_calls: {summary.no_provider_calls}")
    print(f"no_fake_outputs: {summary.no_fake_outputs}")
    print(f"no_empirical_results: {summary.no_empirical_results}")
    print(f"ground_truth_used: {summary.ground_truth_used}")
    print(f"score_against_holdout: {summary.score_against_holdout}")
    print(f"import_manifest_hash: {manifest['import_manifest_hash']}")
    print(f"output_dir: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()

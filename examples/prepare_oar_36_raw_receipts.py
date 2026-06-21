from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.oar_36_raw_receipt_prep import (
    load_expected_raw_output_filenames,
    load_jsonl,
    load_oar_36_raw_receipt_prep_config,
    validate_raw_receipt_prep,
    write_oar_36_receipt_prep_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare OAR-36 normalized judgments and receipt material from raw outputs."
    )
    parser.add_argument("--config", default="configs/oar_36_raw_receipt_prep.json")
    parser.add_argument(
        "--cases",
        default="benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl",
    )
    parser.add_argument(
        "--prompts",
        default="benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_pack.jsonl",
    )
    parser.add_argument(
        "--expected-files",
        default="benchmarks/oar_360/oar_36_dry_run/oar_36_expected_raw_output_filenames.json",
    )
    parser.add_argument(
        "--raw-output-root",
        default="benchmarks/oar_360/oar_36_dry_run/raw_outputs",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/oar_360/oar_36_dry_run/receipt_prep",
    )
    args = parser.parse_args()

    config = load_oar_36_raw_receipt_prep_config(args.config)
    cases = load_jsonl(args.cases)
    prompts = load_jsonl(args.prompts)
    expected_files = load_expected_raw_output_filenames(args.expected_files)
    summary, inventory, lint_records, normalized, receipts = validate_raw_receipt_prep(
        config=config,
        cases=cases,
        prompts=prompts,
        expected_files=expected_files,
        raw_output_root=Path(args.raw_output_root),
    )
    write_oar_36_receipt_prep_outputs(
        summary,
        inventory,
        lint_records,
        normalized,
        receipts,
        args.out_dir,
    )
    manifest = json.loads(
        (Path(args.out_dir) / "oar_36_receipt_prep_manifest.json").read_text(
            encoding="utf-8"
        )
    )

    print(f"suite_name: {summary.suite_name}")
    print(f"import_state: {summary.import_state}")
    print(f"expected_file_count: {summary.expected_file_count}")
    print(f"present_file_count: {summary.present_file_count}")
    print(f"missing_file_count: {summary.missing_file_count}")
    print(f"normalized_judgment_count: {summary.normalized_judgment_count}")
    print(f"receipt_preparation_count: {summary.receipt_preparation_count}")
    print(f"receipt_ready_count: {summary.receipt_ready_count}")
    print(f"receipt_blocked_count: {summary.receipt_blocked_count}")
    print(f"ground_truth_used: {summary.ground_truth_used}")
    print(f"score_against_holdout: {summary.score_against_holdout}")
    print(f"no_provider_calls: {summary.no_provider_calls}")
    print(f"no_fake_outputs: {summary.no_fake_outputs}")
    print(f"empirical_results_created: {summary.empirical_results_created}")
    print(f"manifest_hash: {manifest['manifest_hash']}")
    print(f"output_dir: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()

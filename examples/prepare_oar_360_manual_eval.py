from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare OAR-360 manual evaluation intake artifacts."
    )
    parser.add_argument("--config", default="configs/oar_360_manual_eval_intake.json")
    parser.add_argument("--cases", default="benchmarks/oar_360/oar_360_cases.jsonl")
    parser.add_argument(
        "--case-manifest",
        default="benchmarks/oar_360/oar_360_case_manifest.json",
    )
    parser.add_argument(
        "--prompt-manifest",
        default="benchmarks/oar_360/prompts/oar_360_prompt_manifest.json",
    )
    parser.add_argument("--prompt-root", default="benchmarks/oar_360/prompts")
    parser.add_argument("--out-dir", default="benchmarks/oar_360/manual_eval")
    args = parser.parse_args()

    config = load_oar_360_manual_eval_intake_config(args.config)
    cases = load_cases(args.cases)
    case_manifest = load_case_manifest(args.case_manifest)
    prompt_manifest = load_prompt_manifest(args.prompt_manifest)
    system_registry = build_system_registry_template(config)
    batch_plan = build_oar_360_batch_plan(cases, config)
    expected_files = build_expected_raw_output_filenames(
        system_registry,
        batch_plan,
        config,
    )
    readiness = validate_manual_eval_readiness(
        Path(args.cases),
        Path(args.case_manifest),
        Path(args.prompt_manifest),
        Path(args.prompt_root),
        Path(args.out_dir),
        cases,
        batch_plan,
        system_registry,
        expected_files,
        config,
    )
    summary = write_oar_360_manual_eval_intake_outputs(
        config,
        cases,
        case_manifest,
        prompt_manifest,
        batch_plan,
        system_registry,
        expected_files,
        readiness,
        Path(args.out_dir),
    )

    print(f"suite_name: {summary.suite_name}")
    print(f"case_count: {summary.case_count}")
    print(f"system_count: {summary.system_count}")
    print(f"batch_count: {summary.batch_count}")
    print(f"family_batch_count: {summary.family_batch_count}")
    print(f"mixed_batch_count: {summary.mixed_batch_count}")
    print(f"balanced_batch_count: {summary.balanced_batch_count}")
    print(f"full_batch_count: {summary.full_batch_count}")
    print(f"expected_raw_output_file_count: {summary.expected_raw_output_file_count}")
    print(f"ground_truth_not_exposed: {summary.ground_truth_not_exposed}")
    print(f"no_provider_calls: {summary.no_provider_calls}")
    print(f"no_model_outputs: {summary.no_model_outputs}")
    print(f"evidence_level: {summary.evidence_level}")
    print(f"intake_manifest_hash: {summary.intake_manifest_hash}")
    print(f"output_dir: {Path(args.out_dir)}")
    if readiness.validation_issues:
        print(f"validation_issues: {readiness.validation_issues}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.oar_36_dry_run import (
    build_oar_36_expected_raw_output_filenames,
    build_oar_36_holdout,
    build_oar_36_prompt_pack,
    load_jsonl,
    load_oar_36_dry_run_config,
    load_oar_360_cases,
    load_oar_360_holdout,
    load_oar_360_prompts,
    select_oar_36_cases,
    summarize_selection,
    validate_oar_36_selection,
    write_oar_36_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the OAR-36 dry-run subset.")
    parser.add_argument("--config", default="configs/oar_36_dry_run_config.json")
    parser.add_argument("--cases", default="benchmarks/oar_360/oar_360_cases.jsonl")
    parser.add_argument(
        "--case-manifest",
        default="benchmarks/oar_360/oar_360_case_manifest.json",
    )
    parser.add_argument(
        "--prompts",
        default="benchmarks/oar_360/prompts/oar_360_prompt_pack.jsonl",
    )
    parser.add_argument(
        "--prompt-manifest",
        default="benchmarks/oar_360/prompts/oar_360_prompt_manifest.json",
    )
    parser.add_argument(
        "--holdout",
        default="benchmarks/oar_360/prompts/ground_truth_holdout/oar_360_ground_truth_holdout.jsonl",
    )
    parser.add_argument(
        "--holdout-manifest",
        default="benchmarks/oar_360/prompts/ground_truth_holdout/oar_360_ground_truth_holdout_manifest.json",
    )
    parser.add_argument("--out-dir", default="benchmarks/oar_360/oar_36_dry_run")
    args = parser.parse_args()

    config = load_oar_36_dry_run_config(args.config)
    cases = load_oar_360_cases(args.cases)
    prompts = load_oar_360_prompts(args.prompts)
    holdout = load_oar_360_holdout(args.holdout)
    case_manifest = json.loads(Path(args.case_manifest).read_text(encoding="utf-8"))
    prompt_manifest = json.loads(Path(args.prompt_manifest).read_text(encoding="utf-8"))
    holdout_manifest = json.loads(Path(args.holdout_manifest).read_text(encoding="utf-8"))

    selected_cases = select_oar_36_cases(cases, config)
    selected_ids = [case["case_id"] for case in selected_cases]
    prompt_pack = build_oar_36_prompt_pack(selected_ids, prompts, config)
    dry_holdout = build_oar_36_holdout(selected_ids, holdout, config)
    expected_raw_outputs = build_oar_36_expected_raw_output_filenames(config)
    validation_issues = validate_oar_36_selection(
        selected_cases,
        prompt_pack,
        dry_holdout,
        config,
    )
    if validation_issues:
        raise SystemExit(f"OAR-36 validation failed: {validation_issues}")
    summary = write_oar_36_outputs(
        config=config,
        selected_cases=selected_cases,
        prompts=prompt_pack,
        holdout=dry_holdout,
        expected_raw_outputs=expected_raw_outputs,
        source_case_file=args.cases,
        source_case_manifest=case_manifest,
        source_prompt_pack=args.prompts,
        source_prompt_manifest=prompt_manifest,
        source_holdout_file=args.holdout,
        source_holdout_manifest=holdout_manifest,
        out_dir=args.out_dir,
    )

    print(f"suite_name: {summary.suite_name}")
    print(f"source_suite: {summary.source_suite}")
    print(f"total_cases: {summary.total_cases}")
    print(f"family_count: {len(summary.family_distribution)}")
    print(f"domain_count: {len(summary.domain_distribution)}")
    print(f"label_distribution: {summary.label_distribution}")
    print(f"expected_decision_distribution: {summary.expected_decision_distribution}")
    print(f"risk_band_distribution: {summary.risk_band_distribution}")
    print(f"distinct_edge_tags: {summary.distinct_edge_tags}")
    print(f"prompt_count: {summary.prompt_count}")
    print(f"holdout_count: {summary.holdout_count}")
    print(f"expected_raw_output_file_count: {summary.expected_raw_output_file_count}")
    print(f"no_provider_calls: {summary.no_provider_calls}")
    print(f"no_model_outputs: {summary.no_model_outputs}")
    print(f"evidence_level: {summary.evidence_level}")
    print(f"case_manifest_hash: {summary.case_manifest_hash}")
    print(f"prompt_manifest_hash: {summary.prompt_manifest_hash}")
    print(f"holdout_manifest_hash: {summary.holdout_manifest_hash}")
    print(f"output_dir: {Path(args.out_dir)}")


if __name__ == "__main__":
    main()

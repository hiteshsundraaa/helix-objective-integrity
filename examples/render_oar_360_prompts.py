from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.oar_360_prompt_rendering import (
    build_ground_truth_holdout,
    build_prompt_pack,
    load_oar_360_cases,
    load_oar_360_prompt_rendering_config,
    summarize_prompt_rendering,
    validate_prompt_pack,
    write_oar_360_prompt_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render OAR-360 prompt packs and ground-truth holdout."
    )
    parser.add_argument(
        "--config",
        default="configs/oar_360_prompt_rendering.json",
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/oar_360/oar_360_cases.jsonl",
    )
    parser.add_argument(
        "--case-manifest",
        default="benchmarks/oar_360/oar_360_case_manifest.json",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/oar_360/prompts",
    )
    args = parser.parse_args()

    config = load_oar_360_prompt_rendering_config(args.config)
    cases = load_oar_360_cases(args.cases)
    prompt_records = build_prompt_pack(cases, config)
    holdout_records = build_ground_truth_holdout(cases, config)
    validation_issues = validate_prompt_pack(
        prompt_records,
        holdout_records,
        config,
        cases,
    )
    summary = summarize_prompt_rendering(
        prompt_records,
        holdout_records,
        config,
        validation_issues,
    )
    result = write_oar_360_prompt_outputs(
        prompt_records,
        holdout_records,
        summary,
        args.out_dir,
        source_cases_path=args.cases,
        source_case_manifest_path=args.case_manifest,
        config=config,
    )

    print(f"prompt_count: {len(prompt_records)}")
    print(f"holdout_count: {len(holdout_records)}")
    print(f"ground_truth_excluded: {result['manifest']['ground_truth_excluded']}")
    print(f"no_provider_calls: {result['manifest']['no_provider_calls']}")
    print(f"no_model_outputs: {result['manifest']['no_model_outputs']}")
    print(f"prompt_pack_hash: {result['prompt_pack_hash']}")
    print(f"holdout_file_hash: {result['holdout_file_hash']}")
    print(f"manifest_hash: {result['manifest_hash']}")
    print(f"validation_issues: {validation_issues}")
    print(f"output_dir: {Path(args.out_dir)}")
    if validation_issues:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

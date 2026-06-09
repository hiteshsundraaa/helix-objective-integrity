from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_provider_dry_run_bridge import (
    load_v10_provider_dry_run_bridge_config,
    write_provider_dry_run_bridge_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bridge a v10 provider dry-run directory into the existing v10 pipeline."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_provider_dry_run_pipeline_bridge.json",
    )
    parser.add_argument(
        "--provider-run-dir",
        default="benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1",
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/v10_calibrated/v10_cases.jsonl",
    )
    parser.add_argument("--out-subdir", default="pipeline_bridge")
    args = parser.parse_args()

    config = load_v10_provider_dry_run_bridge_config(args.config)
    paths = write_provider_dry_run_bridge_outputs(
        provider_run_dir=args.provider_run_dir,
        cases_path=args.cases,
        config=config,
        config_path=args.config,
        out_subdir=args.out_subdir,
    )
    summary = json.loads(paths["bridge_summary"].read_text(encoding="utf-8"))
    print(f"run_id: {summary['run_id']}")
    print(f"dry_run_bridge: {summary['dry_run_bridge']}")
    print(f"raw_judgment_count: {summary['raw_judgment_count']}")
    print(f"normalized_judgment_count: {summary['normalized_judgment_count']}")
    print(f"benchmark_receipt_count: {summary['benchmark_receipt_count']}")
    print(f"matched_case_count: {summary['matched_case_count']}")
    print(f"missing_judgment_case_count: {summary['missing_judgment_case_count']}")
    print(f"normalization_status: {summary['normalization_status']}")
    print(f"benchmark_status: {summary['benchmark_status']}")
    print(f"diagnostics_status: {summary['diagnostics_status']}")
    print(f"mechanical_reportability_passed: {summary['mechanical_reportability_passed']}")
    print(f"final_evidence_level: {summary['final_evidence_level']}")
    print(f"output_path: {paths['bridge_dir']}")


if __name__ == "__main__":
    main()

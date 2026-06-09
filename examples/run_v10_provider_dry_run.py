from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_provider_dry_run import (
    default_run_id,
    load_provider_run_plan,
    load_v10_cases,
    load_v10_provider_dry_run_config,
    write_provider_dry_run_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a HELIX v10 provider dry-run executor using fixture responses only."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_provider_dry_run_executor.json",
    )
    parser.add_argument(
        "--plan",
        default="benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json",
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/v10_calibrated/v10_cases.jsonl",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--out-root",
        default="benchmarks/v10_calibrated/provider_runs",
    )
    args = parser.parse_args()

    config = load_v10_provider_dry_run_config(args.config)
    plan = load_provider_run_plan(args.plan)
    cases = load_v10_cases(args.cases)
    run_id = args.run_id or default_run_id(plan, config)
    paths = write_provider_dry_run_outputs(
        run_id=run_id,
        plan=plan,
        plan_path=args.plan,
        cases=cases,
        config=config,
        config_path=args.config,
        out_root=args.out_root,
    )
    summary = json.loads(paths["provider_dry_run_summary"].read_text(encoding="utf-8"))
    print(f"run_id: {summary['run_id']}")
    print(f"dry_run: {summary['dry_run']}")
    print(f"case_count: {summary['case_count']}")
    print(f"batch_count: {summary['batch_count']}")
    print(f"raw_response_count: {summary['raw_response_count']}")
    print(f"parsed_raw_judgment_count: {summary['parsed_raw_judgment_count']}")
    print(f"no_api_calls_made: {summary['no_api_calls_made']}")
    print(f"evidence_level_cap: {summary['evidence_level_cap']}")
    print(f"output_path: {paths['run_dir']}")


if __name__ == "__main__":
    main()

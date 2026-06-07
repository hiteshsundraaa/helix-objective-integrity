from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_provider_protocol import (
    build_v10_provider_run_plan,
    load_v10_cases,
    load_v10_provider_protocol_config,
    write_v10_provider_run_plan,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan a HELIX v10 provider judgment run without making API calls."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_provider_judgment_protocol.json",
    )
    parser.add_argument(
        "--stage",
        choices=["pilot", "full"],
        default="pilot",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/provider_run_plans/pilot_v1",
    )
    args = parser.parse_args()

    config = load_v10_provider_protocol_config(args.config)
    cases = load_v10_cases(config.cases_path)
    plan = build_v10_provider_run_plan(
        cases=cases,
        config=config,
        config_path=args.config,
        stage=args.stage,
    )
    paths = write_v10_provider_run_plan(
        plan=plan,
        config_path=args.config,
        out_dir=args.out_dir,
    )

    print(f"stage: {plan.stage}")
    print(f"case_count: {plan.case_count}")
    print(f"family_counts: {json.dumps(plan.family_counts, sort_keys=True)}")
    print(f"label_counts: {json.dumps(plan.label_counts, sort_keys=True)}")
    print(f"provider: {plan.provider}")
    print(f"model: {plan.model}")
    print(f"no_api_calls_made: {plan.no_api_calls_made}")
    print(f"level_5_allowed: {plan.level_5_allowed}")
    print(f"plan_hash: {plan.plan_hash}")
    print(f"manifest_path: {paths['manifest']}")
    print(f"report_path: {paths['report']}")


if __name__ == "__main__":
    main()

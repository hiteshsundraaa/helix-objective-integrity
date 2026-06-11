from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_live_provider_runner import (
    V10LivePilotInput,
    load_v10_guarded_live_pilot_config,
    validate_live_pilot_input,
)
from helix.benchmark.v10_live_runner_design_gate import load_v10_live_runner_design_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Guarded v10.15C live one-provider pilot runner."
    )
    parser.add_argument(
        "--config",
        default="configs/v10_guarded_live_one_provider_pilot.json",
    )
    parser.add_argument(
        "--live-design-config",
        default="configs/v10_live_provider_runner_design_gate.json",
    )
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--plan",
        default="benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json",
    )
    parser.add_argument(
        "--out-root",
        default="benchmarks/v10_calibrated/provider_runs/live",
    )
    parser.add_argument("--case-limit", type=int, default=30)
    parser.add_argument("--allow-full-300", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--adapter-kind", default="unavailable")
    args = parser.parse_args()

    config = load_v10_guarded_live_pilot_config(args.config)
    live_design_config = load_v10_live_runner_design_config(args.live_design_config)
    live_input = V10LivePilotInput(
        provider=args.provider,
        model=args.model,
        run_id=args.run_id,
        plan_path=args.plan,
        output_root=args.out_root,
        live_flag=args.live,
        case_limit=args.case_limit,
        allow_full_300=args.allow_full_300,
    )
    issues = validate_live_pilot_input(live_input, config, live_design_config)
    if issues:
        print("live_pilot_validation_status: failed")
        print(f"validation_issues: {json.dumps(issues, sort_keys=True)}")
        raise SystemExit(2)
    if args.adapter_kind == "unavailable":
        print("live_pilot_validation_status: passed")
        print("adapter_status: unavailable")
        print(
            "No live provider adapter configured in this patch. Use tests with mock adapter or implement provider adapter in a future patch."
        )
        raise SystemExit(2)
    print("Unsupported adapter kind. No API call made.")
    raise SystemExit(2)


if __name__ == "__main__":
    main()

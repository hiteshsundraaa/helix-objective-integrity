from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_live_runner_design_gate import load_v10_live_runner_design_config
from helix.benchmark.v10_manual_pilot_runner import (
    V10ManualPilotInput,
    load_v10_manual_pilot_config,
    run_manual_pilot,
    validate_manual_pilot_inputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the v10.15B manual one-provider pilot over an externally saved raw output file."
    )
    parser.add_argument("--config", default="configs/v10_manual_one_provider_pilot.json")
    parser.add_argument("--raw-output-file", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--collection-method", required=True)
    parser.add_argument(
        "--plan",
        default=None,
    )
    parser.add_argument(
        "--out-root",
        default=None,
    )
    parser.add_argument("--notes")
    args = parser.parse_args()

    config = load_v10_manual_pilot_config(args.config)
    plan_path = args.plan or config.default_plan_path
    out_root = args.out_root or config.provider_runs_root
    pilot_input = V10ManualPilotInput(
        provider=args.provider,
        model=args.model,
        run_id=args.run_id,
        raw_output_file=args.raw_output_file,
        collection_method=args.collection_method,
        plan_path=plan_path,
        output_root=out_root,
        notes=args.notes,
    )
    validation_issues = validate_manual_pilot_inputs(
        pilot_input,
        config,
        load_v10_live_runner_design_config(config.live_design_config_path),
    )
    if validation_issues:
        print("manual_pilot_validation_status: failed")
        print(f"validation_issues: {json.dumps(validation_issues, sort_keys=True)}")
        raise SystemExit(2)

    summary, paths = run_manual_pilot(pilot_input, config)
    print(f"run_id: {summary.run_id}")
    print(f"provider: {summary.provider}")
    print(f"model: {summary.model}")
    print(f"execution_mode: {summary.execution_mode}")
    print(f"import_validation_status: {summary.import_validation_status}")
    print(f"bridge_status: {summary.bridge_status}")
    print(f"evidence_assessment_status: {summary.evidence_assessment_status}")
    print(f"final_evidence_level: {summary.final_evidence_level}")
    print(f"level_4_allowed: {str(summary.level_4_allowed).lower()}")
    print(f"level_5_allowed: {str(summary.level_5_allowed).lower()}")
    print(f"receipt_count: {summary.receipt_count}")
    print(f"invalid_receipt_count: {summary.invalid_receipt_count}")
    print(f"receipt_chain_complete: {str(summary.receipt_chain_complete).lower()}")
    print(f"raw_output_hash: {summary.raw_output_hash}")
    print(f"manifest_hash: {summary.manifest_hash}")
    print(f"blocking_issues: {json.dumps(summary.blocking_issues, sort_keys=True)}")
    print(f"warnings: {json.dumps(summary.warnings, sort_keys=True)}")
    print(f"limitations: {json.dumps(summary.limitations, sort_keys=True)}")
    print(f"pilot_manifest_path: {summary.pilot_manifest_path}")
    print(f"pilot_report_path: {summary.pilot_report_path}")
    print(f"manual_pilot_summary_path: {paths['manual_pilot_summary']}")


if __name__ == "__main__":
    main()

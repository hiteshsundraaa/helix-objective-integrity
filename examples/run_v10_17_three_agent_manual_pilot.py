from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_live_runner_design_gate import load_v10_live_runner_design_config
from helix.benchmark.v10_three_agent_consistency_protocol import (
    load_v10_three_agent_consistency_protocol_config,
)
from helix.benchmark.v10_three_agent_manual_pilot import (
    V10ManualAgentSystemInput,
    V10ThreeAgentManualPilotInput,
    load_v10_three_agent_manual_pilot_config,
    run_three_agent_manual_pilot,
    validate_three_agent_manual_pilot_input,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v10.17 three-agent manual consistency pilot."
    )
    parser.add_argument("--config", default="configs/v10_three_agent_manual_pilot.json")
    parser.add_argument("--consistency-run-id", required=True)
    parser.add_argument("--system-json", required=True)
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

    config = load_v10_three_agent_manual_pilot_config(args.config)
    system_payload = json.loads(Path(args.system_json).read_text(encoding="utf-8"))
    systems = [
        V10ManualAgentSystemInput.model_validate(item)
        for item in system_payload.get("systems", [])
    ]
    pilot_input = V10ThreeAgentManualPilotInput(
        consistency_run_id=args.consistency_run_id,
        systems=systems,
        plan_path=args.plan or config.default_plan_path,
        output_root=args.out_root or config.consistency_output_root,
        notes=args.notes,
    )
    protocol_config = load_v10_three_agent_consistency_protocol_config(
        config.three_agent_protocol_config_path
    )
    live_design_config = load_v10_live_runner_design_config(config.live_design_config_path)
    validation_issues = validate_three_agent_manual_pilot_input(
        pilot_input,
        config,
        protocol_config,
        live_design_config,
    )
    if validation_issues:
        print("three_agent_manual_pilot_validation_status: failed")
        print(f"validation_issues: {json.dumps(validation_issues, sort_keys=True)}")
        raise SystemExit(2)

    summary, paths = run_three_agent_manual_pilot(pilot_input, config)
    print(f"consistency_run_id: {summary.consistency_run_id}")
    print(f"system_count: {summary.system_count}")
    print(f"case_count: {summary.case_count}")
    print(f"consistency_evidence_level: {summary.consistency_evidence_level}")
    print(f"unanimous_decision_rate: {summary.unanimous_decision_rate:.6f}")
    print(f"majority_decision_rate: {summary.majority_decision_rate:.6f}")
    print(f"severe_disagreement_rate: {summary.severe_disagreement_rate:.6f}")
    print(f"all_receipts_valid_rate: {summary.all_receipts_valid_rate:.6f}")
    print(f"consistency_hash: {summary.consistency_hash}")
    print(f"blocking_issues: {json.dumps(summary.blocking_issues, sort_keys=True)}")
    print(
        "non_blocking_warnings: "
        + json.dumps(summary.non_blocking_warnings, sort_keys=True)
    )
    print(f"consistency_report_path: {paths['consistency_report']}")
    print(f"consistency_receipt_path: {paths['consistency_receipt']}")


if __name__ == "__main__":
    main()

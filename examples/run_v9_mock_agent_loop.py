from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.runtime.mock_agent_loop import (
    build_default_v9_mock_loop_scenario,
    run_mock_agent_loop,
    write_mock_agent_loop_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v9.1 deterministic mock agent-loop adapter."
    )
    parser.add_argument("--out-dir", default="outputs/v9_mock_agent_loop/basic")
    args = parser.parse_args()

    contract, plan_steps, tool_registry = build_default_v9_mock_loop_scenario()
    trace, summary = run_mock_agent_loop(
        contract=contract,
        plan_steps=plan_steps,
        tool_registry=tool_registry,
    )
    manifest = write_mock_agent_loop_outputs(
        contract=contract,
        trace=trace,
        summary=summary,
        out_dir=args.out_dir,
    )

    print(f"Attempted tool calls: {summary.attempted_tool_calls}")
    print(f"Executed tool calls: {summary.executed_tool_calls}")
    print(f"Blocked tool calls: {summary.blocked_tool_calls}")
    print(f"Escalated tool calls: {summary.escalated_tool_calls}")
    print(f"Prevented executions: {summary.prevented_execution_count}")
    print(f"Blocked calls executed: {summary.blocked_call_executed_count}")
    print(f"Blocked tool invocations: {summary.blocked_tool_invocation_count}")
    print(f"Escalated tool invocations: {summary.escalated_tool_invocation_count}")
    print(f"Forbidden side effects: {summary.forbidden_side_effect_count}")
    print(f"Invalid receipts: {summary.invalid_receipt_count}")
    print(f"Manifest hash: {manifest.manifest_hash}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

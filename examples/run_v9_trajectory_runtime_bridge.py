from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.runtime.trajectory_runtime_bridge import run_trajectory_runtime_bridge


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v9.3 trajectory-to-runtime bridge."
    )
    parser.add_argument(
        "--trajectory-runs",
        default="outputs/trajectory_runs/v8_basic/trajectory_runs.json",
    )
    parser.add_argument("--cp-config", default="configs/cp_config_v8.json")
    parser.add_argument(
        "--expectations",
        default="configs/v9_3_preregistered_expectations.json",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/v9_trajectory_runtime_bridge/v9",
    )
    args = parser.parse_args()

    try:
        summary = run_trajectory_runtime_bridge(
            trajectory_runs_path=Path(args.trajectory_runs),
            cp_config_path=Path(args.cp_config),
            expectations_path=Path(args.expectations),
            out_dir=Path(args.out_dir),
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            f"{exc}. If v8 trajectories are missing, run: "
            "python examples/run_v8_minimal_trajectory_runner.py "
            "--out-dir outputs/trajectory_runs/v8_basic "
            "--trajectory-count 6 --steps-per-trajectory 12 --seed 42"
        ) from exc

    print(f"Trajectories: {summary.trajectory_count}")
    print(f"Steps: {summary.step_count}")
    print(f"Attempted tool calls: {summary.attempted_tool_calls}")
    print(f"Receipt count: {summary.receipt_count}")
    print(f"Invalid receipts: {summary.invalid_receipt_count}")
    print(f"Blocked calls executed: {summary.blocked_call_executed_count}")
    print(f"Escalated calls executed: {summary.escalated_call_executed_count}")
    print(f"V8/runtime agreement rate: {summary.v8_runtime_decision_agreement_rate:.6f}")
    print(
        "Locally-safe/globally-drifted disagreement rate: "
        f"{summary.locally_safe_globally_drifted_disagreement_rate:.6f}"
    )
    print(f"Trajectory drift gap: {summary.trajectory_drift_gap:.6f}")
    print(f"CP_t signal unused rate: {summary.cp_t_signal_unused_rate:.6f}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.runtime.cp_policy_sensitivity import (
    run_cp_policy_sensitivity,
    write_cp_policy_sensitivity_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v9.5 CP-aware runtime execution-policy sensitivity."
    )
    parser.add_argument(
        "--trajectory-runs",
        default="outputs/trajectory_runs/v8_basic/trajectory_runs.json",
    )
    parser.add_argument("--cp-config", default="configs/cp_config_v8.json")
    parser.add_argument(
        "--policy-config",
        default="configs/v9_5_policy_sensitivity.json",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/v9_cp_policy_sensitivity/v9",
    )
    args = parser.parse_args()

    try:
        records, summary = run_cp_policy_sensitivity(
            trajectory_runs_path=Path(args.trajectory_runs),
            cp_config_path=Path(args.cp_config),
            policy_config_path=Path(args.policy_config),
        )
        write_cp_policy_sensitivity_outputs(
            records=records,
            summary=summary,
            trajectory_runs_path=Path(args.trajectory_runs),
            cp_config_path=Path(args.cp_config),
            policy_config_path=Path(args.policy_config),
            out_dir=Path(args.out_dir),
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            f"{exc}. If v8 trajectories are missing, run: "
            "python examples/run_v8_minimal_trajectory_runner.py "
            "--out-dir outputs/trajectory_runs/v8_basic "
            "--trajectory-count 6 --steps-per-trajectory 12 --seed 42"
        ) from exc

    drift_gaps = {
        result.policy_id: result.trajectory_drift_gap
        for result in summary.policy_results
    }
    safe_prevention = {
        result.policy_id: result.safe_prevention_rate
        for result in summary.policy_results
    }
    print(f"Policy count: {summary.policy_count}")
    print(f"Baseline policy: {summary.baseline_policy_id}")
    print(f"Best drift gap policy: {summary.best_drift_gap_policy_id}")
    print(
        "Lowest safe prevention policy: "
        f"{summary.lowest_safe_prevention_policy_id}"
    )
    print(f"Drift gap by policy: {drift_gaps}")
    print(f"Safe prevention by policy: {safe_prevention}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

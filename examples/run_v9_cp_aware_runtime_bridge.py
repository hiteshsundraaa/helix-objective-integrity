from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.runtime.trajectory_runtime_bridge import (
    run_cp_aware_trajectory_runtime_bridge,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v9.4 CP-aware trajectory runtime bridge."
    )
    parser.add_argument(
        "--trajectory-runs",
        default="outputs/trajectory_runs/v8_basic/trajectory_runs.json",
    )
    parser.add_argument("--cp-config", default="configs/cp_config_v8.json")
    parser.add_argument(
        "--expectations",
        default="configs/v9_4_preregistered_expectations.json",
    )
    parser.add_argument(
        "--v9-3-summary",
        default="outputs/v9_trajectory_runtime_bridge/v9/trajectory_runtime_bridge_summary.json",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/v9_cp_aware_runtime_bridge/v9",
    )
    args = parser.parse_args()

    try:
        summary = run_cp_aware_trajectory_runtime_bridge(
            trajectory_runs_path=Path(args.trajectory_runs),
            cp_config_path=Path(args.cp_config),
            expectations_path=Path(args.expectations),
            v9_3_summary_path=Path(args.v9_3_summary),
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
    print(f"Receipt count: {summary.receipt_count}")
    print(f"Invalid receipts: {summary.invalid_receipt_count}")
    print(
        "Locally-safe/globally-drifted disagreement rate v9.3: "
        f"{summary.locally_safe_globally_drifted_disagreement_rate_v9_3:.6f}"
    )
    print(
        "Locally-safe/globally-drifted disagreement rate v9.4: "
        f"{summary.locally_safe_globally_drifted_disagreement_rate_v9_4:.6f}"
    )
    print(f"Drift gap reduction: {summary.drift_gap_reduction:.6f}")
    print(f"CP_t signal unused rate v9.4: {summary.cp_t_signal_unused_rate_v9_4:.6f}")
    print(f"Decisions changed by CP_t: {summary.decision_changed_by_cp_count}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

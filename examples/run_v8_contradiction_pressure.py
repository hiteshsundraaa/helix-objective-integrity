from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.trajectory.contradiction_pressure import load_cp_config, write_cp_outputs
from helix.trajectory.schema import TrajectoryRun


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v8.2 contradiction pressure analysis over trajectory outputs."
    )
    parser.add_argument(
        "--trajectory-records",
        default="outputs/trajectory_runs/v8_basic/trajectory_records.jsonl",
    )
    parser.add_argument(
        "--trajectory-runs",
        default="outputs/trajectory_runs/v8_basic/trajectory_runs.json",
    )
    parser.add_argument("--config", default="configs/cp_config_v8.json")
    parser.add_argument("--out-dir", default="outputs/trajectory_cp/v8")
    args = parser.parse_args()

    records_path = Path(args.trajectory_records)
    runs_path = Path(args.trajectory_runs)
    if not records_path.exists() or not runs_path.exists():
        raise SystemExit(
            "Missing v8.1 trajectory outputs. Run: "
            "python examples/run_v8_minimal_trajectory_runner.py --out-dir outputs/trajectory_runs/v8_basic"
        )
    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Missing CP config: {config_path}")

    trajectories = [
        TrajectoryRun.model_validate(item)
        for item in json.loads(runs_path.read_text(encoding="utf-8"))
    ]
    config = load_cp_config(config_path)
    summary = write_cp_outputs(trajectories, config, out_dir=args.out_dir)

    print(f"Trajectories: {summary.trajectory_count}")
    print(f"Steps: {summary.step_count}")
    print(f"Crossed block count: {summary.crossed_block_count}")
    print(f"Max CP_t: {summary.max_cp_t:.6f}")
    print(f"Predicted T*: {summary.predicted_T_star}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

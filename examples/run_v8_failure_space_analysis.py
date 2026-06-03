from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.trajectory.contradiction_pressure import load_cp_config
from helix.trajectory.dose_ladder import load_dose_ladder_config
from helix.trajectory.drift_halflife import load_drift_halflife_config
from helix.trajectory.failure_space import (
    load_failure_space_config,
    write_failure_space_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v8.7 failure-space trajectory analysis."
    )
    parser.add_argument("--failure-config", default="configs/failure_space_v8.json")
    parser.add_argument("--drift-config", default="configs/drift_halflife_v8.json")
    parser.add_argument("--cp-config", default="configs/cp_config_v8.json")
    parser.add_argument("--dose-config", default="configs/dose_ladder_v8.json")
    parser.add_argument("--out-dir", default="outputs/trajectory_failure_space/v8")
    args = parser.parse_args()

    summary = write_failure_space_outputs(
        failure_config=load_failure_space_config(args.failure_config),
        drift_config=load_drift_halflife_config(args.drift_config),
        cp_config=load_cp_config(args.cp_config),
        dose_config=load_dose_ladder_config(args.dose_config),
        out_dir=args.out_dir,
        failure_config_path=args.failure_config,
        drift_config_path=args.drift_config,
        cp_config_path=args.cp_config,
        dose_config_path=args.dose_config,
    )

    print(f"Dose levels: {summary.dose_level_count}")
    print(f"Trajectories: {summary.trajectory_count}")
    print(f"Steps: {summary.step_count}")
    print(f"Dominant failure mode counts: {summary.dominant_failure_mode_counts}")
    print(f"Low confidence step count: {summary.low_confidence_step_count}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

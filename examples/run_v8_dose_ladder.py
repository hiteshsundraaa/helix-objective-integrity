from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.trajectory.contradiction_pressure import load_cp_config
from helix.trajectory.dose_ladder import (
    load_dose_ladder_config,
    write_dose_ladder_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v8.3 perturbation dose ladder."
    )
    parser.add_argument("--dose-config", default="configs/dose_ladder_v8.json")
    parser.add_argument("--cp-config", default="configs/cp_config_v8.json")
    parser.add_argument("--out-dir", default="outputs/trajectory_dose_ladder/v8")
    args = parser.parse_args()

    dose_config = load_dose_ladder_config(args.dose_config)
    cp_config = load_cp_config(args.cp_config)
    summary = write_dose_ladder_outputs(
        dose_config=dose_config,
        cp_config=cp_config,
        out_dir=args.out_dir,
        dose_config_path=args.dose_config,
        cp_config_path=args.cp_config,
    )

    print(f"Dose levels: {summary.dose_level_count}")
    print(f"First WARN dose level: {summary.first_warn_dose_level}")
    print(f"First DEGRADE dose level: {summary.first_degrade_dose_level}")
    print(f"First QUARANTINE dose level: {summary.first_quarantine_dose_level}")
    print(f"First BLOCK dose level: {summary.first_block_dose_level}")
    print(f"Monotonic max CP_t: {summary.monotonic_max_cp_t}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

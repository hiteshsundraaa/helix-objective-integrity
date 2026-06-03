from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.trajectory.dose_ladder import load_dose_ladder_config
from helix.trajectory.drift_halflife import (
    load_drift_halflife_config,
    write_drift_halflife_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v8.6 deterministic drift-halflife scaffold."
    )
    parser.add_argument("--drift-config", default="configs/drift_halflife_v8.json")
    parser.add_argument("--dose-config", default="configs/dose_ladder_v8.json")
    parser.add_argument("--out-dir", default="outputs/trajectory_drift_halflife/v8")
    args = parser.parse_args()

    drift_config = load_drift_halflife_config(args.drift_config)
    dose_config = load_dose_ladder_config(args.dose_config)
    summary = write_drift_halflife_outputs(
        drift_config=drift_config,
        dose_config=dose_config,
        out_dir=args.out_dir,
        drift_config_path=args.drift_config,
        dose_config_path=args.dose_config,
    )

    print(f"Condition count: {summary.condition_count}")
    print(f"Clean halflife crossing rate: {summary.clean_halflife_crossing_rate}")
    print(f"Contaminated halflife crossing rate: {summary.contaminated_halflife_crossing_rate}")
    print(f"Halflife crossing lift: {summary.halflife_crossing_lift}")
    print(f"Clean final similarity mean: {summary.clean_final_similarity_mean}")
    print(f"Contaminated final similarity mean: {summary.contaminated_final_similarity_mean}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

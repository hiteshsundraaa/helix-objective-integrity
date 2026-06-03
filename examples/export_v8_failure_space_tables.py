from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.trajectory.failure_space_exports import write_failure_space_export_outputs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export HELIX v8.7 failure-space records to v8.8 CSV and optional PNG artifacts."
    )
    parser.add_argument("--records", default="outputs/trajectory_failure_space/v8/failure_space_records.jsonl")
    parser.add_argument("--trajectories", default="outputs/trajectory_failure_space/v8/failure_space_trajectories.jsonl")
    parser.add_argument("--summary", default="outputs/trajectory_failure_space/v8/failure_space_summary.json")
    parser.add_argument("--manifest", default="outputs/trajectory_failure_space/v8/failure_space_manifest.json")
    parser.add_argument("--out-dir", default="outputs/trajectory_failure_space_exports/v8")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()

    try:
        summary = write_failure_space_export_outputs(
            records_path=args.records,
            trajectories_path=args.trajectories,
            summary_path=args.summary,
            manifest_path=args.manifest,
            out_dir=args.out_dir,
            generate_plots=not args.no_plots,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    output_dir = Path(args.out_dir)
    generated_files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    print(f"Status: {summary.status}")
    print(f"Step rows: {summary.step_row_count}")
    print(f"Trajectory curve rows: {summary.trajectory_curve_row_count}")
    print(f"Generated files: {generated_files}")
    print(f"Plot generation status: {summary.plot_generation_status}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.trajectory.generator import generate_neutral_trajectories
from helix.trajectory.io import write_trajectory_run_outputs
from helix.trajectory.perturbations import (
    DEFAULT_PERTURBATION_CONFIG,
    inject_trajectory_perturbations,
)
from helix.trajectory.runner import DEFAULT_GATE_THRESHOLDS, run_trajectory_batch


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v8.1 deterministic minimal trajectory runner."
    )
    parser.add_argument("--out-dir", default="outputs/trajectory_runs/v8_basic")
    parser.add_argument("--trajectory-count", type=int, default=6)
    parser.add_argument("--steps-per-trajectory", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    neutral = generate_neutral_trajectories(
        trajectory_count=args.trajectory_count,
        steps_per_trajectory=args.steps_per_trajectory,
        seed=args.seed,
    )
    perturbed = inject_trajectory_perturbations(
        neutral,
        perturbation_config=DEFAULT_PERTURBATION_CONFIG,
        seed=args.seed,
    )
    gated = run_trajectory_batch(
        perturbed,
        gate_thresholds=DEFAULT_GATE_THRESHOLDS,
    )
    summary = write_trajectory_run_outputs(
        gated,
        out_dir=args.out_dir,
        manifest_config={
            "generator_seed": args.seed,
            "perturbation_config": DEFAULT_PERTURBATION_CONFIG,
            "gate_thresholds": DEFAULT_GATE_THRESHOLDS,
            "helix_version": "unknown",
        },
    )

    print(f"Trajectories: {summary['trajectory_count']}")
    print(f"Steps: {summary['step_count']}")
    print(f"Ground truth counts: {summary['ground_truth_counts']}")
    print(f"Decision counts: {summary['decision_counts']}")
    print(f"Intervention necessary: {summary['intervention_necessary_count']}")
    print(f"Trajectory context required: {summary['trajectory_context_required_count']}")
    print(f"Manifest hash: {summary['manifest_hash']}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

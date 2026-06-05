from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_generator import (
    audit_v10_generated_cases,
    generate_v10_cases,
    load_v10_generator_config,
    write_v10_generation_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate deterministic v10 calibrated benchmark scaffold cases."
    )
    parser.add_argument("--config", default="configs/v10_case_generator.json")
    parser.add_argument(
        "--spec-config",
        default="configs/v10_calibrated_benchmark_spec.json",
    )
    parser.add_argument("--out-dir", default="benchmarks/v10_calibrated")
    args = parser.parse_args()

    config = load_v10_generator_config(args.config)
    cases = generate_v10_cases(config)
    summary = audit_v10_generated_cases(cases, config)
    write_v10_generation_outputs(
        cases,
        summary,
        args.out_dir,
        args.config,
        spec_config_path=args.spec_config,
    )

    print(f"total_cases: {summary.total_cases}")
    print(f"family_counts: {summary.family_counts}")
    print(f"label_counts: {summary.label_counts}")
    print(f"target_score_band_counts: {summary.target_score_band_counts}")
    print(f"mid_risk_fraction: {summary.mid_risk_fraction:.6f}")
    print(f"near_boundary_fraction: {summary.near_boundary_fraction:.6f}")
    print(f"generator_overlap_mean: {summary.generator_overlap_mean:.6f}")
    print(f"high_overlap_case_count: {summary.high_overlap_case_count}")
    print(f"status: {summary.status}")
    print(f"failed_targets: {summary.failed_targets}")


if __name__ == "__main__":
    main()

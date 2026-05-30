from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.threshold_sensitivity import (
    run_threshold_sensitivity_sweep,
    write_threshold_sensitivity_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v6 threshold sensitivity sweep over frozen split-view evidence."
    )
    parser.add_argument(
        "--cases",
        default="benchmarks/blind_cases/mock_workspace_blind_v5_hard_paired_split_view.jsonl",
    )
    parser.add_argument(
        "--generic-judgments",
        default="benchmarks/semantic_judgments/blind_v5_hard_pair_generic_gpt5.jsonl",
    )
    parser.add_argument(
        "--contract-judgments",
        default="benchmarks/semantic_judgments/blind_v5_hard_pair_contract_gpt5.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/threshold_sensitivity/v6",
    )
    parser.add_argument("--random-seed", type=int, default=1337)
    args = parser.parse_args()

    summary = run_threshold_sensitivity_sweep(
        cases_path=args.cases,
        generic_judgments_path=args.generic_judgments,
        contract_judgments_path=args.contract_judgments,
        random_seed=args.random_seed,
    )
    write_threshold_sensitivity_outputs(summary, args.out_dir)

    print("HELIX v6 Threshold Sensitivity Sweep")
    print(f"Sweep points: {summary.sweep_point_count}")
    print(f"min_main_tpr: {summary.min_main_tpr:.3f}")
    print(f"max_main_fpr: {summary.max_main_fpr:.3f}")
    print(f"mean_selectivity_delta_vs_matched_random: {summary.mean_selectivity_delta_vs_matched_random:.3f}")
    print(f"Output path: {args.out_dir}")


if __name__ == "__main__":
    main()

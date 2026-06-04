from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.runtime.benign_noise_policy_stress import (
    run_benign_noise_policy_stress,
    write_benign_noise_policy_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v9.6 benign-noise runtime policy stress test."
    )
    parser.add_argument(
        "--benign-config",
        default="configs/v9_6_benign_noise_policy_stress.json",
    )
    parser.add_argument("--cp-config", default="configs/cp_config_v8.json")
    parser.add_argument(
        "--policy-config",
        default="configs/v9_5_policy_sensitivity.json",
    )
    parser.add_argument(
        "--v9-5-summary",
        default="outputs/v9_cp_policy_sensitivity/v9/cp_policy_sensitivity_summary.json",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/v9_benign_noise_policy_stress/v9",
    )
    args = parser.parse_args()

    records, summary = run_benign_noise_policy_stress(
        benign_config_path=Path(args.benign_config),
        cp_config_path=Path(args.cp_config),
        policy_config_path=Path(args.policy_config),
        v9_5_summary_path=Path(args.v9_5_summary),
    )
    write_benign_noise_policy_outputs(
        records=records,
        summary=summary,
        benign_config_path=Path(args.benign_config),
        cp_config_path=Path(args.cp_config),
        policy_config_path=Path(args.policy_config),
        v9_5_summary_path=Path(args.v9_5_summary),
        out_dir=Path(args.out_dir),
    )

    prevention = {
        metric.policy_id: metric.safe_noisy_prevention_rate
        for metric in summary.policy_metrics
    }
    false_interruption = {
        metric.policy_id: metric.false_interruption_rate
        for metric in summary.policy_metrics
    }
    net_tradeoff = {
        metric.policy_id: metric.net_policy_tradeoff
        for metric in summary.policy_metrics
    }
    print(f"Policy count: {summary.policy_count}")
    print(f"Benign step count: {summary.benign_step_count}")
    print(f"Safe prevention rate by policy: {prevention}")
    print(f"False interruption rate by policy: {false_interruption}")
    print(f"Net tradeoff by policy: {net_tradeoff}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

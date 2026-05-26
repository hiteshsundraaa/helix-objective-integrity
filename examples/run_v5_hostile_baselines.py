from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.hostile_baselines import (
    evaluate_hostile_baselines,
    write_hostile_baseline_outputs,
)
from helix.contracts.build_contract import load_contract_yaml


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run hostile baseline evaluation for HELIX v5 split-view evidence."
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
        "--receipt-path",
        default="outputs/v5_acceptance/paired_split_view_analysis/benchmark_decision_receipts.jsonl",
    )
    parser.add_argument(
        "--contract",
        default="scenarios/mock_workspace/contract.yaml",
    )
    parser.add_argument("--random-seed", type=int, default=1729)
    parser.add_argument("--out-dir", default="outputs/hostile_baselines/v5")
    args = parser.parse_args()

    contract = load_contract_yaml(args.contract)
    receipt_path = Path(args.receipt_path)

    evaluation = evaluate_hostile_baselines(
        cases_path=args.cases,
        generic_judgments_path=args.generic_judgments,
        contract_judgments_path=args.contract_judgments,
        receipt_path=receipt_path if receipt_path.exists() else None,
        allowed_actions=contract.allowed_actions,
        forbidden_actions=contract.forbidden_actions,
        random_seed=args.random_seed,
    )
    write_hostile_baseline_outputs(evaluation, args.out_dir)

    print("HELIX v5 Hostile Baseline Evaluation")
    print(f"Dataset: {evaluation.dataset_name}")
    print(f"Cases: {evaluation.case_count}")
    print(f"HELIX TPR: {evaluation.helix_true_positive_rate:.3f}")
    print(f"HELIX FPR: {evaluation.helix_false_positive_rate:.3f}")
    print(f"Matched-friction random seed: {evaluation.matched_friction_random_seed}")
    print("Selectivity deltas vs baselines:")
    for baseline, delta in sorted(evaluation.selectivity_delta_vs_baselines.items()):
        print(f"- {baseline}: {delta:.3f}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

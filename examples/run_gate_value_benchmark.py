from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.evaluator import evaluate_gate_value, export_benchmark_outputs
from helix.benchmark.synthetic import generate_mock_workspace_samples
from helix.contracts.build_contract import load_contract_yaml


def main() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_mock_workspace_samples(contract, trajectories_per_level=20)
    report, enriched_samples = evaluate_gate_value(contract, samples)

    output_dir = Path("outputs/gate_value_benchmark")
    export_benchmark_outputs(report, enriched_samples, output_dir)

    print("HELIX Gate Value Benchmark")
    print(f"Scenario: {report.scenario}")
    print(f"Samples: {report.samples}")
    print(f"Perturbation levels: {', '.join(report.perturbation_levels)}")
    print("")
    for metric in report.metrics.values():
        print(
            f"{metric.name}: block_rate={metric.block_rate:.3f} "
            f"TPR={metric.true_positive_rate:.3f} FPR={metric.false_positive_rate:.3f} "
            f"precision={metric.precision:.3f}"
        )
    print("")
    print(f"SelectivityDelta vs random: {report.selectivity_delta_vs_random:+.3f}")
    print(f"SelectivityDelta vs allowlist: {report.selectivity_delta_vs_allowlist:+.3f}")
    print(f"SelectivityDelta vs prompt-filter: {report.selectivity_delta_vs_prompt_filter:+.3f}")
    print(f"Outputs written to {output_dir}")


if __name__ == "__main__":
    main()

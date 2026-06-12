from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_citation_elicitation_gate import (
    analyze_second_pass_elicitation_outputs,
    prepare_citation_elicitation_experiment,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare HELIX v10.21 citation elicitation prompts and optionally analyze second-pass outputs."
    )
    parser.add_argument(
        "--real-pilot-root",
        default="benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1",
    )
    parser.add_argument(
        "--v10-20-root",
        default="benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_resolver_v10_20",
    )
    parser.add_argument(
        "--preregistration-config",
        default="configs/v10_citation_elicitation_preregistration.json",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_elicitation_v10_21",
    )
    parser.add_argument("--analyze-second-pass", action="store_true")
    args = parser.parse_args()

    result = prepare_citation_elicitation_experiment(
        Path(args.real_pilot_root),
        Path(args.v10_20_root),
        Path(args.out_dir),
        Path(args.preregistration_config),
    )
    summary = result["summary"]
    support = result["contract_support_precheck"]
    lint = result["prompt_lint_report"]
    manifest = result["manifest"]
    print(f"missing_citation_case_count: {summary['missing_citation_case_count']}")
    print(
        "contract_supports_citation_count: "
        f"{support['contract_supports_citation_count']}"
    )
    print(f"contract_authoring_gap_count: {support['contract_authoring_gap_count']}")
    print(f"prompt_count: {summary['prompt_count']}")
    print(f"prompt_lint_passed: {str(lint['prompt_lint_passed']).lower()}")
    print(f"status: {summary['status']}")
    print(f"output_dir: {args.out_dir}")
    print(f"manifest_hash: {manifest['manifest_hash']}")

    if args.analyze_second_pass:
        analysis = analyze_second_pass_elicitation_outputs(Path(args.out_dir))
        analyzed_summary = analysis["summary"]
        print(
            "post_elicitation_missing_rate: "
            f"{analyzed_summary['post_elicitation_missing_rate']}"
        )
        print(
            "recoverable_prompt_omission_rate: "
            f"{analyzed_summary['recoverable_prompt_omission_rate']}"
        )
        print(
            "persistent_missing_rate: "
            f"{analyzed_summary['persistent_missing_rate']}"
        )
        print(
            "decision_instability_rate: "
            f"{analyzed_summary['decision_instability_rate']}"
        )
        print(
            "outcome_distribution: "
            + json.dumps(analyzed_summary["outcome_distribution"], sort_keys=True)
        )


if __name__ == "__main__":
    main()

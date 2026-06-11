from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_disagreement_analysis import (
    run_v10_real_pilot_disagreement_analysis,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v10.19 real pilot disagreement analysis."
    )
    parser.add_argument(
        "--real-pilot-root",
        default="benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/disagreement_analysis_v10_19",
    )
    args = parser.parse_args()

    result = run_v10_real_pilot_disagreement_analysis(
        Path(args.real_pilot_root),
        Path(args.out_dir),
    )
    rates = result["disaggregated_severe_rates"]
    normalization = result["citation_normalization_experiment"]
    manifest = result["manifest"]
    print(f"source_consistency_run_id: {manifest['source_consistency_run_id']}")
    print(f"source_consistency_hash: {manifest['source_consistency_hash']}")
    print(f"output_dir: {manifest['output_dir']}")
    print(f"composite_severe_rate: {rates['composite_severe_rate']:.6f}")
    print(f"decision_severe_rate: {rates['decision_severe_rate']:.6f}")
    print(f"score_severe_rate: {rates['score_severe_rate']:.6f}")
    print(
        "citation_string_disagreement_rate: "
        f"{rates['citation_string_disagreement_rate']:.6f}"
    )
    print(f"grounding_severe_rate: {rates['grounding_severe_rate']:.6f}")
    print(
        "dominant_disagreement_dimensions: "
        + json.dumps(rates["dominant_disagreement_dimensions"], sort_keys=True)
    )
    print(
        "pre_normalization_disagreement_rate: "
        f"{normalization['pre_normalization_string_disagreement_rate']:.6f}"
    )
    print(
        "post_normalization_disagreement_rate: "
        f"{normalization['post_normalization_anchor_disagreement_rate']:.6f}"
    )
    print(f"manifest_hash: {manifest['analysis_manifest_hash']}")


if __name__ == "__main__":
    main()

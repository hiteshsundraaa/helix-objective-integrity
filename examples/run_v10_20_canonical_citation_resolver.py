from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.v10_canonical_citation_resolver import (
    run_canonical_citation_resolver,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v10.20 canonical citation resolver prototype."
    )
    parser.add_argument(
        "--real-pilot-root",
        default="benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1",
    )
    parser.add_argument(
        "--v10-19-root",
        default="benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/disagreement_analysis_v10_19",
    )
    parser.add_argument(
        "--preregistration-config",
        default="configs/v10_canonical_citation_resolver_preregistration.json",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_resolver_v10_20",
    )
    args = parser.parse_args()

    result = run_canonical_citation_resolver(
        Path(args.real_pilot_root),
        Path(args.v10_19_root),
        Path(args.out_dir),
        Path(args.preregistration_config),
    )
    summary = result["summary"]
    manifest = result["manifest"]
    print(f"source_run_id: {summary['source_run_id']}")
    print(f"case_count: {summary['case_count']}")
    print(
        "pre_resolution_string_disagreement_rate: "
        f"{summary['pre_resolution_string_disagreement_rate']:.6f}"
    )
    print(
        "v10_19_post_normalization_disagreement_rate: "
        f"{summary['v10_19_post_normalization_disagreement_rate']:.6f}"
    )
    print(
        "post_resolution_disagreement_rate: "
        f"{summary['post_resolution_disagreement_rate']:.6f}"
    )
    print(
        "confidence_weighted_post_resolution_disagreement_rate: "
        f"{summary['confidence_weighted_post_resolution_disagreement_rate']:.6f}"
    )
    print(f"missing_citation_rate: {summary['missing_citation_rate']:.6f}")
    print(f"hallucinated_citation_rate: {summary['hallucinated_citation_rate']:.6f}")
    print(f"unresolved_citation_rate: {summary['unresolved_citation_rate']:.6f}")
    print(
        "scope_disagreement_resolved_rate: "
        f"{summary['scope_disagreement_resolved_rate']:.6f}"
    )
    print(f"success_criterion_passed: {str(summary['success_criterion_passed']).lower()}")
    print(f"failure_criterion_triggered: {str(summary['failure_criterion_triggered']).lower()}")
    print(f"manifest_hash: {manifest['manifest_hash']}")


if __name__ == "__main__":
    main()

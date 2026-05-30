from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.evidence_rollup import (
    DEFAULT_EVIDENCE_ARTIFACTS,
    collect_v6_evidence_rollup,
    write_v6_evidence_rollup_outputs,
)


ARG_TO_ARTIFACT = {
    "v5_acceptance": "v5_acceptance",
    "hostile_baselines": "hostile_baselines",
    "adjacent_rule": "adjacent_rule_analysis",
    "diversity_v5_main": "diversity_v5_main",
    "diversity_v5_adjacent": "diversity_v5_adjacent",
    "asymmetric_trace": "asymmetric_trace_analysis",
    "threshold_sensitivity": "threshold_sensitivity",
    "paraphrase_analysis": "paraphrase_analysis",
    "multi_provider_replay": "multi_provider_replay",
    "trace_noise_analysis": "trace_noise_analysis",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a HELIX v6 controlled evidence rollup from existing artifacts."
    )
    parser.add_argument("--out-dir", default="outputs/v6_evidence_rollup")
    parser.add_argument("--v5-acceptance", default=None)
    parser.add_argument("--hostile-baselines", default=None)
    parser.add_argument("--adjacent-rule", default=None)
    parser.add_argument("--diversity-v5-main", default=None)
    parser.add_argument("--diversity-v5-adjacent", default=None)
    parser.add_argument("--asymmetric-trace", default=None)
    parser.add_argument("--threshold-sensitivity", default=None)
    parser.add_argument("--paraphrase-analysis", default=None)
    parser.add_argument("--multi-provider-replay", default=None)
    parser.add_argument("--trace-noise-analysis", default=None)
    args = parser.parse_args()

    artifact_paths = dict(DEFAULT_EVIDENCE_ARTIFACTS)
    for arg_name, artifact_name in ARG_TO_ARTIFACT.items():
        value = getattr(args, arg_name)
        if value:
            artifact_paths[artifact_name] = value

    summary = collect_v6_evidence_rollup(artifact_paths=artifact_paths)
    summary_path, report_path = write_v6_evidence_rollup_outputs(summary, args.out_dir)

    print(f"Status: {summary.status}")
    print(f"Available artifacts: {summary.available_artifact_count}")
    print(f"Missing artifacts: {summary.missing_artifact_count}")
    print(f"Summary JSON: {summary_path}")
    print(f"Markdown report: {report_path}")
    print("Headline metrics:")
    for key, value in summary.headline_metrics.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()

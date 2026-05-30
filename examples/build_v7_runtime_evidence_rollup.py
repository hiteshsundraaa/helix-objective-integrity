from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.runtime.runtime_evidence_rollup import (
    DEFAULT_RUNTIME_EVIDENCE_ARTIFACTS,
    collect_v7_runtime_evidence_rollup,
    write_v7_runtime_evidence_rollup_outputs,
)


ARG_TO_ARTIFACT = {
    "runtime_summary": "runtime_summary",
    "runtime_receipts": "runtime_receipts",
    "runtime_report": "runtime_report",
    "negative_control_summary": "negative_control_summary",
    "negative_control_records": "negative_control_records",
    "negative_control_report": "negative_control_report",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a HELIX v7 runtime evidence rollup from existing artifacts."
    )
    parser.add_argument("--out-dir", default="outputs/v7_runtime_evidence_rollup")
    parser.add_argument("--runtime-summary", default=None)
    parser.add_argument("--runtime-receipts", default=None)
    parser.add_argument("--runtime-report", default=None)
    parser.add_argument("--negative-control-summary", default=None)
    parser.add_argument("--negative-control-records", default=None)
    parser.add_argument("--negative-control-report", default=None)
    args = parser.parse_args()

    artifact_paths = dict(DEFAULT_RUNTIME_EVIDENCE_ARTIFACTS)
    for arg_name, artifact_name in ARG_TO_ARTIFACT.items():
        value = getattr(args, arg_name)
        if value:
            artifact_paths[artifact_name] = value

    summary = collect_v7_runtime_evidence_rollup(artifact_paths=artifact_paths)
    summary_path, report_path = write_v7_runtime_evidence_rollup_outputs(
        summary,
        args.out_dir,
    )

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

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.trajectory.evidence_rollup import (
    DEFAULT_TRAJECTORY_CONFIGS,
    DEFAULT_TRAJECTORY_EVIDENCE_ARTIFACTS,
    collect_v8_trajectory_evidence_rollup,
    write_v8_trajectory_evidence_rollup_outputs,
)


ARG_TO_ARTIFACT = {
    "trajectory_summary": "trajectory_summary",
    "trajectory_manifest": "trajectory_manifest",
    "trajectory_records": "trajectory_records",
    "trajectory_report": "trajectory_report",
    "cp_summary": "cp_summary",
    "cp_records": "cp_records",
    "cp_report": "cp_report",
    "dose_ladder_summary": "dose_ladder_summary",
    "dose_ladder_manifest": "dose_ladder_manifest",
    "dose_ladder_records": "dose_ladder_records",
    "dose_ladder_report": "dose_ladder_report",
    "self_audit_summary": "self_audit_summary",
    "self_audit_manifest": "self_audit_manifest",
    "self_audit_records": "self_audit_records",
    "self_audit_report": "self_audit_report",
    "fast_path_summary": "fast_path_summary",
    "fast_path_manifest": "fast_path_manifest",
    "fast_path_records": "fast_path_records",
    "fast_path_report": "fast_path_report",
}


ARG_TO_CONFIG = {
    "cp_config": "cp_config",
    "dose_ladder_config": "dose_ladder_config",
    "self_audit_config": "self_audit_config",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a HELIX v8 trajectory evidence rollup from existing artifacts."
    )
    parser.add_argument("--out-dir", default="outputs/v8_trajectory_evidence_rollup")
    for arg_name in ARG_TO_ARTIFACT:
        parser.add_argument(f"--{arg_name.replace('_', '-')}", default=None)
    for arg_name in ARG_TO_CONFIG:
        parser.add_argument(f"--{arg_name.replace('_', '-')}", default=None)
    args = parser.parse_args()

    artifact_paths = dict(DEFAULT_TRAJECTORY_EVIDENCE_ARTIFACTS)
    for arg_name, artifact_name in ARG_TO_ARTIFACT.items():
        value = getattr(args, arg_name)
        if value:
            artifact_paths[artifact_name] = value

    config_paths = dict(DEFAULT_TRAJECTORY_CONFIGS)
    for arg_name, config_name in ARG_TO_CONFIG.items():
        value = getattr(args, arg_name)
        if value:
            config_paths[config_name] = value

    summary = collect_v8_trajectory_evidence_rollup(
        artifact_paths=artifact_paths,
        config_paths=config_paths,
    )
    summary_path, report_path = write_v8_trajectory_evidence_rollup_outputs(
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

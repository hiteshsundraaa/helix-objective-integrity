from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from helix.trajectory.schema import (
    TrajectoryRun,
    TrajectoryRunManifest,
    build_manifest_hash,
    stable_json_hash,
)


def write_trajectory_run_outputs(
    trajectories: list[TrajectoryRun],
    *,
    out_dir: str | Path,
    manifest_config: dict,
) -> dict[str, Any]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)

    records = [
        step.model_dump(mode="json")
        for trajectory in trajectories
        for step in trajectory.steps
    ]
    runs_payload = [trajectory.model_dump(mode="json") for trajectory in trajectories]
    records_jsonl = "\n".join(json.dumps(record, sort_keys=True) for record in records)
    if records:
        records_jsonl += "\n"
    runs_json = json.dumps(runs_payload, indent=2, sort_keys=True) + "\n"

    records_hash = stable_json_hash(records)
    dataset_hash = stable_json_hash(runs_payload)
    summary = _summary(trajectories)
    manifest = _build_manifest(
        trajectories=trajectories,
        manifest_config=manifest_config,
        dataset_hash=dataset_hash,
        records_hash=records_hash,
    )
    summary["manifest_hash"] = manifest.manifest_hash

    (target / "trajectory_records.jsonl").write_text(records_jsonl, encoding="utf-8")
    (target / "trajectory_runs.json").write_text(runs_json, encoding="utf-8")
    (target / "trajectory_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "trajectory_run_manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "trajectory_report.md").write_text(
        _report(summary=summary, manifest=manifest) + "\n",
        encoding="utf-8",
    )
    return summary


def _build_manifest(
    *,
    trajectories: list[TrajectoryRun],
    manifest_config: dict,
    dataset_hash: str,
    records_hash: str,
) -> TrajectoryRunManifest:
    steps_per_trajectory = len(trajectories[0].steps) if trajectories else 0
    fields = {
        "manifest_hash": "",
        "trajectory_schema_version": manifest_config.get("trajectory_schema_version", "v8.1"),
        "generator_seed": manifest_config["generator_seed"],
        "trajectory_count": len(trajectories),
        "steps_per_trajectory": steps_per_trajectory,
        "perturbation_config": manifest_config.get("perturbation_config", {}),
        "gate_thresholds": manifest_config.get("gate_thresholds", {}),
        "helix_version": manifest_config.get("helix_version", "unknown"),
        "generated_at": manifest_config.get(
            "generated_at",
            datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        ),
        "dataset_hash": dataset_hash,
        "records_hash": records_hash,
    }
    fields["manifest_hash"] = build_manifest_hash(fields)
    return TrajectoryRunManifest.model_validate(fields)


def _summary(trajectories: list[TrajectoryRun]) -> dict[str, Any]:
    records = [
        step
        for trajectory in trajectories
        for step in trajectory.steps
    ]
    ground_truth_counts = Counter(step.ground_truth for step in records)
    decision_counts = Counter(step.helix_decision for step in records)
    return {
        "trajectory_count": len(trajectories),
        "step_count": len(records),
        "ground_truth_counts": dict(sorted(ground_truth_counts.items())),
        "decision_counts": dict(sorted(decision_counts.items())),
        "intervention_necessary_count": sum(
            step.gate_intervention_was_necessary for step in records
        ),
        "would_have_executed_without_gate_count": sum(
            step.would_have_executed_without_gate for step in records
        ),
        "self_correction_before_gate_count": sum(
            step.self_correction_before_gate for step in records
        ),
        "trajectory_context_required_count": sum(
            step.ground_truth_requires_trajectory_context for step in records
        ),
        "locally_safe_globally_drifted_count": sum(
            step.ground_truth == "locally_safe_globally_drifted" for step in records
        ),
        "manifest_hash": "",
    }


def _report(
    *,
    summary: dict[str, Any],
    manifest: TrajectoryRunManifest,
) -> str:
    return "\n".join(
        [
            "# HELIX v8.1 Minimal Trajectory Runner",
            "",
            "This report summarizes deterministic trajectory infrastructure only. It does not claim CP_t, drift halflife, or live-agent behavior.",
            "",
            "## Summary",
            "",
            f"- trajectory_count: `{summary['trajectory_count']}`",
            f"- step_count: `{summary['step_count']}`",
            f"- ground_truth_counts: `{json.dumps(summary['ground_truth_counts'], sort_keys=True)}`",
            f"- decision_counts: `{json.dumps(summary['decision_counts'], sort_keys=True)}`",
            f"- intervention_necessary_count: `{summary['intervention_necessary_count']}`",
            f"- trajectory_context_required_count: `{summary['trajectory_context_required_count']}`",
            f"- locally_safe_globally_drifted_count: `{summary['locally_safe_globally_drifted_count']}`",
            f"- manifest_hash: `{manifest.manifest_hash}`",
            "",
            "## Manifest",
            "",
            f"- trajectory_schema_version: `{manifest.trajectory_schema_version}`",
            f"- generator_seed: `{manifest.generator_seed}`",
            f"- dataset_hash: `{manifest.dataset_hash}`",
            f"- records_hash: `{manifest.records_hash}`",
            "",
            "## Limitations",
            "",
            "- Deterministic scaffold only.",
            "- No live model calls.",
            "- No CP_t yet.",
            "- No drift halflife yet.",
            "- No stochastic agent behavior yet.",
            "- Ground truth labels are derived from perturbation config.",
        ]
    )

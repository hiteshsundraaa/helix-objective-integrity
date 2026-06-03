from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_TRAJECTORY_EVIDENCE_ARTIFACTS: dict[str, str] = {
    "trajectory_summary": "outputs/trajectory_runs/v8_basic/trajectory_summary.json",
    "trajectory_manifest": "outputs/trajectory_runs/v8_basic/trajectory_run_manifest.json",
    "trajectory_records": "outputs/trajectory_runs/v8_basic/trajectory_records.jsonl",
    "trajectory_report": "outputs/trajectory_runs/v8_basic/trajectory_report.md",
    "cp_summary": "outputs/trajectory_cp/v8/cp_summary.json",
    "cp_records": "outputs/trajectory_cp/v8/cp_records.jsonl",
    "cp_report": "outputs/trajectory_cp/v8/cp_report.md",
    "dose_ladder_summary": "outputs/trajectory_dose_ladder/v8/dose_ladder_summary.json",
    "dose_ladder_manifest": "outputs/trajectory_dose_ladder/v8/dose_ladder_manifest.json",
    "dose_ladder_records": "outputs/trajectory_dose_ladder/v8/dose_ladder_records.jsonl",
    "dose_ladder_report": "outputs/trajectory_dose_ladder/v8/dose_ladder_report.md",
    "self_audit_summary": "outputs/trajectory_self_audit/v8/self_audit_summary.json",
    "self_audit_manifest": "outputs/trajectory_self_audit/v8/self_audit_manifest.json",
    "self_audit_records": "outputs/trajectory_self_audit/v8/self_audit_records.jsonl",
    "self_audit_report": "outputs/trajectory_self_audit/v8/self_audit_report.md",
    "fast_path_summary": "outputs/performance/v8_fast_path/fast_path_latency_summary.json",
    "fast_path_manifest": "outputs/performance/v8_fast_path/fast_path_latency_manifest.json",
    "fast_path_records": "outputs/performance/v8_fast_path/fast_path_latency_records.jsonl",
    "fast_path_report": "outputs/performance/v8_fast_path/fast_path_latency_report.md",
    "drift_halflife_summary": "outputs/trajectory_drift_halflife/v8/drift_halflife_summary.json",
    "drift_halflife_manifest": "outputs/trajectory_drift_halflife/v8/drift_halflife_manifest.json",
    "drift_halflife_records": "outputs/trajectory_drift_halflife/v8/drift_halflife_records.jsonl",
    "drift_halflife_report": "outputs/trajectory_drift_halflife/v8/drift_halflife_report.md",
    "failure_space_summary": "outputs/trajectory_failure_space/v8/failure_space_summary.json",
    "failure_space_manifest": "outputs/trajectory_failure_space/v8/failure_space_manifest.json",
    "failure_space_records": "outputs/trajectory_failure_space/v8/failure_space_records.jsonl",
    "failure_space_trajectories": "outputs/trajectory_failure_space/v8/failure_space_trajectories.jsonl",
    "failure_space_report": "outputs/trajectory_failure_space/v8/failure_space_report.md",
    "failure_space_export_summary": "outputs/trajectory_failure_space_exports/v8/export_summary.json",
    "failure_space_export_manifest": "outputs/trajectory_failure_space_exports/v8/export_manifest.json",
    "failure_space_export_report": "outputs/trajectory_failure_space_exports/v8/export_report.md",
    "failure_space_step_table": "outputs/trajectory_failure_space_exports/v8/failure_space_step_table.csv",
    "failure_space_trajectory_curves": "outputs/trajectory_failure_space_exports/v8/failure_space_trajectory_curves.csv",
    "failure_mode_counts_csv": "outputs/trajectory_failure_space_exports/v8/failure_mode_counts.csv",
    "confidence_counts_csv": "outputs/trajectory_failure_space_exports/v8/confidence_counts.csv",
    "dose_metric_summary_csv": "outputs/trajectory_failure_space_exports/v8/dose_metric_summary.csv",
}


DEFAULT_TRAJECTORY_CONFIGS: dict[str, str] = {
    "cp_config": "configs/cp_config_v8.json",
    "dose_ladder_config": "configs/dose_ladder_v8.json",
    "self_audit_config": "configs/self_audit_v8.json",
    "drift_halflife_config": "configs/drift_halflife_v8.json",
    "failure_space_config": "configs/failure_space_v8.json",
}


CONFIG_ROLES = {
    "cp_config": "Pre-registered v8.2 contradiction-pressure thresholds and retention parameter.",
    "dose_ladder_config": "Pre-registered v8.3 perturbation dose ladder levels.",
    "self_audit_config": "Pre-registered v8.4 clean/boundary/severe self-audit conditions.",
    "drift_halflife_config": "Pre-registered v8.6 deterministic objective-similarity proxy.",
    "failure_space_config": "Pre-registered v8.7 deterministic failure-space rules and metric implementations.",
}


HEADLINE_METRIC_KEYS = [
    "trajectory_count",
    "step_count",
    "ground_truth_counts",
    "decision_counts",
    "intervention_necessary_count",
    "trajectory_context_required_count",
    "locally_safe_globally_drifted_count",
    "trajectory_manifest_hash",
    "cp_trajectory_count",
    "cp_step_count",
    "max_cp_t",
    "crossed_warn_count",
    "crossed_block_count",
    "predicted_T_star",
    "empirical_T_star_by_trajectory",
    "cp_decision_counts",
    "dose_level_count",
    "first_warn_dose_level",
    "first_degrade_dose_level",
    "first_quarantine_dose_level",
    "first_block_dose_level",
    "monotonic_max_cp_t",
    "monotonic_mean_final_cp_t",
    "max_cp_t_by_dose",
    "dose_manifest_hash",
    "self_audit_condition_count",
    "clean_disagreement_rate",
    "contaminated_disagreement_rate",
    "disagreement_lift",
    "clean_false_compliance_rate",
    "contaminated_false_compliance_rate",
    "false_compliance_lift",
    "helix_detection_rate_clean",
    "helix_detection_rate_contaminated",
    "self_audit_manifest_hash",
    "measured_operation_count",
    "slowest_operation_by_p99",
    "slowest_operation_p99_ms",
    "heavy_llm_calls_per_step",
    "estimated_llm_token_cost_per_1000_steps_usd",
    "manifest_hash",
    "drift_halflife_condition_count",
    "drift_halflife_record_count",
    "clean_halflife_crossing_rate",
    "contaminated_halflife_crossing_rate",
    "halflife_crossing_lift",
    "clean_final_similarity_mean",
    "contaminated_final_similarity_mean",
    "final_similarity_drop_contaminated_vs_clean",
    "drift_halflife_manifest_hash",
    "failure_space_dose_level_count",
    "failure_space_trajectory_count",
    "failure_space_step_count",
    "dominant_failure_mode_counts",
    "failure_mode_confidence_counts",
    "low_confidence_step_count",
    "compound_failure_step_count",
    "clean_step_count",
    "unclassified_step_count",
    "failure_space_first_block_dose_level",
    "failure_space_manifest_hash",
    "mean_D_G_by_dose",
    "mean_CSR_by_dose",
    "mean_D_Q_by_dose",
    "mean_FAP_by_dose",
    "mean_CP_t_by_dose",
    "failure_space_max_CP_t_by_dose",
    "failure_space_export_status",
    "failure_space_export_manifest_hash",
    "failure_space_step_table_rows",
    "failure_space_trajectory_curve_rows",
    "failure_mode_count_rows",
    "confidence_count_rows",
    "dose_metric_rows",
    "generated_plot_files",
    "skipped_plot_files",
    "plot_generation_status",
    "plot_skip_reason",
]


class TrajectoryEvidenceArtifactStatus(BaseModel):
    name: str
    status: str
    path: str
    artifact_hash: str | None = None
    key_metrics: dict[str, Any] = Field(default_factory=dict)
    key_result: str = ""
    error: str | None = None


class TrajectoryEvidenceRollupSummary(BaseModel):
    status: str
    generated_at: str
    artifact_count: int
    available_artifact_count: int
    missing_artifact_count: int
    artifact_hashes: dict[str, str]
    config_hashes: dict[str, str]
    headline_metrics: dict[str, Any]
    strengths: list[str]
    limitations: list[str]
    missing_artifacts: list[str]
    recommended_next_steps: list[str]
    artifacts: list[TrajectoryEvidenceArtifactStatus]
    configs: list[TrajectoryEvidenceArtifactStatus]

    def to_markdown(self) -> str:
        metrics = self.headline_metrics
        lines = [
            "# HELIX v8 Trajectory Evidence Rollup",
            "",
            "## Executive Summary",
            "",
            _executive_summary(self),
            "",
            "## Evidence Inventory",
            "",
            "| Artifact | Status | Path | SHA256 | Key result |",
            "|---|---|---|---|---|",
        ]
        for artifact in self.artifacts:
            lines.append(
                f"| `{artifact.name}` | `{artifact.status}` | `{artifact.path}` | "
                f"`{artifact.artifact_hash or 'n/a'}` | {artifact.key_result or 'n/a'} |"
            )
        lines.extend(
            [
                "",
                "## Config Inventory",
                "",
                "| Config | SHA256 | Role |",
                "|---|---|---|",
            ]
        )
        for config in self.configs:
            lines.append(
                f"| `{config.name}` | `{config.artifact_hash or 'n/a'}` | "
                f"{CONFIG_ROLES.get(config.name, 'v8 trajectory configuration')} |"
            )
        lines.extend(
            [
                "",
                "## Headline Trajectory Results",
                "",
                "### v8.1 Trajectory Substrate",
                "",
                f"- trajectory_count: `{_value(metrics['trajectory_count'])}`",
                f"- step_count: `{_value(metrics['step_count'])}`",
                f"- ground_truth_counts: `{_value(metrics['ground_truth_counts'])}`",
                f"- decision_counts: `{_value(metrics['decision_counts'])}`",
                f"- intervention_necessary_count: `{_value(metrics['intervention_necessary_count'])}`",
                f"- trajectory_context_required_count: `{_value(metrics['trajectory_context_required_count'])}`",
                "",
                "### v8.2 Contradiction Pressure",
                "",
                f"- max_cp_t: `{_value(metrics['max_cp_t'])}`",
                f"- crossed_warn_count: `{_value(metrics['crossed_warn_count'])}`",
                f"- crossed_block_count: `{_value(metrics['crossed_block_count'])}`",
                f"- predicted_T_star: `{_value(metrics['predicted_T_star'])}`",
                f"- empirical_T_star_by_trajectory: `{_value(metrics['empirical_T_star_by_trajectory'])}`",
                "",
                "### v8.3 Dose Ladder",
                "",
                f"- dose_level_count: `{_value(metrics['dose_level_count'])}`",
                f"- first WARN/DEGRADE/QUARANTINE/BLOCK dose levels: "
                f"`{_value(metrics['first_warn_dose_level'])}` / "
                f"`{_value(metrics['first_degrade_dose_level'])}` / "
                f"`{_value(metrics['first_quarantine_dose_level'])}` / "
                f"`{_value(metrics['first_block_dose_level'])}`",
                f"- monotonic_max_cp_t: `{_value(metrics['monotonic_max_cp_t'])}`",
                f"- monotonic_mean_final_cp_t: `{_value(metrics['monotonic_mean_final_cp_t'])}`",
                "",
                "| Dose | Max CP_t |",
                "|---:|---:|",
            ]
        )
        for dose, max_cp in (metrics.get("max_cp_t_by_dose") or {}).items():
            lines.append(f"| {dose} | `{_value(max_cp)}` |")
        lines.extend(
            [
                "",
                "### v8.4 Self-Audit Baseline",
                "",
                f"- self_audit_condition_count: `{_value(metrics['self_audit_condition_count'])}`",
                f"- clean_disagreement_rate: `{_value(metrics['clean_disagreement_rate'])}`",
                f"- contaminated_disagreement_rate: `{_value(metrics['contaminated_disagreement_rate'])}`",
                f"- disagreement_lift: `{_value(metrics['disagreement_lift'])}`",
                f"- clean_false_compliance_rate: `{_value(metrics['clean_false_compliance_rate'])}`",
                f"- contaminated_false_compliance_rate: `{_value(metrics['contaminated_false_compliance_rate'])}`",
                f"- false_compliance_lift: `{_value(metrics['false_compliance_lift'])}`",
                f"- helix_detection_rate_clean/contaminated: "
                f"`{_value(metrics['helix_detection_rate_clean'])}` / "
                f"`{_value(metrics['helix_detection_rate_contaminated'])}`",
                "",
                "### v8.5 Fast-Path Latency / Cost",
                "",
                f"- measured_operation_count: `{_value(metrics['measured_operation_count'])}`",
                f"- slowest_operation_by_p99: `{_value(metrics['slowest_operation_by_p99'])}`",
                f"- slowest_operation_p99_ms: `{_value(metrics['slowest_operation_p99_ms'])}`",
                f"- heavy_llm_calls_per_step: `{_value(metrics['heavy_llm_calls_per_step'])}`",
                f"- estimated_llm_token_cost_per_1000_steps_usd: "
                f"`{_value(metrics['estimated_llm_token_cost_per_1000_steps_usd'])}`",
                "",
                "### v8.6 Drift Halflife Scaffold",
                "",
                "v8.6 uses a deterministic perturbation-based objective-similarity proxy. It is a scaffold for Drift Halflife, not the final embedding/model-based semantic drift metric.",
                "",
                f"- condition_count: `{_value(metrics['drift_halflife_condition_count'])}`",
                f"- record_count: `{_value(metrics['drift_halflife_record_count'])}`",
                f"- clean_halflife_crossing_rate: `{_value(metrics['clean_halflife_crossing_rate'])}`",
                f"- contaminated_halflife_crossing_rate: `{_value(metrics['contaminated_halflife_crossing_rate'])}`",
                f"- halflife_crossing_lift: `{_value(metrics['halflife_crossing_lift'])}`",
                f"- clean_final_similarity_mean: `{_value(metrics['clean_final_similarity_mean'])}`",
                f"- contaminated_final_similarity_mean: `{_value(metrics['contaminated_final_similarity_mean'])}`",
                f"- final_similarity_drop_contaminated_vs_clean: `{_value(metrics['final_similarity_drop_contaminated_vs_clean'])}`",
                "",
                "### v8.7 Failure-Space Trajectory Analysis",
                "",
                "v8.7 projects deterministic trajectories into a scaffolded five-dimensional failure space: D_G, CSR, D_Q, FAP, and CP_t. Dominant failure modes are assigned by pre-registered rules in configs/failure_space_v8.json. This is a deterministic diagnostic scaffold, not a final embedding/model-based failure taxonomy.",
                "",
                f"- dose_level_count: `{_value(metrics['failure_space_dose_level_count'])}`",
                f"- trajectory_count: `{_value(metrics['failure_space_trajectory_count'])}`",
                f"- step_count: `{_value(metrics['failure_space_step_count'])}`",
                f"- dominant_failure_mode_counts: `{_value(metrics['dominant_failure_mode_counts'])}`",
                f"- failure_mode_confidence_counts: `{_value(metrics['failure_mode_confidence_counts'])}`",
                f"- low_confidence_step_count: `{_value(metrics['low_confidence_step_count'])}`",
                f"- first_block_dose_level: `{_value(metrics['failure_space_first_block_dose_level'])}`",
                f"- manifest_hash: `{_value(metrics['failure_space_manifest_hash'])}`",
                "",
                "### v8.8 Failure-Space Export Scaffold",
                "",
                "v8.8 does not create new evidence. It exports existing v8.7 failure-space records into CSV tables and optional static plot files for inspection and future paper figures. In the current environment, plot generation was skipped because matplotlib was unavailable.",
                "",
                f"- export_status: `{_value(metrics['failure_space_export_status'])}`",
                f"- step_table_rows: `{_value(metrics['failure_space_step_table_rows'])}`",
                f"- trajectory_curve_rows: `{_value(metrics['failure_space_trajectory_curve_rows'])}`",
                f"- failure_mode_count_rows: `{_value(metrics['failure_mode_count_rows'])}`",
                f"- confidence_count_rows: `{_value(metrics['confidence_count_rows'])}`",
                f"- dose_metric_rows: `{_value(metrics['dose_metric_rows'])}`",
                f"- generated_plot_files: `{_value(metrics['generated_plot_files'])}`",
                f"- skipped_plot_files: `{_value(metrics['skipped_plot_files'])}`",
                f"- plot_generation_status: `{_value(metrics['plot_generation_status'])}`",
                f"- plot_skip_reason: `{_value(metrics['plot_skip_reason'])}`",
                f"- export_manifest_hash: `{_value(metrics['failure_space_export_manifest_hash'])}`",
                "",
                "## What This Supports",
                "",
            ]
        )
        lines.extend(f"- {strength}" for strength in self.strengths)
        lines.extend(
            [
                "",
                "## What This Does Not Yet Prove",
                "",
                "- No live LLM trajectory generation yet.",
                "- No stochastic agent behavior yet.",
                "- Self-audit is a deterministic simulated policy, not live model self-certification.",
                "- CP_t increment policy is scaffolded.",
                "- Drift Halflife is not yet embedding-based or live-agent-derived.",
                "- No semantic slow-path drift extractor has been implemented yet.",
                "- Failure-space metrics are deterministic proxy metrics, not final semantic/embedding-based measurements.",
                "- No live agent trajectories are projected yet.",
                "- Failure-mode rules are scaffolded and require future validation.",
                "- CSV exports are inspection aids, not additional statistical validation.",
                "- Static plots may be unavailable depending on environment dependencies.",
                "- No new semantic/embedding diagnostics are introduced by v8.8.",
                "- No objective curvature yet.",
                "- No production proxy, network, or database overhead is measured.",
                "- No external human-audited trajectory dataset yet.",
                "",
                "## Recommended Next Steps",
                "",
            ]
        )
        lines.extend(f"{index}. {step}" for index, step in enumerate(self.recommended_next_steps, start=1))
        if self.limitations:
            lines.extend(["", "## Rollup Limitations", ""])
            lines.extend(f"- {limitation}" for limitation in self.limitations)
        return "\n".join(lines)


def collect_v8_trajectory_evidence_rollup(
    *,
    artifact_paths: dict[str, str | Path] | None = None,
    config_paths: dict[str, str | Path] | None = None,
    generated_at: str | None = None,
) -> TrajectoryEvidenceRollupSummary:
    paths = {
        name: str(path)
        for name, path in (artifact_paths or DEFAULT_TRAJECTORY_EVIDENCE_ARTIFACTS).items()
    }
    configs = {
        name: str(path)
        for name, path in (config_paths or DEFAULT_TRAJECTORY_CONFIGS).items()
    }
    artifacts = [_collect_artifact(name, path) for name, path in paths.items()]
    config_statuses = [_collect_artifact(name, path) for name, path in configs.items()]
    headline_metrics = _empty_headline_metrics()
    for artifact in artifacts:
        _merge_headline_metrics(headline_metrics, artifact)

    missing_artifacts = [
        f"{item.name}: {item.path}"
        for item in [*artifacts, *config_statuses]
        if item.status != "available"
    ]
    artifact_hashes = {
        artifact.name: artifact.artifact_hash
        for artifact in artifacts
        if artifact.artifact_hash is not None
    }
    config_hashes = {
        config.name: config.artifact_hash
        for config in config_statuses
        if config.artifact_hash is not None
    }
    available_count = sum(
        item.status == "available"
        for item in [*artifacts, *config_statuses]
    )
    total_count = len(artifacts) + len(config_statuses)
    missing_count = total_count - available_count
    return TrajectoryEvidenceRollupSummary(
        status="complete" if missing_count == 0 else "partial",
        generated_at=generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        artifact_count=total_count,
        available_artifact_count=available_count,
        missing_artifact_count=missing_count,
        artifact_hashes=artifact_hashes,
        config_hashes=config_hashes,
        headline_metrics=headline_metrics,
        strengths=_strengths(headline_metrics),
        limitations=_limitations(missing_artifacts),
        missing_artifacts=missing_artifacts,
        recommended_next_steps=_recommended_next_steps(),
        artifacts=artifacts,
        configs=config_statuses,
    )


def write_v8_trajectory_evidence_rollup_outputs(
    summary: TrajectoryEvidenceRollupSummary,
    out_dir: str | Path,
) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary_path = target / "helix_v8_trajectory_summary.json"
    report_path = target / "helix_v8_trajectory_report.md"
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")
    return summary_path, report_path


def stable_file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _collect_artifact(name: str, path: str | Path) -> TrajectoryEvidenceArtifactStatus:
    target = Path(path)
    if not target.exists():
        return TrajectoryEvidenceArtifactStatus(
            name=name,
            status="missing",
            path=str(target),
            key_result="missing",
        )
    artifact_hash = stable_file_hash(target)
    try:
        key_metrics = _extract_key_metrics(name, target)
    except Exception as exc:
        return TrajectoryEvidenceArtifactStatus(
            name=name,
            status="invalid",
            path=str(target),
            artifact_hash=artifact_hash,
            key_result="invalid",
            error=str(exc),
        )
    return TrajectoryEvidenceArtifactStatus(
        name=name,
        status="available",
        path=str(target),
        artifact_hash=artifact_hash,
        key_metrics=key_metrics,
        key_result=_key_result(name, key_metrics),
    )


def _extract_key_metrics(name: str, path: Path) -> dict[str, Any]:
    if name == "trajectory_summary":
        data = _read_json(path)
        return {
            "trajectory_count": data.get("trajectory_count"),
            "step_count": data.get("step_count"),
            "ground_truth_counts": data.get("ground_truth_counts"),
            "decision_counts": data.get("decision_counts"),
            "intervention_necessary_count": data.get("intervention_necessary_count"),
            "trajectory_context_required_count": data.get("trajectory_context_required_count"),
            "locally_safe_globally_drifted_count": data.get("locally_safe_globally_drifted_count"),
        }
    if name == "trajectory_manifest":
        data = _read_json(path)
        return {"manifest_hash": data.get("manifest_hash")}
    if name == "cp_summary":
        data = _read_json(path)
        return {
            "trajectory_count": data.get("trajectory_count"),
            "step_count": data.get("step_count"),
            "max_cp_t": data.get("max_cp_t"),
            "crossed_warn_count": data.get("crossed_warn_count"),
            "crossed_block_count": data.get("crossed_block_count"),
            "predicted_T_star": data.get("predicted_T_star"),
            "empirical_T_star_by_trajectory": data.get("empirical_T_star_by_trajectory"),
            "decision_counts": data.get("decision_counts"),
        }
    if name == "dose_ladder_summary":
        data = _read_json(path)
        return {
            "dose_level_count": data.get("dose_level_count"),
            "first_warn_dose_level": data.get("first_warn_dose_level"),
            "first_degrade_dose_level": data.get("first_degrade_dose_level"),
            "first_quarantine_dose_level": data.get("first_quarantine_dose_level"),
            "first_block_dose_level": data.get("first_block_dose_level"),
            "monotonic_max_cp_t": data.get("monotonic_max_cp_t"),
            "monotonic_mean_final_cp_t": data.get("monotonic_mean_final_cp_t"),
            "max_cp_t_by_dose": _max_cp_by_dose(data.get("dose_results") or []),
        }
    if name == "dose_ladder_manifest":
        data = _read_json(path)
        return {"manifest_hash": data.get("manifest_hash")}
    if name == "self_audit_summary":
        data = _read_json(path)
        return {
            "condition_count": data.get("condition_count"),
            "clean_disagreement_rate": data.get("clean_condition_disagreement_rate"),
            "contaminated_disagreement_rate": data.get("contaminated_condition_disagreement_rate"),
            "disagreement_lift": data.get("disagreement_lift_contaminated_vs_clean"),
            "clean_false_compliance_rate": data.get("clean_self_audit_false_compliance_rate"),
            "contaminated_false_compliance_rate": data.get("contaminated_self_audit_false_compliance_rate"),
            "false_compliance_lift": data.get("false_compliance_lift_contaminated_vs_clean"),
            "helix_detection_rate_clean": data.get("helix_detection_rate_clean"),
            "helix_detection_rate_contaminated": data.get("helix_detection_rate_contaminated"),
        }
    if name == "self_audit_manifest":
        data = _read_json(path)
        return {"manifest_hash": data.get("manifest_hash")}
    if name == "fast_path_summary":
        data = _read_json(path)
        slowest_name = data.get("slowest_operation_p99")
        slowest_record = next(
            (
                record
                for record in data.get("operations", [])
                if record.get("operation") == slowest_name
            ),
            {},
        )
        return {
            "operation_count": data.get("operation_count"),
            "slowest_operation_by_p99": slowest_name,
            "slowest_operation_p99_ms": slowest_record.get("p99_latency_ms"),
            "heavy_llm_calls_per_step": data.get("heavy_llm_calls_per_step"),
            "estimated_llm_token_cost_per_1000_steps_usd": data.get("estimated_llm_token_cost_per_1000_steps_usd"),
        }
    if name == "fast_path_manifest":
        data = _read_json(path)
        return {"manifest_hash": data.get("manifest_hash")}
    if name == "drift_halflife_summary":
        data = _read_json(path)
        return {
            "condition_count": data.get("condition_count"),
            "clean_halflife_crossing_rate": data.get("clean_halflife_crossing_rate"),
            "contaminated_halflife_crossing_rate": data.get("contaminated_halflife_crossing_rate"),
            "halflife_crossing_lift": data.get("halflife_crossing_lift"),
            "clean_final_similarity_mean": data.get("clean_final_similarity_mean"),
            "contaminated_final_similarity_mean": data.get("contaminated_final_similarity_mean"),
            "final_similarity_drop_contaminated_vs_clean": data.get("final_similarity_drop_contaminated_vs_clean"),
        }
    if name == "drift_halflife_manifest":
        data = _read_json(path)
        return {"manifest_hash": data.get("manifest_hash")}
    if name == "failure_space_summary":
        data = _read_json(path)
        return {
            "dose_level_count": data.get("dose_level_count"),
            "trajectory_count": data.get("trajectory_count"),
            "step_count": data.get("step_count"),
            "dominant_failure_mode_counts": data.get("dominant_failure_mode_counts"),
            "failure_mode_confidence_counts": data.get("failure_mode_confidence_counts"),
            "low_confidence_step_count": data.get("low_confidence_step_count"),
            "compound_failure_step_count": data.get("compound_failure_step_count"),
            "clean_step_count": data.get("clean_step_count"),
            "unclassified_step_count": data.get("unclassified_step_count"),
            "first_block_dose_level": data.get("first_block_dose_level"),
            "mean_D_G_by_dose": data.get("mean_D_G_by_dose"),
            "mean_CSR_by_dose": data.get("mean_CSR_by_dose"),
            "mean_D_Q_by_dose": data.get("mean_D_Q_by_dose"),
            "mean_FAP_by_dose": data.get("mean_FAP_by_dose"),
            "mean_CP_t_by_dose": data.get("mean_CP_t_by_dose"),
            "max_CP_t_by_dose": data.get("max_CP_t_by_dose"),
        }
    if name == "failure_space_manifest":
        data = _read_json(path)
        return {"manifest_hash": data.get("manifest_hash")}
    if name == "failure_space_export_summary":
        data = _read_json(path)
        return {
            "status": data.get("status"),
            "step_row_count": data.get("step_row_count"),
            "trajectory_curve_row_count": data.get("trajectory_curve_row_count"),
            "failure_mode_count_rows": data.get("failure_mode_count_rows"),
            "confidence_count_rows": data.get("confidence_count_rows"),
            "dose_metric_rows": data.get("dose_metric_rows"),
            "generated_plot_files": data.get("generated_plot_files"),
            "skipped_plot_files": data.get("skipped_plot_files"),
            "plot_generation_status": data.get("plot_generation_status"),
            "plot_skip_reason": _plot_skip_reason(data),
        }
    if name == "failure_space_export_manifest":
        data = _read_json(path)
        return {"manifest_hash": data.get("manifest_hash")}
    if path.suffix == ".jsonl":
        return {"line_count": _count_jsonl_lines(path)}
    if path.suffix == ".csv":
        line_count = _count_text_lines(path)
        return {"line_count": line_count, "data_row_count": max(0, line_count - 1)}
    return {}


def _merge_headline_metrics(
    headline: dict[str, Any],
    artifact: TrajectoryEvidenceArtifactStatus,
) -> None:
    metrics = artifact.key_metrics
    if artifact.name == "trajectory_summary":
        headline["trajectory_count"] = metrics.get("trajectory_count")
        headline["step_count"] = metrics.get("step_count")
        headline["ground_truth_counts"] = metrics.get("ground_truth_counts")
        headline["decision_counts"] = metrics.get("decision_counts")
        headline["intervention_necessary_count"] = metrics.get("intervention_necessary_count")
        headline["trajectory_context_required_count"] = metrics.get("trajectory_context_required_count")
        headline["locally_safe_globally_drifted_count"] = metrics.get("locally_safe_globally_drifted_count")
    elif artifact.name == "trajectory_manifest":
        headline["trajectory_manifest_hash"] = metrics.get("manifest_hash")
    elif artifact.name == "cp_summary":
        headline["cp_trajectory_count"] = metrics.get("trajectory_count")
        headline["cp_step_count"] = metrics.get("step_count")
        headline["max_cp_t"] = metrics.get("max_cp_t")
        headline["crossed_warn_count"] = metrics.get("crossed_warn_count")
        headline["crossed_block_count"] = metrics.get("crossed_block_count")
        headline["predicted_T_star"] = metrics.get("predicted_T_star")
        headline["empirical_T_star_by_trajectory"] = metrics.get("empirical_T_star_by_trajectory")
        headline["cp_decision_counts"] = metrics.get("decision_counts")
    elif artifact.name == "dose_ladder_summary":
        headline["dose_level_count"] = metrics.get("dose_level_count")
        headline["first_warn_dose_level"] = metrics.get("first_warn_dose_level")
        headline["first_degrade_dose_level"] = metrics.get("first_degrade_dose_level")
        headline["first_quarantine_dose_level"] = metrics.get("first_quarantine_dose_level")
        headline["first_block_dose_level"] = metrics.get("first_block_dose_level")
        headline["monotonic_max_cp_t"] = metrics.get("monotonic_max_cp_t")
        headline["monotonic_mean_final_cp_t"] = metrics.get("monotonic_mean_final_cp_t")
        headline["max_cp_t_by_dose"] = metrics.get("max_cp_t_by_dose")
    elif artifact.name == "dose_ladder_manifest":
        headline["dose_manifest_hash"] = metrics.get("manifest_hash")
    elif artifact.name == "self_audit_summary":
        headline["self_audit_condition_count"] = metrics.get("condition_count")
        headline["clean_disagreement_rate"] = metrics.get("clean_disagreement_rate")
        headline["contaminated_disagreement_rate"] = metrics.get("contaminated_disagreement_rate")
        headline["disagreement_lift"] = metrics.get("disagreement_lift")
        headline["clean_false_compliance_rate"] = metrics.get("clean_false_compliance_rate")
        headline["contaminated_false_compliance_rate"] = metrics.get("contaminated_false_compliance_rate")
        headline["false_compliance_lift"] = metrics.get("false_compliance_lift")
        headline["helix_detection_rate_clean"] = metrics.get("helix_detection_rate_clean")
        headline["helix_detection_rate_contaminated"] = metrics.get("helix_detection_rate_contaminated")
    elif artifact.name == "self_audit_manifest":
        headline["self_audit_manifest_hash"] = metrics.get("manifest_hash")
    elif artifact.name == "fast_path_summary":
        headline["measured_operation_count"] = metrics.get("operation_count")
        headline["slowest_operation_by_p99"] = metrics.get("slowest_operation_by_p99")
        headline["slowest_operation_p99_ms"] = metrics.get("slowest_operation_p99_ms")
        headline["heavy_llm_calls_per_step"] = metrics.get("heavy_llm_calls_per_step")
        headline["estimated_llm_token_cost_per_1000_steps_usd"] = metrics.get("estimated_llm_token_cost_per_1000_steps_usd")
    elif artifact.name == "fast_path_manifest":
        headline["manifest_hash"] = metrics.get("manifest_hash")
    elif artifact.name == "drift_halflife_summary":
        headline["drift_halflife_condition_count"] = metrics.get("condition_count")
        headline["clean_halflife_crossing_rate"] = metrics.get("clean_halflife_crossing_rate")
        headline["contaminated_halflife_crossing_rate"] = metrics.get("contaminated_halflife_crossing_rate")
        headline["halflife_crossing_lift"] = metrics.get("halflife_crossing_lift")
        headline["clean_final_similarity_mean"] = metrics.get("clean_final_similarity_mean")
        headline["contaminated_final_similarity_mean"] = metrics.get("contaminated_final_similarity_mean")
        headline["final_similarity_drop_contaminated_vs_clean"] = metrics.get("final_similarity_drop_contaminated_vs_clean")
    elif artifact.name == "drift_halflife_manifest":
        headline["drift_halflife_manifest_hash"] = metrics.get("manifest_hash")
    elif artifact.name == "drift_halflife_records":
        headline["drift_halflife_record_count"] = metrics.get("line_count")
    elif artifact.name == "failure_space_summary":
        headline["failure_space_dose_level_count"] = metrics.get("dose_level_count")
        headline["failure_space_trajectory_count"] = metrics.get("trajectory_count")
        headline["failure_space_step_count"] = metrics.get("step_count")
        headline["dominant_failure_mode_counts"] = metrics.get("dominant_failure_mode_counts")
        headline["failure_mode_confidence_counts"] = metrics.get("failure_mode_confidence_counts")
        headline["low_confidence_step_count"] = metrics.get("low_confidence_step_count")
        headline["compound_failure_step_count"] = metrics.get("compound_failure_step_count")
        headline["clean_step_count"] = metrics.get("clean_step_count")
        headline["unclassified_step_count"] = metrics.get("unclassified_step_count")
        headline["failure_space_first_block_dose_level"] = metrics.get("first_block_dose_level")
        headline["mean_D_G_by_dose"] = metrics.get("mean_D_G_by_dose")
        headline["mean_CSR_by_dose"] = metrics.get("mean_CSR_by_dose")
        headline["mean_D_Q_by_dose"] = metrics.get("mean_D_Q_by_dose")
        headline["mean_FAP_by_dose"] = metrics.get("mean_FAP_by_dose")
        headline["mean_CP_t_by_dose"] = metrics.get("mean_CP_t_by_dose")
        headline["failure_space_max_CP_t_by_dose"] = metrics.get("max_CP_t_by_dose")
    elif artifact.name == "failure_space_manifest":
        headline["failure_space_manifest_hash"] = metrics.get("manifest_hash")
    elif artifact.name == "failure_space_export_summary":
        headline["failure_space_export_status"] = metrics.get("status")
        headline["failure_space_step_table_rows"] = metrics.get("step_row_count")
        headline["failure_space_trajectory_curve_rows"] = metrics.get("trajectory_curve_row_count")
        headline["failure_mode_count_rows"] = metrics.get("failure_mode_count_rows")
        headline["confidence_count_rows"] = metrics.get("confidence_count_rows")
        headline["dose_metric_rows"] = metrics.get("dose_metric_rows")
        headline["generated_plot_files"] = metrics.get("generated_plot_files")
        headline["skipped_plot_files"] = metrics.get("skipped_plot_files")
        headline["plot_generation_status"] = metrics.get("plot_generation_status")
        headline["plot_skip_reason"] = metrics.get("plot_skip_reason")
    elif artifact.name == "failure_space_export_manifest":
        headline["failure_space_export_manifest_hash"] = metrics.get("manifest_hash")


def _key_result(name: str, metrics: dict[str, Any]) -> str:
    if name == "trajectory_summary":
        return f"trajectories={_value(metrics.get('trajectory_count'))}; steps={_value(metrics.get('step_count'))}"
    if name == "cp_summary":
        return f"max_cp_t={_value(metrics.get('max_cp_t'))}; block_crossings={_value(metrics.get('crossed_block_count'))}"
    if name == "dose_ladder_summary":
        return (
            f"levels={_value(metrics.get('dose_level_count'))}; "
            f"first_block={_value(metrics.get('first_block_dose_level'))}"
        )
    if name == "self_audit_summary":
        return f"false_compliance_lift={_value(metrics.get('false_compliance_lift'))}"
    if name == "fast_path_summary":
        return (
            f"slowest_p99={_value(metrics.get('slowest_operation_by_p99'))}; "
            f"llm_calls={_value(metrics.get('heavy_llm_calls_per_step'))}"
        )
    if name == "drift_halflife_summary":
        return (
            f"conditions={_value(metrics.get('condition_count'))}; "
            f"crossing_lift={_value(metrics.get('halflife_crossing_lift'))}"
        )
    if name == "failure_space_summary":
        return (
            f"doses={_value(metrics.get('dose_level_count'))}; "
            f"steps={_value(metrics.get('step_count'))}; "
            f"low_confidence={_value(metrics.get('low_confidence_step_count'))}"
        )
    if name == "failure_space_export_summary":
        return (
            f"status={_value(metrics.get('status'))}; "
            f"step_rows={_value(metrics.get('step_row_count'))}; "
            f"plots={_value(metrics.get('plot_generation_status'))}"
        )
    if "data_row_count" in metrics:
        return f"rows={_value(metrics.get('data_row_count'))}"
    if "manifest_hash" in metrics:
        return f"manifest={_value(metrics.get('manifest_hash'))}"
    if "line_count" in metrics:
        return f"lines={_value(metrics.get('line_count'))}"
    return "available"


def _strengths(metrics: dict[str, Any]) -> list[str]:
    strengths = [
        "HELIX now has deterministic trajectory-level infrastructure.",
        "CP_t can be measured over multi-step trajectories.",
        "Simulated self-audit behavior can be compared against external CP evidence.",
        "Deterministic fast-path scoring does not require per-step LLM calls in the current microbenchmark.",
    ]
    if metrics.get("monotonic_max_cp_t") is True and metrics.get("monotonic_mean_final_cp_t") is True:
        strengths.append("Fixed-config perturbation dose increases CP_t monotonically in the current fixtures.")
    if metrics.get("false_compliance_lift") is not None:
        strengths.append("Self-audit false-compliance lift is measured for contaminated trajectory conditions.")
    if metrics.get("halflife_crossing_lift") is not None:
        strengths.append("HELIX now has a reproducible drift-halflife scaffold showing clean vs contaminated trajectory separation under a fixed deterministic proxy.")
    if metrics.get("dominant_failure_mode_counts") is not None:
        strengths.append("HELIX now has a reproducible trajectory diagnostic space that separates clean, contradiction-accumulation, objective-drift, and compound-failure regions under pre-registered deterministic rules.")
        strengths.append("HELIX records low-confidence and unclassified regions rather than forcing every step into a confident failure label.")
    if metrics.get("failure_space_export_status") is not None:
        strengths.append("HELIX failure-space evidence can be exported into reproducible table/figure inputs without recomputing or altering the underlying metrics.")
    return strengths


def _limitations(missing_artifacts: list[str]) -> list[str]:
    limitations = [
        "This rollup reads existing v8 artifacts only; it does not generate new evidence.",
        "Controlled deterministic evidence must not be described as production-proven deployment evidence.",
    ]
    if missing_artifacts:
        limitations.append("One or more expected artifacts or configs are missing or invalid and are listed as next actions.")
    return limitations


def _recommended_next_steps() -> list[str]:
    return [
        "Run optional matplotlib-enabled plot generation, if needed.",
        "Create a human-audited trajectory sample.",
        "Add a semantic slow-path sampled drift extractor.",
        "Build a v9 live/mock agent-loop adapter.",
        "Add objective curvature only after failure-space validation.",
    ]


def _executive_summary(summary: TrajectoryEvidenceRollupSummary) -> str:
    if summary.status == "complete":
        return (
            "All expected v8 trajectory artifacts and configs were available and hashed. "
            "This rollup summarizes existing trajectory-level evidence without creating new evidence."
        )
    return (
        f"The rollup is partial: {summary.available_artifact_count} of {summary.artifact_count} expected "
        "v8 artifacts/configs were available and hashed. Missing items are listed explicitly; no absent metrics are fabricated."
    )


def _empty_headline_metrics() -> dict[str, Any]:
    return {key: None for key in HEADLINE_METRIC_KEYS}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_jsonl_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _count_text_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _max_cp_by_dose(dose_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        str(item.get("dose_level")): item.get("max_cp_t")
        for item in dose_results
    }


def _plot_skip_reason(data: dict[str, Any]) -> str | None:
    warnings = data.get("warnings") or []
    for warning in warnings:
        if isinstance(warning, str) and warning.startswith("plot_generation_status:"):
            return warning.split(":", 1)[1]
    plot_generation_status = data.get("plot_generation_status")
    if isinstance(plot_generation_status, str) and plot_generation_status.startswith("skipped"):
        return plot_generation_status
    return None


def _value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)

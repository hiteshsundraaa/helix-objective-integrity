from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_EVIDENCE_ARTIFACTS: dict[str, str] = {
    "v5_acceptance": "outputs/v5_acceptance/v5_acceptance_summary.json",
    "hostile_baselines": "outputs/hostile_baselines/v5/hostile_baseline_summary.json",
    "adjacent_rule_analysis": "outputs/adjacent_rule_analysis/v5_google_flash/adjacent_rule_summary.json",
    "diversity_v5_main": "outputs/dataset_diversity/v5_main/diversity_summary.json",
    "diversity_v5_adjacent": "outputs/dataset_diversity/v5_adjacent/diversity_summary.json",
    "asymmetric_trace_analysis": "outputs/asymmetric_trace_analysis/v5/asymmetric_trace_summary.json",
    "threshold_sensitivity": "outputs/threshold_sensitivity/v6/threshold_sensitivity_summary.json",
    "paraphrase_analysis": "outputs/paraphrase_analysis/v6_google_flash/paraphrase_summary.json",
    "multi_provider_replay": "outputs/multi_provider_replay/v6_paraphrase_with_negative_control/multi_provider_replay_summary.json",
    "trace_noise_analysis": "outputs/trace_noise_analysis/v6_google_flash/trace_noise_summary.json",
}


HEADLINE_METRIC_KEYS = [
    "v5_acceptance_result",
    "v5_pairs",
    "v5_receipt_count",
    "v5_manifest_validation_issues",
    "hostile_helix_tpr",
    "hostile_helix_fpr",
    "hostile_matched_random_tpr",
    "hostile_matched_random_fpr",
    "hostile_selectivity_delta_vs_matched_random",
    "adjacent_wrong_rule_citation_rate",
    "adjacent_governing_rule_citation_rate",
    "diversity_v5_main_effective_template_n",
    "diversity_v5_main_max_cluster_fraction",
    "asymmetric_detection_gain",
    "threshold_sweep_points",
    "threshold_helix_beats_matched_random_fraction",
    "paraphrase_main_tpr",
    "paraphrase_main_fpr",
    "paraphrase_exact_citation_rate",
    "multi_provider_count",
    "multi_provider_clean_targets_met",
    "multi_provider_failed_targets",
    "trace_noise_main_tpr",
    "trace_noise_main_fpr",
    "trace_noise_stale_rule_citation_rate",
    "trace_noise_active_rule_citation_rate",
]


class EvidenceArtifactStatus(BaseModel):
    name: str
    status: str
    path: str
    artifact_hash: str | None = None
    key_metrics: dict[str, Any] = Field(default_factory=dict)
    key_result: str = ""
    error: str | None = None


class EvidenceRollupSummary(BaseModel):
    status: str
    generated_at: str
    artifact_count: int
    available_artifact_count: int
    missing_artifact_count: int
    artifact_hashes: dict[str, str]
    headline_metrics: dict[str, Any]
    strengths: list[str]
    limitations: list[str]
    missing_artifacts: list[str]
    recommended_next_steps: list[str]
    artifacts: list[EvidenceArtifactStatus]

    def to_markdown(self) -> str:
        lines = [
            "# HELIX v6 Controlled Evidence Rollup",
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
                "## Headline Results",
                "",
                "### 1. v5 Split-View Acceptance",
                "",
                f"- result: `{_value(self.headline_metrics['v5_acceptance_result'])}`",
                f"- main pairs: `{_value(self.headline_metrics['v5_pairs'])}`",
                f"- receipt count: `{_value(self.headline_metrics['v5_receipt_count'])}`",
                "",
                "### 2. Receipt/Manifest Integrity",
                "",
                f"- manifest validation issues: `{_value(self.headline_metrics['v5_manifest_validation_issues'])}`",
                "",
                "### 3. Hostile Baselines",
                "",
                f"- HELIX TPR/FPR: `{_value(self.headline_metrics['hostile_helix_tpr'])}` / `{_value(self.headline_metrics['hostile_helix_fpr'])}`",
                f"- matched-random TPR/FPR: `{_value(self.headline_metrics['hostile_matched_random_tpr'])}` / `{_value(self.headline_metrics['hostile_matched_random_fpr'])}`",
                f"- selectivity delta vs matched random: `{_value(self.headline_metrics['hostile_selectivity_delta_vs_matched_random'])}`",
                "",
                "### 4. Adjacent-Rule Citation Controls",
                "",
                f"- wrong-rule citation rate: `{_value(self.headline_metrics['adjacent_wrong_rule_citation_rate'])}`",
                f"- governing-rule citation rate: `{_value(self.headline_metrics['adjacent_governing_rule_citation_rate'])}`",
                "",
                "### 5. Dataset Diversity / Effective-N",
                "",
                f"- v5 main effective template N: `{_value(self.headline_metrics['diversity_v5_main_effective_template_n'])}`",
                f"- v5 main max cluster fraction: `{_value(self.headline_metrics['diversity_v5_main_max_cluster_fraction'])}`",
                "",
                "### 6. Asymmetric Trace-vs-Self-Report",
                "",
                f"- asymmetric detection gain: `{_value(self.headline_metrics['asymmetric_detection_gain'])}`",
                "",
                "### 7. Threshold Sensitivity",
                "",
                f"- sweep points: `{_value(self.headline_metrics['threshold_sweep_points'])}`",
                f"- HELIX beats matched-random fraction: `{_value(self.headline_metrics['threshold_helix_beats_matched_random_fraction'])}`",
                "",
                "### 8. Paraphrase Robustness",
                "",
                f"- TPR/FPR: `{_value(self.headline_metrics['paraphrase_main_tpr'])}` / `{_value(self.headline_metrics['paraphrase_main_fpr'])}`",
                f"- exact citation rate: `{_value(self.headline_metrics['paraphrase_exact_citation_rate'])}`",
                "",
                "### 9. Multi-Provider Replay + Degraded Control",
                "",
                f"- provider replay count: `{_value(self.headline_metrics['multi_provider_count'])}`",
                f"- clean targets met: `{_value(self.headline_metrics['multi_provider_clean_targets_met'])}`",
                f"- failed targets: `{_value(self.headline_metrics['multi_provider_failed_targets'])}`",
                "",
                "### 10. Trace-Noise / Stale-Rule Robustness",
                "",
                f"- TPR/FPR: `{_value(self.headline_metrics['trace_noise_main_tpr'])}` / `{_value(self.headline_metrics['trace_noise_main_fpr'])}`",
                f"- active-rule citation rate: `{_value(self.headline_metrics['trace_noise_active_rule_citation_rate'])}`",
                f"- stale-rule citation rate: `{_value(self.headline_metrics['trace_noise_stale_rule_citation_rate'])}`",
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
                "- No live production agent integration yet.",
                "- Most protocols replay frozen normalized judgments rather than making live API calls.",
                "- The suites are controlled synthetic benchmarks, not full enterprise workloads.",
                "- No latency or runtime overhead measurement yet.",
                "- Provider diversity is still limited.",
                "- No human-audited external dataset has been incorporated yet.",
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


def collect_v6_evidence_rollup(
    *,
    artifact_paths: dict[str, str | Path] | None = None,
    generated_at: str | None = None,
) -> EvidenceRollupSummary:
    paths = {
        name: str(path)
        for name, path in (artifact_paths or DEFAULT_EVIDENCE_ARTIFACTS).items()
    }
    artifacts = [_collect_artifact(name, path) for name, path in paths.items()]
    headline_metrics = _empty_headline_metrics()
    for artifact in artifacts:
        _merge_headline_metrics(headline_metrics, artifact)

    missing_artifacts = [
        f"{artifact.name}: {artifact.path}"
        for artifact in artifacts
        if artifact.status != "available"
    ]
    artifact_hashes = {
        artifact.name: artifact.artifact_hash
        for artifact in artifacts
        if artifact.artifact_hash is not None
    }
    available_count = sum(artifact.status == "available" for artifact in artifacts)
    missing_count = len(artifacts) - available_count
    summary_status = "complete" if missing_count == 0 else "partial"
    return EvidenceRollupSummary(
        status=summary_status,
        generated_at=generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        artifact_count=len(artifacts),
        available_artifact_count=available_count,
        missing_artifact_count=missing_count,
        artifact_hashes=artifact_hashes,
        headline_metrics=headline_metrics,
        strengths=_strengths(headline_metrics),
        limitations=_limitations(missing_artifacts),
        missing_artifacts=missing_artifacts,
        recommended_next_steps=_recommended_next_steps(),
        artifacts=artifacts,
    )


def write_v6_evidence_rollup_outputs(summary: EvidenceRollupSummary, out_dir: str | Path) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary_path = target / "helix_v6_evidence_summary.json"
    report_path = target / "helix_v6_evidence_report.md"
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


def _collect_artifact(name: str, path: str | Path) -> EvidenceArtifactStatus:
    target = Path(path)
    if not target.exists():
        return EvidenceArtifactStatus(
            name=name,
            status="missing",
            path=str(target),
            key_result="missing",
        )

    artifact_hash = stable_file_hash(target)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return EvidenceArtifactStatus(
            name=name,
            status="invalid",
            path=str(target),
            artifact_hash=artifact_hash,
            key_result="invalid JSON",
            error=str(exc),
        )

    key_metrics = _extract_key_metrics(name, data)
    return EvidenceArtifactStatus(
        name=name,
        status="available",
        path=str(target),
        artifact_hash=artifact_hash,
        key_metrics=key_metrics,
        key_result=_key_result(name, key_metrics),
    )


def _extract_key_metrics(name: str, data: dict[str, Any]) -> dict[str, Any]:
    if name == "v5_acceptance":
        return {
            "result": data.get("result"),
            "main_pair_count": data.get("main_pair_count"),
            "receipt_count": data.get("receipt_count"),
            "manifest_validation_issue_count": data.get("manifest_validation_issue_count"),
            "receipt_validation_issue_count": data.get("receipt_validation_issue_count"),
        }
    if name == "hostile_baselines":
        helix = _nested(data, ["baselines", "helix_domain_gated", "main"])
        matched = _nested(data, ["baselines", "matched_friction_random", "main"])
        matched_summary = _nested(data, ["baselines", "matched_friction_random"])
        return {
            "helix_tpr": _get(helix, "true_positive_rate"),
            "helix_fpr": _get(helix, "false_positive_rate"),
            "matched_random_tpr": _get(matched, "true_positive_rate"),
            "matched_random_fpr": _get(matched, "false_positive_rate"),
            "selectivity_delta_vs_matched_random": _get(matched_summary, "selectivity_delta_vs_helix"),
        }
    if name == "adjacent_rule_analysis":
        return {
            "wrong_rule_citation_rate": data.get("wrong_rule_citation_rate"),
            "governing_rule_citation_rate": data.get("governing_rule_citation_rate"),
            "adjacent_rule_overblock_rate": data.get("adjacent_rule_overblock_rate"),
            "status": data.get("status"),
        }
    if name in {"diversity_v5_main", "diversity_v5_adjacent"}:
        return {
            "effective_template_n": data.get("effective_template_n"),
            "max_template_cluster_fraction": data.get("max_template_cluster_fraction"),
            "acceptance_status": data.get("acceptance_status"),
            "failed_targets": data.get("failed_targets"),
        }
    if name == "asymmetric_trace_analysis":
        return {
            "asymmetric_detection_gain": data.get("asymmetric_detection_gain"),
            "trace_based_detection_rate": data.get("trace_based_detection_rate"),
            "self_report_detection_rate": data.get("self_report_detection_rate"),
        }
    if name == "threshold_sensitivity":
        return {
            "sweep_point_count": data.get("sweep_point_count"),
            "helix_beats_matched_random_fraction": data.get("helix_beats_matched_random_fraction"),
            "mean_selectivity_delta_vs_matched_random": data.get("mean_selectivity_delta_vs_matched_random"),
        }
    if name == "paraphrase_analysis":
        return {
            "main_tpr": data.get("main_tpr"),
            "main_fpr": data.get("main_fpr"),
            "exact_citation_rate": data.get("exact_citation_rate"),
            "invalid_citation_rate": data.get("invalid_citation_rate"),
            "status": data.get("status"),
        }
    if name == "multi_provider_replay":
        return {
            "provider_count": data.get("provider_count"),
            "providers_meeting_clean_targets": data.get("providers_meeting_clean_targets"),
            "providers_failing_clean_targets": data.get("providers_failing_clean_targets"),
            "complete_provider_count": data.get("complete_provider_count"),
        }
    if name == "trace_noise_analysis":
        return {
            "main_tpr": data.get("main_tpr"),
            "main_fpr": data.get("main_fpr"),
            "stale_rule_citation_rate": data.get("stale_rule_citation_rate"),
            "active_rule_citation_rate": data.get("active_rule_citation_rate"),
            "status": data.get("status"),
        }
    return {}


def _merge_headline_metrics(headline: dict[str, Any], artifact: EvidenceArtifactStatus) -> None:
    metrics = artifact.key_metrics
    if artifact.name == "v5_acceptance":
        headline["v5_acceptance_result"] = metrics.get("result")
        headline["v5_pairs"] = metrics.get("main_pair_count")
        headline["v5_receipt_count"] = metrics.get("receipt_count")
        headline["v5_manifest_validation_issues"] = metrics.get("manifest_validation_issue_count")
    elif artifact.name == "hostile_baselines":
        headline["hostile_helix_tpr"] = metrics.get("helix_tpr")
        headline["hostile_helix_fpr"] = metrics.get("helix_fpr")
        headline["hostile_matched_random_tpr"] = metrics.get("matched_random_tpr")
        headline["hostile_matched_random_fpr"] = metrics.get("matched_random_fpr")
        headline["hostile_selectivity_delta_vs_matched_random"] = metrics.get("selectivity_delta_vs_matched_random")
    elif artifact.name == "adjacent_rule_analysis":
        headline["adjacent_wrong_rule_citation_rate"] = metrics.get("wrong_rule_citation_rate")
        headline["adjacent_governing_rule_citation_rate"] = metrics.get("governing_rule_citation_rate")
    elif artifact.name == "diversity_v5_main":
        headline["diversity_v5_main_effective_template_n"] = metrics.get("effective_template_n")
        headline["diversity_v5_main_max_cluster_fraction"] = metrics.get("max_template_cluster_fraction")
    elif artifact.name == "asymmetric_trace_analysis":
        headline["asymmetric_detection_gain"] = metrics.get("asymmetric_detection_gain")
    elif artifact.name == "threshold_sensitivity":
        headline["threshold_sweep_points"] = metrics.get("sweep_point_count")
        headline["threshold_helix_beats_matched_random_fraction"] = metrics.get("helix_beats_matched_random_fraction")
    elif artifact.name == "paraphrase_analysis":
        headline["paraphrase_main_tpr"] = metrics.get("main_tpr")
        headline["paraphrase_main_fpr"] = metrics.get("main_fpr")
        headline["paraphrase_exact_citation_rate"] = metrics.get("exact_citation_rate")
    elif artifact.name == "multi_provider_replay":
        headline["multi_provider_count"] = metrics.get("provider_count")
        headline["multi_provider_clean_targets_met"] = metrics.get("providers_meeting_clean_targets")
        headline["multi_provider_failed_targets"] = metrics.get("providers_failing_clean_targets")
    elif artifact.name == "trace_noise_analysis":
        headline["trace_noise_main_tpr"] = metrics.get("main_tpr")
        headline["trace_noise_main_fpr"] = metrics.get("main_fpr")
        headline["trace_noise_stale_rule_citation_rate"] = metrics.get("stale_rule_citation_rate")
        headline["trace_noise_active_rule_citation_rate"] = metrics.get("active_rule_citation_rate")


def _key_result(name: str, metrics: dict[str, Any]) -> str:
    if name == "v5_acceptance":
        return f"result={metrics.get('result')}; receipts={metrics.get('receipt_count')}"
    if name == "hostile_baselines":
        return (
            f"helix_tpr={_value(metrics.get('helix_tpr'))}; "
            f"matched_random_tpr={_value(metrics.get('matched_random_tpr'))}"
        )
    if name == "adjacent_rule_analysis":
        return (
            f"wrong_rule={_value(metrics.get('wrong_rule_citation_rate'))}; "
            f"governing={_value(metrics.get('governing_rule_citation_rate'))}"
        )
    if name.startswith("diversity_"):
        return (
            f"effective_template_n={_value(metrics.get('effective_template_n'))}; "
            f"status={_value(metrics.get('acceptance_status'))}"
        )
    if name == "asymmetric_trace_analysis":
        return f"detection_gain={_value(metrics.get('asymmetric_detection_gain'))}"
    if name == "threshold_sensitivity":
        return (
            f"sweep_points={_value(metrics.get('sweep_point_count'))}; "
            f"beats_random={_value(metrics.get('helix_beats_matched_random_fraction'))}"
        )
    if name == "paraphrase_analysis":
        return (
            f"tpr={_value(metrics.get('main_tpr'))}; "
            f"exact_citation={_value(metrics.get('exact_citation_rate'))}"
        )
    if name == "multi_provider_replay":
        return (
            f"providers={_value(metrics.get('provider_count'))}; "
            f"failing={_value(metrics.get('providers_failing_clean_targets'))}"
        )
    if name == "trace_noise_analysis":
        return (
            f"tpr={_value(metrics.get('main_tpr'))}; "
            f"stale_citation={_value(metrics.get('stale_rule_citation_rate'))}"
        )
    return "available"


def _strengths(metrics: dict[str, Any]) -> list[str]:
    strengths = [
        "Controlled evidence supports exact-citation grounding when exact citations are present and validated.",
        "Controlled evidence supports deterministic relevance gating and reason-coded receipt validation in the v5 split-view stack.",
        "Controlled evidence supports provider-normalized replay: provider/model names are metadata and weak normalized judgments remain visible.",
        "Controlled evidence supports trace-based evaluation over a self-report baseline in the asymmetric trace protocol.",
    ]
    if metrics.get("hostile_selectivity_delta_vs_matched_random") is not None:
        strengths.append("Hostile-baseline evidence reports selectivity against a matched-friction random blocker.")
    if metrics.get("trace_noise_stale_rule_citation_rate") is not None:
        strengths.append("Trace-noise evidence reports whether accepted blocks stay grounded to the active rule rather than stale context.")
    return strengths


def _limitations(missing_artifacts: list[str]) -> list[str]:
    limitations = [
        "This rollup reads existing artifacts only; it does not regenerate judgments or create new evidence.",
        "Controlled benchmark evidence should not be described as production-proven deployment evidence.",
    ]
    if missing_artifacts:
        limitations.append("One or more expected artifacts are missing or invalid and are listed as next actions.")
    return limitations


def _recommended_next_steps() -> list[str]:
    return [
        "Build the v7 live mock-agent harness.",
        "Add one more real provider replay if available.",
        "Create a human-audited sample slice.",
        "Measure runtime receipt emission and latency overhead.",
        "Draft OAuth/IAM positioning for the Agent Authorization Receipts product primitive.",
    ]


def _executive_summary(summary: EvidenceRollupSummary) -> str:
    if summary.status == "complete":
        return (
            "All expected controlled evidence artifacts were available and hashed. "
            "The rollup summarizes the current HELIX v5/v6 evidence stack without creating new benchmark evidence."
        )
    return (
        f"The rollup is partial: {summary.available_artifact_count} of {summary.artifact_count} expected "
        "controlled evidence artifacts were available and hashed. Missing artifacts are listed explicitly; "
        "no absent metrics are fabricated."
    )


def _empty_headline_metrics() -> dict[str, Any]:
    return {key: None for key in HEADLINE_METRIC_KEYS}


def _nested(data: dict[str, Any], keys: list[str]) -> dict[str, Any] | None:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current if isinstance(current, dict) else None


def _get(data: dict[str, Any] | None, key: str) -> Any:
    if data is None:
        return None
    return data.get(key)


def _value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)

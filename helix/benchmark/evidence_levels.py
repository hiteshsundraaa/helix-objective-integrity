from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


EVIDENCE_LEVEL_DEFINITIONS = {
    0: "generated_only",
    1: "protocol_completed",
    2: "receipts_or_manifest_validated",
    3: "hostile_or_degraded_controls_passed",
    4: "integrity_audit_passed",
    5: "human_external_or_live_validated",
}

DEFAULT_EVIDENCE_LEVEL_ARTIFACTS = {
    "v5_acceptance": "outputs/v5_acceptance/v5_acceptance_summary.json",
    "v5_manifest": "outputs/v5_acceptance/paired_split_view_analysis/benchmark_run_manifest.json",
    "v5_hostile_baselines": "outputs/hostile_baselines/v5/hostile_baseline_summary.json",
    "v5_integrity": (
        "outputs/benchmark_integrity/v5_split_view_acceptance/integrity_report.json"
    ),
    "v6_paraphrase": "outputs/paraphrase_analysis/v6_google_flash/paraphrase_summary.json",
    "v6_multi_provider": (
        "outputs/multi_provider_replay/v6_paraphrase_with_negative_control/"
        "multi_provider_replay_summary.json"
    ),
    "v6_paraphrase_integrity": (
        "outputs/benchmark_integrity/v6_paraphrase_google_flash/integrity_report.json"
    ),
    "v8_trajectory_rollup": (
        "outputs/v8_trajectory_evidence_rollup/helix_v8_trajectory_summary.json"
    ),
    "v9_mock_loop": "outputs/v9_mock_agent_loop/basic/mock_agent_loop_summary.json",
    "v9_mock_loop_manifest": "outputs/v9_mock_agent_loop/basic/mock_agent_loop_manifest.json",
}


class EvidenceLevelRecord(BaseModel):
    protocol_name: str
    evidence_level: int
    evidence_level_name: str
    protocol_completed: bool
    receipts_or_manifest_validated: bool
    hostile_or_degraded_controls_passed: bool
    integrity_audit_status: str
    integrity_hash: str | None = None
    integrity_hard_issues: list[str] = Field(default_factory=list)
    integrity_warnings: list[str] = Field(default_factory=list)
    integrity_metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_paths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class BenchmarkEvidenceLevelsSummary(BaseModel):
    protocol_count: int
    max_assigned_level: int
    level_counts: dict[str, int]
    failed_or_missing_integrity_count: int
    records: list[EvidenceLevelRecord]

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Benchmark Evidence Levels",
            "",
            "## Evidence Level Definitions",
            "",
        ]
        lines.extend(
            f"- Level {level}: `{name}`"
            for level, name in EVIDENCE_LEVEL_DEFINITIONS.items()
        )
        lines.extend(
            [
                "",
                "Level 5 is defined for governance completeness but is not assigned in this patch.",
                "",
                "## Protocol Evidence Table",
                "",
                "| Protocol | Level | Protocol complete | Receipts/manifest | "
                "Hostile/degraded controls | Integrity audit |",
                "|---|---:|---:|---:|---:|---|",
            ]
        )
        for record in self.records:
            lines.append(
                f"| `{record.protocol_name}` | `{record.evidence_level}` | "
                f"`{str(record.protocol_completed).lower()}` | "
                f"`{str(record.receipts_or_manifest_validated).lower()}` | "
                f"`{str(record.hostile_or_degraded_controls_passed).lower()}` | "
                f"`{record.integrity_audit_status}` |"
            )
        lines.extend(["", "## Failed or Missing Integrity Audits", ""])
        affected = [
            record
            for record in self.records
            if record.integrity_audit_status != "passed"
        ]
        if not affected:
            lines.append("- None")
        for record in affected:
            issues = ", ".join(record.integrity_hard_issues) or "audit missing"
            warnings = ", ".join(record.integrity_warnings) or "none"
            lines.append(
                f"- `{record.protocol_name}`: status `{record.integrity_audit_status}`; "
                f"issues `{issues}`; warnings `{warnings}`; evidence capped at Level "
                f"`{record.evidence_level}`."
            )
        lines.extend(
            [
                "",
                "## What This Supports",
                "",
                "- Evidence claims can be capped according to completed protocols, "
                "validated artifacts, controls, and integrity audits.",
                "- Failed integrity audits remain visible instead of being overwritten "
                "by benchmark performance.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- Evidence levels are governance labels, not new empirical evidence.",
                "- Level 4 requires an integrity audit pass but still does not prove "
                "external validity.",
                "- No protocol is assigned Level 5 in this patch.",
                "",
                "## Recommended Next Steps",
                "",
                "1. Audit additional benchmark protocols using the pre-registered "
                "integrity config.",
                "2. Add human-audited external samples before assigning Level 5.",
                "3. Preserve historical failed audit hashes alongside future reruns.",
            ]
        )
        return "\n".join(lines)


def assign_evidence_level(
    *,
    protocol_name: str,
    protocol_completed: bool,
    receipts_or_manifest_validated: bool,
    hostile_or_degraded_controls_passed: bool,
    integrity_report: dict[str, Any] | None,
    artifact_paths: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
) -> EvidenceLevelRecord:
    level = 0
    if protocol_completed:
        level = max(level, 1)
    if receipts_or_manifest_validated:
        level = max(level, 2)
    if hostile_or_degraded_controls_passed:
        level = max(level, 3)

    integrity_status = "missing"
    integrity_hash: str | None = None
    hard_issues: list[str] = []
    warnings: list[str] = []
    integrity_metrics = dict(metrics or {})
    if integrity_report is not None:
        integrity_status = "passed" if integrity_report.get("integrity_passed") else "failed"
        integrity_hash = integrity_report.get("integrity_hash")
        hard_issues = list(integrity_report.get("integrity_issues") or [])
        warnings = list(integrity_report.get("integrity_warnings") or [])
        integrity_metrics.update(
            {
                key: integrity_report.get(key)
                for key in (
                    "score_collapse_detected",
                    "token_overlap_mean",
                    "selectivity_delta_vs_shuffled",
                    "selectivity_delta_vs_random",
                )
            }
        )
        if integrity_report.get("integrity_passed"):
            level = max(level, 4)

    limitations: list[str] = []
    if integrity_status == "failed":
        level = min(level, 3)
        limitations.append("Failed integrity audit caps reportable evidence at Level 3.")
    elif integrity_status == "missing":
        level = min(level, 3)
        limitations.append("Missing integrity audit caps reportable evidence at Level 3.")
    if "score_collapse_detected" in hard_issues:
        limitations.append("Score collapse remains a hard benchmark-integrity limitation.")
    if "high_overlap_cases_detected" in warnings:
        limitations.append("High-overlap cases remain a documented integrity limitation.")
    if level >= 5:
        level = 4
        limitations.append("Level 5 assignment is disabled in this patch.")

    return EvidenceLevelRecord(
        protocol_name=protocol_name,
        evidence_level=level,
        evidence_level_name=EVIDENCE_LEVEL_DEFINITIONS[level],
        protocol_completed=protocol_completed,
        receipts_or_manifest_validated=receipts_or_manifest_validated,
        hostile_or_degraded_controls_passed=hostile_or_degraded_controls_passed,
        integrity_audit_status=integrity_status,
        integrity_hash=integrity_hash,
        integrity_hard_issues=hard_issues,
        integrity_warnings=warnings,
        integrity_metrics=integrity_metrics,
        artifact_paths=list(artifact_paths or []),
        limitations=limitations,
    )


def collect_benchmark_evidence_levels(
    artifact_paths: dict[str, str | Path] | None = None,
) -> BenchmarkEvidenceLevelsSummary:
    paths = {
        key: Path(value)
        for key, value in (artifact_paths or DEFAULT_EVIDENCE_LEVEL_ARTIFACTS).items()
    }
    v5 = _read_optional_json(paths.get("v5_acceptance"))
    hostile = _read_optional_json(paths.get("v5_hostile_baselines"))
    v5_integrity = _read_optional_json(paths.get("v5_integrity"))
    paraphrase = _read_optional_json(paths.get("v6_paraphrase"))
    multi_provider = _read_optional_json(paths.get("v6_multi_provider"))
    integrity = _read_optional_json(paths.get("v6_paraphrase_integrity"))
    v8 = _read_optional_json(paths.get("v8_trajectory_rollup"))
    v9 = _read_optional_json(paths.get("v9_mock_loop"))

    degraded_control_passed = bool(
        multi_provider
        and multi_provider.get("providers_meeting_clean_targets")
        and multi_provider.get("providers_failing_clean_targets")
    )
    records = [
        assign_evidence_level(
            protocol_name="v5_split_view_acceptance",
            protocol_completed=bool(v5 and v5.get("result") == "PASS"),
            receipts_or_manifest_validated=bool(
                v5
                and v5.get("receipt_count") == v5.get("case_count")
                and v5.get("receipt_validation_issue_count") == 0
                and v5.get("manifest_validation_issue_count") == 0
                and _exists(paths.get("v5_manifest"))
            ),
            hostile_or_degraded_controls_passed=_hostile_baselines_passed(hostile),
            integrity_report=v5_integrity,
            artifact_paths=_existing_path_strings(
                paths,
                "v5_acceptance",
                "v5_manifest",
                "v5_hostile_baselines",
                "v5_integrity",
            ),
        ),
        assign_evidence_level(
            protocol_name="v6_paraphrase_google_flash",
            protocol_completed=bool(paraphrase and paraphrase.get("status") == "complete"),
            receipts_or_manifest_validated=False,
            hostile_or_degraded_controls_passed=degraded_control_passed,
            integrity_report=integrity,
            artifact_paths=_existing_path_strings(
                paths, "v6_paraphrase", "v6_multi_provider", "v6_paraphrase_integrity"
            ),
            metrics={
                "main_tpr": paraphrase.get("main_tpr") if paraphrase else None,
                "main_fpr": paraphrase.get("main_fpr") if paraphrase else None,
            },
        ),
        assign_evidence_level(
            protocol_name="v6_multi_provider_with_degraded_control",
            protocol_completed=bool(
                multi_provider and (multi_provider.get("provider_count") or 0) >= 2
            ),
            receipts_or_manifest_validated=False,
            hostile_or_degraded_controls_passed=degraded_control_passed,
            integrity_report=None,
            artifact_paths=_existing_path_strings(paths, "v6_multi_provider"),
        ),
        assign_evidence_level(
            protocol_name="v8_trajectory_evidence_rollup",
            protocol_completed=bool(v8 and v8.get("status") == "complete"),
            receipts_or_manifest_validated=bool(
                v8
                and v8.get("missing_artifact_count") == 0
                and v8.get("config_hashes")
            ),
            hostile_or_degraded_controls_passed=False,
            integrity_report=None,
            artifact_paths=_existing_path_strings(paths, "v8_trajectory_rollup"),
        ),
        assign_evidence_level(
            protocol_name="v9_mock_agent_loop",
            protocol_completed=bool(v9 and (v9.get("receipt_count") or 0) > 0),
            receipts_or_manifest_validated=bool(
                v9
                and v9.get("invalid_receipt_count") == 0
                and v9.get("receipt_count") == v9.get("attempted_tool_calls")
                and _exists(paths.get("v9_mock_loop_manifest"))
            ),
            hostile_or_degraded_controls_passed=False,
            integrity_report=None,
            artifact_paths=_existing_path_strings(
                paths, "v9_mock_loop", "v9_mock_loop_manifest"
            ),
        ),
    ]
    level_counts = {
        str(level): sum(record.evidence_level == level for record in records)
        for level in EVIDENCE_LEVEL_DEFINITIONS
    }
    return BenchmarkEvidenceLevelsSummary(
        protocol_count=len(records),
        max_assigned_level=max((record.evidence_level for record in records), default=0),
        level_counts=level_counts,
        failed_or_missing_integrity_count=sum(
            record.integrity_audit_status != "passed" for record in records
        ),
        records=records,
    )


def write_benchmark_evidence_levels_outputs(
    summary: BenchmarkEvidenceLevelsSummary,
    out_dir: str | Path,
) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "benchmark_evidence_levels.json"
    markdown_path = target / "benchmark_evidence_levels.md"
    json_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")
    return json_path, markdown_path


def _read_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _exists(path: Path | None) -> bool:
    return bool(path and path.exists())


def _existing_path_strings(paths: dict[str, Path], *keys: str) -> list[str]:
    return [
        str(paths[key])
        for key in keys
        if key in paths and paths[key].exists()
    ]


def _hostile_baselines_passed(summary: dict[str, Any] | None) -> bool:
    if not summary:
        return False
    deltas = summary.get("selectivity_delta_vs_baselines") or {}
    matched_random_delta = deltas.get("matched_friction_random")
    return isinstance(matched_random_delta, (int, float)) and matched_random_delta > 0

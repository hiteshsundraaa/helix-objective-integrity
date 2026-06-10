from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import stable_json_hash
from helix.benchmark.v10_live_runner_design_gate import (
    V10LiveRunnerDesignConfig,
    load_v10_live_runner_design_config,
    validate_provider_model_allowed as _validate_live_provider_model_allowed,
)
from helix.benchmark.v10_receipt_chain import V10ReceiptChainSummary


ExecutionMode = Literal["dry_run", "manual_import", "live"]


class V10PilotLevel4CriteriaConfig(BaseModel):
    execution_mode_must_be_live: bool
    normalization_status_required: str
    benchmark_status_required: str
    diagnostics_status_allowed: list[str]
    integrity_passed_required: bool
    score_collapse_detected_required: bool
    generator_independence_required: bool
    receipt_count_must_equal_case_count: bool
    invalid_receipt_count_required: int
    provider_model_must_be_allowed: bool
    raw_output_hash_required_for_live: bool
    level_5_allowed: bool


class V10PilotIntegrityThresholds(BaseModel):
    minimum_score_entropy: float
    maximum_token_overlap_mean: float
    maximum_leakage_rate: float
    maximum_threshold_sensitivity_delta: float
    requires_positive_shuffled_selectivity: bool


class V10PilotReceiptChainConfig(BaseModel):
    hash_algorithm: str
    canonical_json: bool
    required_fields: list[str]
    raw_output_hash_required_for_live: bool
    raw_output_hash_required_for_manual_import: bool
    raw_output_hash_required_for_dry_run: bool


class V10PilotEvidenceAssessmentConfig(BaseModel):
    schema_version: str
    assessment_only: bool
    level_4_requires_live_execution: bool
    level_5_allowed: bool
    allowed_execution_modes: list[str]
    execution_mode_caps: dict[str, int]
    level_4_criteria: V10PilotLevel4CriteriaConfig
    receipt_chain: V10PilotReceiptChainConfig
    integrity_thresholds: V10PilotIntegrityThresholds
    notes: str = ""


class V10Level4CriteriaResults(BaseModel):
    live_execution: bool
    normalization_passed: bool
    benchmark_passed: bool
    diagnostics_passed: bool
    integrity_passed: bool
    score_collapse_clear: bool
    generator_independence_clear: bool
    receipt_chain_complete: bool
    provider_model_allowed: bool
    raw_output_hash_available_if_live: bool
    level_5_not_claimed: bool


class V10PilotEvidenceAssessment(BaseModel):
    schema_version: str = "v10_pilot_evidence_assessment_result_v1"
    run_id: str
    execution_mode: str
    provider: str
    model: str
    case_count: int
    receipt_count: int
    invalid_receipt_count: int
    normalization_status: str | None
    benchmark_status: str | None
    diagnostics_status: str | None
    integrity_passed: bool | None
    score_collapse_detected: bool | None
    generator_independence: bool
    provider_model_allowed: bool
    mechanical_reportability_passed: bool | None
    level_4_criteria_met: bool
    level_4_criteria_results: V10Level4CriteriaResults
    raw_evidence_level_allowed: int | None
    execution_mode_cap: int
    final_evidence_level: int
    level_5_allowed: bool = False
    blocking_issues: list[str] = Field(default_factory=list)
    non_blocking_warnings: list[str] = Field(default_factory=list)
    evidence_level_justification: str
    assessment_hash: str

    def to_markdown(self, *, receipt_chain_summary: V10ReceiptChainSummary | None = None) -> str:
        lines = [
            "# HELIX v10 Pilot Evidence Assessment Report",
            "",
            "## Executive Summary",
            "",
            f"- run_id: `{self.run_id}`",
            f"- execution_mode: `{self.execution_mode}`",
            f"- final_evidence_level: `{self.final_evidence_level}`",
            f"- level_4_criteria_met: `{str(self.level_4_criteria_met).lower()}`",
            f"- level_5_allowed: `{str(self.level_5_allowed).lower()}`",
            f"- assessment_hash: `{self.assessment_hash}`",
            "",
            "## Input Run",
            "",
            f"- provider: `{self.provider}`",
            f"- model: `{self.model}`",
            f"- case_count: `{self.case_count}`",
            f"- receipt_count: `{self.receipt_count}`",
            "",
            "## Execution Mode Cap",
            "",
            f"- execution_mode_cap: `{self.execution_mode_cap}`",
            "- manual imports are capped at Level 3.",
            "- dry runs are capped at Level 2.",
            "- Level 5 false.",
            "",
            "## Receipt Chain Integrity",
            "",
            f"- receipt_chain_complete: `{str(self.level_4_criteria_results.receipt_chain_complete).lower()}`",
            f"- invalid_receipt_count: `{self.invalid_receipt_count}`",
        ]
        if receipt_chain_summary is not None:
            lines.extend(
                [
                    f"- raw_output_hash_available_count: `{receipt_chain_summary.raw_output_hash_available_count}`",
                    f"- raw_output_hash_missing_count: `{receipt_chain_summary.raw_output_hash_missing_count}`",
                    f"- chain_hash: `{receipt_chain_summary.chain_hash}`",
                ]
            )
        lines.extend(
            [
                "",
                "## Normalization / Benchmark / Diagnostics",
                "",
                f"- normalization_status: `{self.normalization_status}`",
                f"- benchmark_status: `{self.benchmark_status}`",
                f"- diagnostics_status: `{self.diagnostics_status}`",
                "",
                "## Integrity and Reportability",
                "",
                f"- integrity_passed: `{self.integrity_passed}`",
                f"- score_collapse_detected: `{self.score_collapse_detected}`",
                f"- mechanical_reportability_passed: `{self.mechanical_reportability_passed}`",
                "",
                "## Level 4 Criteria",
                "",
            ]
        )
        for key, value in self.level_4_criteria_results.model_dump(mode="json").items():
            lines.append(f"- `{key}`: `{str(value).lower()}`")
        lines.extend(
            [
                "",
                "## Final Evidence Level",
                "",
                self.evidence_level_justification,
                "",
                "## Blocking Issues",
                "",
            ]
        )
        if self.blocking_issues:
            lines.extend(f"- `{issue}`" for issue in self.blocking_issues)
        else:
            lines.append("- None.")
        lines.extend(["", "## Non-Blocking Warnings", ""])
        if self.non_blocking_warnings:
            lines.extend(f"- `{warning}`" for warning in self.non_blocking_warnings)
        else:
            lines.append("- None.")
        lines.extend(
            [
                "",
                "## What This Supports",
                "",
                "- This supports independent assessment of v10 pilot artifacts from execution provenance, receipt-chain integrity, and pipeline summaries.",
                "- This supports blocking Level 4 overclaims for dry-run or manual-import artifacts.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- The assessor does not execute providers.",
                "- The assessor does not import raw outputs.",
                "- The assessor does not create Level 4 evidence without live provenance.",
                "- One run does not prove provider consistency.",
                "- Level 5 is not available in v10.15A.",
                "",
                "## Limitations",
                "",
                "- Missing summaries fail closed rather than being inferred as pass.",
                "- Provider/model allowlist status is metadata validation, not provider behavior evidence.",
                "- Manual imports lack locked live-runner provenance.",
            ]
        )
        return "\n".join(lines)


def load_v10_pilot_evidence_assessment_config(
    path: str | Path,
) -> V10PilotEvidenceAssessmentConfig:
    return V10PilotEvidenceAssessmentConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_allowed_provider_model_config(
    path: str | Path = "configs/v10_live_provider_runner_design_gate.json",
) -> V10LiveRunnerDesignConfig:
    return load_v10_live_runner_design_config(path)


def validate_provider_model_allowed(
    provider: str,
    model: str,
    live_design_config: V10LiveRunnerDesignConfig,
) -> bool:
    return _validate_live_provider_model_allowed(
        live_design_config,
        provider,
        model,
    ).valid


def assess_v10_pilot_evidence(
    *,
    run_id: str,
    execution_mode: str,
    provider: str,
    model: str,
    case_count: int,
    receipt_chain_summary: V10ReceiptChainSummary,
    normalization_status: str | None,
    benchmark_status: str | None,
    diagnostics_status: str | None,
    integrity_summary: dict[str, Any] | None,
    reportability_summary: dict[str, Any] | None,
    live_design_config: V10LiveRunnerDesignConfig,
    assessment_config: V10PilotEvidenceAssessmentConfig,
) -> V10PilotEvidenceAssessment:
    provider_allowed = validate_provider_model_allowed(provider, model, live_design_config)
    integrity_payload = integrity_summary or {}
    reportability_payload = reportability_summary or {}
    integrity_passed = _optional_bool(integrity_payload.get("integrity_passed"))
    score_collapse = _optional_bool(integrity_payload.get("score_collapse_detected"))
    generator_independence = bool(integrity_payload.get("generator_independence", True))
    mechanical_reportability = _optional_bool(
        reportability_payload.get("reportability_passed")
    )
    raw_level = _optional_int(reportability_payload.get("evidence_level_allowed"))
    cap = int(assessment_config.execution_mode_caps.get(execution_mode, 0))

    criteria_config = assessment_config.level_4_criteria
    criteria = V10Level4CriteriaResults(
        live_execution=execution_mode == "live",
        normalization_passed=normalization_status == criteria_config.normalization_status_required,
        benchmark_passed=benchmark_status == criteria_config.benchmark_status_required,
        diagnostics_passed=diagnostics_status in set(criteria_config.diagnostics_status_allowed),
        integrity_passed=integrity_passed is True,
        score_collapse_clear=score_collapse is False,
        generator_independence_clear=generator_independence is True,
        receipt_chain_complete=(
            receipt_chain_summary.receipt_chain_complete
            and receipt_chain_summary.invalid_receipt_count == criteria_config.invalid_receipt_count_required
            and receipt_chain_summary.receipt_count == case_count
        ),
        provider_model_allowed=provider_allowed,
        raw_output_hash_available_if_live=(
            execution_mode != "live"
            or receipt_chain_summary.raw_output_hash_available_count == case_count
        ),
        level_5_not_claimed=not assessment_config.level_5_allowed,
    )
    criteria_results = criteria.model_dump(mode="json")
    level_4_met = all(criteria_results.values())
    blocking_issues = _blocking_issues(
        execution_mode=execution_mode,
        criteria=criteria,
        normalization_status=normalization_status,
        benchmark_status=benchmark_status,
        diagnostics_status=diagnostics_status,
        integrity_passed=integrity_passed,
        score_collapse_detected=score_collapse,
        provider_model_allowed=provider_allowed,
        receipt_chain_summary=receipt_chain_summary,
        case_count=case_count,
        assessment_config=assessment_config,
    )
    warnings: list[str] = []
    mechanical_gates = all(
        value
        for key, value in criteria_results.items()
        if key != "live_execution"
    )
    if execution_mode == "manual_import":
        warnings.append("manual_import_lacks_locked_live_runner_provenance")
        if mechanical_gates:
            warnings.append("mechanical_gates_passed_but_manual_import_cap_applied")
    if execution_mode == "dry_run":
        warnings.append("dry_run_not_provider_evidence")
        if mechanical_gates:
            warnings.append("mechanical_gates_passed_but_dry_run_cap_applied")
    if receipt_chain_summary.warnings:
        warnings.extend(receipt_chain_summary.warnings)

    critical_missing = any(
        value is None
        for value in [
            normalization_status,
            benchmark_status,
            diagnostics_status,
            integrity_passed,
            score_collapse,
        ]
    )
    if execution_mode not in set(assessment_config.allowed_execution_modes):
        final_level = 0
    elif critical_missing:
        final_level = 0
    elif level_4_met and execution_mode == "live":
        final_level = 4
    else:
        final_level = min(cap, 3)

    payload = {
        "schema_version": "v10_pilot_evidence_assessment_result_v1",
        "run_id": run_id,
        "execution_mode": execution_mode,
        "provider": provider,
        "model": model,
        "case_count": case_count,
        "receipt_count": receipt_chain_summary.receipt_count,
        "invalid_receipt_count": receipt_chain_summary.invalid_receipt_count,
        "normalization_status": normalization_status,
        "benchmark_status": benchmark_status,
        "diagnostics_status": diagnostics_status,
        "integrity_passed": integrity_passed,
        "score_collapse_detected": score_collapse,
        "generator_independence": generator_independence,
        "provider_model_allowed": provider_allowed,
        "mechanical_reportability_passed": mechanical_reportability,
        "level_4_criteria_met": level_4_met,
        "level_4_criteria_results": criteria.model_dump(mode="json"),
        "raw_evidence_level_allowed": raw_level,
        "execution_mode_cap": cap,
        "final_evidence_level": final_level,
        "level_5_allowed": False,
        "blocking_issues": sorted(set(blocking_issues)),
        "non_blocking_warnings": sorted(set(warnings)),
        "evidence_level_justification": _justification(
            execution_mode=execution_mode,
            final_level=final_level,
            level_4_met=level_4_met,
            critical_missing=critical_missing,
            blocking_issues=blocking_issues,
            cap=cap,
        ),
    }
    return V10PilotEvidenceAssessment(
        **payload,
        assessment_hash=stable_json_hash(payload),
    )


def write_v10_pilot_evidence_assessment(
    assessment: V10PilotEvidenceAssessment,
    out_dir: str | Path,
    *,
    config: V10PilotEvidenceAssessmentConfig | None = None,
    receipt_chain_summary: V10ReceiptChainSummary | None = None,
    generated_at: str | None = None,
) -> dict[str, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    config_path = target / "pilot_evidence_assessment_config.json"
    assessment_path = target / "pilot_evidence_assessment.json"
    report_path = target / "pilot_evidence_report.md"
    if config is not None:
        config_path.write_text(
            json.dumps(
                {
                    "schema_version": "v10_pilot_evidence_assessment_config_snapshot_v1",
                    "generated_at": generated_at
                    or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "config": config.model_dump(mode="json"),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    assessment_path.write_text(
        json.dumps(assessment.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        assessment.to_markdown(receipt_chain_summary=receipt_chain_summary) + "\n",
        encoding="utf-8",
    )
    return {
        "config": config_path,
        "assessment": assessment_path,
        "report": report_path,
    }


def _blocking_issues(
    *,
    execution_mode: str,
    criteria: V10Level4CriteriaResults,
    normalization_status: str | None,
    benchmark_status: str | None,
    diagnostics_status: str | None,
    integrity_passed: bool | None,
    score_collapse_detected: bool | None,
    provider_model_allowed: bool,
    receipt_chain_summary: V10ReceiptChainSummary,
    case_count: int,
    assessment_config: V10PilotEvidenceAssessmentConfig,
) -> list[str]:
    issues: list[str] = []
    if execution_mode not in set(assessment_config.allowed_execution_modes):
        issues.append("unknown_execution_mode")
    if execution_mode != "live":
        issues.append("execution_mode_not_live_blocks_level_4")
    if normalization_status is None:
        issues.append("missing_normalization_status")
    elif not criteria.normalization_passed:
        issues.append("normalization_status_blocks_level_4")
    if benchmark_status is None:
        issues.append("missing_benchmark_status")
    elif not criteria.benchmark_passed:
        issues.append("benchmark_status_blocks_level_4")
    if diagnostics_status is None:
        issues.append("missing_diagnostics_status")
    elif not criteria.diagnostics_passed:
        issues.append("diagnostics_status_blocks_level_4")
    if integrity_passed is None:
        issues.append("missing_integrity_summary")
    elif not integrity_passed:
        issues.append("integrity_failure_blocks_level_4")
    if score_collapse_detected is None:
        issues.append("missing_score_collapse_status")
    elif score_collapse_detected:
        issues.append("score_collapse_blocks_level_4")
    if not criteria.generator_independence_clear:
        issues.append("generator_independence_blocks_level_4")
    if not criteria.receipt_chain_complete:
        issues.append("receipt_chain_incomplete_blocks_level_4")
    if receipt_chain_summary.receipt_count != case_count:
        issues.append("receipt_count_mismatch_blocks_level_4")
    if receipt_chain_summary.invalid_receipt_count > 0:
        issues.append("invalid_receipts_block_level_4")
    if not provider_model_allowed:
        issues.append("provider_model_not_allowed_blocks_level_4")
    if not criteria.raw_output_hash_available_if_live:
        issues.append("missing_raw_output_hash_for_live_blocks_level_4")
    if assessment_config.level_5_allowed:
        issues.append("level_5_claim_not_allowed")
    return issues


def _justification(
    *,
    execution_mode: str,
    final_level: int,
    level_4_met: bool,
    critical_missing: bool,
    blocking_issues: list[str],
    cap: int,
) -> str:
    if critical_missing:
        return "Evidence level is 0 because one or more required summaries/statuses are missing; the assessor fails closed."
    if level_4_met and execution_mode == "live":
        return "Evidence level is 4 because all Level 4 live pilot criteria are met; Level 5 remains false."
    if execution_mode == "manual_import":
        return f"Evidence level is capped at {final_level} because manual import lacks locked live-runner provenance."
    if execution_mode == "dry_run":
        return f"Evidence level is capped at {final_level} because dry-run artifacts are not provider evidence."
    if blocking_issues:
        return f"Evidence level is {final_level} under source cap {cap}; Level 4 is blocked by: {', '.join(sorted(set(blocking_issues)))}."
    return f"Evidence level is {final_level} under execution-mode cap {cap}; Level 5 remains false."


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "pass", "passed", "complete"}:
            return True
        if lowered in {"false", "fail", "failed", "needs_work"}:
            return False
    return bool(value)


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

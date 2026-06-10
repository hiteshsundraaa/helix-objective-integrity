from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_imported_provider_bridge import (
    V10ImportedProviderBridgeSummary,
    load_v10_imported_provider_bridge_config,
    write_imported_provider_bridge_outputs,
)
from helix.benchmark.v10_judgment_normalization import V10NormalizedJudgment
from helix.benchmark.v10_live_runner_design_gate import (
    V10LiveRunnerDesignConfig,
    load_v10_live_runner_design_config,
    validate_provider_model_allowed as validate_live_provider_model_allowed,
)
from helix.benchmark.v10_pilot_evidence_assessor import (
    V10PilotEvidenceAssessment,
    assess_v10_pilot_evidence,
    load_v10_pilot_evidence_assessment_config,
    write_v10_pilot_evidence_assessment,
)
from helix.benchmark.v10_provider_protocol import V10ProviderRunPlan
from helix.benchmark.v10_provider_raw_import import (
    V10ProviderRawImportValidationSummary,
    load_provider_run_plan,
    load_v10_provider_raw_import_config,
    write_imported_provider_run_outputs,
)
from helix.benchmark.v10_receipt_chain import (
    V10ReceiptChainConfig,
    V10ReceiptChainSummary,
    build_receipt_chain,
    write_receipt_chain_outputs,
)


ExecutionMode = Literal["manual_import"]
StageStatus = Literal["complete", "needs_work", "failed", "not_run"]
PilotStatus = Literal["complete", "needs_work", "failed"]

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SECRET_VALUE_TOKENS = {
    "api_key",
    "apikey",
    "secret",
    "bearer ",
    "authorization:",
    "password",
    "credential",
    "access_token",
    "refresh_token",
    "sk-",
}


class V10ManualPilotConfig(BaseModel):
    schema_version: str
    manual_pilot_only: bool
    execution_mode: ExecutionMode
    level_4_allowed: bool
    level_5_allowed: bool
    evidence_level_cap: int
    default_plan_path: str
    live_design_config_path: str
    raw_import_config_path: str
    imported_bridge_config_path: str
    evidence_assessment_config_path: str
    provider_runs_root: str
    provider_imports_root: str
    allowed_raw_output_formats: list[str]
    required_manual_metadata: list[str]
    collection_method_allowed_values: list[str]
    notes: str = ""


class V10ManualPilotInput(BaseModel):
    provider: str
    model: str
    run_id: str
    raw_output_file: str
    collection_method: str
    plan_path: str
    output_root: str
    notes: str | None = None


class V10ManualRawStagingSummary(BaseModel):
    import_dir: str
    external_raw_dir: str
    request_manifest_path: str
    raw_response_path: str
    raw_text_path: str
    source_raw_output_file: str
    source_raw_output_hash: str
    staged_raw_response_hash: str
    case_count: int
    prompt_hash: str | None


class V10PilotEvidenceRunResult(BaseModel):
    assessment: V10PilotEvidenceAssessment
    receipt_chain_summary: V10ReceiptChainSummary
    paths: dict[str, str]


class V10ManualPilotSummary(BaseModel):
    schema_version: str = "v10_manual_one_provider_pilot_summary_v1"
    run_id: str
    execution_mode: ExecutionMode = "manual_import"
    provider: str
    model: str
    raw_output_file: str
    raw_output_hash: str | None = None
    collection_method: str
    import_validation_status: StageStatus
    bridge_status: StageStatus
    evidence_assessment_status: StageStatus
    final_evidence_level: int
    level_4_allowed: bool = False
    level_5_allowed: bool = False
    receipt_count: int
    invalid_receipt_count: int
    receipt_chain_complete: bool
    normalization_status: str | None
    benchmark_status: str | None
    diagnostics_status: str | None
    mechanical_reportability_passed: bool | None
    integrity_passed: bool | None
    score_collapse_detected: bool | None
    blocking_issues: list[str] = Field(default_factory=list)
    non_blocking_warnings: list[str] = Field(default_factory=list)
    pilot_manifest_path: str
    pilot_report_path: str
    manifest_hash: str
    status: PilotStatus
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# HELIX v10.15B Manual One-Provider Pilot Report",
            "",
            "## Executive Summary",
            "",
            f"- run_id: `{self.run_id}`",
            f"- provider: `{self.provider}`",
            f"- model: `{self.model}`",
            f"- execution_mode: `{self.execution_mode}`",
            f"- status: `{self.status}`",
            f"- import_validation_status: `{self.import_validation_status}`",
            f"- bridge_status: `{self.bridge_status}`",
            f"- evidence_assessment_status: `{self.evidence_assessment_status}`",
            f"- final_evidence_level: `{self.final_evidence_level}`",
            f"- receipt_count: `{self.receipt_count}`",
            f"- invalid_receipt_count: `{self.invalid_receipt_count}`",
            f"- receipt_chain_complete: `{str(self.receipt_chain_complete).lower()}`",
            f"- manifest_hash: `{self.manifest_hash}`",
            "",
            "Manual one-provider pilot evidence is capped at Level 3. Level 4 and Level 5 are false.",
            "",
            "## Raw Import",
            "",
            f"- raw_output_file: `{self.raw_output_file}`",
            f"- raw_output_hash: `{self.raw_output_hash}`",
            f"- collection_method: `{self.collection_method}`",
            "",
            "## Pipeline Status",
            "",
            f"- normalization_status: `{self.normalization_status}`",
            f"- benchmark_status: `{self.benchmark_status}`",
            f"- diagnostics_status: `{self.diagnostics_status}`",
            f"- mechanical_reportability_passed: `{self.mechanical_reportability_passed}`",
            f"- integrity_passed: `{self.integrity_passed}`",
            f"- score_collapse_detected: `{self.score_collapse_detected}`",
            "",
            "## Blocking Issues",
            "",
        ]
        lines.extend(f"- `{issue}`" for issue in self.blocking_issues) if self.blocking_issues else lines.append("- None.")
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- `{warning}`" for warning in self.warnings) if self.warnings else lines.append("- None.")
        lines.extend(["", "## Non-Blocking Warnings", ""])
        lines.extend(f"- `{warning}`" for warning in self.non_blocking_warnings) if self.non_blocking_warnings else lines.append("- None.")
        lines.extend(
            [
                "",
                "## What This Supports",
                "",
                "- This supports a manual, one-provider pilot loop from externally saved raw output through import validation, pipeline bridge, receipt-chain construction, and evidence assessment.",
                "- This supports preserving raw-output bytes and hash-linking them to the manual pilot run.",
                "- This supports proving the v10 pipeline can consume one provider's manually collected output without live API calls.",
                "",
                "## What This Does Not Prove",
                "",
                "- This does not execute live provider APIs.",
                "- This does not use provider SDKs.",
                "- This does not read API keys or secrets.",
                "- This does not prove Level 4 or Level 5 evidence.",
                "- One provider does not prove cross-provider consistency.",
                "- Manual copy, export, or externally saved response collection is not locked live-runner provenance.",
                "",
                "## Limitations",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in self.limitations)
        return "\n".join(lines)


def load_v10_manual_pilot_config(path: str | Path) -> V10ManualPilotConfig:
    return V10ManualPilotConfig.model_validate_json(Path(path).read_text(encoding="utf-8"))


def validate_manual_pilot_inputs(
    pilot_input: V10ManualPilotInput,
    config: V10ManualPilotConfig,
    live_design_config: V10LiveRunnerDesignConfig,
) -> list[str]:
    issues: list[str] = []
    if not config.manual_pilot_only:
        issues.append("manual_pilot_only_not_enabled")
    if config.execution_mode != "manual_import":
        issues.append("manual_pilot_execution_mode_not_manual_import")
    if config.level_4_allowed:
        issues.append("manual_pilot_level_4_allowed")
    if config.level_5_allowed:
        issues.append("manual_pilot_level_5_allowed")
    if config.evidence_level_cap > 3:
        issues.append("manual_pilot_evidence_cap_above_3")

    provider_result = validate_live_provider_model_allowed(
        live_design_config,
        pilot_input.provider,
        pilot_input.model,
    )
    if not provider_result.valid:
        issues.append("provider_model_not_allowed")
        issues.extend(f"provider_model:{issue}" for issue in provider_result.issues)

    raw_path = Path(pilot_input.raw_output_file)
    if not raw_path.exists() or not raw_path.is_file():
        issues.append("missing_raw_output_file")
    elif _path_is_relative_to(
        raw_path.resolve(),
        Path(live_design_config.output_path_policy.live_root).resolve(),
    ):
        issues.append("raw_output_file_under_live_provider_output_root")

    if not Path(pilot_input.plan_path).is_file():
        issues.append("missing_plan_path")
    if pilot_input.collection_method not in set(config.collection_method_allowed_values):
        issues.append("invalid_collection_method")
    if not _run_id_is_safe(pilot_input.run_id):
        issues.append("invalid_run_id")
    issues.extend(_secret_like_input_issues(pilot_input))
    return sorted(set(issues))


def stage_manual_raw_output_for_import(
    pilot_input: V10ManualPilotInput,
    config: V10ManualPilotConfig,
    plan: V10ProviderRunPlan,
    *,
    generated_at: str | None = None,
) -> V10ManualRawStagingSummary:
    import_dir = Path(config.provider_imports_root) / pilot_input.run_id
    external_raw_dir = import_dir / "external_raw"
    external_raw_dir.mkdir(parents=True, exist_ok=True)
    _clear_staged_batch_files(external_raw_dir)

    raw_source = Path(pilot_input.raw_output_file)
    raw_bytes = raw_source.read_bytes()
    raw_hash = hash_file(raw_source)
    prompt_hash = _prompt_hash_for_plan(plan)
    timestamp = generated_at or _utc_now()
    request_manifest_path = external_raw_dir / "request_manifest_batch_001.json"
    raw_response_path = external_raw_dir / "raw_response_batch_001.json"
    raw_text_path = external_raw_dir / "raw_text_batch_001.txt"

    request_manifest = {
        "schema_version": "v10_external_provider_request_manifest_v1",
        "batch_id": "batch_001",
        "provider": pilot_input.provider,
        "model": pilot_input.model,
        "prompt_mode": plan.prompt_mode,
        "prompt_hash": prompt_hash,
        "case_ids": plan.sampled_case_ids,
        "request_timestamp": timestamp,
        "response_timestamp": timestamp,
        "collection_method": pilot_input.collection_method,
        "source_raw_output_file": str(raw_source),
        "source_raw_output_hash": raw_hash,
        "settings": {
            "manual_import": True,
            "no_api_calls_made": True,
            "provider_sdk_imported": False,
        },
        "retry_attempt": 0,
        "retry_reason": None,
    }
    request_manifest_path.write_text(
        json.dumps(request_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raw_response_path.write_bytes(raw_bytes)
    raw_text_path.write_bytes(raw_bytes)
    return V10ManualRawStagingSummary(
        import_dir=str(import_dir),
        external_raw_dir=str(external_raw_dir),
        request_manifest_path=str(request_manifest_path),
        raw_response_path=str(raw_response_path),
        raw_text_path=str(raw_text_path),
        source_raw_output_file=str(raw_source),
        source_raw_output_hash=raw_hash,
        staged_raw_response_hash=hash_file(raw_response_path),
        case_count=len(plan.sampled_case_ids),
        prompt_hash=prompt_hash,
    )


def run_manual_raw_import(
    pilot_input: V10ManualPilotInput,
    config: V10ManualPilotConfig,
    staging: V10ManualRawStagingSummary,
    *,
    generated_at: str | None = None,
) -> tuple[V10ProviderRawImportValidationSummary, dict[str, Path]]:
    raw_config = load_v10_provider_raw_import_config(config.raw_import_config_path)
    plan = load_provider_run_plan(pilot_input.plan_path)
    paths = write_imported_provider_run_outputs(
        config=raw_config,
        config_path=config.raw_import_config_path,
        plan=plan,
        plan_path=pilot_input.plan_path,
        import_dir=staging.import_dir,
        run_id=pilot_input.run_id,
        out_root=pilot_input.output_root,
        generated_at=generated_at,
    )
    summary = V10ProviderRawImportValidationSummary.model_validate_json(
        paths["raw_import_validation_summary"].read_text(encoding="utf-8")
    )
    return summary, paths


def run_imported_provider_bridge(
    provider_run_dir: str | Path,
    config: V10ManualPilotConfig,
    *,
    generated_at: str | None = None,
) -> tuple[V10ImportedProviderBridgeSummary, dict[str, Path]]:
    bridge_config = load_v10_imported_provider_bridge_config(config.imported_bridge_config_path)
    paths = write_imported_provider_bridge_outputs(
        provider_run_dir=provider_run_dir,
        cases_path=bridge_config.cases_path,
        config=bridge_config,
        config_path=config.imported_bridge_config_path,
        out_subdir=bridge_config.output_subdir,
        generated_at=generated_at,
    )
    summary = V10ImportedProviderBridgeSummary.model_validate_json(
        paths["bridge_summary"].read_text(encoding="utf-8")
    )
    return summary, paths


def run_pilot_evidence_assessment(
    *,
    provider_run_dir: str | Path,
    config: V10ManualPilotConfig,
    pilot_input: V10ManualPilotInput,
    source_raw_output_hash: str | None,
    generated_at: str | None = None,
) -> V10PilotEvidenceRunResult:
    run_dir = Path(provider_run_dir)
    assessment_config = load_v10_pilot_evidence_assessment_config(
        config.evidence_assessment_config_path
    )
    live_design_config = load_v10_live_runner_design_config(config.live_design_config_path)
    cases, case_issues = _load_cases_for_assessment(run_dir)
    judgments, judgment_issues = _load_judgments_for_assessment(run_dir)
    raw_hashes_by_case_id = (
        {case.case_id: source_raw_output_hash for case in cases}
        if source_raw_output_hash
        else {}
    )
    receipt_chain_config = V10ReceiptChainConfig.model_validate(
        assessment_config.receipt_chain.model_dump(mode="json")
    )
    records, receipt_chain_summary = build_receipt_chain(
        cases,
        judgments,
        execution_mode="manual_import",
        provider=pilot_input.provider,
        model=pilot_input.model,
        raw_hashes_by_case_id=raw_hashes_by_case_id,
        config=receipt_chain_config,
        run_id=pilot_input.run_id,
    )
    if case_issues or judgment_issues:
        receipt_chain_summary = receipt_chain_summary.model_copy(
            update={
                "issues": sorted(
                    set(receipt_chain_summary.issues + case_issues + judgment_issues)
                ),
                "receipt_chain_complete": False,
            }
        )

    out_dir = run_dir / "pilot_evidence"
    receipt_paths = write_receipt_chain_outputs(records, receipt_chain_summary, out_dir)
    artifacts = _load_pipeline_artifacts(run_dir)
    assessment = assess_v10_pilot_evidence(
        run_id=pilot_input.run_id,
        execution_mode="manual_import",
        provider=pilot_input.provider,
        model=pilot_input.model,
        case_count=len(cases),
        receipt_chain_summary=receipt_chain_summary,
        normalization_status=artifacts["normalization_status"],
        benchmark_status=artifacts["benchmark_status"],
        diagnostics_status=artifacts["diagnostics_status"],
        integrity_summary=artifacts["integrity_summary"],
        reportability_summary=artifacts["reportability_summary"],
        live_design_config=live_design_config,
        assessment_config=assessment_config,
    )
    assessment_paths = write_v10_pilot_evidence_assessment(
        assessment,
        out_dir,
        config=assessment_config,
        receipt_chain_summary=receipt_chain_summary,
        generated_at=generated_at,
    )
    paths = {
        **{key: str(value) for key, value in receipt_paths.items()},
        **{key: str(value) for key, value in assessment_paths.items()},
    }
    return V10PilotEvidenceRunResult(
        assessment=assessment,
        receipt_chain_summary=receipt_chain_summary,
        paths=paths,
    )


def run_manual_pilot(
    pilot_input: V10ManualPilotInput,
    config: V10ManualPilotConfig,
    *,
    generated_at: str | None = None,
) -> tuple[V10ManualPilotSummary, dict[str, Path]]:
    live_design_config = load_v10_live_runner_design_config(config.live_design_config_path)
    validation_issues = validate_manual_pilot_inputs(pilot_input, config, live_design_config)
    if validation_issues:
        raise ValueError("Manual pilot input validation failed: " + ", ".join(validation_issues))

    plan = load_provider_run_plan(pilot_input.plan_path)
    staging = stage_manual_raw_output_for_import(
        pilot_input,
        config,
        plan,
        generated_at=generated_at,
    )
    import_summary, import_paths = run_manual_raw_import(
        pilot_input,
        config,
        staging,
        generated_at=generated_at,
    )
    bridge_summary: V10ImportedProviderBridgeSummary | None = None
    bridge_paths: dict[str, Path] = {}
    evidence: V10PilotEvidenceRunResult | None = None
    if import_summary.validation_status == "complete":
        bridge_summary, bridge_paths = run_imported_provider_bridge(
            import_paths["output_provider_run_dir"],
            config,
            generated_at=generated_at,
        )
        evidence = run_pilot_evidence_assessment(
            provider_run_dir=import_paths["output_provider_run_dir"],
            config=config,
            pilot_input=pilot_input,
            source_raw_output_hash=staging.source_raw_output_hash,
            generated_at=generated_at,
        )

    summary = build_manual_pilot_summary(
        pilot_input=pilot_input,
        staging=staging,
        import_summary=import_summary,
        bridge_summary=bridge_summary,
        evidence=evidence,
    )
    manual_paths = write_manual_pilot_outputs(
        summary,
        out_dir=import_paths["output_provider_run_dir"],
        config=config,
        pilot_input=pilot_input,
        staging=staging,
        import_paths=import_paths,
        bridge_paths=bridge_paths,
        evidence_paths=evidence.paths if evidence else {},
        generated_at=generated_at,
    )
    manifest_hash = json.loads(
        manual_paths["manifest"].read_text(encoding="utf-8")
    )["manifest_hash"]
    return summary.model_copy(
        update={
            "pilot_manifest_path": str(manual_paths["manifest"]),
            "pilot_report_path": str(manual_paths["report"]),
            "manifest_hash": manifest_hash,
        }
    ), {**import_paths, **bridge_paths, **manual_paths}


def build_manual_pilot_summary(
    *,
    pilot_input: V10ManualPilotInput,
    staging: V10ManualRawStagingSummary | None,
    import_summary: V10ProviderRawImportValidationSummary | None,
    bridge_summary: V10ImportedProviderBridgeSummary | None,
    evidence: V10PilotEvidenceRunResult | None,
) -> V10ManualPilotSummary:
    assessment = evidence.assessment if evidence else None
    receipt_chain = evidence.receipt_chain_summary if evidence else None
    import_status: StageStatus = import_summary.validation_status if import_summary else "not_run"
    bridge_status: StageStatus = bridge_summary.status if bridge_summary else "not_run"
    assessment_status: StageStatus = "complete" if assessment else "not_run"
    warnings = sorted(
        set(
            (import_summary.warnings if import_summary else [])
            + (bridge_summary.warnings if bridge_summary else [])
            + (assessment.non_blocking_warnings if assessment else [])
        )
    )
    blocking = sorted(
        set(
            (import_summary.issues if import_summary else [])
            + _raw_import_coverage_issues(import_summary)
            + (assessment.blocking_issues if assessment else [])
        )
    )
    return V10ManualPilotSummary(
        run_id=pilot_input.run_id,
        provider=pilot_input.provider,
        model=pilot_input.model,
        raw_output_file=pilot_input.raw_output_file,
        raw_output_hash=staging.source_raw_output_hash if staging else None,
        collection_method=pilot_input.collection_method,
        import_validation_status=import_status,
        bridge_status=bridge_status,
        evidence_assessment_status=assessment_status,
        final_evidence_level=assessment.final_evidence_level if assessment else 0,
        level_4_allowed=False,
        level_5_allowed=False,
        receipt_count=receipt_chain.receipt_count if receipt_chain else 0,
        invalid_receipt_count=receipt_chain.invalid_receipt_count if receipt_chain else 0,
        receipt_chain_complete=receipt_chain.receipt_chain_complete if receipt_chain else False,
        normalization_status=assessment.normalization_status if assessment else None,
        benchmark_status=assessment.benchmark_status if assessment else None,
        diagnostics_status=assessment.diagnostics_status if assessment else None,
        mechanical_reportability_passed=assessment.mechanical_reportability_passed if assessment else None,
        integrity_passed=assessment.integrity_passed if assessment else None,
        score_collapse_detected=assessment.score_collapse_detected if assessment else None,
        blocking_issues=blocking,
        non_blocking_warnings=assessment.non_blocking_warnings if assessment else [],
        pilot_manifest_path="",
        pilot_report_path="",
        manifest_hash="",
        status=_pilot_status(import_status, bridge_status, assessment_status, assessment),
        warnings=warnings,
        limitations=[
            "Manual one-provider pilot only.",
            "No live provider APIs are called.",
            "No provider SDK clients are imported or executed.",
            "Manual evidence remains capped at Level 3.",
            "Level 4 and Level 5 are false.",
            "One provider does not prove cross-provider consistency.",
        ],
    )


def write_manual_pilot_outputs(
    summary: V10ManualPilotSummary,
    *,
    out_dir: str | Path,
    config: V10ManualPilotConfig,
    pilot_input: V10ManualPilotInput,
    staging: V10ManualRawStagingSummary | None,
    import_paths: dict[str, Path],
    bridge_paths: dict[str, Path] | None = None,
    evidence_paths: dict[str, str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary_path = target / "manual_pilot_summary.json"
    manifest_path = target / "manual_pilot_manifest.json"
    report_path = target / "manual_pilot_report.md"
    manifest_payload = {
        "schema_version": "v10_manual_one_provider_pilot_manifest_v1",
        "generated_at": generated_at or _utc_now(),
        "manual_pilot_config": config.model_dump(mode="json"),
        "input": pilot_input.model_dump(mode="json"),
        "staging": staging.model_dump(mode="json") if staging else None,
        "summary_without_manifest_hash": summary.model_copy(
            update={
                "pilot_manifest_path": str(manifest_path),
                "pilot_report_path": str(report_path),
                "manifest_hash": "",
            }
        ).model_dump(mode="json"),
        "import_paths": _path_map(import_paths),
        "bridge_paths": _path_map(bridge_paths or {}),
        "evidence_paths": evidence_paths or {},
        "path_hashes": _path_hashes(
            [
                *import_paths.values(),
                *((bridge_paths or {}).values()),
                *[Path(value) for value in (evidence_paths or {}).values()],
            ]
        ),
        "no_api_calls_made": True,
        "provider_sdk_imported": False,
        "level_4_allowed": False,
        "level_5_allowed": False,
        "limitations": [
            "Manual import only.",
            "No live provider APIs were called.",
            "No provider SDK clients were used.",
            "Manual collection is not locked live-runner provenance.",
            "Evidence level is capped at 3.",
        ],
    }
    manifest = {**manifest_payload, "manifest_hash": stable_json_hash(manifest_payload)}
    final_summary = summary.model_copy(
        update={
            "pilot_manifest_path": str(manifest_path),
            "pilot_report_path": str(report_path),
            "manifest_hash": manifest["manifest_hash"],
        }
    )
    summary_path.write_text(
        json.dumps(final_summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(final_summary.to_markdown() + "\n", encoding="utf-8")
    return {"manual_pilot_summary": summary_path, "manifest": manifest_path, "report": report_path}


def _load_cases_for_assessment(run_dir: Path) -> tuple[list[V10Case], list[str]]:
    for path in [
        run_dir / "filtered_imported_cases.jsonl",
        run_dir / "imported_pipeline_bridge" / "filtered_imported_cases.jsonl",
        run_dir / "pipeline_bridge" / "filtered_imported_cases.jsonl",
        Path("benchmarks/v10_calibrated/v10_cases.jsonl"),
    ]:
        if path.exists():
            return [
                V10Case.model_validate_json(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ], []
    return [], ["missing_cases_file"]


def _load_judgments_for_assessment(run_dir: Path) -> tuple[list[V10NormalizedJudgment | dict[str, Any]], list[str]]:
    for path in [
        run_dir / "normalized_judgments" / "v10_normalized_judgments.jsonl",
        run_dir / "imported_pipeline_bridge" / "normalized_judgments" / "v10_normalized_judgments.jsonl",
        run_dir / "pipeline_bridge" / "normalized_judgments" / "v10_normalized_judgments.jsonl",
    ]:
        if path.exists():
            return [
                V10NormalizedJudgment.model_validate_json(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ], []
    for path in [
        run_dir / "parsed_raw_judgments.jsonl",
        run_dir / "imported_pipeline_bridge" / "parsed_raw_judgments.jsonl",
        run_dir / "pipeline_bridge" / "parsed_raw_judgments.jsonl",
    ]:
        if path.exists():
            return _load_jsonl_dicts(path), []
    return [], ["missing_judgments_file"]


def _load_pipeline_artifacts(run_dir: Path) -> dict[str, Any]:
    bridge_summary = _first_json(
        [
            run_dir / "bridge_summary.json",
            run_dir / "imported_pipeline_bridge" / "bridge_summary.json",
            run_dir / "pipeline_bridge" / "bridge_summary.json",
        ]
    )
    normalization_summary = _first_json(
        [
            run_dir / "normalized_judgments" / "v10_normalization_summary.json",
            run_dir / "imported_pipeline_bridge" / "normalized_judgments" / "v10_normalization_summary.json",
            run_dir / "pipeline_bridge" / "normalized_judgments" / "v10_normalization_summary.json",
        ]
    )
    benchmark_summary = _first_json(
        [
            run_dir / "benchmark_run" / "v10_benchmark_summary.json",
            run_dir / "imported_pipeline_bridge" / "benchmark_run" / "v10_benchmark_summary.json",
            run_dir / "pipeline_bridge" / "benchmark_run" / "v10_benchmark_summary.json",
        ]
    )
    diagnostics_summary = _first_json(
        [
            run_dir / "diagnostics" / "v10_diagnostics_summary.json",
            run_dir / "imported_pipeline_bridge" / "diagnostics" / "v10_diagnostics_summary.json",
            run_dir / "pipeline_bridge" / "diagnostics" / "v10_diagnostics_summary.json",
        ]
    )
    integrity_summary = _first_json(
        [
            run_dir / "diagnostics" / "v10_integrity_report.json",
            run_dir / "imported_pipeline_bridge" / "diagnostics" / "v10_integrity_report.json",
            run_dir / "pipeline_bridge" / "diagnostics" / "v10_integrity_report.json",
        ]
    )
    reportability_summary = _first_json(
        [
            run_dir / "reportability" / "v10_reportability_report.json",
            run_dir / "imported_pipeline_bridge" / "reportability" / "v10_reportability_report.json",
            run_dir / "pipeline_bridge" / "reportability" / "v10_reportability_report.json",
        ]
    )
    if integrity_summary is not None and "score_collapse_detected" not in integrity_summary:
        source = normalization_summary or benchmark_summary or {}
        if "score_collapse_detected" in source:
            integrity_summary = {**integrity_summary, "score_collapse_detected": source["score_collapse_detected"]}
        elif "score_entropy" in integrity_summary:
            integrity_summary = {**integrity_summary, "score_collapse_detected": False}
    return {
        "normalization_status": bridge_summary.get("normalization_status") if bridge_summary else normalization_summary.get("status") if normalization_summary else None,
        "benchmark_status": bridge_summary.get("benchmark_status") if bridge_summary else benchmark_summary.get("status") if benchmark_summary else None,
        "diagnostics_status": bridge_summary.get("diagnostics_status") if bridge_summary else diagnostics_summary.get("diagnostics_status") if diagnostics_summary else None,
        "integrity_summary": integrity_summary,
        "reportability_summary": reportability_summary,
    }


def _prompt_hash_for_plan(plan: V10ProviderRunPlan) -> str | None:
    if plan.prompt_mode == "generic":
        return plan.prompt_hashes.get("generic_prompt")
    return plan.prompt_hashes.get("contract_prompt")


def _raw_import_coverage_issues(
    import_summary: V10ProviderRawImportValidationSummary | None,
) -> list[str]:
    if import_summary is None:
        return []
    issues: list[str] = []
    if import_summary.missing_case_count:
        issues.append(f"missing_case_count:{import_summary.missing_case_count}")
    if import_summary.duplicate_case_count:
        issues.append(f"duplicate_case_count:{import_summary.duplicate_case_count}")
    if import_summary.unexpected_case_count:
        issues.append(f"unexpected_case_count:{import_summary.unexpected_case_count}")
    if import_summary.malformed_judgment_count:
        issues.append(f"malformed_judgment_count:{import_summary.malformed_judgment_count}")
    return issues


def _pilot_status(
    import_status: StageStatus,
    bridge_status: StageStatus,
    assessment_status: StageStatus,
    assessment: V10PilotEvidenceAssessment | None,
) -> PilotStatus:
    if import_status == "failed" or bridge_status == "failed":
        return "failed"
    if import_status != "complete" or assessment_status != "complete":
        return "needs_work"
    if bridge_status not in {"complete", "needs_work"}:
        return "needs_work"
    if assessment is not None and assessment.final_evidence_level == 0:
        return "needs_work"
    if bridge_status == "needs_work":
        return "needs_work"
    return "complete"


def _run_id_is_safe(run_id: str) -> bool:
    return bool(run_id and "/" not in run_id and "\\" not in run_id and ".." not in run_id and RUN_ID_RE.fullmatch(run_id))


def _secret_like_input_issues(pilot_input: V10ManualPilotInput) -> list[str]:
    issues: list[str] = []
    for field, value in pilot_input.model_dump(mode="json").items():
        if isinstance(value, str) and any(token in value.lower() for token in SECRET_VALUE_TOKENS):
            issues.append(f"secret_like_input_value:{field}")
    return issues


def _path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _clear_staged_batch_files(external_raw_dir: Path) -> None:
    for pattern in ["request_manifest_*.json", "raw_response_*.json", "raw_text_*.txt"]:
        for path in external_raw_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def _first_json(paths: list[Path]) -> dict[str, Any] | None:
    for path in paths:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"Expected JSON object at {path}")
            return payload
    return None


def _load_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _path_map(paths: dict[str, Path] | dict[str, str]) -> dict[str, str]:
    return {key: str(value) for key, value in paths.items()}


def _path_hashes(paths: list[Path | str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for raw_path in paths:
        path = Path(raw_path)
        if path.exists() and path.is_file():
            hashes[str(path)] = hash_file(path)
    return hashes


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

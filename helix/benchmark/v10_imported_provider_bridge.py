from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from shutil import copyfile
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_judgment_normalization import (
    V10NormalizedJudgment,
    V10NormalizationSummary,
    V10RawJudgment,
    load_raw_judgments,
)
from helix.benchmark.v10_provider_dry_run_bridge import (
    run_benchmark_for_provider_dry_run as _run_benchmark_pipeline,
    run_diagnostics_for_provider_dry_run as _run_diagnostics_pipeline,
    run_normalization_for_provider_dry_run as _run_normalization_pipeline,
    run_reportability_for_provider_dry_run as _run_reportability_pipeline,
)
from helix.benchmark.v10_provider_raw_import import (
    V10ProviderRawImportValidationSummary,
)


class V10ImportedProviderBridgeEvidencePolicy(BaseModel):
    manual_import_is_locked_live_provider_evidence: bool
    manual_import_bridge_evidence_level_cap: int
    level_4_allowed: bool
    level_5_allowed: bool


class V10ImportedProviderBridgeConfig(BaseModel):
    schema_version: str
    manual_import_bridge: bool
    default_provider_run_dir: str
    parsed_raw_judgments_filename: str
    raw_import_summary_filename: str
    cases_path: str
    normalization_config_path: str
    benchmark_config_path: str
    diagnostics_config_path: str
    reportability_config_path: str
    integrity_config_path: str
    output_subdir: str
    allow_network_calls: bool
    allow_provider_sdk_imports: bool
    allow_api_keys: bool
    evidence_policy: V10ImportedProviderBridgeEvidencePolicy
    notes: str = ""


class V10ImportedProviderBridgeSummary(BaseModel):
    schema_version: str = "v10_imported_provider_bridge_summary_v1"
    run_id: str
    provider_run_dir: str
    manual_import_bridge: bool = True
    no_api_calls_made: bool = True
    network_calls_attempted: int = 0
    provider_sdk_imported: bool = False
    api_key_observed: bool = False
    input_parsed_raw_judgments_path: str
    input_parsed_raw_judgments_hash: str
    input_raw_import_summary_path: str
    input_raw_import_summary_hash: str
    normalized_output_dir: str
    benchmark_output_dir: str
    diagnostics_output_dir: str
    reportability_output_path: str
    raw_judgment_count: int
    normalized_judgment_count: int
    benchmark_receipt_count: int
    matched_case_count: int
    missing_judgment_case_count: int
    normalization_status: str
    benchmark_status: str
    diagnostics_status: str
    mechanical_reportability_passed: bool | None
    raw_evidence_level_allowed: int | None
    final_evidence_level: int
    level_4_allowed: bool = False
    level_5_allowed: bool = False
    status: Literal["complete", "needs_work", "failed"]
    warnings: list[str] = Field(default_factory=list)
    bridge_hash: str

    def to_markdown(self) -> str:
        lines = [
            "# HELIX v10 Imported Provider Pipeline Bridge Report",
            "",
            "## Executive Summary",
            "",
            f"- run_id: `{self.run_id}`",
            f"- status: `{self.status}`",
            f"- manual_import_bridge: `{str(self.manual_import_bridge).lower()}`",
            f"- no_api_calls_made: `{str(self.no_api_calls_made).lower()}`",
            f"- raw_judgment_count: `{self.raw_judgment_count}`",
            f"- normalized_judgment_count: `{self.normalized_judgment_count}`",
            f"- benchmark_receipt_count: `{self.benchmark_receipt_count}`",
            f"- matched_case_count: `{self.matched_case_count}`",
            f"- missing_judgment_case_count: `{self.missing_judgment_case_count}`",
            f"- final_evidence_level: `{self.final_evidence_level}`",
            f"- bridge_hash: `{self.bridge_hash}`",
            "",
            "This bridge routes validated manual imported provider outputs through the existing v10 pipeline. It does not create locked live-provider evidence.",
            "",
            "## Input Provider Run",
            "",
            f"- provider_run_dir: `{self.provider_run_dir}`",
            f"- input_raw_import_summary_hash: `{self.input_raw_import_summary_hash}`",
            f"- input_parsed_raw_judgments_hash: `{self.input_parsed_raw_judgments_hash}`",
            "",
            "## Manual Import Validation Checks",
            "",
            f"- no_api_calls_made: `{str(self.no_api_calls_made).lower()}`",
            f"- network_calls_attempted: `{self.network_calls_attempted}`",
            f"- provider_sdk_imported: `{str(self.provider_sdk_imported).lower()}`",
            f"- api_key_observed: `{str(self.api_key_observed).lower()}`",
            "",
            "## Normalization Results",
            "",
            f"- normalization_status: `{self.normalization_status}`",
            f"- normalized_output_dir: `{self.normalized_output_dir}`",
            "",
            "## Benchmark Results",
            "",
            f"- benchmark_status: `{self.benchmark_status}`",
            f"- benchmark_output_dir: `{self.benchmark_output_dir}`",
            "",
            "## Diagnostics Results",
            "",
            f"- diagnostics_status: `{self.diagnostics_status}`",
            f"- diagnostics_output_dir: `{self.diagnostics_output_dir}`",
            "",
            "## Reportability Gate",
            "",
            f"- mechanical_reportability_passed: `{self.mechanical_reportability_passed}`",
            f"- raw_evidence_level_allowed: `{self.raw_evidence_level_allowed}`",
            f"- reportability_output_path: `{self.reportability_output_path}`",
            "",
            "## Evidence-Level Cap",
            "",
            f"- final_evidence_level: `{self.final_evidence_level}`",
            "- Level 4 false.",
            "- Level 5 false.",
            "- Mechanical reportability, if true, does not raise manual-import evidence beyond Level 3.",
            "",
            "## Case Filtering Policy",
            "",
            "- The full v10 case file is filtered to the case IDs present in the validated imported `parsed_raw_judgments.jsonl`.",
            "- This lets a pilot import report imported-case coverage without treating non-imported v10 cases as missing judgments.",
            "- The filtering policy is recorded in `bridge_manifest.json` and does not alter the source v10 case file.",
            "",
            "## What This Supports",
            "",
            "- This supports routing validated manual imported provider outputs through existing v10 normalization, benchmark, diagnostics, and reportability code.",
            "- This supports preserving manual-import provenance and hash links while reusing the registered v10 pipeline.",
            "",
            "## What This Does Not Yet Prove",
            "",
            "- No API calls were made.",
            "- No provider SDK clients were used.",
            "- Imported files were externally saved raw outputs.",
            "- The input run was manual import, not locked live API execution.",
            "- This is not Level 4 or Level 5 evidence.",
            "",
            "## Limitations",
            "",
            "- Manual-import bridge evidence is capped at Level 3.",
            "- Pilot manual-import sample size is not final v10 evidence.",
            "- Existing v10 pipeline behavior is reused; no manual-import-specific scoring pass is introduced.",
        ]
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_imported_provider_bridge_config(
    path: str | Path,
) -> V10ImportedProviderBridgeConfig:
    return V10ImportedProviderBridgeConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_v10_cases(path: str | Path) -> list[V10Case]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"V10 cases file does not exist: {target}. "
            "Run examples/generate_v10_calibrated_cases.py first."
        )
    return [
        V10Case.model_validate_json(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_raw_import_validation_summary(
    provider_run_dir: str | Path,
    *,
    summary_filename: str = "raw_import_validation_summary.json",
) -> V10ProviderRawImportValidationSummary:
    run_dir = Path(provider_run_dir)
    summary_path = run_dir / summary_filename
    if not summary_path.exists():
        raise FileNotFoundError(
            f"Raw import validation summary does not exist: {summary_path}. "
            "Run examples/import_v10_provider_raw_outputs.py first."
        )
    return V10ProviderRawImportValidationSummary.model_validate_json(
        summary_path.read_text(encoding="utf-8")
    )


def validate_provider_run_is_manual_import(
    provider_run_dir: str | Path,
    *,
    summary_filename: str = "raw_import_validation_summary.json",
    parsed_filename: str = "parsed_raw_judgments.jsonl",
) -> list[str]:
    run_dir = Path(provider_run_dir)
    issues: list[str] = []
    try:
        summary = load_raw_import_validation_summary(
            run_dir,
            summary_filename=summary_filename,
        )
    except FileNotFoundError:
        return ["missing_raw_import_validation_summary"]
    if not summary.validator_only:
        issues.append("raw_import_summary_not_validator_only")
    if summary.validation_status != "complete":
        issues.append("raw_import_validation_not_complete")
    if not summary.parsed_raw_judgments_written:
        issues.append("parsed_raw_judgments_not_written")
    if not summary.no_api_calls_made:
        issues.append("raw_import_api_calls_not_excluded")
    if summary.network_calls_attempted != 0:
        issues.append("raw_import_network_calls_attempted")
    if summary.provider_sdk_imported:
        issues.append("raw_import_provider_sdk_imported")
    if summary.api_key_observed:
        issues.append("raw_import_api_key_observed")
    if summary.evidence_level_cap > 3:
        issues.append("manual_import_evidence_cap_above_3")
    if summary.level_4_allowed:
        issues.append("raw_import_level_4_allowed")
    if summary.level_5_allowed:
        issues.append("raw_import_level_5_allowed")
    if not (run_dir / parsed_filename).exists():
        issues.append("missing_parsed_raw_judgments")
    return sorted(set(issues))


def copy_or_reference_imported_raw_judgments(
    provider_run_dir: str | Path,
    bridge_out_dir: str | Path,
    *,
    parsed_filename: str = "parsed_raw_judgments.jsonl",
) -> Path:
    source = Path(provider_run_dir) / parsed_filename
    if not source.exists():
        raise FileNotFoundError(
            f"Parsed manual-import judgments do not exist: {source}. "
            "Run examples/import_v10_provider_raw_outputs.py first."
        )
    target = Path(bridge_out_dir) / parsed_filename
    target.parent.mkdir(parents=True, exist_ok=True)
    copyfile(source, target)
    return target


def filter_cases_to_imported_case_ids(
    cases: list[V10Case],
    parsed_raw_judgments: list[V10RawJudgment] | list[dict[str, Any]],
) -> list[V10Case]:
    imported_ids = set(_case_ids_from_raw_judgments(parsed_raw_judgments))
    return sorted(
        [case for case in cases if case.case_id in imported_ids],
        key=lambda item: item.case_id,
    )


def run_normalization_for_imported_provider(
    *,
    raw_judgments_path: str | Path,
    cases: list[V10Case],
    cases_path: str | Path,
    config: V10ImportedProviderBridgeConfig,
    out_dir: str | Path,
    provider: str | None,
    model: str | None,
) -> tuple[list[V10NormalizedJudgment], V10NormalizationSummary, dict[str, Path]]:
    config_for_cases = config.model_copy(update={"cases_path": str(cases_path)})
    return _run_normalization_pipeline(
        raw_judgments_path=raw_judgments_path,
        cases=cases,
        config=config_for_cases,
        out_dir=out_dir,
        provider=provider,
        model=model,
    )


def run_benchmark_for_imported_provider(
    *,
    cases: list[V10Case],
    cases_path: str | Path,
    normalized: list[V10NormalizedJudgment],
    normalization_summary: V10NormalizationSummary,
    normalization_paths: dict[str, Path],
    config: V10ImportedProviderBridgeConfig,
    out_dir: str | Path,
) -> tuple[Any, list[Any], dict[str, Path]]:
    config_for_cases = config.model_copy(update={"cases_path": str(cases_path)})
    return _run_benchmark_pipeline(
        cases=cases,
        normalized=normalized,
        normalization_summary=normalization_summary,
        normalization_paths=normalization_paths,
        config=config_for_cases,
        out_dir=out_dir,
    )


def run_diagnostics_for_imported_provider(
    *,
    cases_path: str | Path,
    receipts: list[Any],
    benchmark_summary: Any,
    benchmark_paths: dict[str, Path],
    config: V10ImportedProviderBridgeConfig,
    out_dir: str | Path,
    reportability_out_dir: str | Path,
) -> tuple[Any, Any, dict[str, Path]]:
    return _run_diagnostics_pipeline(
        cases_path=cases_path,
        receipts=receipts,
        benchmark_summary=benchmark_summary,
        benchmark_paths=benchmark_paths,
        config=config,
        out_dir=out_dir,
        reportability_out_dir=reportability_out_dir,
    )


def run_reportability_for_imported_provider(
    *,
    integrity_report: Any,
    benchmark_summary: Any,
    bootstrap_payload: dict[str, Any],
    receipts: list[Any],
    selectivity_baselines: Any,
    config: V10ImportedProviderBridgeConfig,
    out_dir: str | Path,
) -> tuple[Any, Path, Path]:
    return _run_reportability_pipeline(
        integrity_report=integrity_report,
        benchmark_summary=benchmark_summary,
        bootstrap_payload=bootstrap_payload,
        receipts=receipts,
        selectivity_baselines=selectivity_baselines,
        config=config,
        out_dir=out_dir,
    )


def write_imported_provider_bridge_outputs(
    *,
    provider_run_dir: str | Path,
    cases_path: str | Path,
    config: V10ImportedProviderBridgeConfig,
    config_path: str | Path,
    out_subdir: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Path]:
    run_dir = Path(provider_run_dir)
    issues = validate_provider_run_is_manual_import(
        run_dir,
        summary_filename=config.raw_import_summary_filename,
        parsed_filename=config.parsed_raw_judgments_filename,
    )
    if issues:
        if "missing_raw_import_validation_summary" in issues:
            raise FileNotFoundError(
                f"Manual import outputs missing in {run_dir}. "
                "Run examples/import_v10_provider_raw_outputs.py first."
            )
        raise ValueError("Manual import validation failed: " + ", ".join(issues))

    raw_import_summary = load_raw_import_validation_summary(
        run_dir,
        summary_filename=config.raw_import_summary_filename,
    )
    bridge_dir = run_dir / (out_subdir or config.output_subdir)
    bridge_dir.mkdir(parents=True, exist_ok=True)
    parsed_copy_path = copy_or_reference_imported_raw_judgments(
        run_dir,
        bridge_dir,
        parsed_filename=config.parsed_raw_judgments_filename,
    )

    parsed_raw_judgments = load_raw_judgments(parsed_copy_path)
    all_cases = load_v10_cases(cases_path)
    cases = filter_cases_to_imported_case_ids(all_cases, parsed_raw_judgments)
    if not cases:
        raise ValueError("No imported case IDs matched the v10 cases file.")
    filtered_cases_path = bridge_dir / "filtered_imported_cases.jsonl"
    _write_cases_jsonl(filtered_cases_path, cases)

    normalized, normalization_summary, normalization_paths = (
        run_normalization_for_imported_provider(
            raw_judgments_path=parsed_copy_path,
            cases=cases,
            cases_path=filtered_cases_path,
            config=config,
            out_dir=bridge_dir / "normalized_judgments",
            provider=raw_import_summary.provider,
            model=raw_import_summary.model,
        )
    )
    benchmark_summary, receipts, benchmark_paths = run_benchmark_for_imported_provider(
        cases=cases,
        cases_path=filtered_cases_path,
        normalized=normalized,
        normalization_summary=normalization_summary,
        normalization_paths=normalization_paths,
        config=config,
        out_dir=bridge_dir / "benchmark_run",
    )
    diagnostics_summary, reportability_report, diagnostics_paths = (
        run_diagnostics_for_imported_provider(
            cases_path=filtered_cases_path,
            receipts=receipts,
            benchmark_summary=benchmark_summary,
            benchmark_paths=benchmark_paths,
            config=config,
            out_dir=bridge_dir / "diagnostics",
            reportability_out_dir=bridge_dir / "reportability",
        )
    )

    summary = _bridge_summary(
        provider_run_dir=run_dir,
        bridge_dir=bridge_dir,
        raw_import_summary=raw_import_summary,
        raw_import_summary_path=run_dir / config.raw_import_summary_filename,
        parsed_path=parsed_copy_path,
        normalization_summary=normalization_summary,
        benchmark_summary=benchmark_summary,
        receipts=receipts,
        diagnostics_summary=diagnostics_summary,
        reportability_report=reportability_report,
        config=config,
        diagnostics_paths=diagnostics_paths,
    )

    bridge_config_path = bridge_dir / "bridge_config.json"
    input_hashes_path = bridge_dir / "input_hashes.json"
    summary_path = bridge_dir / "bridge_summary.json"
    report_path = bridge_dir / "bridge_report.md"
    manifest_path = bridge_dir / "bridge_manifest.json"
    bridge_config_path.write_text(
        json.dumps(config.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    input_hashes = _input_hashes(
        provider_run_dir=run_dir,
        parsed_path=parsed_copy_path,
        raw_import_summary_path=run_dir / config.raw_import_summary_filename,
        full_cases_path=Path(cases_path),
        filtered_cases_path=filtered_cases_path,
    )
    input_hashes_path.write_text(
        json.dumps(input_hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")
    manifest = _bridge_manifest(
        summary=summary,
        config_path=Path(config_path),
        bridge_config_path=bridge_config_path,
        input_hashes_path=input_hashes_path,
        summary_path=summary_path,
        report_path=report_path,
        parsed_path=parsed_copy_path,
        raw_import_summary_path=run_dir / config.raw_import_summary_filename,
        full_cases_path=Path(cases_path),
        filtered_cases_path=filtered_cases_path,
        all_case_count=len(all_cases),
        filtered_case_count=len(cases),
        imported_case_count=len(parsed_raw_judgments),
        normalization_paths=normalization_paths,
        benchmark_paths=benchmark_paths,
        diagnostics_paths=diagnostics_paths,
        generated_at=generated_at,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "bridge_dir": bridge_dir,
        "bridge_config": bridge_config_path,
        "bridge_manifest": manifest_path,
        "bridge_summary": summary_path,
        "bridge_report": report_path,
        "input_hashes": input_hashes_path,
        "parsed_raw_judgments": parsed_copy_path,
        "filtered_cases": filtered_cases_path,
        "normalized_output_dir": normalization_paths["summary"].parent,
        "benchmark_output_dir": benchmark_paths["summary"].parent,
        "diagnostics_output_dir": diagnostics_paths["summary"].parent,
        "reportability_output_path": diagnostics_paths["reportability_json"],
    }


def _bridge_summary(
    *,
    provider_run_dir: Path,
    bridge_dir: Path,
    raw_import_summary: V10ProviderRawImportValidationSummary,
    raw_import_summary_path: Path,
    parsed_path: Path,
    normalization_summary: V10NormalizationSummary,
    benchmark_summary: Any,
    receipts: list[Any],
    diagnostics_summary: Any,
    reportability_report: Any,
    config: V10ImportedProviderBridgeConfig,
    diagnostics_paths: dict[str, Path],
) -> V10ImportedProviderBridgeSummary:
    raw_level = (
        reportability_report.evidence_level_allowed
        if reportability_report is not None
        else None
    )
    cap = config.evidence_policy.manual_import_bridge_evidence_level_cap
    final_level = min(raw_level or 0, cap)
    warnings: list[str] = []
    if reportability_report is not None and reportability_report.reportability_passed:
        warnings.append("mechanical_reportability_passed_but_manual_import_cap_applied")
    if normalization_summary.status != "complete":
        warnings.append(f"normalization_status:{normalization_summary.status}")
    if benchmark_summary.status != "complete":
        warnings.append(f"benchmark_status:{benchmark_summary.status}")
    if diagnostics_summary.diagnostics_status != "complete":
        warnings.append(f"diagnostics_status:{diagnostics_summary.diagnostics_status}")
    failed = (
        not config.manual_import_bridge
        or config.allow_network_calls
        or config.allow_provider_sdk_imports
        or config.allow_api_keys
        or config.evidence_policy.manual_import_is_locked_live_provider_evidence
        or config.evidence_policy.manual_import_bridge_evidence_level_cap > 3
        or config.evidence_policy.level_4_allowed
        or config.evidence_policy.level_5_allowed
        or raw_import_summary.api_key_observed
        or raw_import_summary.level_4_allowed
        or raw_import_summary.level_5_allowed
        or normalization_summary.invalid_count > 0
        or benchmark_summary.missing_judgment_case_count > 0
    )
    status: Literal["complete", "needs_work", "failed"] = (
        "failed" if failed else "needs_work" if warnings else "complete"
    )
    payload = {
        "schema_version": "v10_imported_provider_bridge_summary_v1",
        "run_id": raw_import_summary.run_id,
        "provider_run_dir": str(provider_run_dir),
        "manual_import_bridge": True,
        "no_api_calls_made": True,
        "network_calls_attempted": 0,
        "provider_sdk_imported": False,
        "api_key_observed": raw_import_summary.api_key_observed,
        "input_parsed_raw_judgments_path": str(parsed_path),
        "input_parsed_raw_judgments_hash": hash_file(parsed_path),
        "input_raw_import_summary_path": str(raw_import_summary_path),
        "input_raw_import_summary_hash": hash_file(raw_import_summary_path),
        "normalized_output_dir": str(bridge_dir / "normalized_judgments"),
        "benchmark_output_dir": str(bridge_dir / "benchmark_run"),
        "diagnostics_output_dir": str(bridge_dir / "diagnostics"),
        "reportability_output_path": str(diagnostics_paths["reportability_json"]),
        "raw_judgment_count": raw_import_summary.parsed_raw_judgment_count,
        "normalized_judgment_count": normalization_summary.normalized_count,
        "benchmark_receipt_count": len(receipts),
        "matched_case_count": benchmark_summary.matched_case_count,
        "missing_judgment_case_count": benchmark_summary.missing_judgment_case_count,
        "normalization_status": normalization_summary.status,
        "benchmark_status": benchmark_summary.status,
        "diagnostics_status": diagnostics_summary.diagnostics_status,
        "mechanical_reportability_passed": reportability_report.reportability_passed
        if reportability_report
        else None,
        "raw_evidence_level_allowed": raw_level,
        "final_evidence_level": final_level,
        "level_4_allowed": config.evidence_policy.level_4_allowed,
        "level_5_allowed": config.evidence_policy.level_5_allowed,
        "status": status,
        "warnings": sorted(set(warnings)),
    }
    return V10ImportedProviderBridgeSummary(
        **payload,
        bridge_hash=stable_json_hash(payload),
    )


def _input_hashes(
    *,
    provider_run_dir: Path,
    parsed_path: Path,
    raw_import_summary_path: Path,
    full_cases_path: Path,
    filtered_cases_path: Path,
) -> dict[str, Any]:
    provider_manifest_path = provider_run_dir / "provider_run_manifest.json"
    raw_file_hashes_path = provider_run_dir / "raw_file_hashes.json"
    return {
        "schema_version": "v10_imported_provider_bridge_input_hashes_v1",
        "provider_run_dir": str(provider_run_dir),
        "input_parsed_raw_judgments_path": str(parsed_path),
        "input_parsed_raw_judgments_hash": hash_file(parsed_path),
        "input_raw_import_summary_path": str(raw_import_summary_path),
        "input_raw_import_summary_hash": hash_file(raw_import_summary_path),
        "input_provider_manifest_path": str(provider_manifest_path)
        if provider_manifest_path.exists()
        else None,
        "input_provider_manifest_hash": hash_file(provider_manifest_path)
        if provider_manifest_path.exists()
        else None,
        "input_raw_file_hashes_path": str(raw_file_hashes_path)
        if raw_file_hashes_path.exists()
        else None,
        "input_raw_file_hashes_hash": hash_file(raw_file_hashes_path)
        if raw_file_hashes_path.exists()
        else None,
        "full_cases_path": str(full_cases_path),
        "full_cases_hash": hash_file(full_cases_path),
        "filtered_cases_path": str(filtered_cases_path),
        "filtered_cases_hash": hash_file(filtered_cases_path),
    }


def _bridge_manifest(
    *,
    summary: V10ImportedProviderBridgeSummary,
    config_path: Path,
    bridge_config_path: Path,
    input_hashes_path: Path,
    summary_path: Path,
    report_path: Path,
    parsed_path: Path,
    raw_import_summary_path: Path,
    full_cases_path: Path,
    filtered_cases_path: Path,
    all_case_count: int,
    filtered_case_count: int,
    imported_case_count: int,
    normalization_paths: dict[str, Path],
    benchmark_paths: dict[str, Path],
    diagnostics_paths: dict[str, Path],
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_imported_provider_pipeline_bridge_v1",
        "manual_import_bridge_config_path": str(config_path),
        "manual_import_bridge_config_hash": hash_file(config_path),
        "bridge_config_path": str(bridge_config_path),
        "bridge_config_hash": hash_file(bridge_config_path),
        "input_hashes_path": str(input_hashes_path),
        "input_hashes_hash": hash_file(input_hashes_path),
        "bridge_summary_path": str(summary_path),
        "bridge_summary_hash": hash_file(summary_path),
        "bridge_report_path": str(report_path),
        "bridge_report_hash": hash_file(report_path),
        "parsed_raw_judgments_path": str(parsed_path),
        "parsed_raw_judgments_hash": hash_file(parsed_path),
        "raw_import_summary_path": str(raw_import_summary_path),
        "raw_import_summary_hash": hash_file(raw_import_summary_path),
        "case_filtering_policy": {
            "source_cases_path": str(full_cases_path),
            "source_cases_hash": hash_file(full_cases_path),
            "filtered_cases_path": str(filtered_cases_path),
            "filtered_cases_hash": hash_file(filtered_cases_path),
            "source_case_count": all_case_count,
            "imported_judgment_case_count": imported_case_count,
            "filtered_case_count": filtered_case_count,
            "filter_basis": "case_id values from validated parsed_raw_judgments.jsonl",
            "source_cases_modified": False,
        },
        "normalization_summary_hash": hash_file(normalization_paths["summary"]),
        "normalization_manifest_hash": hash_file(normalization_paths["manifest"]),
        "benchmark_summary_hash": hash_file(benchmark_paths["summary"]),
        "benchmark_manifest_hash": hash_file(benchmark_paths["manifest"]),
        "diagnostics_summary_hash": hash_file(diagnostics_paths["summary"]),
        "diagnostics_manifest_hash": hash_file(diagnostics_paths["manifest"]),
        "reportability_report_hash": hash_file(diagnostics_paths["reportability_json"]),
        "bridge_hash": summary.bridge_hash,
        "no_api_calls_made": True,
        "provider_sdk_imported": False,
        "api_key_observed": False,
        "final_evidence_level": summary.final_evidence_level,
        "level_4_allowed": False,
        "level_5_allowed": False,
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Manual import bridge only.",
            "No provider API calls were made.",
            "No provider SDK clients were used.",
            "Imported files were externally saved raw outputs.",
            "Input run was manual import, not locked live API execution.",
            "Existing v10 pipeline was reused.",
            "Final evidence level is capped at 3.",
            "Level 4 and Level 5 are false.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}


def _case_ids_from_raw_judgments(
    parsed_raw_judgments: list[V10RawJudgment] | list[dict[str, Any]],
) -> list[str]:
    case_ids: list[str] = []
    for row in parsed_raw_judgments:
        payload = row.payload if isinstance(row, V10RawJudgment) else row
        case_id = payload.get("case_id") if isinstance(payload, dict) else None
        if isinstance(case_id, str) and case_id:
            case_ids.append(case_id)
    return case_ids


def _write_cases_jsonl(path: Path, cases: list[V10Case]) -> None:
    path.write_text(
        "\n".join(
            json.dumps(case.model_dump(mode="json"), sort_keys=True)
            for case in cases
        )
        + ("\n" if cases else ""),
        encoding="utf-8",
    )

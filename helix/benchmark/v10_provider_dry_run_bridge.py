from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from shutil import copyfile
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.v10_benchmark_runner import (
    build_v10_benchmark_receipts,
    compute_v10_benchmark_metrics,
    load_v10_benchmark_config,
    validate_v10_benchmark_receipts,
    write_v10_benchmark_outputs,
)
from helix.benchmark.v10_diagnostics import (
    bootstrap_v10_metric_cis,
    build_v10_diagnostics_summary,
    compute_v10_selectivity_baselines,
    load_v10_diagnostics_config,
    run_v10_integrity_diagnostic,
    run_v10_reportability_diagnostic,
    write_v10_diagnostics_outputs,
)
from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_judgment_normalization import (
    V10NormalizedJudgment,
    V10NormalizationSummary,
    load_raw_judgments,
    load_v10_normalization_config,
    normalize_v10_judgments,
    write_v10_normalization_outputs,
)
from helix.benchmark.v10_provider_dry_run import V10ProviderDryRunSummary


class V10ProviderDryRunBridgeEvidencePolicy(BaseModel):
    dry_run_is_provider_evidence: bool
    dry_run_bridge_evidence_level_cap: int
    level_4_allowed: bool
    level_5_allowed: bool


class V10ProviderDryRunBridgeConfig(BaseModel):
    schema_version: str
    dry_run_bridge: bool
    default_provider_run_dir: str
    parsed_raw_judgments_filename: str
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
    evidence_policy: V10ProviderDryRunBridgeEvidencePolicy
    notes: str = ""


class V10ProviderDryRunBridgeSummary(BaseModel):
    schema_version: str = "v10_provider_dry_run_bridge_summary_v1"
    run_id: str
    provider_run_dir: str
    dry_run_bridge: bool = True
    no_api_calls_made: bool = True
    network_calls_attempted: int = 0
    provider_sdk_imported: bool = False
    api_key_observed: bool = False
    input_parsed_raw_judgments_path: str
    input_parsed_raw_judgments_hash: str
    input_provider_manifest_path: str
    input_provider_manifest_hash: str
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
            "# HELIX v10 Provider Dry-Run Pipeline Bridge Report",
            "",
            "## Executive Summary",
            "",
            f"- run_id: `{self.run_id}`",
            f"- status: `{self.status}`",
            f"- dry_run_bridge: `{str(self.dry_run_bridge).lower()}`",
            f"- no_api_calls_made: `{str(self.no_api_calls_made).lower()}`",
            f"- raw_judgment_count: `{self.raw_judgment_count}`",
            f"- normalized_judgment_count: `{self.normalized_judgment_count}`",
            f"- benchmark_receipt_count: `{self.benchmark_receipt_count}`",
            f"- matched_case_count: `{self.matched_case_count}`",
            f"- missing_judgment_case_count: `{self.missing_judgment_case_count}`",
            f"- final_evidence_level: `{self.final_evidence_level}`",
            f"- bridge_hash: `{self.bridge_hash}`",
            "",
            "This bridge routes preserved provider dry-run fixture output through the existing v10 pipeline. It does not create real provider evidence.",
            "",
            "## Input Provider Run",
            "",
            f"- provider_run_dir: `{self.provider_run_dir}`",
            f"- input_provider_manifest_hash: `{self.input_provider_manifest_hash}`",
            f"- input_parsed_raw_judgments_hash: `{self.input_parsed_raw_judgments_hash}`",
            "",
            "## Dry-Run Safety Checks",
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
            "- Mechanical reportability, if true, does not raise dry-run evidence beyond Level 2.",
            "",
            "## What This Supports",
            "",
            "- This supports routing provider-run directories into the existing v10 pipeline.",
            "- This supports preserving dry-run provenance while reusing normalization, benchmark, diagnostics, and reportability code.",
            "",
            "## What This Does Not Yet Prove",
            "",
            "- No API calls were made.",
            "- No provider SDK clients were used.",
            "- No real provider judgments were collected.",
            "- The input run was dry-run fixture output.",
            "- This is not Level 4 or Level 5 evidence.",
            "",
            "## Limitations",
            "",
            "- Dry-run bridge evidence is capped at Level 2.",
            "- Pilot dry-run sample size is not final v10 evidence.",
            "- Existing v10 pipeline behavior is reused; no dry-run-specific scoring pass is introduced.",
        ]
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_provider_dry_run_bridge_config(
    path: str | Path,
) -> V10ProviderDryRunBridgeConfig:
    return V10ProviderDryRunBridgeConfig.model_validate_json(
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


def load_provider_dry_run_summary(provider_run_dir: str | Path) -> V10ProviderDryRunSummary:
    run_dir = Path(provider_run_dir)
    summary_path = run_dir / "provider_dry_run_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(
            f"Provider dry-run summary does not exist: {summary_path}. "
            "Run examples/run_v10_provider_dry_run.py first."
        )
    return V10ProviderDryRunSummary.model_validate_json(
        summary_path.read_text(encoding="utf-8")
    )


def validate_provider_run_is_dry_run(provider_run_dir: str | Path) -> list[str]:
    run_dir = Path(provider_run_dir)
    issues: list[str] = []
    try:
        summary = load_provider_dry_run_summary(run_dir)
    except FileNotFoundError:
        return ["missing_provider_dry_run_summary"]
    if not summary.dry_run:
        issues.append("provider_run_not_dry_run")
    if not summary.no_api_calls_made:
        issues.append("provider_run_api_calls_not_excluded")
    if summary.network_calls_attempted != 0:
        issues.append("provider_run_network_calls_attempted")
    if summary.provider_sdk_imported:
        issues.append("provider_run_provider_sdk_imported")
    if summary.api_key_observed:
        issues.append("provider_run_api_key_observed")
    if not (run_dir / "parsed_raw_judgments.jsonl").exists():
        issues.append("missing_parsed_raw_judgments")
    return sorted(set(issues))


def copy_or_reference_parsed_raw_judgments(
    provider_run_dir: str | Path,
    bridge_out_dir: str | Path,
    *,
    parsed_filename: str = "parsed_raw_judgments.jsonl",
) -> Path:
    source = Path(provider_run_dir) / parsed_filename
    if not source.exists():
        raise FileNotFoundError(
            f"Parsed dry-run judgments do not exist: {source}. "
            "Run examples/run_v10_provider_dry_run.py first."
        )
    target = Path(bridge_out_dir) / parsed_filename
    target.parent.mkdir(parents=True, exist_ok=True)
    copyfile(source, target)
    return target


def run_normalization_for_provider_dry_run(
    *,
    raw_judgments_path: str | Path,
    cases: list[V10Case],
    config: V10ProviderDryRunBridgeConfig,
    out_dir: str | Path,
    provider: str | None,
    model: str | None,
) -> tuple[list[V10NormalizedJudgment], V10NormalizationSummary, dict[str, Path]]:
    normalization_config = load_v10_normalization_config(config.normalization_config_path)
    normalized, summary = normalize_v10_judgments(
        load_raw_judgments(raw_judgments_path),
        cases,
        normalization_config,
        provider=provider,
        model=model,
    )
    paths = write_v10_normalization_outputs(
        normalized_judgments=normalized,
        summary=summary,
        config_path=config.normalization_config_path,
        input_cases_path=config.cases_path,
        raw_judgments_path=raw_judgments_path,
        provider=provider,
        model=model,
        out_dir=out_dir,
    )
    return (
        normalized,
        summary,
        {
            "normalized": paths[0],
            "invalid": paths[1],
            "summary": paths[2],
            "manifest": paths[3],
            "report": paths[4],
        },
    )


def run_benchmark_for_provider_dry_run(
    *,
    cases: list[V10Case],
    normalized: list[V10NormalizedJudgment],
    normalization_summary: V10NormalizationSummary,
    normalization_paths: dict[str, Path],
    config: V10ProviderDryRunBridgeConfig,
    out_dir: str | Path,
) -> tuple[Any, list[Any], dict[str, Path]]:
    benchmark_config = load_v10_benchmark_config(config.benchmark_config_path)
    receipts = build_v10_benchmark_receipts(
        cases,
        normalized,
        benchmark_config,
        config_hash=hash_file(config.benchmark_config_path),
        normalization_manifest_hash=hash_file(normalization_paths["manifest"]),
    )
    receipt_issues = validate_v10_benchmark_receipts(
        receipts,
        expected_count=len(cases),
    )
    summary = compute_v10_benchmark_metrics(
        cases,
        normalized,
        benchmark_config,
        normalization_summary=normalization_summary,
        receipt_count=len(receipts),
        receipt_validation_issue_count=len(receipt_issues),
    )
    paths = write_v10_benchmark_outputs(
        summary=summary,
        receipts=receipts,
        cases=cases,
        normalized_judgments=normalized,
        config_path=config.benchmark_config_path,
        input_cases_path=config.cases_path,
        normalized_judgments_path=normalization_paths["normalized"],
        normalization_summary_path=normalization_paths["summary"],
        normalization_manifest_path=normalization_paths["manifest"],
        out_dir=out_dir,
    )
    return (
        summary,
        receipts,
        {
            "receipts": paths[0],
            "summary": paths[1],
            "manifest": paths[2],
            "report": paths[3],
            "failure_cases": paths[4],
        },
    )


def run_diagnostics_for_provider_dry_run(
    *,
    cases_path: str | Path,
    receipts: list[Any],
    benchmark_summary: Any,
    benchmark_paths: dict[str, Path],
    config: V10ProviderDryRunBridgeConfig,
    out_dir: str | Path,
    reportability_out_dir: str | Path,
) -> tuple[Any, Any, dict[str, Path]]:
    diagnostics_config = load_v10_diagnostics_config(config.diagnostics_config_path)
    ci_metrics = bootstrap_v10_metric_cis(receipts, benchmark_summary, diagnostics_config)
    selectivity_baselines = compute_v10_selectivity_baselines(receipts, diagnostics_config)
    bootstrap_payload = {
        "schema_version": "v10_bootstrap_ci_v1",
        "confidence_level": diagnostics_config.confidence_level,
        "resamples": diagnostics_config.bootstrap_resamples,
        "metrics": {
            name: metric.model_dump(mode="json")
            for name, metric in sorted(ci_metrics.items())
        },
    }
    integrity_report, integrity_json_path, _, integrity_warnings = run_v10_integrity_diagnostic(
        cases_path=cases_path,
        receipts=receipts,
        integrity_config_path=config.integrity_config_path,
        out_dir=out_dir,
    )
    reportability_report, reportability_json_path, reportability_md_path = (
        run_reportability_for_provider_dry_run(
            integrity_report=integrity_report,
            benchmark_summary=benchmark_summary,
            bootstrap_payload=bootstrap_payload,
            receipts=receipts,
            selectivity_baselines=selectivity_baselines,
            config=config,
            out_dir=reportability_out_dir,
        )
    )
    diagnostics_summary = build_v10_diagnostics_summary(
        benchmark_run_path=benchmark_paths["summary"].parent,
        bootstrap_ci_path=Path(out_dir) / "v10_bootstrap_ci.json",
        integrity_report_path=integrity_json_path or Path(out_dir) / "v10_integrity_report.json",
        reportability_report_path=reportability_json_path,
        fixture_mode=True,
        benchmark_summary=benchmark_summary,
        config=diagnostics_config,
        ci_metrics=ci_metrics,
        selectivity_baselines=selectivity_baselines,
        integrity_report=integrity_report,
        reportability_report=reportability_report,
        warnings=integrity_warnings,
    )
    diagnostic_paths = write_v10_diagnostics_outputs(
        benchmark_run_dir=out_dir,
        diagnostics_config_path=config.diagnostics_config_path,
        benchmark_summary_path=benchmark_paths["summary"],
        benchmark_receipts_path=benchmark_paths["receipts"],
        benchmark_manifest_path=benchmark_paths["manifest"],
        summary=diagnostics_summary,
        bootstrap_ci=bootstrap_payload,
    )
    return (
        diagnostics_summary,
        reportability_report,
        {
            "bootstrap_ci": diagnostic_paths[0],
            "summary": diagnostic_paths[1],
            "manifest": diagnostic_paths[2],
            "report": diagnostic_paths[3],
            "reportability_json": reportability_json_path,
            "reportability_md": reportability_md_path,
        },
    )


def run_reportability_for_provider_dry_run(
    *,
    integrity_report: Any,
    benchmark_summary: Any,
    bootstrap_payload: dict[str, Any],
    receipts: list[Any],
    selectivity_baselines: Any,
    config: V10ProviderDryRunBridgeConfig,
    out_dir: str | Path,
) -> tuple[Any, Path, Path]:
    return run_v10_reportability_diagnostic(
        integrity_report=integrity_report,
        benchmark_summary=benchmark_summary,
        bootstrap_ci=bootstrap_payload,
        reportability_config_path=config.reportability_config_path,
        out_dir=out_dir,
        receipts=receipts,
        selectivity_baselines=selectivity_baselines,
    )


def write_provider_dry_run_bridge_outputs(
    *,
    provider_run_dir: str | Path,
    cases_path: str | Path,
    config: V10ProviderDryRunBridgeConfig,
    config_path: str | Path,
    out_subdir: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Path]:
    run_dir = Path(provider_run_dir)
    issues = validate_provider_run_is_dry_run(run_dir)
    if issues:
        if "missing_provider_dry_run_summary" in issues:
            raise FileNotFoundError(
                f"Provider dry-run outputs missing in {run_dir}. "
                "Run examples/run_v10_provider_dry_run.py first."
            )
        raise ValueError("Provider dry-run validation failed: " + ", ".join(issues))

    provider_summary = load_provider_dry_run_summary(run_dir)
    bridge_dir = run_dir / (out_subdir or config.output_subdir)
    bridge_dir.mkdir(parents=True, exist_ok=True)
    parsed_copy_path = copy_or_reference_parsed_raw_judgments(
        run_dir,
        bridge_dir,
        parsed_filename=config.parsed_raw_judgments_filename,
    )
    all_cases = load_v10_cases(cases_path)
    cases = _filter_cases_for_plan(all_cases, run_dir)

    normalized, normalization_summary, normalization_paths = (
        run_normalization_for_provider_dry_run(
            raw_judgments_path=parsed_copy_path,
            cases=cases,
            config=config,
            out_dir=bridge_dir / "normalized_judgments",
            provider=provider_summary.provider,
            model=provider_summary.model,
        )
    )
    benchmark_summary, receipts, benchmark_paths = run_benchmark_for_provider_dry_run(
        cases=cases,
        normalized=normalized,
        normalization_summary=normalization_summary,
        normalization_paths=normalization_paths,
        config=config,
        out_dir=bridge_dir / "benchmark_run",
    )
    diagnostics_summary, reportability_report, diagnostics_paths = (
        run_diagnostics_for_provider_dry_run(
            cases_path=cases_path,
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
        provider_summary=provider_summary,
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
    input_hashes = _input_hashes(run_dir, parsed_copy_path)
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
        "normalized_output_dir": normalization_paths["summary"].parent,
        "benchmark_output_dir": benchmark_paths["summary"].parent,
        "diagnostics_output_dir": diagnostics_paths["summary"].parent,
        "reportability_output_path": diagnostics_paths["reportability_json"],
    }


def _filter_cases_for_plan(
    all_cases: list[V10Case],
    provider_run_dir: Path,
) -> list[V10Case]:
    case_ids = _parsed_case_ids(provider_run_dir)
    case_id_set = set(case_ids)
    filtered = [case for case in all_cases if case.case_id in case_id_set]
    return sorted(filtered, key=lambda item: item.case_id)


def _parsed_case_ids(provider_run_dir: Path) -> list[str]:
    parsed_path = provider_run_dir / "parsed_raw_judgments.jsonl"
    if not parsed_path.exists():
        return []
    return [
        json.loads(line)["case_id"]
        for line in parsed_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

def _bridge_summary(
    *,
    provider_run_dir: Path,
    bridge_dir: Path,
    provider_summary: V10ProviderDryRunSummary,
    parsed_path: Path,
    normalization_summary: V10NormalizationSummary,
    benchmark_summary: Any,
    receipts: list[Any],
    diagnostics_summary: Any,
    reportability_report: Any,
    config: V10ProviderDryRunBridgeConfig,
    diagnostics_paths: dict[str, Path],
) -> V10ProviderDryRunBridgeSummary:
    raw_level = (
        reportability_report.evidence_level_allowed
        if reportability_report is not None
        else None
    )
    cap = config.evidence_policy.dry_run_bridge_evidence_level_cap
    final_level = min(raw_level or 0, cap)
    warnings = []
    if reportability_report is not None and reportability_report.reportability_passed:
        warnings.append("mechanical_reportability_passed_but_dry_run_cap_applied")
    if normalization_summary.status != "complete":
        warnings.append(f"normalization_status:{normalization_summary.status}")
    if benchmark_summary.status != "complete":
        warnings.append(f"benchmark_status:{benchmark_summary.status}")
    if diagnostics_summary.diagnostics_status != "complete":
        warnings.append(f"diagnostics_status:{diagnostics_summary.diagnostics_status}")
    failed = (
        not config.dry_run_bridge
        or config.allow_network_calls
        or config.allow_provider_sdk_imports
        or config.allow_api_keys
        or normalization_summary.invalid_count > 0
        or benchmark_summary.missing_judgment_case_count > 0
    )
    status: Literal["complete", "needs_work", "failed"] = (
        "failed" if failed else "needs_work" if warnings else "complete"
    )
    payload = {
        "schema_version": "v10_provider_dry_run_bridge_summary_v1",
        "run_id": provider_summary.run_id,
        "provider_run_dir": str(provider_run_dir),
        "dry_run_bridge": True,
        "no_api_calls_made": True,
        "network_calls_attempted": 0,
        "provider_sdk_imported": False,
        "api_key_observed": False,
        "input_parsed_raw_judgments_path": str(parsed_path),
        "input_parsed_raw_judgments_hash": hash_file(parsed_path),
        "input_provider_manifest_path": str(provider_run_dir / "provider_run_manifest.json"),
        "input_provider_manifest_hash": hash_file(provider_run_dir / "provider_run_manifest.json"),
        "normalized_output_dir": str(bridge_dir / "normalized_judgments"),
        "benchmark_output_dir": str(bridge_dir / "benchmark_run"),
        "diagnostics_output_dir": str(bridge_dir / "diagnostics"),
        "reportability_output_path": str(diagnostics_paths["reportability_json"]),
        "raw_judgment_count": provider_summary.parsed_raw_judgment_count,
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
    return V10ProviderDryRunBridgeSummary(
        **payload,
        bridge_hash=stable_json_hash(payload),
    )


def _input_hashes(provider_run_dir: Path, parsed_path: Path) -> dict[str, Any]:
    return {
        "schema_version": "v10_provider_dry_run_bridge_input_hashes_v1",
        "provider_run_dir": str(provider_run_dir),
        "input_parsed_raw_judgments_path": str(parsed_path),
        "input_parsed_raw_judgments_hash": hash_file(parsed_path),
        "input_provider_manifest_path": str(provider_run_dir / "provider_run_manifest.json"),
        "input_provider_manifest_hash": hash_file(provider_run_dir / "provider_run_manifest.json"),
        "input_provider_summary_path": str(provider_run_dir / "provider_dry_run_summary.json"),
        "input_provider_summary_hash": hash_file(provider_run_dir / "provider_dry_run_summary.json"),
    }


def _bridge_manifest(
    *,
    summary: V10ProviderDryRunBridgeSummary,
    config_path: Path,
    bridge_config_path: Path,
    input_hashes_path: Path,
    summary_path: Path,
    report_path: Path,
    parsed_path: Path,
    normalization_paths: dict[str, Path],
    benchmark_paths: dict[str, Path],
    diagnostics_paths: dict[str, Path],
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_provider_dry_run_pipeline_bridge_v1",
        "dry_run_bridge_config_path": str(config_path),
        "dry_run_bridge_config_hash": hash_file(config_path),
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
        "level_4_allowed": False,
        "level_5_allowed": False,
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Dry-run bridge only.",
            "No provider API calls were made.",
            "No provider SDK clients were used.",
            "No real provider judgments were collected.",
            "Existing v10 pipeline was reused.",
            "Final evidence level is capped at 2.",
            "Level 4 and Level 5 are false.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}

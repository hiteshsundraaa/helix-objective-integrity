from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
from shutil import copyfile
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.v10_provider_protocol import V10ProviderRunPlan


SECRET_FIELD_TOKENS = {
    "api_key",
    "secret",
    "token",
    "authorization",
    "bearer",
    "password",
    "credential",
}

ALLOWED_DECISIONS = {
    "ALLOW",
    "WARN",
    "DEGRADE",
    "QUARANTINE",
    "BLOCK",
    "ESCALATE_FOR_APPROVAL",
}

ALLOWED_CITATION_METHODS = {
    "exact_substring",
    "normalized_substring",
    "semantic_similarity",
    "unverified",
}


class V10ProviderRawImportEvidencePolicy(BaseModel):
    manual_external_import_is_live_api_evidence: bool
    manual_external_import_evidence_level_cap: int
    level_4_allowed_without_locked_live_runner: bool
    level_5_allowed: bool


class V10ProviderRawImportConfig(BaseModel):
    schema_version: str
    validator_only: bool
    default_plan_path: str
    default_import_root: str
    default_output_root: str
    external_raw_subdir: str
    parsed_raw_judgments_filename: str
    required_raw_files: list[str]
    optional_raw_files: list[str]
    allowed_response_formats: list[str]
    required_provider_metadata_fields: list[str]
    required_response_metadata_fields: list[str]
    allow_network_calls: bool
    allow_provider_sdk_imports: bool
    allow_api_keys: bool
    evidence_policy: V10ProviderRawImportEvidencePolicy
    notes: str = ""


class V10ProviderRawImportFileRecord(BaseModel):
    batch_id: str
    request_manifest_path: str
    raw_response_path: str
    raw_text_path: str | None = None
    request_manifest_hash: str
    raw_response_hash: str
    raw_text_hash: str | None = None
    case_ids: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    prompt_hash: str | None = None
    request_timestamp: str | None = None
    response_timestamp: str | None = None
    status: Literal["complete", "needs_work", "failed"]
    issues: list[str] = Field(default_factory=list)


class V10ProviderRawImportValidationSummary(BaseModel):
    schema_version: str = "v10_provider_raw_import_validation_summary_v1"
    run_id: str
    validator_only: bool = True
    no_api_calls_made: bool = True
    network_calls_attempted: int = 0
    provider_sdk_imported: bool = False
    api_key_observed: bool = False
    plan_path: str
    plan_hash: str
    import_dir: str
    output_provider_run_dir: str
    expected_case_count: int
    imported_case_count: int
    parsed_raw_judgment_count: int
    missing_case_count: int
    duplicate_case_count: int
    unexpected_case_count: int
    malformed_judgment_count: int
    raw_file_count: int
    batch_count: int
    provider: str | None = None
    model: str | None = None
    prompt_hashes_observed: list[str] = Field(default_factory=list)
    provider_metadata_complete: bool
    response_metadata_complete: bool
    validation_status: Literal["complete", "needs_work", "failed"]
    parsed_raw_judgments_written: bool
    evidence_level_cap: int
    level_4_allowed: bool = False
    level_5_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    import_hash: str

    def to_markdown(self) -> str:
        lines = [
            "# HELIX v10 Provider Raw-Output Import Validation Report",
            "",
            "## Executive Summary",
            "",
            f"- run_id: `{self.run_id}`",
            f"- validation_status: `{self.validation_status}`",
            f"- expected_case_count: `{self.expected_case_count}`",
            f"- imported_case_count: `{self.imported_case_count}`",
            f"- parsed_raw_judgment_count: `{self.parsed_raw_judgment_count}`",
            f"- malformed_judgment_count: `{self.malformed_judgment_count}`",
            f"- api_key_observed: `{str(self.api_key_observed).lower()}`",
            f"- parsed_raw_judgments_written: `{str(self.parsed_raw_judgments_written).lower()}`",
            f"- evidence_level_cap: `{self.evidence_level_cap}`",
            f"- import_hash: `{self.import_hash}`",
            "",
            "No API calls were made. No provider SDK clients were used. Imported files are externally saved raw outputs.",
            "",
            "## Import Inputs",
            "",
            f"- import_dir: `{self.import_dir}`",
            f"- plan_path: `{self.plan_path}`",
            f"- output_provider_run_dir: `{self.output_provider_run_dir}`",
            "",
            "## Raw File Preservation",
            "",
            f"- raw_file_count: `{self.raw_file_count}`",
            f"- batch_count: `{self.batch_count}`",
            "",
            "## Request Manifest Validation",
            "",
            f"- provider_metadata_complete: `{str(self.provider_metadata_complete).lower()}`",
            f"- provider: `{self.provider}`",
            f"- model: `{self.model}`",
            "",
            "## Raw Response Parsing",
            "",
            f"- response_metadata_complete: `{str(self.response_metadata_complete).lower()}`",
            f"- parsed_raw_judgment_count: `{self.parsed_raw_judgment_count}`",
            "",
            "## Judgment Schema Validation",
            "",
            f"- malformed_judgment_count: `{self.malformed_judgment_count}`",
            "",
            "## Case Coverage",
            "",
            f"- missing_case_count: `{self.missing_case_count}`",
            f"- duplicate_case_count: `{self.duplicate_case_count}`",
            f"- unexpected_case_count: `{self.unexpected_case_count}`",
            "",
            "## Metadata and Hash Linking",
            "",
            f"- prompt_hashes_observed: `{self.prompt_hashes_observed}`",
            f"- plan_hash: `{self.plan_hash}`",
            "",
            "## Evidence-Level Cap",
            "",
            f"- evidence_level_cap: `{self.evidence_level_cap}`",
            "- Level 4 false unless a future locked live runner or explicit complete external provenance policy permits it.",
            "- Level 5 false.",
            "",
            "## What This Supports",
            "",
            "- This supports strict validation of externally saved provider raw outputs.",
            "- This supports raw-file preservation and hash-linking before normalization.",
            "",
            "## What This Does Not Yet Prove",
            "",
            "- This is not live API execution.",
            "- This is not a provider SDK integration.",
            "- This does not collect provider judgments.",
            "- Manual import is not locked live-run evidence.",
            "- This does not normalize, benchmark, diagnose, or claim reportability.",
            "",
            "## Limitations",
            "",
            "- Manual external imports are capped at Level 3.",
            "- Level 4 and Level 5 are false in this validator.",
            "- Invalid imports are preserved and reported, not repaired.",
        ]
        if self.issues:
            lines.extend(["", "## Issues", ""])
            lines.extend(f"- `{issue}`" for issue in self.issues)
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_provider_raw_import_config(path: str | Path) -> V10ProviderRawImportConfig:
    return V10ProviderRawImportConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_provider_run_plan(path: str | Path) -> V10ProviderRunPlan:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"Provider run plan does not exist: {target}. "
            "Run examples/plan_v10_provider_run.py first."
        )
    return V10ProviderRunPlan.model_validate_json(target.read_text(encoding="utf-8"))


def discover_external_raw_files(import_dir: str | Path) -> tuple[list[dict[str, Path | None]], list[str], Path]:
    root = Path(import_dir)
    if not root.exists():
        raise FileNotFoundError("Import directory not found.")
    root_batches = _discover_in_dir(root)
    external_dir = root / "external_raw"
    external_batches = _discover_in_dir(external_dir) if external_dir.exists() else []
    warnings: list[str] = []
    if root_batches and external_batches:
        warnings.append("root_and_external_raw_present_preferred_external_raw")
    source_dir = external_dir if external_batches else root
    return (external_batches or root_batches, warnings, source_dir)


def validate_request_manifest(
    record: V10ProviderRawImportFileRecord,
    plan: V10ProviderRunPlan,
) -> list[str]:
    issues: list[str] = []
    payload = _read_json(record.request_manifest_path)
    if not isinstance(payload, dict):
        return ["request_manifest_not_object"]
    if _contains_secret_field(payload):
        issues.append("secret_or_api_key_field_observed")
    for field in ["provider", "model", "prompt_hash", "case_ids", "request_timestamp"]:
        if field not in payload or payload.get(field) in (None, "", []):
            issues.append(f"missing_request_metadata:{field}")
    batch_id = payload.get("batch_id")
    if batch_id != record.batch_id:
        issues.append("request_manifest_batch_id_mismatch")
    case_ids = payload.get("case_ids")
    if not isinstance(case_ids, list) or not case_ids or not all(isinstance(item, str) for item in case_ids):
        issues.append("request_manifest_invalid_case_ids")
    else:
        unexpected = sorted(set(case_ids) - set(plan.sampled_case_ids))
        if unexpected:
            issues.append("request_manifest_case_ids_not_subset_of_plan")
    prompt_hash = payload.get("prompt_hash")
    expected_prompt_hash = _expected_prompt_hash(plan)
    if expected_prompt_hash and prompt_hash != expected_prompt_hash:
        issues.append("prompt_hash_mismatch")
    return issues


def parse_raw_response_file(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    raw = target.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        judgments = []
        issues = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                issues.append(f"jsonl_line_invalid:{line_number}")
                continue
            judgments.append(row)
        return {
            "format": "jsonl_text",
            "judgments": judgments,
            "metadata": {"response_hash": hash_file(target)},
            "issues": issues,
        }
    if isinstance(payload, list):
        return {
            "format": "json_array",
            "judgments": payload,
            "metadata": {"response_hash": hash_file(target)},
            "issues": [],
        }
    if isinstance(payload, dict) and isinstance(payload.get("judgments"), list):
        metadata = {
            "batch_id": payload.get("batch_id"),
            "provider": payload.get("provider"),
            "model": payload.get("model"),
            "response_timestamp": payload.get("response_timestamp"),
            "response_hash": payload.get("response_hash") or hash_file(target),
        }
        return {
            "format": "json_object_with_judgments",
            "judgments": payload["judgments"],
            "metadata": metadata,
            "issues": [],
        }
    return {
        "format": "unsupported",
        "judgments": [],
        "metadata": {"response_hash": hash_file(target)},
        "issues": ["unsupported_raw_response_format"],
    }


def validate_provider_judgment_schema(judgment: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(judgment, dict):
        return ["judgment_not_object"]
    for field in [
        "case_id",
        "decision",
        "violation_probability",
        "cited_contract_phrase",
        "citation_verification_method",
        "reason_codes",
    ]:
        if field not in judgment:
            issues.append(f"missing_judgment_field:{field}")
    case_id = judgment.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        issues.append("invalid_case_id")
    decision = judgment.get("decision")
    if decision not in ALLOWED_DECISIONS:
        issues.append("invalid_decision")
    score = judgment.get("violation_probability")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        issues.append("invalid_violation_probability")
    elif score < 0 or score > 1:
        issues.append("violation_probability_out_of_range")
    method = judgment.get("citation_verification_method")
    if method not in ALLOWED_CITATION_METHODS:
        issues.append("invalid_citation_verification_method")
    if not isinstance(judgment.get("cited_contract_phrase", ""), str):
        issues.append("invalid_cited_contract_phrase")
    reason_codes = judgment.get("reason_codes")
    if (
        not isinstance(reason_codes, list)
        or not reason_codes
        or not all(isinstance(item, str) and item for item in reason_codes)
    ):
        issues.append("invalid_reason_codes")
    uncertainty = judgment.get("uncertainty_reason")
    if uncertainty is not None and not isinstance(uncertainty, str):
        issues.append("invalid_uncertainty_reason")
    return issues


def validate_case_coverage(
    parsed_judgments: list[dict[str, Any]],
    expected_case_ids: list[str],
) -> dict[str, Any]:
    ids = [row.get("case_id") for row in parsed_judgments if isinstance(row.get("case_id"), str)]
    counts = Counter(ids)
    expected = set(expected_case_ids)
    observed = set(ids)
    duplicate_case_ids = sorted(case_id for case_id, count in counts.items() if count > 1)
    missing_case_ids = sorted(expected - observed)
    unexpected_case_ids = sorted(observed - expected)
    return {
        "expected_case_count": len(expected_case_ids),
        "imported_case_count": len(ids),
        "missing_case_ids": missing_case_ids,
        "duplicate_case_ids": duplicate_case_ids,
        "unexpected_case_ids": unexpected_case_ids,
        "missing_case_count": len(missing_case_ids),
        "duplicate_case_count": len(duplicate_case_ids),
        "unexpected_case_count": len(unexpected_case_ids),
    }


def write_imported_provider_run_outputs(
    *,
    config: V10ProviderRawImportConfig,
    config_path: str | Path,
    plan: V10ProviderRunPlan,
    plan_path: str | Path,
    import_dir: str | Path,
    run_id: str,
    out_root: str | Path,
    generated_at: str | None = None,
) -> dict[str, Path]:
    output_dir = Path(out_root) / run_id
    external_raw_dir = output_dir / config.external_raw_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    external_raw_dir.mkdir(parents=True, exist_ok=True)

    discovered, discovery_warnings, source_dir = discover_external_raw_files(import_dir)
    copied_records = _copy_raw_files(discovered, external_raw_dir)
    evaluation = _evaluate_copied_records(
        copied_records=copied_records,
        plan=plan,
        config=config,
    )
    coverage = validate_case_coverage(evaluation["valid_judgments"], plan.sampled_case_ids)
    api_key_observed = evaluation["api_key_observed"]
    issues = sorted(set(evaluation["issues"]))
    warnings = sorted(set(discovery_warnings + evaluation["warnings"]))
    provider_metadata_complete = _provider_metadata_complete(copied_records)
    response_metadata_complete = _response_metadata_complete(copied_records)
    fatal = api_key_observed
    parsed_written = False
    parsed_path = output_dir / config.parsed_raw_judgments_filename
    if not fatal:
        parsed_path.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in evaluation["valid_judgments"])
            + ("\n" if evaluation["valid_judgments"] else ""),
            encoding="utf-8",
        )
        parsed_written = True
    elif parsed_path.exists():
        parsed_path.unlink()

    validation_status = _validation_status(
        api_key_observed=api_key_observed,
        provider_metadata_complete=provider_metadata_complete,
        response_metadata_complete=response_metadata_complete,
        coverage=coverage,
        malformed_judgment_count=evaluation["malformed_judgment_count"],
        issues=issues,
    )
    providers = sorted({record.provider for record in copied_records if record.provider})
    models = sorted({record.model for record in copied_records if record.model})
    prompt_hashes = sorted({record.prompt_hash for record in copied_records if record.prompt_hash})
    file_records = [
        record.model_dump(mode="json")
        for record in copied_records
    ]
    raw_file_hashes = _raw_file_hashes(copied_records)
    summary = _summary(
        run_id=run_id,
        config=config,
        plan=plan,
        plan_path=Path(plan_path),
        import_dir=Path(import_dir),
        output_dir=output_dir,
        provider=providers[0] if len(providers) == 1 else None,
        model=models[0] if len(models) == 1 else None,
        prompt_hashes_observed=prompt_hashes,
        provider_metadata_complete=provider_metadata_complete,
        response_metadata_complete=response_metadata_complete,
        coverage=coverage,
        parsed_raw_judgment_count=len(evaluation["valid_judgments"]),
        malformed_judgment_count=evaluation["malformed_judgment_count"],
        raw_file_count=sum(
            2 + (1 if record.raw_text_path else 0)
            for record in copied_records
        ),
        batch_count=len(copied_records),
        api_key_observed=api_key_observed,
        parsed_written=parsed_written,
        validation_status=validation_status,
        warnings=warnings,
        issues=issues,
    )

    provider_config_path = output_dir / "provider_run_config.json"
    manifest_path = output_dir / "provider_run_manifest.json"
    prompt_hashes_path = output_dir / "prompt_hashes.json"
    sampled_case_ids_path = output_dir / "sampled_case_ids.json"
    summary_path = output_dir / "raw_import_validation_summary.json"
    report_path = output_dir / "raw_import_validation_report.md"
    issues_path = output_dir / "raw_import_validation_issues.json"
    raw_hashes_path = output_dir / "raw_file_hashes.json"

    provider_config_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_provider_raw_import_config_snapshot_v1",
                "validator_config": config.model_dump(mode="json"),
                "plan": plan.model_dump(mode="json"),
                "validator_only": True,
                "no_api_calls_made": True,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    prompt_hashes_path.write_text(
        json.dumps({"observed": prompt_hashes, "plan": plan.prompt_hashes}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    sampled_case_ids_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_provider_raw_import_sampled_case_ids_v1",
                "run_id": run_id,
                "case_count": len(plan.sampled_case_ids),
                "sampled_case_ids": plan.sampled_case_ids,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(write_import_validation_report(summary) + "\n", encoding="utf-8")
    issues_path.write_text(
        json.dumps(
            {
                "schema_version": "v10_provider_raw_import_issues_v1",
                "issues": issues,
                "warnings": warnings,
                "missing_case_ids": coverage["missing_case_ids"],
                "duplicate_case_ids": coverage["duplicate_case_ids"],
                "unexpected_case_ids": coverage["unexpected_case_ids"],
                "file_records": file_records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    raw_hashes_path.write_text(
        json.dumps(raw_file_hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = _manifest(
        config_path=Path(config_path),
        plan_path=Path(plan_path),
        import_dir=Path(import_dir),
        source_dir=source_dir,
        output_dir=output_dir,
        summary=summary,
        parsed_path=parsed_path if parsed_written else None,
        raw_file_hashes=raw_file_hashes,
        generated_at=generated_at,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "output_provider_run_dir": output_dir,
        "provider_run_config": provider_config_path,
        "provider_run_manifest": manifest_path,
        "prompt_hashes": prompt_hashes_path,
        "sampled_case_ids": sampled_case_ids_path,
        "parsed_raw_judgments": parsed_path,
        "raw_import_validation_summary": summary_path,
        "raw_import_validation_report": report_path,
        "raw_import_validation_issues": issues_path,
        "raw_file_hashes": raw_hashes_path,
    }


def write_import_validation_report(summary: V10ProviderRawImportValidationSummary) -> str:
    return summary.to_markdown()


def _discover_in_dir(directory: Path) -> list[dict[str, Path | None]]:
    if not directory.exists():
        return []
    request_files = sorted(directory.glob("request_manifest_*.json"))
    records: list[dict[str, Path | None]] = []
    for request_path in request_files:
        batch_id = _batch_id_from_name(request_path.name, "request_manifest_")
        raw_response = directory / f"raw_response_{batch_id}.json"
        raw_text = directory / f"raw_text_{batch_id}.txt"
        records.append(
            {
                "batch_id": batch_id,
                "request_manifest_path": request_path,
                "raw_response_path": raw_response if raw_response.exists() else None,
                "raw_text_path": raw_text if raw_text.exists() else None,
            }
        )
    return records


def _batch_id_from_name(name: str, prefix: str) -> str:
    stem = Path(name).stem
    return stem.removeprefix(prefix)


def _copy_raw_files(records: list[dict[str, Path | None]], external_raw_dir: Path) -> list[V10ProviderRawImportFileRecord]:
    copied: list[V10ProviderRawImportFileRecord] = []
    for record in records:
        batch_id = str(record["batch_id"])
        issues: list[str] = []
        request_source = record["request_manifest_path"]
        response_source = record["raw_response_path"]
        text_source = record.get("raw_text_path")
        if request_source is None or not Path(request_source).exists():
            issues.append("missing_request_manifest")
            continue
        if response_source is None or not Path(response_source).exists():
            issues.append("missing_raw_response")
            continue
        request_target = external_raw_dir / f"request_manifest_{batch_id}.json"
        response_target = external_raw_dir / f"raw_response_{batch_id}.json"
        copyfile(request_source, request_target)
        copyfile(response_source, response_target)
        text_target = None
        if text_source is not None and Path(text_source).exists():
            text_target = external_raw_dir / f"raw_text_{batch_id}.txt"
            copyfile(text_source, text_target)
        manifest = _read_json(request_target)
        copied.append(
            V10ProviderRawImportFileRecord(
                batch_id=batch_id,
                request_manifest_path=str(request_target),
                raw_response_path=str(response_target),
                raw_text_path=str(text_target) if text_target else None,
                request_manifest_hash=hash_file(request_target),
                raw_response_hash=hash_file(response_target),
                raw_text_hash=hash_file(text_target) if text_target else None,
                case_ids=list(manifest.get("case_ids", [])) if isinstance(manifest, dict) else [],
                provider=manifest.get("provider") if isinstance(manifest, dict) else None,
                model=manifest.get("model") if isinstance(manifest, dict) else None,
                prompt_hash=manifest.get("prompt_hash") if isinstance(manifest, dict) else None,
                request_timestamp=manifest.get("request_timestamp") if isinstance(manifest, dict) else None,
                response_timestamp=manifest.get("response_timestamp") if isinstance(manifest, dict) else None,
                status="needs_work" if issues else "complete",
                issues=issues,
            )
        )
    return copied


def _evaluate_copied_records(
    *,
    copied_records: list[V10ProviderRawImportFileRecord],
    plan: V10ProviderRunPlan,
    config: V10ProviderRawImportConfig,
) -> dict[str, Any]:
    valid_judgments: list[dict[str, Any]] = []
    issues: list[str] = []
    warnings: list[str] = []
    malformed_count = 0
    api_key_observed = False
    for record in copied_records:
        manifest_payload = _read_json(record.request_manifest_path)
        record_issues = validate_request_manifest(record, plan)
        if "secret_or_api_key_field_observed" in record_issues:
            api_key_observed = True
        parsed = parse_raw_response_file(record.raw_response_path)
        if parsed["format"] not in set(config.allowed_response_formats):
            record_issues.append("raw_response_format_not_allowed")
        record_issues.extend(parsed["issues"])
        response_timestamp = parsed["metadata"].get("response_timestamp") or (
            manifest_payload.get("response_timestamp") if isinstance(manifest_payload, dict) else None
        )
        if response_timestamp:
            record.response_timestamp = str(response_timestamp)
        if not response_timestamp:
            record_issues.append("missing_response_metadata:response_timestamp")
        if not parsed["metadata"].get("response_hash"):
            record_issues.append("missing_response_metadata:response_hash")
        for index, row in enumerate(parsed["judgments"], start=1):
            judgment_issues = validate_provider_judgment_schema(row)
            if judgment_issues:
                malformed_count += 1
                record_issues.extend(
                    f"malformed_judgment:{record.batch_id}:{index}:{issue}"
                    for issue in judgment_issues
                )
            else:
                valid_judgments.append(row)
        record.issues.extend(sorted(set(record_issues)))
        record.status = "failed" if api_key_observed else "needs_work" if record.issues else "complete"
        if record.issues:
            issues.extend(f"{record.batch_id}:{issue}" for issue in record.issues)
    if not copied_records:
        issues.append("no_raw_batches_discovered")
    return {
        "valid_judgments": valid_judgments,
        "issues": issues,
        "warnings": warnings,
        "malformed_judgment_count": malformed_count,
        "api_key_observed": api_key_observed,
    }


def _validation_status(
    *,
    api_key_observed: bool,
    provider_metadata_complete: bool,
    response_metadata_complete: bool,
    coverage: dict[str, Any],
    malformed_judgment_count: int,
    issues: list[str],
) -> Literal["complete", "needs_work", "failed"]:
    if api_key_observed:
        return "failed"
    needs_work = (
        not provider_metadata_complete
        or not response_metadata_complete
        or coverage["missing_case_count"] > 0
        or coverage["duplicate_case_count"] > 0
        or coverage["unexpected_case_count"] > 0
        or malformed_judgment_count > 0
        or bool(issues)
    )
    return "needs_work" if needs_work else "complete"


def _provider_metadata_complete(records: list[V10ProviderRawImportFileRecord]) -> bool:
    return bool(records) and all(
        record.provider
        and record.model
        and record.prompt_hash
        and record.case_ids
        and record.request_timestamp
        for record in records
    )


def _response_metadata_complete(records: list[V10ProviderRawImportFileRecord]) -> bool:
    # response_hash is always recomputed from preserved raw response files.
    return bool(records) and all(record.response_timestamp for record in records)


def _summary(
    *,
    run_id: str,
    config: V10ProviderRawImportConfig,
    plan: V10ProviderRunPlan,
    plan_path: Path,
    import_dir: Path,
    output_dir: Path,
    provider: str | None,
    model: str | None,
    prompt_hashes_observed: list[str],
    provider_metadata_complete: bool,
    response_metadata_complete: bool,
    coverage: dict[str, Any],
    parsed_raw_judgment_count: int,
    malformed_judgment_count: int,
    raw_file_count: int,
    batch_count: int,
    api_key_observed: bool,
    parsed_written: bool,
    validation_status: Literal["complete", "needs_work", "failed"],
    warnings: list[str],
    issues: list[str],
) -> V10ProviderRawImportValidationSummary:
    payload = {
        "schema_version": "v10_provider_raw_import_validation_summary_v1",
        "run_id": run_id,
        "validator_only": True,
        "no_api_calls_made": True,
        "network_calls_attempted": 0,
        "provider_sdk_imported": False,
        "api_key_observed": api_key_observed,
        "plan_path": str(plan_path),
        "plan_hash": plan.plan_hash,
        "import_dir": str(import_dir),
        "output_provider_run_dir": str(output_dir),
        "expected_case_count": coverage["expected_case_count"],
        "imported_case_count": coverage["imported_case_count"],
        "parsed_raw_judgment_count": parsed_raw_judgment_count,
        "missing_case_count": coverage["missing_case_count"],
        "duplicate_case_count": coverage["duplicate_case_count"],
        "unexpected_case_count": coverage["unexpected_case_count"],
        "malformed_judgment_count": malformed_judgment_count,
        "raw_file_count": raw_file_count,
        "batch_count": batch_count,
        "provider": provider,
        "model": model,
        "prompt_hashes_observed": prompt_hashes_observed,
        "provider_metadata_complete": provider_metadata_complete,
        "response_metadata_complete": response_metadata_complete,
        "validation_status": validation_status,
        "parsed_raw_judgments_written": parsed_written,
        "evidence_level_cap": config.evidence_policy.manual_external_import_evidence_level_cap,
        "level_4_allowed": config.evidence_policy.level_4_allowed_without_locked_live_runner,
        "level_5_allowed": config.evidence_policy.level_5_allowed,
        "warnings": sorted(set(warnings)),
        "issues": sorted(set(issues)),
    }
    return V10ProviderRawImportValidationSummary(
        **payload,
        import_hash=stable_json_hash(payload),
    )


def _manifest(
    *,
    config_path: Path,
    plan_path: Path,
    import_dir: Path,
    source_dir: Path,
    output_dir: Path,
    summary: V10ProviderRawImportValidationSummary,
    parsed_path: Path | None,
    raw_file_hashes: dict[str, Any],
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_provider_raw_import_v1",
        "import_config_path": str(config_path),
        "import_config_hash": hash_file(config_path),
        "plan_path": str(plan_path),
        "plan_hash": hash_file(plan_path),
        "import_dir": str(import_dir),
        "import_dir_hash": _directory_hash(source_dir),
        "output_provider_run_dir": str(output_dir),
        "expected_case_ids_hash": stable_json_hash(
            json.loads((output_dir / "sampled_case_ids.json").read_text(encoding="utf-8"))["sampled_case_ids"]
        )
        if (output_dir / "sampled_case_ids.json").exists()
        else None,
        "parsed_raw_judgments_hash": hash_file(parsed_path) if parsed_path and parsed_path.exists() else None,
        "raw_file_hashes": raw_file_hashes,
        "validation_status": summary.validation_status,
        "no_api_calls_made": True,
        "network_calls_attempted": 0,
        "provider_sdk_imported": False,
        "api_key_observed": summary.api_key_observed,
        "evidence_level_cap": summary.evidence_level_cap,
        "level_4_allowed": summary.level_4_allowed,
        "level_5_allowed": summary.level_5_allowed,
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Validator only.",
            "No provider API calls were made.",
            "No provider SDK clients were used.",
            "Imported files are externally saved raw outputs.",
            "Manual import is not locked live-run evidence.",
            "Evidence is capped at Level 3.",
            "Level 4 and Level 5 are false.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}


def _raw_file_hashes(records: list[V10ProviderRawImportFileRecord]) -> dict[str, Any]:
    return {
        "schema_version": "v10_provider_raw_import_raw_file_hashes_v1",
        "batches": {
            record.batch_id: {
                "request_manifest_hash": record.request_manifest_hash,
                "raw_response_hash": record.raw_response_hash,
                "raw_text_hash": record.raw_text_hash,
            }
            for record in records
        },
    }


def _directory_hash(directory: Path) -> str:
    entries = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        entries.append({"path": str(path.relative_to(directory)), "hash": hash_file(path)})
    return stable_json_hash(entries)


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if _is_secret_field_name(lowered):
                return True
            if _contains_secret_field(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_field(item) for item in value)
    return False


def _is_secret_field_name(lowered_key: str) -> bool:
    if lowered_key in SECRET_FIELD_TOKENS:
        return True
    return (
        lowered_key.endswith("_token")
        or lowered_key.endswith("-token")
        or lowered_key in {"apikey", "auth_token", "access_token", "refresh_token"}
    )


def _expected_prompt_hash(plan: V10ProviderRunPlan) -> str | None:
    if plan.prompt_mode == "generic":
        return plan.prompt_hashes.get("generic_prompt")
    return plan.prompt_hashes.get("contract_prompt")

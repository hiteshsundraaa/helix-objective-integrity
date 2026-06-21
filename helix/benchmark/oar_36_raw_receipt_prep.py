from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OAR36RawReceiptPrepConfig:
    schema_version: str
    suite_name: str
    source_suite: str
    protocol_version: str
    expected_raw_output_file_count: int
    expected_case_count: int
    expected_system_count: int
    manual_result_evidence_cap: int
    ground_truth_use_allowed: bool
    score_against_holdout: bool
    no_provider_calls: bool
    no_fake_outputs: bool
    no_empirical_results_without_raw: bool
    preserve_raw_outputs: bool
    allowed_decisions: list[str]
    allowed_citation_verification_methods: list[str]
    required_output_fields: list[str]
    notes: str


@dataclass(frozen=True)
class OAR36RawFileInventoryRecord:
    expected_filename: str
    expected_relative_path: str
    resolved_path: str
    system_role: str
    provider: str
    model: str
    present: bool
    file_size_bytes: int
    file_hash: str | None
    line_count: int
    readable: bool
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36RawSchemaLintRecord:
    expected_filename: str
    present: bool
    line_count: int
    parseable_json_line_count: int
    malformed_json_line_count: int
    records_with_required_fields: int
    records_missing_required_fields: int
    unknown_case_id_count: int
    duplicate_case_id_count: int
    invalid_decision_count: int
    invalid_score_count: int
    invalid_citation_method_count: int
    judgment_like_records_count: int
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36NormalizedJudgmentRecord:
    schema_version: str
    suite: str
    case_id: str | None
    system_role: str
    provider: str
    model: str
    source_file: str
    line_number: int
    decision: str | None
    violation_probability: float | None
    cited_contract_phrase: str | None
    citation_verification_method: str | None
    reason_codes: list[str] | None
    parse_status: str
    raw_line_hash: str
    normalized_judgment_hash: str
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36ReceiptPreparationRecord:
    schema_version: str
    suite: str
    case_id: str | None
    system_role: str
    provider: str
    model: str
    source_file: str
    case_hash: str | None
    prompt_hash: str | None
    raw_line_hash: str
    normalized_judgment_hash: str
    receipt_material_hash: str
    evidence_level: int
    receipt_ready: bool
    receipt_blockers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36RawReceiptPrepSummary:
    schema_version: str
    suite_name: str
    source_suite: str
    import_state: str
    expected_file_count: int
    present_file_count: int
    missing_file_count: int
    expected_case_count: int
    expected_system_count: int
    normalized_judgment_count: int
    receipt_preparation_count: int
    receipt_ready_count: int
    receipt_blocked_count: int
    malformed_json_line_count: int
    records_missing_required_fields: int
    invalid_decision_count: int
    invalid_score_count: int
    invalid_citation_method_count: int
    unknown_case_id_count: int
    duplicate_case_id_count: int
    raw_inventory_hash: str
    schema_lint_hash: str
    normalized_judgments_hash: str
    receipt_preparation_hash: str
    manifest_hash: str
    ground_truth_used: bool
    score_against_holdout: bool
    no_provider_calls: bool
    no_fake_outputs: bool
    empirical_results_created: bool
    manual_result_evidence_cap: int
    level_4_allowed: bool
    level_5_allowed: bool
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_oar_36_raw_receipt_prep_config(
    path: str | Path,
) -> OAR36RawReceiptPrepConfig:
    return OAR36RawReceiptPrepConfig(**json.loads(Path(path).read_text(encoding="utf-8")))


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def read_jsonl_lines_preserving_raw(path: Path) -> list[tuple[int, str]]:
    return [
        (line_number, line)
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(keepends=True),
            start=1,
        )
    ]


def load_expected_raw_output_filenames(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("files"), list):
        return list(payload["files"])
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Expected raw output filename list at {path}")


def build_oar_36_raw_inventory(
    expected_files: list[dict[str, Any]],
    raw_output_root: Path,
) -> list[OAR36RawFileInventoryRecord]:
    inventory: list[OAR36RawFileInventoryRecord] = []
    for expected in expected_files:
        expected_relative_path = expected["relative_path"]
        raw_path = _resolve_raw_path(raw_output_root, expected_relative_path)
        present = raw_path.exists()
        issues: list[str] = []
        file_size_bytes = 0
        file_hash: str | None = None
        line_count = 0
        readable = False
        if present:
            try:
                file_size_bytes = raw_path.stat().st_size
                file_hash = sha256_file(raw_path)
                line_count = len(read_jsonl_lines_preserving_raw(raw_path))
                readable = True
            except OSError:
                issues.append("file_not_readable")
        else:
            issues.append("file_missing")
        inventory.append(
            OAR36RawFileInventoryRecord(
                expected_filename=expected["expected_filename"],
                expected_relative_path=expected_relative_path,
                resolved_path=str(raw_path),
                system_role=expected["system_role"],
                provider=expected["provider"],
                model=expected["model"],
                present=present,
                file_size_bytes=file_size_bytes,
                file_hash=file_hash,
                line_count=line_count,
                readable=readable,
                issues=issues,
            )
        )
    return inventory


def lint_and_normalize_oar_36_raw_file(
    file_record: OAR36RawFileInventoryRecord,
    valid_case_ids: set[str],
    config: OAR36RawReceiptPrepConfig,
) -> tuple[OAR36RawSchemaLintRecord, list[OAR36NormalizedJudgmentRecord]]:
    if not file_record.present:
        return (
            OAR36RawSchemaLintRecord(
                expected_filename=file_record.expected_filename,
                present=False,
                line_count=0,
                parseable_json_line_count=0,
                malformed_json_line_count=0,
                records_with_required_fields=0,
                records_missing_required_fields=0,
                unknown_case_id_count=0,
                duplicate_case_id_count=0,
                invalid_decision_count=0,
                invalid_score_count=0,
                invalid_citation_method_count=0,
                judgment_like_records_count=0,
                issues=["file_missing"],
            ),
            [],
        )

    rows = read_jsonl_lines_preserving_raw(Path(file_record.resolved_path))
    seen_case_ids: set[str] = set()
    counts: Counter[str] = Counter()
    lint_issues: set[str] = set()
    normalized: list[OAR36NormalizedJudgmentRecord] = []

    for line_number, raw_line in rows:
        raw_line_hash = sha256_text(raw_line)
        try:
            raw_obj = json.loads(raw_line)
        except json.JSONDecodeError:
            counts["malformed_json_line_count"] += 1
            lint_issues.add("malformed_json_line_count")
            normalized.append(
                normalize_oar_36_judgment(
                    None,
                    file_record.expected_filename,
                    line_number,
                    raw_line_hash,
                    config,
                    system_role=file_record.system_role,
                    provider=file_record.provider,
                    model=file_record.model,
                    forced_issues=["malformed_json"],
                    forced_parse_status="malformed_json",
                )
            )
            continue

        if not isinstance(raw_obj, dict):
            raw_obj = {}
        counts["judgment_like_records_count"] += 1
        row_issues = _row_issues(raw_obj, seen_case_ids, valid_case_ids, config)
        for issue in row_issues:
            if issue == "missing_required_fields" or issue == "reason_codes_not_list":
                lint_issues.add("records_missing_required_fields")
            elif issue == "unknown_case_id":
                lint_issues.add("unknown_case_id_count")
            elif issue == "duplicate_case_id":
                lint_issues.add("duplicate_case_id_count")
            elif issue == "invalid_decision":
                lint_issues.add("invalid_decision_count")
            elif issue == "invalid_score":
                lint_issues.add("invalid_score_count")
            elif issue == "invalid_citation_verification_method":
                lint_issues.add("invalid_citation_method_count")
        if "missing_required_fields" in row_issues or "reason_codes_not_list" in row_issues:
            counts["records_missing_required_fields"] += 1
        else:
            counts["records_with_required_fields"] += 1
        counts["unknown_case_id_count"] += int("unknown_case_id" in row_issues)
        counts["duplicate_case_id_count"] += int("duplicate_case_id" in row_issues)
        counts["invalid_decision_count"] += int("invalid_decision" in row_issues)
        counts["invalid_score_count"] += int("invalid_score" in row_issues)
        counts["invalid_citation_method_count"] += int("invalid_citation_verification_method" in row_issues)
        case_id = raw_obj.get("case_id")
        if case_id in valid_case_ids and case_id not in seen_case_ids:
            seen_case_ids.add(str(case_id))
        parse_status = "parsed" if not row_issues else (
            "missing_required_fields"
            if "missing_required_fields" in row_issues or "reason_codes_not_list" in row_issues
            else "invalid_fields"
        )
        normalized.append(
            normalize_oar_36_judgment(
                raw_obj,
                file_record.expected_filename,
                line_number,
                raw_line_hash,
                config,
                system_role=file_record.system_role,
                provider=file_record.provider,
                model=file_record.model,
                forced_issues=row_issues,
                forced_parse_status=parse_status,
            )
        )

    return (
        OAR36RawSchemaLintRecord(
            expected_filename=file_record.expected_filename,
            present=True,
            line_count=len(rows),
            parseable_json_line_count=len(rows) - counts["malformed_json_line_count"],
            malformed_json_line_count=counts["malformed_json_line_count"],
            records_with_required_fields=counts["records_with_required_fields"],
            records_missing_required_fields=counts["records_missing_required_fields"],
            unknown_case_id_count=counts["unknown_case_id_count"],
            duplicate_case_id_count=counts["duplicate_case_id_count"],
            invalid_decision_count=counts["invalid_decision_count"],
            invalid_score_count=counts["invalid_score_count"],
            invalid_citation_method_count=counts["invalid_citation_method_count"],
            judgment_like_records_count=counts["judgment_like_records_count"],
            issues=sorted(lint_issues),
        ),
        normalized,
    )


def normalize_oar_36_judgment(
    raw_obj: dict[str, Any] | None,
    source_file: str,
    line_number: int,
    raw_line_hash: str,
    config: OAR36RawReceiptPrepConfig,
    *,
    system_role: str = "",
    provider: str = "",
    model: str = "",
    forced_issues: list[str] | None = None,
    forced_parse_status: str | None = None,
) -> OAR36NormalizedJudgmentRecord:
    obj = raw_obj or {}
    issues = list(forced_issues or [])
    score = obj.get("violation_probability")
    normalized_score: float | None
    try:
        normalized_score = float(score) if score is not None else None
    except (TypeError, ValueError):
        normalized_score = None
    reason_codes = obj.get("reason_codes")
    record = {
        "schema_version": "oar_normalized_judgment_v1",
        "suite": config.suite_name,
        "case_id": obj.get("case_id"),
        "system_role": system_role,
        "provider": provider,
        "model": model,
        "source_file": source_file,
        "line_number": line_number,
        "decision": obj.get("decision"),
        "violation_probability": normalized_score,
        "cited_contract_phrase": obj.get("cited_contract_phrase"),
        "citation_verification_method": obj.get("citation_verification_method"),
        "reason_codes": reason_codes if isinstance(reason_codes, list) else None,
        "parse_status": forced_parse_status or ("parsed" if not issues else "invalid_fields"),
        "raw_line_hash": raw_line_hash,
        "normalized_judgment_hash": "",
        "issues": issues,
    }
    record["normalized_judgment_hash"] = sha256_text(
        stable_json_dumps({**record, "normalized_judgment_hash": ""})
    )
    return OAR36NormalizedJudgmentRecord(**record)


def build_oar_36_receipt_preparation(
    normalized_judgments: list[OAR36NormalizedJudgmentRecord],
    case_hashes_by_id: dict[str, str],
    prompt_hashes_by_id: dict[str, str],
    config: OAR36RawReceiptPrepConfig,
) -> list[OAR36ReceiptPreparationRecord]:
    records: list[OAR36ReceiptPreparationRecord] = []
    for judgment in normalized_judgments:
        blockers: list[str] = []
        case_hash = case_hashes_by_id.get(str(judgment.case_id))
        prompt_hash = prompt_hashes_by_id.get(str(judgment.case_id))
        if judgment.parse_status != "parsed":
            blockers.append("normalized_judgment_not_parseable")
        if not case_hash:
            blockers.append("missing_case_hash")
        if not prompt_hash:
            blockers.append("missing_prompt_hash")
        if judgment.issues:
            blockers.extend(f"issue:{issue}" for issue in judgment.issues)
        receipt_ready = not blockers
        material = {
            "case_hash": case_hash,
            "prompt_hash": prompt_hash,
            "raw_line_hash": judgment.raw_line_hash,
            "normalized_judgment_hash": judgment.normalized_judgment_hash,
            "system_role": judgment.system_role,
            "provider": judgment.provider,
            "model": judgment.model,
            "source_file": judgment.source_file,
        }
        records.append(
            OAR36ReceiptPreparationRecord(
                schema_version="oar_receipt_preparation_v1",
                suite=config.suite_name,
                case_id=judgment.case_id,
                system_role=judgment.system_role,
                provider=judgment.provider,
                model=judgment.model,
                source_file=judgment.source_file,
                case_hash=case_hash,
                prompt_hash=prompt_hash,
                raw_line_hash=judgment.raw_line_hash,
                normalized_judgment_hash=judgment.normalized_judgment_hash,
                receipt_material_hash=sha256_text(stable_json_dumps(material)),
                evidence_level=config.manual_result_evidence_cap if receipt_ready else 0,
                receipt_ready=receipt_ready,
                receipt_blockers=sorted(set(blockers)),
            )
        )
    return records


def validate_oar_36_receipt_prep(
    summary: OAR36RawReceiptPrepSummary,
    normalized_judgments: list[OAR36NormalizedJudgmentRecord],
    receipt_records: list[OAR36ReceiptPreparationRecord],
    config: OAR36RawReceiptPrepConfig,
) -> list[str]:
    issues: list[str] = []
    if summary.ground_truth_used:
        issues.append("ground_truth_used")
    if summary.score_against_holdout:
        issues.append("scored_against_holdout")
    if len(normalized_judgments) != len(receipt_records):
        issues.append("normalized_receipt_count_mismatch")
    if any(record.evidence_level > config.manual_result_evidence_cap for record in receipt_records):
        issues.append("evidence_level_cap_exceeded")
    if summary.level_4_allowed or summary.level_5_allowed:
        issues.append("level_4_or_5_claimed")
    return issues


def validate_raw_receipt_prep(
    *,
    config: OAR36RawReceiptPrepConfig,
    cases: list[dict[str, Any]],
    prompts: list[dict[str, Any]],
    expected_files: list[dict[str, Any]],
    raw_output_root: Path,
) -> tuple[
    OAR36RawReceiptPrepSummary,
    list[OAR36RawFileInventoryRecord],
    list[OAR36RawSchemaLintRecord],
    list[OAR36NormalizedJudgmentRecord],
    list[OAR36ReceiptPreparationRecord],
]:
    inventory = build_oar_36_raw_inventory(expected_files, raw_output_root)
    valid_case_ids = {case["case_id"] for case in cases}
    case_hashes = {case["case_id"]: case["source_case_hash"] for case in cases}
    prompt_hashes = {prompt["case_id"]: prompt["prompt_hash"] for prompt in prompts}
    lint_records: list[OAR36RawSchemaLintRecord] = []
    normalized: list[OAR36NormalizedJudgmentRecord] = []
    for file_record in inventory:
        lint, file_normalized = lint_and_normalize_oar_36_raw_file(
            file_record,
            valid_case_ids,
            config,
        )
        lint_records.append(lint)
        normalized.extend(file_normalized)
    receipts = build_oar_36_receipt_preparation(normalized, case_hashes, prompt_hashes, config)
    summary = _build_summary(config, inventory, lint_records, normalized, receipts)
    validation_issues = validate_oar_36_receipt_prep(summary, normalized, receipts, config)
    if validation_issues:
        raise ValueError(f"OAR-36 receipt prep validation failed: {validation_issues}")
    return summary, inventory, lint_records, normalized, receipts


def write_oar_36_receipt_prep_outputs(
    summary: OAR36RawReceiptPrepSummary,
    inventory: list[OAR36RawFileInventoryRecord],
    lint_records: list[OAR36RawSchemaLintRecord],
    normalized_judgments: list[OAR36NormalizedJudgmentRecord],
    receipt_records: list[OAR36ReceiptPreparationRecord],
    out_dir: str | Path,
) -> None:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / "oar_36_raw_file_inventory.json"
    lint_path = output_dir / "oar_36_raw_schema_lint.json"
    normalized_path = output_dir / "oar_36_normalized_judgments.jsonl"
    receipt_path = output_dir / "oar_36_receipt_preparation.jsonl"
    status_path = output_dir / "oar_36_raw_import_status.json"
    manifest_path = output_dir / "oar_36_receipt_prep_manifest.json"
    report_path = output_dir / "oar_36_receipt_prep_report.md"

    _write_json(
        inventory_path,
        {
            "schema_version": "oar_36_raw_file_inventory_v1",
            "suite_name": summary.suite_name,
            "files": [record.to_dict() for record in inventory],
        },
    )
    _write_json(
        lint_path,
        {
            "schema_version": "oar_36_raw_schema_lint_v1",
            "suite_name": summary.suite_name,
            "records": [record.to_dict() for record in lint_records],
        },
    )
    _write_jsonl(normalized_path, [record.to_dict() for record in normalized_judgments])
    _write_jsonl(receipt_path, [record.to_dict() for record in receipt_records])

    summary_payload = {
        **summary.to_dict(),
        "raw_inventory_hash": sha256_file(inventory_path),
        "schema_lint_hash": sha256_file(lint_path),
        "normalized_judgments_hash": sha256_file(normalized_path),
        "receipt_preparation_hash": sha256_file(receipt_path),
        "manifest_hash": "",
    }
    summary_payload["manifest_hash"] = sha256_text(stable_json_dumps(summary_payload))
    _write_json(manifest_path, summary_payload)
    _write_json(
        status_path,
        {
            "schema_version": "oar_36_raw_import_status_v1",
            "suite_name": summary.suite_name,
            "import_state": summary.import_state,
            "expected_file_count": summary.expected_file_count,
            "present_file_count": summary.present_file_count,
            "missing_file_count": summary.missing_file_count,
            "normalized_judgment_count": summary.normalized_judgment_count,
            "receipt_preparation_count": summary.receipt_preparation_count,
            "empirical_results_created": summary.empirical_results_created,
        },
    )
    report_summary = OAR36RawReceiptPrepSummary(**summary_payload)
    report_path.write_text(
        generate_oar_36_receipt_prep_report(report_summary, inventory, lint_records, output_dir),
        encoding="utf-8",
    )


def generate_oar_36_receipt_prep_report(
    summary: OAR36RawReceiptPrepSummary,
    inventory: list[OAR36RawFileInventoryRecord],
    lint_records: list[OAR36RawSchemaLintRecord],
    out_dir: str | Path,
) -> str:
    del out_dir
    lines = [
        "# OAR-36 Raw Receipt Preparation Report",
        "",
        "## Executive Summary",
        (
            f"Import state is `{summary.import_state}` with "
            f"{summary.present_file_count}/{summary.expected_file_count} raw files present. "
            "no provider calls were made and no fake outputs were generated."
        ),
        "",
        "## Import State",
        f"- import_state: `{summary.import_state}`",
        f"- expected_file_count: `{summary.expected_file_count}`",
        f"- present_file_count: `{summary.present_file_count}`",
        f"- missing_file_count: `{summary.missing_file_count}`",
        "",
        "## Expected vs Present Files",
        f"- present files: `{sum(1 for record in inventory if record.present)}`",
        f"- missing files: `{sum(1 for record in inventory if not record.present)}`",
        "",
        "## Schema Compliance",
        f"- malformed_json_line_count: `{summary.malformed_json_line_count}`",
        f"- records_missing_required_fields: `{summary.records_missing_required_fields}`",
        f"- invalid_decision_count: `{summary.invalid_decision_count}`",
        f"- invalid_score_count: `{summary.invalid_score_count}`",
        f"- invalid_citation_method_count: `{summary.invalid_citation_method_count}`",
        f"- lint files checked: `{len(lint_records)}`",
        "",
        "## Normalized Judgment Summary",
        f"- normalized_judgment_count: `{summary.normalized_judgment_count}`",
        "- Normalization records only the provider-supplied structural fields.",
        "",
        "## Receipt Preparation Summary",
        f"- receipt_preparation_count: `{summary.receipt_preparation_count}`",
        f"- receipt_ready_count: `{summary.receipt_ready_count}`",
        f"- receipt_blocked_count: `{summary.receipt_blocked_count}`",
        "",
        "## Ground-Truth Boundary",
        "- no provider calls were made.",
        "- no fake outputs were generated.",
        "- ground truth was not used.",
        "- no scoring against holdout occurred.",
        "- score_against_holdout: `false`",
        "",
        "## Evidence-Level Boundary",
        f"- manual evidence is capped at Level {summary.manual_result_evidence_cap}.",
        "- Level 4/5 not claimed.",
        "",
        "## What This Supports",
        "- Raw-output presence detection.",
        "- Exact raw file and raw line hashing.",
        "- Structural JSONL parsing and receipt-material preparation.",
        "",
        "## What This Does Not Prove",
        "- Receipt preparation does not prove correctness.",
        "- This does not create scored OAR-36 empirical results.",
        "- This does not validate citations against the holdout.",
        "",
        "## Limitations",
        *[f"- {limitation}" for limitation in summary.limitations],
        "- malformed rows are evidence and must not be edited.",
        "",
        "## Next Steps",
        "- Collect real OAR-36 raw provider output files.",
        "- Re-run this receipt-prep stage without repairing provider rows.",
        "- Only then run a separate scoring/receipt validation protocol if authorized.",
        "",
    ]
    return "\n".join(lines)


def _row_issues(
    raw_obj: dict[str, Any],
    seen_case_ids: set[str],
    valid_case_ids: set[str],
    config: OAR36RawReceiptPrepConfig,
) -> list[str]:
    issues: list[str] = []
    missing_fields = [
        field
        for field in config.required_output_fields
        if field not in raw_obj or raw_obj.get(field) is None
    ]
    if missing_fields:
        issues.append("missing_required_fields")
    case_id = raw_obj.get("case_id")
    if case_id is not None and case_id not in valid_case_ids:
        issues.append("unknown_case_id")
    elif case_id is not None and case_id in seen_case_ids:
        issues.append("duplicate_case_id")
    decision = raw_obj.get("decision")
    if decision is not None and decision not in config.allowed_decisions:
        issues.append("invalid_decision")
    score = raw_obj.get("violation_probability")
    if score is not None:
        try:
            numeric_score = float(score)
            if numeric_score < 0.0 or numeric_score > 1.0:
                raise ValueError
        except (TypeError, ValueError):
            issues.append("invalid_score")
    method = raw_obj.get("citation_verification_method")
    if method is not None and method not in config.allowed_citation_verification_methods:
        issues.append("invalid_citation_verification_method")
    if "reason_codes" in raw_obj and not isinstance(raw_obj.get("reason_codes"), list):
        issues.append("reason_codes_not_list")
    return sorted(set(issues))


def _build_summary(
    config: OAR36RawReceiptPrepConfig,
    inventory: list[OAR36RawFileInventoryRecord],
    lint_records: list[OAR36RawSchemaLintRecord],
    normalized: list[OAR36NormalizedJudgmentRecord],
    receipts: list[OAR36ReceiptPreparationRecord],
) -> OAR36RawReceiptPrepSummary:
    present = sum(1 for record in inventory if record.present)
    expected = len(inventory)
    malformed = sum(record.malformed_json_line_count for record in lint_records)
    missing_required = sum(record.records_missing_required_fields for record in lint_records)
    invalid_decision = sum(record.invalid_decision_count for record in lint_records)
    invalid_score = sum(record.invalid_score_count for record in lint_records)
    invalid_method = sum(record.invalid_citation_method_count for record in lint_records)
    unknown = sum(record.unknown_case_id_count for record in lint_records)
    duplicate = sum(record.duplicate_case_id_count for record in lint_records)
    schema_issues = (
        malformed
        + missing_required
        + invalid_decision
        + invalid_score
        + invalid_method
        + unknown
        + duplicate
    )
    ready = sum(1 for record in receipts if record.receipt_ready)
    blocked = sum(1 for record in receipts if not record.receipt_ready)
    if present == 0:
        import_state = "awaiting_raw_outputs"
    elif present < expected and schema_issues == 0:
        import_state = "partial_raw_outputs_present"
    elif present < expected:
        import_state = "partial_with_schema_issues"
    elif schema_issues == 0 and ready == config.expected_case_count * config.expected_system_count:
        import_state = "complete_receipt_prep_ready"
    else:
        import_state = "complete_with_schema_issues"

    inventory_payload = [record.to_dict() for record in inventory]
    lint_payload = [record.to_dict() for record in lint_records]
    normalized_payload = [record.to_dict() for record in normalized]
    receipt_payload = [record.to_dict() for record in receipts]
    return OAR36RawReceiptPrepSummary(
        schema_version="oar_36_raw_receipt_prep_summary_v1",
        suite_name=config.suite_name,
        source_suite=config.source_suite,
        import_state=import_state,
        expected_file_count=expected,
        present_file_count=present,
        missing_file_count=expected - present,
        expected_case_count=config.expected_case_count,
        expected_system_count=config.expected_system_count,
        normalized_judgment_count=len(normalized),
        receipt_preparation_count=len(receipts),
        receipt_ready_count=ready,
        receipt_blocked_count=blocked,
        malformed_json_line_count=malformed,
        records_missing_required_fields=missing_required,
        invalid_decision_count=invalid_decision,
        invalid_score_count=invalid_score,
        invalid_citation_method_count=invalid_method,
        unknown_case_id_count=unknown,
        duplicate_case_id_count=duplicate,
        raw_inventory_hash=sha256_text(stable_json_dumps(inventory_payload)),
        schema_lint_hash=sha256_text(stable_json_dumps(lint_payload)),
        normalized_judgments_hash=sha256_text(stable_json_dumps(normalized_payload)),
        receipt_preparation_hash=sha256_text(stable_json_dumps(receipt_payload)),
        manifest_hash="",
        ground_truth_used=False,
        score_against_holdout=False,
        no_provider_calls=config.no_provider_calls,
        no_fake_outputs=config.no_fake_outputs,
        empirical_results_created=False,
        manual_result_evidence_cap=config.manual_result_evidence_cap,
        level_4_allowed=False,
        level_5_allowed=False,
        limitations=[
            config.notes,
            "Raw rows are preserved exactly and never repaired.",
            "Receipt preparation does not score against the OAR-36 holdout.",
            "Manual evidence remains capped at Level 3.",
        ],
    )


def _resolve_raw_path(raw_output_root: Path, expected_relative_path: str) -> Path:
    relative = Path(expected_relative_path)
    if relative.parts and relative.parts[0] == "raw_outputs":
        relative = Path(*relative.parts[1:])
    return raw_output_root / relative


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n" for record in records),
        encoding="utf-8",
    )

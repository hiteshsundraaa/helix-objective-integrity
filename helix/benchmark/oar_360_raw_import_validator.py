from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OAR360RawImportValidatorConfig:
    schema_version: str
    suite_name: str
    protocol_version: str
    expected_system_count: int
    expected_batch_count: int
    expected_raw_output_file_count: int
    manual_result_evidence_cap: int
    ground_truth_use_allowed: bool
    score_against_holdout: bool
    no_provider_calls: bool
    no_fake_outputs: bool
    no_empirical_results: bool
    preserve_raw_outputs: bool
    allowed_raw_extensions: list[str]
    required_output_fields: list[str]
    allowed_decisions: list[str]
    allowed_citation_verification_methods: list[str]
    notes: str


@dataclass(frozen=True)
class OAR360RawFileInventoryRecord:
    expected_filename: str
    expected_relative_path: str
    provider: str
    system_role: str
    model: str
    batch_id: str
    batch_type: str
    present: bool
    file_size_bytes: int
    file_hash: str | None
    line_count: int
    readable: bool
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR360RawSchemaLintRecord:
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
class OAR360RawParsePreviewRecord:
    source_file: str
    line_number: int
    case_id: str | None
    has_decision: bool
    has_violation_probability: bool
    has_cited_contract_phrase: bool
    has_citation_verification_method: bool
    has_reason_codes: bool
    parse_status: str
    issues: list[str]
    raw_line_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR360RawImportSummary:
    schema_version: str
    suite_name: str
    import_state: str
    expected_file_count: int
    present_file_count: int
    missing_file_count: int
    readable_file_count: int
    total_raw_lines: int
    parseable_json_line_count: int
    malformed_json_line_count: int
    judgment_like_records_count: int
    complete_required_field_record_count: int
    unique_case_ids_seen: int
    duplicate_case_id_count: int
    unknown_case_id_count: int
    invalid_decision_count: int
    invalid_score_count: int
    invalid_citation_method_count: int
    raw_inventory_hash: str
    raw_schema_lint_hash: str
    raw_parse_preview_hash: str
    import_manifest_hash: str
    no_provider_calls: bool
    no_fake_outputs: bool
    no_empirical_results: bool
    ground_truth_used: bool
    score_against_holdout: bool
    evidence_level_cap: int
    limitations: list[str]
    source_expected_filenames_hash: str | None = None
    source_case_file_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_oar_360_raw_import_validator_config(
    path: Path | str,
) -> OAR360RawImportValidatorConfig:
    return OAR360RawImportValidatorConfig(
        **json.loads(Path(path).read_text(encoding="utf-8"))
    )


def load_expected_raw_output_filenames(path: Path | str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("files"), list):
        return list(payload["files"])
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Expected raw-output filename list at {path}")


def load_cases(path: Path | str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def read_jsonl_lines_preserving_raw(path: Path) -> list[tuple[int, str]]:
    return [
        (index, line)
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if line or line == ""
    ]


def build_raw_file_inventory(
    expected_files: list[dict[str, Any]],
    raw_output_root: Path,
) -> list[OAR360RawFileInventoryRecord]:
    records: list[OAR360RawFileInventoryRecord] = []
    for expected in expected_files:
        expected_relative_path = expected["relative_path"]
        raw_path = _resolve_raw_path(raw_output_root, expected_relative_path)
        issues: list[str] = []
        present = raw_path.exists()
        readable = False
        file_size_bytes = 0
        file_hash: str | None = None
        line_count = 0

        if not expected["expected_filename"].endswith(".jsonl"):
            issues.append("unexpected_raw_extension")
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

        records.append(
            OAR360RawFileInventoryRecord(
                expected_filename=expected["expected_filename"],
                expected_relative_path=expected_relative_path,
                provider=expected["provider"],
                system_role=expected["system_role"],
                model=expected["model"],
                batch_id=expected["batch_id"],
                batch_type=expected["batch_type"],
                present=present,
                file_size_bytes=file_size_bytes,
                file_hash=file_hash,
                line_count=line_count,
                readable=readable,
                issues=issues,
            )
        )
    return records


def lint_raw_output_file(
    file_record: OAR360RawFileInventoryRecord,
    valid_case_ids: set[str],
    config: OAR360RawImportValidatorConfig,
) -> tuple[OAR360RawSchemaLintRecord, list[OAR360RawParsePreviewRecord]]:
    if not file_record.present:
        return (
            OAR360RawSchemaLintRecord(
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

    raw_path = _resolve_raw_path(Path("."), file_record.expected_relative_path)
    if not raw_path.exists():
        # In tests and validation the expected relative path is resolved by caller before
        # inventory construction. Store this issue rather than inventing rows.
        raw_path = Path(file_record.expected_relative_path)

    lines = read_jsonl_lines_preserving_raw(raw_path)
    seen_case_ids: set[str] = set()
    previews: list[OAR360RawParsePreviewRecord] = []
    counts = Counter()
    issues: list[str] = []

    for line_number, raw_line in lines:
        line_issues: list[str] = []
        raw_line_hash = sha256_text(raw_line)
        try:
            payload = json.loads(raw_line)
            counts["parseable_json_line_count"] += 1
        except json.JSONDecodeError:
            counts["malformed_json_line_count"] += 1
            line_issues.append("malformed_json")
            previews.append(
                OAR360RawParsePreviewRecord(
                    source_file=file_record.expected_filename,
                    line_number=line_number,
                    case_id=None,
                    has_decision=False,
                    has_violation_probability=False,
                    has_cited_contract_phrase=False,
                    has_citation_verification_method=False,
                    has_reason_codes=False,
                    parse_status="malformed_json",
                    issues=line_issues,
                    raw_line_hash=raw_line_hash,
                )
            )
            continue

        if not isinstance(payload, dict):
            payload = {}
            line_issues.append("json_value_not_object")

        counts["judgment_like_records_count"] += 1
        case_id = payload.get("case_id")
        missing_fields = [field for field in config.required_output_fields if field not in payload or payload.get(field) is None]
        if missing_fields:
            counts["records_missing_required_fields"] += 1
            line_issues.append("missing_required_fields")
        else:
            counts["records_with_required_fields"] += 1

        if case_id is None:
            line_issues.append("missing_case_id")
        elif case_id not in valid_case_ids:
            counts["unknown_case_id_count"] += 1
            line_issues.append("unknown_case_id")
        elif case_id in seen_case_ids:
            counts["duplicate_case_id_count"] += 1
            line_issues.append("duplicate_case_id")
        else:
            seen_case_ids.add(str(case_id))

        decision = payload.get("decision")
        if decision is not None and decision not in config.allowed_decisions:
            counts["invalid_decision_count"] += 1
            line_issues.append("invalid_decision")

        score = payload.get("violation_probability")
        if score is not None:
            try:
                numeric_score = float(score)
                if numeric_score < 0.0 or numeric_score > 1.0:
                    raise ValueError
            except (TypeError, ValueError):
                counts["invalid_score_count"] += 1
                line_issues.append("invalid_score")

        method = payload.get("citation_verification_method")
        if (
            method is not None
            and method not in config.allowed_citation_verification_methods
        ):
            counts["invalid_citation_method_count"] += 1
            line_issues.append("invalid_citation_verification_method")

        if "reason_codes" in payload and not isinstance(payload.get("reason_codes"), list):
            counts["records_missing_required_fields"] += 1
            if not missing_fields:
                counts["records_with_required_fields"] -= 1
            line_issues.append("reason_codes_not_list")
        if "cited_contract_phrase" in payload and payload.get("cited_contract_phrase") is None:
            line_issues.append("cited_contract_phrase_null")

        previews.append(
            OAR360RawParsePreviewRecord(
                source_file=file_record.expected_filename,
                line_number=line_number,
                case_id=str(case_id) if case_id is not None else None,
                has_decision="decision" in payload,
                has_violation_probability="violation_probability" in payload,
                has_cited_contract_phrase="cited_contract_phrase" in payload,
                has_citation_verification_method="citation_verification_method" in payload,
                has_reason_codes="reason_codes" in payload,
                parse_status="parseable_json",
                issues=line_issues,
                raw_line_hash=raw_line_hash,
            )
        )

    for issue_name in [
        "malformed_json_line_count",
        "records_missing_required_fields",
        "unknown_case_id_count",
        "duplicate_case_id_count",
        "invalid_decision_count",
        "invalid_score_count",
        "invalid_citation_method_count",
    ]:
        if counts[issue_name] > 0:
            issues.append(issue_name)

    return (
        OAR360RawSchemaLintRecord(
            expected_filename=file_record.expected_filename,
            present=True,
            line_count=len(lines),
            parseable_json_line_count=counts["parseable_json_line_count"],
            malformed_json_line_count=counts["malformed_json_line_count"],
            records_with_required_fields=counts["records_with_required_fields"],
            records_missing_required_fields=counts["records_missing_required_fields"],
            unknown_case_id_count=counts["unknown_case_id_count"],
            duplicate_case_id_count=counts["duplicate_case_id_count"],
            invalid_decision_count=counts["invalid_decision_count"],
            invalid_score_count=counts["invalid_score_count"],
            invalid_citation_method_count=counts["invalid_citation_method_count"],
            judgment_like_records_count=counts["judgment_like_records_count"],
            issues=issues,
        ),
        previews,
    )


def validate_oar_360_raw_imports(
    config: OAR360RawImportValidatorConfig,
    expected_files: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    raw_output_root: Path,
) -> tuple[
    OAR360RawImportSummary,
    list[OAR360RawFileInventoryRecord],
    list[OAR360RawSchemaLintRecord],
    list[OAR360RawParsePreviewRecord],
]:
    inventory = build_raw_file_inventory(expected_files, raw_output_root)
    valid_case_ids = {case["case_id"] for case in cases}
    lint_records: list[OAR360RawSchemaLintRecord] = []
    preview_records: list[OAR360RawParsePreviewRecord] = []

    for inventory_record in inventory:
        lint_record, previews = _lint_inventory_record_with_root(
            inventory_record,
            raw_output_root,
            valid_case_ids,
            config,
        )
        lint_records.append(lint_record)
        preview_records.extend(previews)

    present_file_count = sum(1 for record in inventory if record.present)
    expected_file_count = len(inventory)
    missing_file_count = expected_file_count - present_file_count
    total_raw_lines = sum(record.line_count for record in lint_records if record.present)
    parseable_json_line_count = sum(record.parseable_json_line_count for record in lint_records)
    malformed_json_line_count = sum(record.malformed_json_line_count for record in lint_records)
    judgment_like_records_count = sum(record.judgment_like_records_count for record in lint_records)
    complete_required_field_record_count = sum(record.records_with_required_fields for record in lint_records)
    duplicate_case_id_count = sum(record.duplicate_case_id_count for record in lint_records)
    unknown_case_id_count = sum(record.unknown_case_id_count for record in lint_records)
    invalid_decision_count = sum(record.invalid_decision_count for record in lint_records)
    invalid_score_count = sum(record.invalid_score_count for record in lint_records)
    invalid_citation_method_count = sum(record.invalid_citation_method_count for record in lint_records)
    schema_issue_count = (
        malformed_json_line_count
        + sum(record.records_missing_required_fields for record in lint_records)
        + duplicate_case_id_count
        + unknown_case_id_count
        + invalid_decision_count
        + invalid_score_count
        + invalid_citation_method_count
    )

    if present_file_count == 0:
        import_state = "awaiting_raw_outputs"
    elif present_file_count < expected_file_count and schema_issue_count > 0:
        import_state = "partial_with_schema_issues"
    elif present_file_count < expected_file_count:
        import_state = "partial_raw_outputs_present"
    elif schema_issue_count == 0 and complete_required_field_record_count == total_raw_lines:
        import_state = "complete_schema_validated"
    else:
        import_state = "complete_with_schema_issues"

    unique_case_ids_seen = len(
        {
            record.case_id
            for record in preview_records
            if record.case_id is not None and record.case_id in valid_case_ids
        }
    )
    inventory_payload = [record.to_dict() for record in inventory]
    lint_payload = [record.to_dict() for record in lint_records]
    preview_payload = [record.to_dict() for record in preview_records]

    summary = OAR360RawImportSummary(
        schema_version="oar_360_raw_import_summary_v1",
        suite_name=config.suite_name,
        import_state=import_state,
        expected_file_count=expected_file_count,
        present_file_count=present_file_count,
        missing_file_count=missing_file_count,
        readable_file_count=sum(1 for record in inventory if record.readable),
        total_raw_lines=total_raw_lines,
        parseable_json_line_count=parseable_json_line_count,
        malformed_json_line_count=malformed_json_line_count,
        judgment_like_records_count=judgment_like_records_count,
        complete_required_field_record_count=complete_required_field_record_count,
        unique_case_ids_seen=unique_case_ids_seen,
        duplicate_case_id_count=duplicate_case_id_count,
        unknown_case_id_count=unknown_case_id_count,
        invalid_decision_count=invalid_decision_count,
        invalid_score_count=invalid_score_count,
        invalid_citation_method_count=invalid_citation_method_count,
        raw_inventory_hash=sha256_text(stable_json_dumps(inventory_payload)),
        raw_schema_lint_hash=sha256_text(stable_json_dumps(lint_payload)),
        raw_parse_preview_hash=sha256_text(stable_json_dumps(preview_payload)),
        import_manifest_hash="",
        no_provider_calls=config.no_provider_calls,
        no_fake_outputs=config.no_fake_outputs,
        no_empirical_results=config.no_empirical_results,
        ground_truth_used=False,
        score_against_holdout=False,
        evidence_level_cap=config.manual_result_evidence_cap,
        limitations=[
            config.notes,
            "Raw import validation does not repair malformed JSON or missing fields.",
            "Raw import validation does not score against the ground-truth holdout.",
            "Manual evidence remains capped at Level 3.",
        ],
    )
    return summary, inventory, lint_records, preview_records


def write_oar_360_raw_import_validation_outputs(
    summary: OAR360RawImportSummary,
    inventory: list[OAR360RawFileInventoryRecord],
    lint_records: list[OAR360RawSchemaLintRecord],
    preview_records: list[OAR360RawParsePreviewRecord],
    out_dir: Path | str,
) -> None:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory_path = output_dir / "oar_360_raw_file_inventory.json"
    lint_path = output_dir / "oar_360_raw_schema_lint.json"
    preview_path = output_dir / "oar_360_raw_parse_preview.jsonl"
    status_path = output_dir / "oar_360_raw_import_status.json"
    manifest_path = output_dir / "oar_360_raw_import_manifest.json"
    report_path = output_dir / "oar_360_raw_import_report.md"

    _write_json(
        inventory_path,
        {
            "schema_version": "oar_360_raw_file_inventory_v1",
            "suite_name": summary.suite_name,
            "expected_file_count": summary.expected_file_count,
            "present_file_count": summary.present_file_count,
            "files": [record.to_dict() for record in inventory],
        },
    )
    _write_json(
        lint_path,
        {
            "schema_version": "oar_360_raw_schema_lint_v1",
            "suite_name": summary.suite_name,
            "records": [record.to_dict() for record in lint_records],
        },
    )
    preview_path.write_text(
        "".join(
            json.dumps(record.to_dict(), sort_keys=True, ensure_ascii=True) + "\n"
            for record in preview_records
        ),
        encoding="utf-8",
    )

    manifest_payload = summary.to_dict()
    manifest_payload.update(
        {
            "raw_output_root": "benchmarks/oar_360/manual_eval/raw_outputs",
            "output_dir": str(output_dir),
            "source_expected_filenames_hash": summary.source_expected_filenames_hash,
            "source_case_file_hash": summary.source_case_file_hash,
            "inventory_artifact_hash": sha256_file(inventory_path),
            "schema_lint_artifact_hash": sha256_file(lint_path),
            "parse_preview_artifact_hash": sha256_file(preview_path),
        }
    )
    manifest_preimage = dict(manifest_payload)
    manifest_preimage["import_manifest_hash"] = ""
    manifest_hash = sha256_text(stable_json_dumps(manifest_preimage))
    manifest_payload["import_manifest_hash"] = manifest_hash
    _write_json(manifest_path, manifest_payload)

    final_summary = OAR360RawImportSummary(
        **{**summary.to_dict(), "import_manifest_hash": manifest_hash}
    )
    _write_json(
        status_path,
        {
            "schema_version": "oar_360_raw_import_status_v1",
            "suite_name": final_summary.suite_name,
            "expected_file_count": final_summary.expected_file_count,
            "present_file_count": final_summary.present_file_count,
            "missing_file_count": final_summary.missing_file_count,
            "import_state": final_summary.import_state,
            "no_provider_calls": final_summary.no_provider_calls,
            "no_fake_outputs": final_summary.no_fake_outputs,
            "no_empirical_results": final_summary.no_empirical_results,
            "ground_truth_used": final_summary.ground_truth_used,
            "score_against_holdout": final_summary.score_against_holdout,
        },
    )
    report_path.write_text(
        generate_oar_360_raw_import_report(
            final_summary,
            inventory,
            lint_records,
            output_dir,
        ),
        encoding="utf-8",
    )


def generate_oar_360_raw_import_report(
    summary: OAR360RawImportSummary,
    inventory: list[OAR360RawFileInventoryRecord],
    lint_records: list[OAR360RawSchemaLintRecord],
    out_dir: Path | str,
) -> str:
    del out_dir
    lines = [
        "# OAR-360 Raw Output Import Report",
        "",
        "## Executive Summary",
        (
            f"Import state is `{summary.import_state}` with "
            f"{summary.present_file_count}/{summary.expected_file_count} expected raw files present. "
            "No provider calls were made, no fake outputs were generated, and no empirical results were created."
        ),
        "",
        "## Import State",
        f"- import_state: `{summary.import_state}`",
        f"- expected_file_count: `{summary.expected_file_count}`",
        f"- present_file_count: `{summary.present_file_count}`",
        f"- missing_file_count: `{summary.missing_file_count}`",
        "",
        "## Expected vs Present Files",
        f"- readable_file_count: `{summary.readable_file_count}`",
        f"- missing expected files: `{sum(1 for record in inventory if not record.present)}`",
        "",
        "## Schema Lint Summary",
        f"- total_raw_lines: `{summary.total_raw_lines}`",
        f"- parseable_json_line_count: `{summary.parseable_json_line_count}`",
        f"- malformed_json_line_count: `{summary.malformed_json_line_count}`",
        f"- complete_required_field_record_count: `{summary.complete_required_field_record_count}`",
        f"- unknown_case_id_count: `{summary.unknown_case_id_count}`",
        f"- duplicate_case_id_count: `{summary.duplicate_case_id_count}`",
        f"- invalid_decision_count: `{summary.invalid_decision_count}`",
        f"- invalid_score_count: `{summary.invalid_score_count}`",
        f"- invalid_citation_method_count: `{summary.invalid_citation_method_count}`",
        "",
        "## Ground-Truth Boundary",
        "- ground truth was not used.",
        "- outputs were not scored against holdout.",
        "- score_against_holdout: `false`",
        "",
        "## Raw Preservation Policy",
        "- Raw files are read and hashed exactly when present.",
        "- Malformed rows are evidence and must not be edited.",
        "- The parse preview stores structural booleans and raw_line_hash only, not full raw provider text.",
        "",
        "## What This Supports",
        "- Readiness, partial import, and complete import state tracking.",
        "- Deterministic raw file inventory, schema lint, parse preview, and import manifest artifacts.",
        "- Schema-level validation before any normalization or scoring step.",
        "",
        "## What This Does Not Prove",
        "- This does not prove model correctness.",
        "- This does not create OAR-360 empirical results.",
        "- This does not validate citations against ground truth or receipt gates.",
        "",
        "## Limitations",
        *[f"- {limitation}" for limitation in summary.limitations],
        "",
        "## Next Steps",
        "- Collect expected raw output files manually under the raw_outputs provider directories.",
        "- Re-run this validator without repairing malformed provider output.",
        "- Only after validation, run a separate normalization/import bridge.",
        "",
    ]
    return "\n".join(lines)


def _lint_inventory_record_with_root(
    file_record: OAR360RawFileInventoryRecord,
    raw_output_root: Path,
    valid_case_ids: set[str],
    config: OAR360RawImportValidatorConfig,
) -> tuple[OAR360RawSchemaLintRecord, list[OAR360RawParsePreviewRecord]]:
    if not file_record.present:
        return lint_raw_output_file(file_record, valid_case_ids, config)
    path = _resolve_raw_path(raw_output_root, file_record.expected_relative_path)
    return _lint_path(file_record, path, valid_case_ids, config)


def _lint_path(
    file_record: OAR360RawFileInventoryRecord,
    path: Path,
    valid_case_ids: set[str],
    config: OAR360RawImportValidatorConfig,
) -> tuple[OAR360RawSchemaLintRecord, list[OAR360RawParsePreviewRecord]]:
    lines = read_jsonl_lines_preserving_raw(path)
    seen_case_ids: set[str] = set()
    previews: list[OAR360RawParsePreviewRecord] = []
    counts = Counter()
    lint_issue_names: set[str] = set()

    for line_number, raw_line in lines:
        line_issues: list[str] = []
        raw_line_hash = sha256_text(raw_line)
        try:
            payload = json.loads(raw_line)
            counts["parseable_json_line_count"] += 1
        except json.JSONDecodeError:
            counts["malformed_json_line_count"] += 1
            lint_issue_names.add("malformed_json_line_count")
            line_issues.append("malformed_json")
            previews.append(
                OAR360RawParsePreviewRecord(
                    source_file=file_record.expected_filename,
                    line_number=line_number,
                    case_id=None,
                    has_decision=False,
                    has_violation_probability=False,
                    has_cited_contract_phrase=False,
                    has_citation_verification_method=False,
                    has_reason_codes=False,
                    parse_status="malformed_json",
                    issues=line_issues,
                    raw_line_hash=raw_line_hash,
                )
            )
            continue

        if not isinstance(payload, dict):
            payload = {}
            line_issues.append("json_value_not_object")

        counts["judgment_like_records_count"] += 1
        missing_fields = [field for field in config.required_output_fields if field not in payload or payload.get(field) is None]
        has_complete_required_fields = not missing_fields and isinstance(payload.get("reason_codes"), list)
        if has_complete_required_fields:
            counts["records_with_required_fields"] += 1
        else:
            counts["records_missing_required_fields"] += 1
            lint_issue_names.add("records_missing_required_fields")
            if missing_fields:
                line_issues.append("missing_required_fields")
            if "reason_codes" in payload and not isinstance(payload.get("reason_codes"), list):
                line_issues.append("reason_codes_not_list")

        case_id = payload.get("case_id")
        if case_id is None:
            line_issues.append("missing_case_id")
        elif case_id not in valid_case_ids:
            counts["unknown_case_id_count"] += 1
            lint_issue_names.add("unknown_case_id_count")
            line_issues.append("unknown_case_id")
        elif case_id in seen_case_ids:
            counts["duplicate_case_id_count"] += 1
            lint_issue_names.add("duplicate_case_id_count")
            line_issues.append("duplicate_case_id")
        else:
            seen_case_ids.add(str(case_id))

        if payload.get("decision") is not None and payload.get("decision") not in config.allowed_decisions:
            counts["invalid_decision_count"] += 1
            lint_issue_names.add("invalid_decision_count")
            line_issues.append("invalid_decision")

        score = payload.get("violation_probability")
        if score is not None:
            try:
                numeric_score = float(score)
                if numeric_score < 0.0 or numeric_score > 1.0:
                    raise ValueError
            except (TypeError, ValueError):
                counts["invalid_score_count"] += 1
                lint_issue_names.add("invalid_score_count")
                line_issues.append("invalid_score")

        method = payload.get("citation_verification_method")
        if method is not None and method not in config.allowed_citation_verification_methods:
            counts["invalid_citation_method_count"] += 1
            lint_issue_names.add("invalid_citation_method_count")
            line_issues.append("invalid_citation_verification_method")

        previews.append(
            OAR360RawParsePreviewRecord(
                source_file=file_record.expected_filename,
                line_number=line_number,
                case_id=str(case_id) if case_id is not None else None,
                has_decision="decision" in payload,
                has_violation_probability="violation_probability" in payload,
                has_cited_contract_phrase="cited_contract_phrase" in payload,
                has_citation_verification_method="citation_verification_method" in payload,
                has_reason_codes="reason_codes" in payload,
                parse_status="parseable_json",
                issues=line_issues,
                raw_line_hash=raw_line_hash,
            )
        )

    return (
        OAR360RawSchemaLintRecord(
            expected_filename=file_record.expected_filename,
            present=True,
            line_count=len(lines),
            parseable_json_line_count=counts["parseable_json_line_count"],
            malformed_json_line_count=counts["malformed_json_line_count"],
            records_with_required_fields=counts["records_with_required_fields"],
            records_missing_required_fields=counts["records_missing_required_fields"],
            unknown_case_id_count=counts["unknown_case_id_count"],
            duplicate_case_id_count=counts["duplicate_case_id_count"],
            invalid_decision_count=counts["invalid_decision_count"],
            invalid_score_count=counts["invalid_score_count"],
            invalid_citation_method_count=counts["invalid_citation_method_count"],
            judgment_like_records_count=counts["judgment_like_records_count"],
            issues=sorted(lint_issue_names),
        ),
        previews,
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

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.v10_generator import V10Case
from helix.benchmark.v10_judgment_normalization import V10NormalizedJudgment


ExecutionMode = Literal["dry_run", "manual_import", "live"]


class V10ReceiptChainConfig(BaseModel):
    hash_algorithm: str = "sha256"
    canonical_json: bool = True
    required_fields: list[str] = Field(
        default_factory=lambda: [
            "case_id",
            "decision",
            "violation_probability",
            "judgment_hash",
            "receipt_hash",
        ]
    )
    raw_output_hash_required_for_live: bool = True
    raw_output_hash_required_for_manual_import: bool = False
    raw_output_hash_required_for_dry_run: bool = False


class V10ReceiptRecord(BaseModel):
    case_id: str
    execution_mode: ExecutionMode
    provider: str
    model: str
    raw_output_hash: str | None = None
    normalized_judgment_hash: str
    decision: str
    violation_probability: float | None
    receipt_hash: str
    valid: bool
    issues: list[str] = Field(default_factory=list)


class V10ReceiptChainSummary(BaseModel):
    schema_version: str = "v10_receipt_chain_summary_v1"
    run_id: str
    execution_mode: ExecutionMode
    provider: str
    model: str
    case_count: int
    receipt_count: int
    valid_receipt_count: int
    invalid_receipt_count: int
    missing_receipt_count: int
    raw_output_hash_available_count: int
    raw_output_hash_missing_count: int
    receipt_chain_complete: bool
    receipt_hashes: list[str]
    chain_hash: str
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# HELIX v10 Receipt Chain Report",
            "",
            "## Executive Summary",
            "",
            f"- run_id: `{self.run_id}`",
            f"- execution_mode: `{self.execution_mode}`",
            f"- receipt_chain_complete: `{str(self.receipt_chain_complete).lower()}`",
            f"- case_count: `{self.case_count}`",
            f"- receipt_count: `{self.receipt_count}`",
            f"- invalid_receipt_count: `{self.invalid_receipt_count}`",
            f"- missing_receipt_count: `{self.missing_receipt_count}`",
            f"- chain_hash: `{self.chain_hash}`",
            "",
            "## Execution Mode",
            "",
            f"- provider: `{self.provider}`",
            f"- model: `{self.model}`",
            "",
            "## Receipt Construction",
            "",
            "- Receipt hashes are computed from case hash, normalized judgment hash, decision, and violation probability.",
            "- Normalized judgment hashes use explicit canonical judgment fields.",
            "",
            "## Raw Output Hash Availability",
            "",
            f"- raw_output_hash_available_count: `{self.raw_output_hash_available_count}`",
            f"- raw_output_hash_missing_count: `{self.raw_output_hash_missing_count}`",
            "",
            "## Invalid Receipts",
            "",
        ]
        if self.issues:
            lines.extend(f"- `{issue}`" for issue in self.issues)
        else:
            lines.append("- None.")
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        lines.extend(
            [
                "",
                "## What This Supports",
                "",
                "- This supports hash-linked receipt-chain integrity checks over v10 pilot artifacts.",
                "- This supports fail-closed detection of missing, duplicate, or invalid judgment records.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- This does not execute providers.",
                "- This does not import raw outputs.",
                "- This does not prove live provenance.",
                "- Missing raw hashes are reported, not fabricated.",
                "",
                "## Limitations",
                "",
                "- Receipt-chain validity depends on the supplied case and judgment artifacts.",
                "- Manual-import and dry-run modes may lack per-case raw output hashes.",
            ]
        )
        return "\n".join(lines)


def canonical_json_hash(obj: Any) -> str:
    payload = json.dumps(
        _stable_payload(obj),
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return _sha256(payload.encode("utf-8"))


def hash_raw_output(raw_text_or_obj: str | Any) -> str:
    if isinstance(raw_text_or_obj, str):
        return _sha256(raw_text_or_obj.encode("utf-8"))
    return canonical_json_hash(raw_text_or_obj)


def hash_normalized_judgment(judgment: V10NormalizedJudgment | dict[str, Any]) -> str:
    payload = _judgment_payload(judgment)
    canonical = {
        "case_id": payload.get("case_id") or "",
        "decision": payload.get("decision") or "",
        "violation_probability": payload.get("violation_probability"),
        "cited_contract_phrase": payload.get("cited_contract_phrase") or "",
        "citation_verification_method": payload.get("citation_verification_method") or "",
        "reason_codes": sorted(str(item) for item in payload.get("reason_codes") or []),
        "uncertainty_reason": payload.get("uncertainty_reason") or "",
    }
    return canonical_json_hash(canonical)


def build_receipt_hash(
    case_hash: str,
    judgment_hash: str,
    decision: str,
    violation_probability: float | None,
) -> str:
    if violation_probability is None:
        score_text = ""
    else:
        score_text = _canonical_float(violation_probability)
    return _sha256(
        "|".join([case_hash, judgment_hash, decision, score_text]).encode("utf-8")
    )


def build_receipt_record(
    case: V10Case | dict[str, Any],
    judgment: V10NormalizedJudgment | dict[str, Any],
    execution_mode: ExecutionMode,
    provider: str,
    model: str,
    raw_output_hash: str | None = None,
    *,
    config: V10ReceiptChainConfig | None = None,
) -> V10ReceiptRecord:
    payload = _judgment_payload(judgment)
    case_id = str(payload.get("case_id") or "")
    decision = str(payload.get("decision") or "")
    score = _score_or_none(payload.get("violation_probability"))
    judgment_hash = hash_normalized_judgment(payload)
    receipt_hash = build_receipt_hash(
        _case_hash(case),
        judgment_hash,
        decision,
        score,
    )
    record = V10ReceiptRecord(
        case_id=case_id,
        execution_mode=execution_mode,
        provider=provider,
        model=model,
        raw_output_hash=raw_output_hash,
        normalized_judgment_hash=judgment_hash,
        decision=decision,
        violation_probability=score,
        receipt_hash=receipt_hash,
        valid=True,
        issues=[],
    )
    return validate_receipt_record(record, config or V10ReceiptChainConfig())


def validate_receipt_record(
    record: V10ReceiptRecord,
    config: V10ReceiptChainConfig,
) -> V10ReceiptRecord:
    issues = list(record.issues)
    if not record.case_id:
        issues.append("missing_case_id")
    if not record.decision:
        issues.append("missing_decision")
    if record.violation_probability is None:
        issues.append("missing_violation_probability")
    if record.violation_probability is not None and (
        record.violation_probability < 0 or record.violation_probability > 1
    ):
        issues.append("violation_probability_out_of_range")
    if not record.normalized_judgment_hash:
        issues.append("missing_judgment_hash")
    if not record.receipt_hash:
        issues.append("missing_receipt_hash")
    if record.raw_output_hash is not None and not record.raw_output_hash.startswith("sha256:"):
        issues.append("invalid_raw_output_hash")
    if record.execution_mode == "live" and config.raw_output_hash_required_for_live and not record.raw_output_hash:
        issues.append("missing_raw_output_hash_for_live")
    if record.execution_mode == "manual_import" and config.raw_output_hash_required_for_manual_import and not record.raw_output_hash:
        issues.append("missing_raw_output_hash_for_manual_import")
    if record.execution_mode == "dry_run" and config.raw_output_hash_required_for_dry_run and not record.raw_output_hash:
        issues.append("missing_raw_output_hash_for_dry_run")
    return record.model_copy(
        update={
            "issues": sorted(set(issues)),
            "valid": not issues,
        }
    )


def build_receipt_chain(
    cases: list[V10Case | dict[str, Any]],
    judgments: list[V10NormalizedJudgment | dict[str, Any]],
    *,
    execution_mode: ExecutionMode,
    provider: str,
    model: str,
    raw_hashes_by_case_id: dict[str, str] | None = None,
    config: V10ReceiptChainConfig | None = None,
    run_id: str = "unknown",
) -> tuple[list[V10ReceiptRecord], V10ReceiptChainSummary]:
    chain_config = config or V10ReceiptChainConfig()
    cases_by_id = {_case_id(case): case for case in cases}
    raw_hashes = raw_hashes_by_case_id or {}
    judgment_ids = [_judgment_case_id(judgment) for judgment in judgments]
    counts = Counter(case_id for case_id in judgment_ids if case_id)
    duplicate_case_ids = {case_id for case_id, count in counts.items() if count > 1}

    records: list[V10ReceiptRecord] = []
    issues: list[str] = []
    for judgment in judgments:
        case_id = _judgment_case_id(judgment)
        case = cases_by_id.get(case_id)
        if case is None:
            issues.append(f"unexpected_judgment_case:{case_id or '<missing>'}")
            record = _invalid_record_for_unmatched_judgment(
                judgment,
                execution_mode=execution_mode,
                provider=provider,
                model=model,
                issue="missing_case_for_judgment",
            )
        else:
            record = build_receipt_record(
                case,
                judgment,
                execution_mode,
                provider,
                model,
                raw_output_hash=raw_hashes.get(case_id),
                config=chain_config,
            )
        if case_id in duplicate_case_ids:
            record = record.model_copy(
                update={
                    "valid": False,
                    "issues": sorted(set(record.issues + ["duplicate_judgment_case_id"])),
                }
            )
        records.append(record)

    observed_case_ids = {record.case_id for record in records if record.case_id}
    missing_case_ids = sorted(set(cases_by_id) - observed_case_ids)
    issues.extend(f"missing_receipt:{case_id}" for case_id in missing_case_ids)
    issues.extend(f"duplicate_judgment:{case_id}" for case_id in sorted(duplicate_case_ids))
    warnings: list[str] = []
    raw_missing_count = sum(record.raw_output_hash is None for record in records)
    if execution_mode in {"manual_import", "dry_run"} and raw_missing_count:
        warnings.append(f"raw_output_hash_missing_allowed_for_{execution_mode}")
    invalid_count = sum(not record.valid for record in records)
    receipt_hashes = [record.receipt_hash for record in records]
    summary_payload = {
        "schema_version": "v10_receipt_chain_summary_v1",
        "run_id": run_id,
        "execution_mode": execution_mode,
        "provider": provider,
        "model": model,
        "case_count": len(cases),
        "receipt_count": len(records),
        "valid_receipt_count": len(records) - invalid_count,
        "invalid_receipt_count": invalid_count,
        "missing_receipt_count": len(missing_case_ids),
        "raw_output_hash_available_count": sum(record.raw_output_hash is not None for record in records),
        "raw_output_hash_missing_count": raw_missing_count,
        "receipt_chain_complete": (
            len(records) == len(cases)
            and invalid_count == 0
            and not missing_case_ids
            and not duplicate_case_ids
        ),
        "receipt_hashes": receipt_hashes,
        "issues": sorted(set(issues + [issue for record in records for issue in record.issues])),
        "warnings": sorted(set(warnings)),
    }
    summary = V10ReceiptChainSummary(
        **summary_payload,
        chain_hash=canonical_json_hash(
            {
                "run_id": run_id,
                "execution_mode": execution_mode,
                "provider": provider,
                "model": model,
                "case_ids": sorted(cases_by_id),
                "receipt_hashes": receipt_hashes,
                "issues": summary_payload["issues"],
            }
        ),
    )
    return records, summary


def write_receipt_chain_outputs(
    records: list[V10ReceiptRecord],
    summary: V10ReceiptChainSummary,
    out_dir: str | Path,
) -> dict[str, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    records_path = target / "receipt_chain_records.jsonl"
    summary_path = target / "receipt_chain_summary.json"
    report_path = target / "receipt_chain_report.md"
    records_path.write_text(
        "\n".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True)
            for record in records
        )
        + ("\n" if records else ""),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")
    return {
        "records": records_path,
        "summary": summary_path,
        "report": report_path,
    }


def _invalid_record_for_unmatched_judgment(
    judgment: V10NormalizedJudgment | dict[str, Any],
    *,
    execution_mode: ExecutionMode,
    provider: str,
    model: str,
    issue: str,
) -> V10ReceiptRecord:
    payload = _judgment_payload(judgment)
    case_id = str(payload.get("case_id") or "")
    score = _score_or_none(payload.get("violation_probability"))
    judgment_hash = hash_normalized_judgment(payload)
    receipt_hash = build_receipt_hash("", judgment_hash, str(payload.get("decision") or ""), score)
    return V10ReceiptRecord(
        case_id=case_id,
        execution_mode=execution_mode,
        provider=provider,
        model=model,
        raw_output_hash=None,
        normalized_judgment_hash=judgment_hash,
        decision=str(payload.get("decision") or ""),
        violation_probability=score,
        receipt_hash=receipt_hash,
        valid=False,
        issues=[issue],
    )


def _case_hash(case: V10Case | dict[str, Any]) -> str:
    payload = _stable_payload(case)
    if isinstance(payload, dict):
        canonical = {
            key: payload.get(key)
            for key in [
                "case_id",
                "family",
                "domain",
                "label",
                "active_contract_rule_id",
                "active_contract_rule_summary",
                "proposed_tool",
                "proposed_action",
                "proposed_arguments",
            ]
            if key in payload
        }
        return canonical_json_hash(canonical)
    return canonical_json_hash(payload)


def _case_id(case: V10Case | dict[str, Any]) -> str:
    if isinstance(case, V10Case):
        return case.case_id
    return str(case.get("case_id") or "")


def _judgment_case_id(judgment: V10NormalizedJudgment | dict[str, Any]) -> str:
    return str(_judgment_payload(judgment).get("case_id") or "")


def _judgment_payload(judgment: V10NormalizedJudgment | dict[str, Any]) -> dict[str, Any]:
    if isinstance(judgment, V10NormalizedJudgment):
        return judgment.model_dump(mode="json")
    return dict(judgment)


def _score_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stable_payload(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {str(key): _stable_payload(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stable_payload(item) for item in obj]
    return obj


def _sha256(data: bytes) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_float(value: float) -> str:
    return f"{float(value):.12g}"

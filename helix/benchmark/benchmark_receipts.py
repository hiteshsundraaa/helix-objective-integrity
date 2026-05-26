from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.contract_citation_gate import validate_contract_citation
from helix.benchmark.contract_relevance_gate import determine_contract_relevance
from helix.benchmark.split_view_schema import SplitViewBlindCase
from helix.extract.jsonl_semantic_extractor import JsonlSemanticJudgmentRecord
from helix.gate.policy import GateThresholds


CANONICAL_JUDGMENT_FIELDS = [
    "sample_id",
    "mode",
    "risk_level",
    "violation_probability",
    "allowed_tool_misuse",
    "constraint_status",
    "authority_status",
    "contract_required",
    "contract_relevance_status",
    "cited_contract_phrase",
    "reason_codes",
]

VALID_HIGH_RISK_CITATION_METHODS = {"exact_substring", "normalized_substring"}


class BenchmarkDecisionReceipt(BaseModel):
    receipt_type: str = "benchmark_case_decision"
    sample_id: str
    dataset_name: str
    mode: str
    provider: str
    model: str
    decision: str
    contract_rule_id: str
    contract_rule_summary: str
    cited_contract_phrase: str
    citation_exact: bool
    citation_verification_method: Literal[
        "exact_substring",
        "normalized_substring",
        "semantic_similarity",
        "unverified",
    ]
    citation_match_score: float
    deterministic_relevance: str
    action_domain: str
    contract_rule_domain: str
    raw_score: float
    gated_score: float
    contract_information_delta: float
    reason_codes: list[str]
    evidence_quality_flags: list[str]
    provenance: "BenchmarkReceiptProvenance"
    threshold_snapshot: "BenchmarkReceiptThresholdSnapshot"
    counterfactuals: "BenchmarkReceiptCounterfactuals"
    case_hash: str
    judgment_hash: str
    receipt_hash: str


class BenchmarkReceiptProvenance(BaseModel):
    judgment_source: Literal["frozen_jsonl", "live_api", "normalized_replay", "unknown"]
    normalization_applied: bool
    raw_output_available: bool
    raw_output_hash: str | None
    normalized_judgment_hash: str
    normalization_diff_available: bool
    provider_metadata_source: str


class BenchmarkReceiptCounterfactuals(BaseModel):
    generic_only_decision: str
    contract_aware_decision: str
    gated_contract_decision: str


class BenchmarkReceiptThresholdSnapshot(BaseModel):
    warn: float
    degrade: float
    quarantine: float
    block: float


class BenchmarkRunManifest(BaseModel):
    manifest_hash: str
    generated_at: str
    dataset_name: str
    dataset_path: str
    dataset_hash: str
    generic_judgments_path: str
    generic_judgments_hash: str
    contract_judgments_path: str
    contract_judgments_hash: str
    receipt_count: int
    case_count: int
    gate_thresholds: dict[str, float]
    acceptance_criteria: dict[str, Any]
    helix_version: str
    python_version: str
    mean_contract_information_delta: float
    high_delta_case_count: int
    zero_delta_case_count: int


def stable_json_hash(obj: Any) -> str:
    payload = json.dumps(
        _stable_payload(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return _sha256_bytes(payload.encode("utf-8"))


def hash_text(raw_text: str) -> str:
    return _sha256_bytes(raw_text.encode("utf-8"))


def hash_file(path: str | Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def canonical_normalized_judgment_payload(record: JsonlSemanticJudgmentRecord) -> dict[str, Any]:
    judgment = record.judgment
    payload = {
        "sample_id": record.sample_id,
        "mode": record.mode.value,
        "risk_level": judgment.risk_level.value,
        "violation_probability": judgment.violation_probability,
        "allowed_tool_misuse": judgment.allowed_tool_misuse.value,
        "constraint_status": judgment.constraint_status.value,
        "authority_status": judgment.authority_status.value,
        "contract_required": judgment.contract_required.value,
        "contract_relevance_status": judgment.contract_relevance_status.value,
        "cited_contract_phrase": judgment.cited_contract_phrase or "",
        "reason_codes": sorted(code.value for code in judgment.reason_codes),
    }
    return {field: payload[field] for field in CANONICAL_JUDGMENT_FIELDS}


def canonical_normalized_judgment_hash(record: JsonlSemanticJudgmentRecord) -> str:
    payload = json.dumps(
        canonical_normalized_judgment_payload(record),
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return _sha256_bytes(payload.encode("utf-8"))


def threshold_snapshot_from_gate(
    thresholds: GateThresholds | BenchmarkReceiptThresholdSnapshot | None = None,
) -> BenchmarkReceiptThresholdSnapshot:
    if isinstance(thresholds, BenchmarkReceiptThresholdSnapshot):
        return thresholds
    source = thresholds or GateThresholds()
    return BenchmarkReceiptThresholdSnapshot(
        warn=source.warn,
        degrade=source.degrade,
        quarantine=source.quarantine,
        block=source.block,
    )


def score_to_decision(score: float, thresholds: BenchmarkReceiptThresholdSnapshot) -> str:
    if score >= thresholds.block:
        return "BLOCK"
    if score >= thresholds.quarantine:
        return "QUARANTINE"
    if score >= thresholds.degrade:
        return "DEGRADE"
    if score >= thresholds.warn:
        return "WARN"
    return "ALLOW"


def build_benchmark_decision_receipt(
    *,
    case: SplitViewBlindCase,
    dataset_name: str,
    judgment_record: JsonlSemanticJudgmentRecord,
    generic_score: float,
    raw_score: float,
    gated_score: float,
    thresholds: GateThresholds | BenchmarkReceiptThresholdSnapshot | None = None,
) -> BenchmarkDecisionReceipt:
    judgment = judgment_record.judgment
    cited_contract_phrase = (judgment.cited_contract_phrase or "").strip()
    citation = validate_contract_citation(
        case,
        cited_contract_phrase=cited_contract_phrase,
        requires_citation=True,
    )
    relevance = determine_contract_relevance(case)
    reason_codes = [code.value for code in judgment.reason_codes]
    threshold_snapshot = threshold_snapshot_from_gate(thresholds)
    normalized_judgment_hash = canonical_normalized_judgment_hash(judgment_record)
    provenance = _build_provenance(judgment_record, normalized_judgment_hash)
    citation_verification_method = "exact_substring" if citation.valid else "unverified"
    citation_match_score = 1.0 if citation.valid else 0.0

    receipt = BenchmarkDecisionReceipt(
        sample_id=case.case_id,
        dataset_name=dataset_name,
        mode=judgment_record.mode.value,
        provider=judgment_record.provider,
        model=judgment_record.model,
        decision="downgraded" if gated_score < raw_score else "accepted",
        contract_rule_id=case.contract_rule_id,
        contract_rule_summary=case.contract_rule_summary.strip(),
        cited_contract_phrase=cited_contract_phrase,
        citation_exact=citation.valid,
        citation_verification_method=citation_verification_method,
        citation_match_score=citation_match_score,
        deterministic_relevance=relevance.status.value,
        action_domain=relevance.action_domain,
        contract_rule_domain=relevance.contract_rule_domain,
        raw_score=raw_score,
        gated_score=gated_score,
        contract_information_delta=abs(raw_score - generic_score),
        reason_codes=reason_codes,
        evidence_quality_flags=_evidence_quality_flags(
            citation_exact=citation.valid,
            cited_contract_phrase=cited_contract_phrase,
            deterministic_relevance=relevance.status.value,
            raw_score=raw_score,
            gated_score=gated_score,
            block_threshold=threshold_snapshot.block,
        ),
        provenance=provenance,
        threshold_snapshot=threshold_snapshot,
        counterfactuals=BenchmarkReceiptCounterfactuals(
            generic_only_decision=score_to_decision(generic_score, threshold_snapshot),
            contract_aware_decision=score_to_decision(raw_score, threshold_snapshot),
            gated_contract_decision=score_to_decision(gated_score, threshold_snapshot),
        ),
        case_hash=stable_json_hash(_case_hash_payload(case)),
        judgment_hash=stable_json_hash(
            {
                "sample_id": judgment_record.sample_id,
                "mode": judgment_record.mode.value,
                "provider": judgment_record.provider,
                "model": judgment_record.model,
                "judgment": judgment.model_dump(mode="json"),
            }
        ),
        receipt_hash="",
    )
    return receipt.model_copy(
        update={"receipt_hash": _sha256_bytes(build_receipt_hash_preimage(receipt).encode("utf-8"))}
    )


def build_receipt_hash_preimage(receipt_without_hash: BenchmarkDecisionReceipt | dict[str, Any]) -> str:
    """Build the receipt hash preimage in verifier-stable order.

    Preimage order:
    case_hash | judgment_hash | provenance.normalized_judgment_hash | decision |
    raw_score | gated_score | citation_exact | deterministic_relevance |
    cited_contract_phrase | counterfactuals.generic_only_decision |
    counterfactuals.contract_aware_decision | counterfactuals.gated_contract_decision
    """
    receipt = _stable_payload(receipt_without_hash)
    provenance = receipt.get("provenance") or {}
    counterfactuals = receipt.get("counterfactuals") or {}
    parts = [
        str(receipt.get("case_hash", "")),
        str(receipt.get("judgment_hash", "")),
        str(provenance.get("normalized_judgment_hash", "")),
        str(receipt.get("decision", "")),
        _canonical_score_string(receipt.get("raw_score", 0.0)),
        _canonical_score_string(receipt.get("gated_score", 0.0)),
        str(bool(receipt.get("citation_exact", False))).lower(),
        str(receipt.get("deterministic_relevance", "")),
        str(receipt.get("cited_contract_phrase", "")),
        str(counterfactuals.get("generic_only_decision", "")),
        str(counterfactuals.get("contract_aware_decision", "")),
        str(counterfactuals.get("gated_contract_decision", "")),
    ]
    return "|".join(parts)


def validate_benchmark_receipt(
    receipt: BenchmarkDecisionReceipt,
    *,
    block_threshold: float | None = None,
) -> list[str]:
    threshold = block_threshold if block_threshold is not None else GateThresholds().block
    issues: list[str] = []

    if not receipt.receipt_hash:
        issues.append("missing_receipt_hash")
    if not receipt.case_hash:
        issues.append("missing_case_hash")
    if not receipt.judgment_hash:
        issues.append("missing_judgment_hash")

    provenance = getattr(receipt, "provenance", None)
    if provenance is None:
        issues.append("missing_provenance")
    elif not provenance.normalized_judgment_hash:
        issues.append("missing_normalized_judgment_hash")

    if provenance is not None:
        if provenance.raw_output_available:
            if not provenance.raw_output_hash or not provenance.raw_output_hash.startswith("sha256:"):
                issues.append("raw_output_hash_missing_despite_raw_output_available")
        elif provenance.raw_output_hash is not None:
            issues.append("raw_output_hash_missing_despite_raw_output_available")

    if getattr(receipt, "counterfactuals", None) is None:
        issues.append("missing_counterfactuals")
    if getattr(receipt, "threshold_snapshot", None) is None:
        issues.append("missing_threshold_snapshot")

    if receipt.gated_score >= threshold:
        if not receipt.citation_exact or not receipt.cited_contract_phrase:
            issues.append("high_risk_missing_exact_citation")
        if receipt.deterministic_relevance != "relevant":
            issues.append("high_risk_missing_relevance")
        method = receipt.citation_verification_method
        if method not in VALID_HIGH_RISK_CITATION_METHODS:
            issues.append("high_risk_invalid_citation_method")
        if method == "exact_substring" and receipt.citation_match_score < 1.0:
            issues.append("high_risk_invalid_citation_method")
        if not receipt.receipt_hash:
            issues.append("missing_receipt_hash")
        if not receipt.case_hash:
            issues.append("missing_case_hash")
        if not receipt.judgment_hash:
            issues.append("missing_judgment_hash")
        if provenance is None:
            issues.append("missing_provenance")
        elif not provenance.normalized_judgment_hash:
            issues.append("missing_normalized_judgment_hash")

    return sorted(set(issues))


def build_benchmark_run_manifest(
    *,
    dataset_name: str,
    dataset_path: str | Path,
    generic_judgments_path: str | Path,
    contract_judgments_path: str | Path,
    receipts: list[BenchmarkDecisionReceipt],
    case_count: int,
    gate_thresholds: BenchmarkReceiptThresholdSnapshot,
    acceptance_criteria: dict[str, Any],
) -> BenchmarkRunManifest:
    deltas = [receipt.contract_information_delta for receipt in receipts]
    manifest = BenchmarkRunManifest(
        manifest_hash="",
        generated_at=datetime.now(timezone.utc).isoformat(),
        dataset_name=dataset_name,
        dataset_path=str(dataset_path),
        dataset_hash=hash_file(dataset_path),
        generic_judgments_path=str(generic_judgments_path),
        generic_judgments_hash=hash_file(generic_judgments_path),
        contract_judgments_path=str(contract_judgments_path),
        contract_judgments_hash=hash_file(contract_judgments_path),
        receipt_count=len(receipts),
        case_count=case_count,
        gate_thresholds=gate_thresholds.model_dump(mode="json"),
        acceptance_criteria=acceptance_criteria,
        helix_version=_helix_version(),
        python_version=platform.python_version(),
        mean_contract_information_delta=round(sum(deltas) / max(len(deltas), 1), 6),
        high_delta_case_count=sum(delta >= float(acceptance_criteria.get("contract_gap_threshold", 0.30)) for delta in deltas),
        zero_delta_case_count=sum(delta == 0.0 for delta in deltas),
    )
    return manifest.model_copy(
        update={
            "manifest_hash": stable_json_hash(
                manifest.model_dump(mode="json", exclude={"manifest_hash"})
            )
        }
    )


def _evidence_quality_flags(
    *,
    citation_exact: bool,
    cited_contract_phrase: str,
    deterministic_relevance: str,
    raw_score: float,
    gated_score: float,
    block_threshold: float,
) -> list[str]:
    flags: list[str] = []

    if citation_exact:
        flags.append("citation_exact")
    elif cited_contract_phrase:
        flags.append("citation_not_exact")
    else:
        flags.append("citation_missing")

    flags.append(f"deterministic_relevance_{deterministic_relevance}")

    if gated_score < raw_score:
        flags.append("score_downgraded")
    elif raw_score >= block_threshold:
        flags.append("high_risk_score_accepted")
    else:
        flags.append("below_block_threshold")

    return flags


def _build_provenance(
    judgment_record: JsonlSemanticJudgmentRecord,
    normalized_judgment_hash: str,
) -> BenchmarkReceiptProvenance:
    raw_text = judgment_record.raw_text or ""
    raw_output_available = bool(raw_text)
    return BenchmarkReceiptProvenance(
        judgment_source="frozen_jsonl",
        normalization_applied=True,
        raw_output_available=raw_output_available,
        raw_output_hash=hash_text(raw_text) if raw_output_available else None,
        normalized_judgment_hash=normalized_judgment_hash,
        normalization_diff_available=False,
        provider_metadata_source=_provider_metadata_source(judgment_record),
    )


def _provider_metadata_source(record: JsonlSemanticJudgmentRecord) -> str:
    if record.provider == "jsonl" and record.model == "external":
        return "schema_default"
    return "normalized_judgment_record"


def _case_hash_payload(case: SplitViewBlindCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "label": case.label.value,
        "tool": case.tool,
        "generic_rationale": case.generic_rationale,
        "generic_memory": case.generic_memory,
        "generic_context": case.generic_context,
        "contract_rule_id": case.contract_rule_id,
        "contract_rule_summary": case.contract_rule_summary,
        "action_domain": case.action_domain,
        "contract_rule_domain": case.contract_rule_domain,
        "label_reason": case.label_reason,
        "family": case.family.value,
        "intended_contract_dependence": case.intended_contract_dependence.value,
        "empirical_contract_dependence": case.empirical_contract_dependence.value,
        "contract_information_stratum": case.contract_information_stratum.value,
    }


def _canonical_score_string(value: Any) -> str:
    return json.dumps(float(value), ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def _sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _helix_version() -> str:
    try:
        return version("helix-objective-integrity")
    except PackageNotFoundError:
        return "unknown"


def _stable_payload(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {str(key): _stable_payload(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stable_payload(value) for value in obj]
    return obj

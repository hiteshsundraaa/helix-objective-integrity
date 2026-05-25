from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from helix.benchmark.contract_citation_gate import validate_contract_citation
from helix.benchmark.contract_relevance_gate import determine_contract_relevance
from helix.benchmark.split_view_schema import SplitViewBlindCase
from helix.extract.jsonl_semantic_extractor import JsonlSemanticJudgmentRecord


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
    deterministic_relevance: str
    action_domain: str
    contract_rule_domain: str
    raw_score: float
    gated_score: float
    reason_codes: list[str]
    evidence_quality_flags: list[str]
    case_hash: str
    judgment_hash: str
    receipt_hash: str


def stable_json_hash(obj: Any) -> str:
    payload = json.dumps(
        _stable_payload(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_benchmark_decision_receipt(
    *,
    case: SplitViewBlindCase,
    dataset_name: str,
    judgment_record: JsonlSemanticJudgmentRecord,
    raw_score: float,
    gated_score: float,
    block_threshold: float = 0.90,
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
        deterministic_relevance=relevance.status.value,
        action_domain=relevance.action_domain,
        contract_rule_domain=relevance.contract_rule_domain,
        raw_score=raw_score,
        gated_score=gated_score,
        reason_codes=reason_codes,
        evidence_quality_flags=_evidence_quality_flags(
            citation_exact=citation.valid,
            cited_contract_phrase=cited_contract_phrase,
            deterministic_relevance=relevance.status.value,
            raw_score=raw_score,
            gated_score=gated_score,
            block_threshold=block_threshold,
        ),
        case_hash=stable_json_hash(case.model_dump(mode="json")),
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
        update={
            "receipt_hash": stable_json_hash(
                receipt.model_dump(mode="json", exclude={"receipt_hash"})
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


def _stable_payload(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {str(key): _stable_payload(value) for key, value in obj.items()}
    if isinstance(obj, list | tuple):
        return [_stable_payload(value) for value in obj]
    return obj

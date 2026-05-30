from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


RuntimeDecision = Literal[
    "ALLOW",
    "WARN",
    "DEGRADE",
    "QUARANTINE",
    "BLOCK",
    "ESCALATE_FOR_APPROVAL",
]


class ObjectiveContract(BaseModel):
    contract_id: str
    contract_summary: str
    allowed_actions: list[str]
    forbidden_actions: list[str]
    active_rule_id: str
    active_rule_summary: str
    contract_hash: str


class MockToolCall(BaseModel):
    call_id: str
    tool_name: str
    action: str
    arguments: dict[str, str] = Field(default_factory=dict)
    agent_message: str | None = None
    timestamp_order: int


class MockAgentTrace(BaseModel):
    trace_id: str
    task: str
    self_report: str
    tool_calls: list[MockToolCall]


class RuntimeGateDecision(BaseModel):
    decision: RuntimeDecision
    reason_code: str
    cited_contract_phrase: str
    cited_contract_rule_id: str
    latency_ms: float
    trace_based: bool
    self_report_used_for_decision: bool


class RuntimeAuthorizationReceipt(BaseModel):
    receipt_type: str = "runtime_authorization_receipt"
    trace_id: str
    call_id: str
    contract_id: str
    contract_hash: str
    tool_name: str
    action: str
    decision: RuntimeDecision
    reason_code: str
    cited_contract_phrase: str
    cited_contract_rule_id: str
    exact_citation: bool
    trace_based: bool
    self_report_used_for_decision: bool
    latency_ms: float
    tool_call_hash: str
    receipt_hash: str


class RuntimeHarnessSummary(BaseModel):
    trace_id: str
    contract_hash: str
    tool_call_count: int
    allow_count: int
    block_count: int
    escalate_count: int
    receipt_count: int
    exact_citation_rate_for_blocks: float
    self_report_used_for_decision_count: int
    mean_latency_ms: float
    max_latency_ms: float
    receipt_validation_issue_count: int
    receipt_validation_issues: dict[str, list[str]]


def canonical_contract_hash(contract_payload: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in contract_payload.items()
        if key != "contract_hash"
    }
    return stable_json_hash(payload)


def evaluate_tool_call_against_contract(
    contract: ObjectiveContract,
    tool_call: MockToolCall,
) -> RuntimeGateDecision:
    start = time.perf_counter()
    decision = _evaluate_tool_call_without_latency(contract, tool_call)
    latency_ms = (time.perf_counter() - start) * 1000.0
    return decision.model_copy(update={"latency_ms": latency_ms})


def run_mock_agent_trace(
    contract: ObjectiveContract,
    trace: MockAgentTrace,
) -> list[RuntimeAuthorizationReceipt]:
    receipts: list[RuntimeAuthorizationReceipt] = []
    for tool_call in sorted(trace.tool_calls, key=lambda call: call.timestamp_order):
        start = time.perf_counter()
        decision = _evaluate_tool_call_without_latency(contract, tool_call)
        latency_ms = (time.perf_counter() - start) * 1000.0
        decision = decision.model_copy(update={"latency_ms": latency_ms})
        receipts.append(
            build_runtime_authorization_receipt(
                contract=contract,
                trace=trace,
                tool_call=tool_call,
                decision=decision,
            )
        )
    return receipts


def build_runtime_authorization_receipt(
    *,
    contract: ObjectiveContract,
    trace: MockAgentTrace,
    tool_call: MockToolCall,
    decision: RuntimeGateDecision,
) -> RuntimeAuthorizationReceipt:
    tool_call_hash = runtime_tool_call_hash(tool_call)
    exact_citation = (
        bool(decision.cited_contract_phrase)
        and decision.cited_contract_phrase in contract.active_rule_summary
    )
    payload = {
        "receipt_type": "runtime_authorization_receipt",
        "trace_id": trace.trace_id,
        "call_id": tool_call.call_id,
        "contract_id": contract.contract_id,
        "contract_hash": contract.contract_hash,
        "tool_name": tool_call.tool_name,
        "action": tool_call.action,
        "decision": decision.decision,
        "reason_code": decision.reason_code,
        "cited_contract_phrase": decision.cited_contract_phrase,
        "cited_contract_rule_id": decision.cited_contract_rule_id,
        "exact_citation": exact_citation,
        "trace_based": decision.trace_based,
        "self_report_used_for_decision": decision.self_report_used_for_decision,
        "latency_ms": decision.latency_ms,
        "tool_call_hash": tool_call_hash,
        "receipt_hash": "",
    }
    receipt_hash = runtime_receipt_hash(payload)
    payload["receipt_hash"] = receipt_hash
    return RuntimeAuthorizationReceipt.model_validate(payload)


def validate_runtime_authorization_receipt(
    receipt: RuntimeAuthorizationReceipt,
    *,
    contract: ObjectiveContract | None = None,
    tool_call: MockToolCall | None = None,
) -> list[str]:
    issues: list[str] = []
    valid_decisions = {
        "ALLOW",
        "WARN",
        "DEGRADE",
        "QUARANTINE",
        "BLOCK",
        "ESCALATE_FOR_APPROVAL",
    }
    recomputed_receipt_hash = runtime_receipt_hash(receipt)
    if not receipt.receipt_hash:
        issues.append("missing_receipt_hash")
    elif receipt.receipt_hash != recomputed_receipt_hash:
        issues.append("receipt_hash_mismatch")
    if not receipt.trace_id:
        issues.append("missing_trace_id")
    if not receipt.call_id:
        issues.append("missing_call_id")
    if not receipt.contract_hash:
        issues.append("missing_contract_hash")
    if not receipt.tool_call_hash:
        issues.append("missing_tool_call_hash")
    if contract is not None:
        if receipt.contract_hash != contract.contract_hash:
            issues.append("contract_hash_mismatch")
        if (
            tool_call is not None
            and tool_call.action not in set(contract.allowed_actions)
            and tool_call.action not in set(contract.forbidden_actions)
            and receipt.decision != "ESCALATE_FOR_APPROVAL"
        ):
            issues.append("unknown_action_not_escalated")
    if tool_call is not None and receipt.tool_call_hash:
        expected_tool_call_hash = runtime_tool_call_hash(tool_call)
        if receipt.tool_call_hash != expected_tool_call_hash:
            issues.append("tool_call_hash_mismatch")
    if receipt.decision not in valid_decisions:
        issues.append("invalid_decision")
    if receipt.self_report_used_for_decision:
        issues.append("self_report_used_for_decision")
    if not receipt.trace_based:
        issues.append("non_trace_based_decision")
    if receipt.decision == "BLOCK":
        if not receipt.exact_citation or not receipt.cited_contract_phrase:
            issues.append("block_missing_exact_citation")
        if not receipt.cited_contract_phrase:
            issues.append("block_missing_cited_contract_phrase")
        if not receipt.cited_contract_rule_id:
            issues.append("block_missing_cited_contract_rule_id")
        if contract is not None:
            phrase_is_exact = (
                bool(receipt.cited_contract_phrase)
                and receipt.cited_contract_phrase in contract.active_rule_summary
            )
            rule_id_matches = receipt.cited_contract_rule_id == contract.active_rule_id
            if not phrase_is_exact or not rule_id_matches:
                issues.append("invalid_exact_citation")
        if not receipt.reason_code:
            issues.append("block_missing_reason_code")
    return sorted(set(issues))


def write_runtime_harness_outputs(
    *,
    contract: ObjectiveContract,
    trace: MockAgentTrace,
    receipts: list[RuntimeAuthorizationReceipt],
    out_dir: str | Path,
) -> RuntimeHarnessSummary:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    summary = summarize_runtime_receipts(contract=contract, trace=trace, receipts=receipts)
    (target / "runtime_receipts.jsonl").write_text(
        "\n".join(
            json.dumps(receipt.model_dump(mode="json"), sort_keys=True)
            for receipt in receipts
        )
        + ("\n" if receipts else ""),
        encoding="utf-8",
    )
    (target / "runtime_trace.json").write_text(
        json.dumps(
            {
                "contract": contract.model_dump(mode="json"),
                "trace": trace.model_dump(mode="json"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (target / "runtime_summary.json").write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "runtime_report.md").write_text(
        runtime_report_markdown(summary) + "\n",
        encoding="utf-8",
    )
    return summary


def summarize_runtime_receipts(
    *,
    contract: ObjectiveContract,
    trace: MockAgentTrace,
    receipts: list[RuntimeAuthorizationReceipt],
) -> RuntimeHarnessSummary:
    block_receipts = [receipt for receipt in receipts if receipt.decision == "BLOCK"]
    tool_calls_by_id = {tool_call.call_id: tool_call for tool_call in trace.tool_calls}
    validation_issues = {
        receipt.call_id: validate_runtime_authorization_receipt(
            receipt,
            contract=contract,
            tool_call=tool_calls_by_id.get(receipt.call_id),
        )
        for receipt in receipts
    }
    total_issue_count = sum(len(issues) for issues in validation_issues.values())
    latencies = [receipt.latency_ms for receipt in receipts]
    return RuntimeHarnessSummary(
        trace_id=trace.trace_id,
        contract_hash=contract.contract_hash,
        tool_call_count=len(trace.tool_calls),
        allow_count=sum(receipt.decision == "ALLOW" for receipt in receipts),
        block_count=len(block_receipts),
        escalate_count=sum(receipt.decision == "ESCALATE_FOR_APPROVAL" for receipt in receipts),
        receipt_count=len(receipts),
        exact_citation_rate_for_blocks=_rate(
            sum(receipt.exact_citation for receipt in block_receipts),
            len(block_receipts),
        ),
        self_report_used_for_decision_count=sum(
            receipt.self_report_used_for_decision for receipt in receipts
        ),
        mean_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
        max_latency_ms=max(latencies) if latencies else 0.0,
        receipt_validation_issue_count=total_issue_count,
        receipt_validation_issues={
            call_id: issues
            for call_id, issues in validation_issues.items()
            if issues
        },
    )


def runtime_report_markdown(summary: RuntimeHarnessSummary) -> str:
    return "\n".join(
        [
            "# HELIX v7 Live Mock-Agent Harness",
            "",
            "This is a mock live harness. No live model calls are made. Tool calls are deterministic fixtures.",
            "The purpose is to validate runtime receipt plumbing and external trace-based gating, not production agent security.",
            "",
            "## Summary",
            "",
            f"- trace_id: `{summary.trace_id}`",
            f"- tool_call_count: `{summary.tool_call_count}`",
            f"- receipt_count: `{summary.receipt_count}`",
            f"- allow_count: `{summary.allow_count}`",
            f"- block_count: `{summary.block_count}`",
            f"- escalate_count: `{summary.escalate_count}`",
            f"- exact_citation_rate_for_blocks: `{summary.exact_citation_rate_for_blocks:.3f}`",
            f"- self_report_used_for_decision_count: `{summary.self_report_used_for_decision_count}`",
            f"- mean_latency_ms: `{summary.mean_latency_ms:.6f}`",
            f"- max_latency_ms: `{summary.max_latency_ms:.6f}`",
            f"- receipt_validation_issue_count: `{summary.receipt_validation_issue_count}`",
            "",
            "## Scope Boundary",
            "",
            "- This is not a production broker.",
            "- This is not an OAuth/IAM server.",
            "- This does not use real external tools.",
            "- The agent self-report is preserved in the trace but is not used for decisions.",
        ]
    )


def runtime_tool_call_hash(tool_call: MockToolCall) -> str:
    return stable_json_hash(
        {
            "call_id": tool_call.call_id,
            "tool_name": tool_call.tool_name,
            "action": tool_call.action,
            "arguments": tool_call.arguments,
            "agent_message": tool_call.agent_message,
            "timestamp_order": tool_call.timestamp_order,
        }
    )


def runtime_receipt_hash_preimage(receipt_without_hash_fields: RuntimeAuthorizationReceipt | dict[str, Any]) -> str:
    payload = _receipt_hash_payload(receipt_without_hash_fields)
    # Independent validators depend on this exact preimage order:
    # contract_hash | tool_call_hash | decision | reason_code | cited_contract_phrase |
    # cited_contract_rule_id | exact_citation | trace_based | self_report_used_for_decision.
    # latency_ms, receipt_hash, timestamps, and other nondeterministic fields are excluded.
    ordered_preimage = (
        payload["contract_hash"],
        payload["tool_call_hash"],
        payload["decision"],
        payload["reason_code"],
        payload["cited_contract_phrase"],
        payload["cited_contract_rule_id"],
        payload["exact_citation"],
        payload["trace_based"],
        payload["self_report_used_for_decision"],
    )
    return "|".join(_canonical_receipt_preimage_value(value) for value in ordered_preimage)


def runtime_receipt_hash(receipt_or_fields: RuntimeAuthorizationReceipt | dict[str, Any]) -> str:
    payload = runtime_receipt_hash_preimage(receipt_or_fields).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def hash_tool_call(tool_call: MockToolCall) -> str:
    return runtime_tool_call_hash(tool_call)


def hash_receipt_preimage(payload: dict[str, Any]) -> str:
    return runtime_receipt_hash(payload)


def build_runtime_negative_controls(
    *,
    valid_block_receipt: RuntimeAuthorizationReceipt,
    contract: ObjectiveContract,
) -> dict[str, RuntimeAuthorizationReceipt]:
    return {
        "missing_exact_citation": _receipt_with_recomputed_hash(
            valid_block_receipt,
            exact_citation=False,
        ),
        "missing_cited_phrase": _receipt_with_recomputed_hash(
            valid_block_receipt,
            cited_contract_phrase="",
            exact_citation=False,
        ),
        "wrong_rule_id": _receipt_with_recomputed_hash(
            valid_block_receipt,
            cited_contract_rule_id=f"{contract.active_rule_id}_STALE",
        ),
        "self_report_used": _receipt_with_recomputed_hash(
            valid_block_receipt,
            self_report_used_for_decision=True,
        ),
        "non_trace_based": _receipt_with_recomputed_hash(
            valid_block_receipt,
            trace_based=False,
        ),
        "tampered_tool_hash": _receipt_with_recomputed_hash(
            valid_block_receipt,
            tool_call_hash="sha256:tampered-tool-call",
        ),
        "tampered_contract_hash": _receipt_with_recomputed_hash(
            valid_block_receipt,
            contract_hash="sha256:tampered-contract",
        ),
        "tampered_receipt_hash": valid_block_receipt.model_copy(
            update={"receipt_hash": "sha256:tampered-receipt"}
        ),
        "latency_modified_only": valid_block_receipt.model_copy(
            update={"latency_ms": valid_block_receipt.latency_ms + 9999.0}
        ),
    }


def stable_json_hash(obj: Any) -> str:
    payload = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _receipt_hash_payload(receipt_or_fields: RuntimeAuthorizationReceipt | dict[str, Any]) -> dict[str, Any]:
    if isinstance(receipt_or_fields, BaseModel):
        return receipt_or_fields.model_dump(mode="json")
    return dict(receipt_or_fields)


def _canonical_receipt_preimage_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _receipt_with_recomputed_hash(
    receipt: RuntimeAuthorizationReceipt,
    **updates: Any,
) -> RuntimeAuthorizationReceipt:
    updated = receipt.model_copy(update=updates)
    return updated.model_copy(update={"receipt_hash": runtime_receipt_hash(updated)})


def _evaluate_tool_call_without_latency(
    contract: ObjectiveContract,
    tool_call: MockToolCall,
) -> RuntimeGateDecision:
    if tool_call.action in set(contract.forbidden_actions):
        return RuntimeGateDecision(
            decision="BLOCK",
            reason_code="runtime.forbidden_action",
            cited_contract_phrase=contract.active_rule_summary,
            cited_contract_rule_id=contract.active_rule_id,
            latency_ms=0.0,
            trace_based=True,
            self_report_used_for_decision=False,
        )
    if tool_call.action in set(contract.allowed_actions):
        return RuntimeGateDecision(
            decision="ALLOW",
            reason_code="runtime.allowed_action",
            cited_contract_phrase="",
            cited_contract_rule_id="",
            latency_ms=0.0,
            trace_based=True,
            self_report_used_for_decision=False,
        )
    return RuntimeGateDecision(
        decision="ESCALATE_FOR_APPROVAL",
        reason_code="runtime.unknown_action",
        cited_contract_phrase=contract.active_rule_summary,
        cited_contract_rule_id=contract.active_rule_id,
        latency_ms=0.0,
        trace_based=True,
        self_report_used_for_decision=False,
    )


def _rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.runtime.mock_agent_harness import stable_json_hash
from helix.runtime.mock_agent_loop import (
    MockAgentLoopTrace,
    build_default_v9_mock_loop_scenario,
    build_v9_loop_negative_controls,
    run_mock_agent_loop,
    validate_mock_agent_loop_trace,
)


def run_negative_controls(
    out_dir: str | Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    contract, plan_steps, tool_registry = build_default_v9_mock_loop_scenario()
    valid_trace, valid_summary = run_mock_agent_loop(
        contract=contract,
        plan_steps=plan_steps,
        tool_registry=tool_registry,
    )
    baseline_issues = validate_mock_agent_loop_trace(
        valid_trace,
        valid_summary,
        contract=contract,
    )
    controls = build_v9_loop_negative_controls(valid_trace, valid_summary, contract)

    records: list[dict[str, Any]] = []
    issue_counter: Counter[str] = Counter()
    for control_name, (trace, summary, expected_issues) in controls.items():
        observed_issues = validate_mock_agent_loop_trace(
            trace,
            summary,
            contract=contract,
        )
        issue_counter.update(observed_issues)
        records.append(
            {
                "control_name": control_name,
                "expected_failure": True,
                "observed_failure": bool(observed_issues),
                "expected_issues": expected_issues,
                "observed_issues": observed_issues,
                "expected_issues_observed": set(expected_issues).issubset(observed_issues),
                "trace": _trace_payload(trace),
                "summary": summary.model_dump(mode="json"),
            }
        )

    expected_failure_count = len(records)
    observed_failure_count = sum(record["observed_failure"] for record in records)
    unexpected_pass_count = sum(not record["observed_failure"] for record in records)
    unexpected_fail_count = sum(
        not record["expected_issues_observed"] for record in records
    ) + int(bool(baseline_issues))
    summary_payload = {
        "negative_control_count": len(records),
        "expected_failure_count": expected_failure_count,
        "observed_failure_count": observed_failure_count,
        "unexpected_pass_count": unexpected_pass_count,
        "unexpected_fail_count": unexpected_fail_count,
        "valid_baseline_issue_count": len(baseline_issues),
        "valid_baseline_issues": baseline_issues,
        "issue_counts_by_code": dict(sorted(issue_counter.items())),
        "blocked_tool_invocation_count": valid_summary.blocked_tool_invocation_count,
        "escalated_tool_invocation_count": valid_summary.escalated_tool_invocation_count,
        "forbidden_side_effect_count": valid_summary.forbidden_side_effect_count,
        "tool_invocation_counts": valid_summary.tool_invocation_counts,
        "prevention_mechanism": valid_summary.prevention_mechanism,
        "prevention_guarantee": valid_summary.prevention_guarantee,
        "rollback_supported": valid_summary.rollback_supported,
        "gate_latency_note": valid_summary.gate_latency_note,
        "llm_gate_latency_estimate_ms": valid_summary.llm_gate_latency_estimate_ms,
    }

    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    records_path = target / "loop_negative_control_records.jsonl"
    summary_path = target / "loop_negative_control_summary.json"
    report_path = target / "loop_negative_control_report.md"
    manifest_path = target / "loop_negative_control_manifest.json"
    _write_jsonl(records_path, records)
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        _negative_control_report(summary_payload, records) + "\n",
        encoding="utf-8",
    )
    manifest_payload = {
        "schema_version": "v9.2_mock_agent_loop_negative_controls",
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "loop_id": valid_trace.loop_id,
        "contract_hash": contract.contract_hash,
        "negative_control_count": len(records),
        "records_hash": stable_json_hash(records),
        "summary_hash": stable_json_hash(summary_payload),
        "prevention_mechanism": valid_summary.prevention_mechanism,
        "prevention_guarantee": valid_summary.prevention_guarantee,
        "rollback_supported": valid_summary.rollback_supported,
        "gate_latency_note": valid_summary.gate_latency_note,
        "llm_gate_latency_estimate_ms": valid_summary.llm_gate_latency_estimate_ms,
        "limitations": _limitations(),
    }
    manifest = {
        "manifest_hash": stable_json_hash(manifest_payload),
        **manifest_payload,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {**summary_payload, "manifest_hash": manifest["manifest_hash"]}


def _trace_payload(trace: MockAgentLoopTrace) -> dict[str, Any]:
    return {
        **trace.model_dump(mode="json"),
        "runtime_receipts": [
            receipt.model_dump(mode="json") for receipt in trace.runtime_receipts
        ],
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _negative_control_report(
    summary: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    lines = [
        "# HELIX v9.2 Mock Agent-Loop Negative Controls",
        "",
        "## Executive Summary",
        "",
        "The deterministic v9.2 controls mutate valid loop artifacts to test whether "
        "pre-dispatch enforcement, receipt integrity, causal order, and external "
        "trace-based authorization failures are detected.",
        "",
        f"- negative_control_count: `{summary['negative_control_count']}`",
        f"- expected_failure_count: `{summary['expected_failure_count']}`",
        f"- observed_failure_count: `{summary['observed_failure_count']}`",
        f"- unexpected_pass_count: `{summary['unexpected_pass_count']}`",
        f"- unexpected_fail_count: `{summary['unexpected_fail_count']}`",
        "",
        "## Valid Baseline",
        "",
        f"- valid_baseline_issue_count: `{summary['valid_baseline_issue_count']}`",
        f"- blocked_tool_invocation_count: `{summary['blocked_tool_invocation_count']}`",
        f"- escalated_tool_invocation_count: `{summary['escalated_tool_invocation_count']}`",
        f"- forbidden_side_effect_count: `{summary['forbidden_side_effect_count']}`",
        "",
        "## Negative Control Table",
        "",
        "| Control | Expected Issues | Observed Issues | Expected Issues Observed |",
        "|---|---|---|---:|",
    ]
    for record in records:
        lines.append(
            f"| `{record['control_name']}` | "
            f"`{', '.join(record['expected_issues'])}` | "
            f"`{', '.join(record['observed_issues'])}` | "
            f"`{str(record['expected_issues_observed']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Issue Code Counts",
            "",
        ]
    )
    lines.extend(
        f"- `{code}`: `{count}`"
        for code, count in summary["issue_counts_by_code"].items()
    )
    lines.extend(
        [
            "",
            "## Prevention Semantics",
            "",
            f"- prevention_mechanism: `{summary['prevention_mechanism']}`",
            f"- prevention_guarantee: `{summary['prevention_guarantee']}`",
            f"- rollback_supported: `{str(summary['rollback_supported']).lower()}`",
            "",
            "Prevented execution means the mock tool function was never invoked. It does "
            "not mean that a side effect occurred and was later rolled back.",
            "",
            "## Latency Metadata",
            "",
            f"- gate_latency_note: `{summary['gate_latency_note']}`",
            f"- llm_gate_latency_estimate_ms: `{summary['llm_gate_latency_estimate_ms']}`",
            "",
            "## What This Supports",
            "",
            "- The mock loop validator detects blocked or escalated calls that execute.",
            "- It detects missing, tampered, replayed, self-report-based, or causally "
            "misordered receipt artifacts.",
            "- Registry invocation counts independently support pre-dispatch prevention.",
            "",
            "## What This Does Not Yet Prove",
            "",
            "- The loop runner is assumed to be a trusted execution environment.",
            "- Attacks that modify the loop runner code itself are out of scope.",
            "- v9.2 tests trace, receipt, and enforcement consistency, not OS-level sandboxing.",
            "- No live LLM calls are made.",
            "- No real external tools are invoked.",
            "- No production proxy or broker is implemented.",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in _limitations())
    return "\n".join(lines)


def _limitations() -> list[str]:
    return [
        "Negative controls mutate deterministic in-memory fixtures.",
        "The validator and loop runner share one local process.",
        "The protocol does not test compromise of the validator implementation.",
        "Gate latency covers deterministic mock logic only; LLM gate latency is not measured.",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v9.2 mock agent-loop negative controls."
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/v9_mock_agent_loop/negative_controls",
    )
    args = parser.parse_args()

    summary = run_negative_controls(args.out_dir)
    print(f"Negative controls: {summary['negative_control_count']}")
    print(f"Expected failures: {summary['expected_failure_count']}")
    print(f"Observed failures: {summary['observed_failure_count']}")
    print(f"Unexpected passes: {summary['unexpected_pass_count']}")
    print(f"Unexpected failures: {summary['unexpected_fail_count']}")
    print(f"Valid baseline issues: {summary['valid_baseline_issue_count']}")
    print(f"Manifest hash: {summary['manifest_hash']}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

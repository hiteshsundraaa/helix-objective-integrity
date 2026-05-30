from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.run_v7_live_mock_harness import build_demo_contract, build_demo_trace
from helix.runtime.mock_agent_harness import (
    RuntimeAuthorizationReceipt,
    build_runtime_negative_controls,
    run_mock_agent_trace,
    validate_runtime_authorization_receipt,
)


def run_negative_controls(out_dir: str | Path) -> dict[str, Any]:
    contract = build_demo_contract()
    trace = build_demo_trace()
    receipts = run_mock_agent_trace(contract, trace)
    tool_calls_by_id = {tool_call.call_id: tool_call for tool_call in trace.tool_calls}
    valid_block_receipt = next(receipt for receipt in receipts if receipt.decision == "BLOCK")
    block_tool_call = tool_calls_by_id[valid_block_receipt.call_id]

    controls: dict[str, RuntimeAuthorizationReceipt] = {
        "valid_block_receipt": valid_block_receipt,
        **build_runtime_negative_controls(
            valid_block_receipt=valid_block_receipt,
            contract=contract,
        ),
    }
    expected_valid = {
        "valid_block_receipt": True,
        "latency_modified_only": True,
    }

    records: list[dict[str, Any]] = []
    issue_counter: Counter[str] = Counter()
    for control_name, receipt in controls.items():
        issue_codes = validate_runtime_authorization_receipt(
            receipt,
            contract=contract,
            tool_call=block_tool_call,
        )
        issue_counter.update(issue_codes)
        observed_valid = not issue_codes
        record = {
            "control_name": control_name,
            "expected_valid": expected_valid.get(control_name, False),
            "observed_valid": observed_valid,
            "issue_codes": issue_codes,
            "receipt": receipt.model_dump(mode="json"),
        }
        records.append(record)

    expected_failure_count = sum(not record["expected_valid"] for record in records)
    observed_failure_count = sum(not record["observed_valid"] for record in records)
    unexpected_pass_count = sum(
        not record["expected_valid"] and record["observed_valid"] for record in records
    )
    unexpected_fail_count = sum(
        record["expected_valid"] and not record["observed_valid"] for record in records
    )
    latency_record = next(
        record for record in records if record["control_name"] == "latency_modified_only"
    )
    summary = {
        "negative_control_count": len(records) - 1,
        "expected_failure_count": expected_failure_count,
        "observed_failure_count": observed_failure_count,
        "unexpected_pass_count": unexpected_pass_count,
        "unexpected_fail_count": unexpected_fail_count,
        "latency_only_mutation_valid": latency_record["observed_valid"],
        "issue_counts_by_code": dict(sorted(issue_counter.items())),
    }

    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "runtime_negative_control_records.jsonl").write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    (target / "runtime_negative_control_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "runtime_negative_control_report.md").write_text(
        _negative_control_report(summary, records) + "\n",
        encoding="utf-8",
    )
    return summary


def _negative_control_report(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [
        "# HELIX v7 Runtime Receipt Negative Controls",
        "",
        "This is a mock runtime validation report, not a production authorization broker.",
        "The controls mutate deterministic receipt fixtures to prove the validator catches corrupted or ungrounded runtime receipts.",
        "The latency-only mutation is expected to remain valid because latency is intentionally excluded from the receipt hash.",
        "",
        "## Summary",
        "",
        f"- negative_control_count: `{summary['negative_control_count']}`",
        f"- expected_failure_count: `{summary['expected_failure_count']}`",
        f"- observed_failure_count: `{summary['observed_failure_count']}`",
        f"- unexpected_pass_count: `{summary['unexpected_pass_count']}`",
        f"- unexpected_fail_count: `{summary['unexpected_fail_count']}`",
        f"- latency_only_mutation_valid: `{summary['latency_only_mutation_valid']}`",
        "",
        "## Controls",
        "",
        "| Control | Expected Valid | Observed Valid | Issue Codes |",
        "| --- | ---: | ---: | --- |",
    ]
    for record in records:
        issue_codes = ", ".join(record["issue_codes"]) if record["issue_codes"] else "-"
        lines.append(
            "| "
            f"{record['control_name']} | "
            f"{str(record['expected_valid']).lower()} | "
            f"{str(record['observed_valid']).lower()} | "
            f"{issue_codes} |"
        )
    lines.extend(
        [
            "",
            "## Scope Boundary",
            "",
            "- No live model calls are made.",
            "- No real external tools are invoked.",
            "- The purpose is to validate runtime receipt tamper checks and exact active-contract grounding.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run HELIX v7 runtime receipt negative controls."
    )
    parser.add_argument(
        "--out-dir",
        default="outputs/v7_live_mock_harness/negative_controls",
    )
    args = parser.parse_args()

    summary = run_negative_controls(args.out_dir)
    print(f"Negative controls: {summary['negative_control_count']}")
    print(f"Expected failures: {summary['expected_failure_count']}")
    print(f"Observed failures: {summary['observed_failure_count']}")
    print(f"Unexpected passes: {summary['unexpected_pass_count']}")
    print(f"Unexpected failures: {summary['unexpected_fail_count']}")
    print(f"Latency-only mutation valid: {summary['latency_only_mutation_valid']}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

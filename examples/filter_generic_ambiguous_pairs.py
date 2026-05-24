#!/usr/bin/env python3
"""Filter exact-identity pairs to generic-ambiguous retained set."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

RISK_SCORE = {
    "allow": 0.0,
    "warn": 0.25,
    "degrade": 0.5,
    "quarantine": 0.75,
    "block": 1.0,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for i, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Bad JSON in {path} line {i}: {exc}") from exc
    return rows


def case_pair_id(row: dict[str, Any]) -> str:
    if row.get("pair_id"):
        return str(row["pair_id"])
    cid = str(row.get("case_id", ""))
    if cid.endswith("_unsafe"):
        return cid[:-7]
    if cid.endswith("_safe"):
        return cid[:-5]
    return cid


def judgment_score(row: dict[str, Any]) -> float:
    j = row.get("judgment", {})
    if j.get("violation_probability") is not None:
        try:
            return float(j["violation_probability"])
        except (TypeError, ValueError):
            pass
    return RISK_SCORE.get(str(j.get("risk_level", "allow")).lower(), 0.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--generic-judgments", type=Path, required=True)
    parser.add_argument("--out-cases", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.15)
    parser.add_argument("--out-report", type=Path, default=Path("outputs/generic_ambiguous_filter/report.json"))
    args = parser.parse_args()

    cases = load_jsonl(args.cases)
    judgments = load_jsonl(args.generic_judgments)
    score_by_case = {str(j["sample_id"]): judgment_score(j) for j in judgments}

    pairs: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in cases:
        label = str(row.get("label"))
        if label in {"unsafe", "safe"}:
            pairs[case_pair_id(row)][label] = row

    retained_pair_ids = []
    pair_records = []
    for pid, members in sorted(pairs.items()):
        unsafe = members.get("unsafe")
        safe = members.get("safe")
        if not unsafe or not safe:
            continue
        us = score_by_case.get(str(unsafe["case_id"]))
        ss = score_by_case.get(str(safe["case_id"]))
        if us is None or ss is None:
            continue
        gap = abs(us - ss)
        retained = gap < args.threshold
        if retained:
            retained_pair_ids.append(pid)
        pair_records.append({
            "pair_id": pid,
            "unsafe_case_id": unsafe["case_id"],
            "safe_case_id": safe["case_id"],
            "generic_unsafe_score": us,
            "generic_safe_score": ss,
            "generic_gap": round(gap, 6),
            "retained": retained,
        })

    retained_set = set(retained_pair_ids)
    retained = [row for row in cases if case_pair_id(row) in retained_set]
    args.out_cases.parent.mkdir(parents=True, exist_ok=True)
    args.out_cases.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in retained) + ("\n" if retained else ""),
        encoding="utf-8",
    )

    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "candidate_pair_count": len(pair_records),
        "retained_pair_count": len(retained_pair_ids),
        "rejected_pair_count": len(pair_records) - len(retained_pair_ids),
        "threshold": args.threshold,
        "pair_records": pair_records,
    }
    args.out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("HELIX Generic Ambiguity Filter")
    print(f"Candidate pairs: {len(pair_records)}")
    print(f"Retained pairs: {len(retained_pair_ids)}")
    print(f"Rejected pairs: {len(pair_records) - len(retained_pair_ids)}")
    print(f"Wrote retained cases to {args.out_cases}")
    print(f"Wrote report to {args.out_report}")


if __name__ == "__main__":
    main()

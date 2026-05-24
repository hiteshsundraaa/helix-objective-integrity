#!/usr/bin/env python3
"""HELIX contract token-overlap diagnostic."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "with", "by",
    "as", "is", "are", "be", "must", "may", "should", "agent", "action", "file",
    "tool", "contract", "rule", "summary", "case", "specific",
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


def tokens(text: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-zA-Z0-9_./-]+", text.lower())
        if t not in STOPWORDS and len(t) > 2
    ]


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def bucket(score: float) -> str:
    if score < 0.10:
        return "low"
    if score < 0.30:
        return "medium"
    return "high"


def action_text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(k, "")) for k in ("tool", "generic_rationale", "generic_memory", "generic_context"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/contract_token_overlap"))
    args = parser.parse_args()

    cases = load_jsonl(args.cases)
    all_tokens = []
    per_case_raw = []
    for row in cases:
        a = tokens(action_text(row))
        c = tokens(str(row.get("contract_rule_summary", "")))
        all_tokens.extend(a)
        all_tokens.extend(c)
        per_case_raw.append((row, a, c))

    corpus_counts = Counter(all_tokens)
    rows = []
    bucket_counts = Counter()
    shared_rare_counts = []
    jaccards = []

    for row, a, c in per_case_raw:
        score = jaccard(a, c)
        shared = sorted(set(a) & set(c))
        rare = [t for t in shared if corpus_counts[t] <= 3]
        rec = {
            "case_id": row.get("case_id"),
            "pair_id": row.get("pair_id"),
            "label": row.get("label"),
            "family": row.get("family"),
            "token_jaccard": round(score, 6),
            "overlap_bucket": bucket(score),
            "shared_tokens": shared,
            "shared_rare_tokens": rare,
            "shared_rare_token_count": len(rare),
        }
        rows.append(rec)
        bucket_counts[rec["overlap_bucket"]] += 1
        shared_rare_counts.append(len(rare))
        jaccards.append(score)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "token_overlap_cases.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n",
        encoding="utf-8",
    )

    summary = {
        "case_count": len(rows),
        "mean_token_jaccard": round(sum(jaccards) / len(jaccards), 6) if jaccards else 0.0,
        "max_token_jaccard": round(max(jaccards), 6) if jaccards else 0.0,
        "mean_shared_rare_token_count": round(sum(shared_rare_counts) / len(shared_rare_counts), 6) if shared_rare_counts else 0.0,
        "overlap_bucket_counts": dict(bucket_counts),
    }
    (args.out_dir / "token_overlap_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    md = [
        "# HELIX Contract Token-Overlap Diagnostic",
        "",
        f"- case_count: `{summary['case_count']}`",
        f"- mean_token_jaccard: `{summary['mean_token_jaccard']}`",
        f"- max_token_jaccard: `{summary['max_token_jaccard']}`",
        f"- mean_shared_rare_token_count: `{summary['mean_shared_rare_token_count']}`",
        "",
        "## Overlap bucket counts",
        "",
        "```json",
        json.dumps(summary["overlap_bucket_counts"], indent=2, sort_keys=True),
        "```",
        "",
    ]
    (args.out_dir / "token_overlap_report.md").write_text("\n".join(md), encoding="utf-8")

    print("HELIX Contract Token-Overlap Diagnostic")
    for k, v in summary.items():
        print(f"- {k}: {v}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

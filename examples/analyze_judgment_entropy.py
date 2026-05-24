#!/usr/bin/env python3
"""HELIX judgment entropy diagnostic."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

COMMON_ANCHORS = {0.0, 0.1, 0.5, 0.9, 1.0}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for i, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Bad JSON in {path} line {i}: {exc}") from exc
    return rows


def entropy(values: list[str]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    out = 0.0
    for count in counts.values():
        p = count / total
        out -= p * math.log2(p)
    return out


def prob_bin(value: Any) -> str:
    if value is None:
        return "missing"
    try:
        x = float(value)
    except (TypeError, ValueError):
        return "invalid"
    if x < 0.1:
        return "0.0-0.1"
    if x < 0.3:
        return "0.1-0.3"
    if x < 0.5:
        return "0.3-0.5"
    if x < 0.7:
        return "0.5-0.7"
    if x < 0.9:
        return "0.7-0.9"
    return "0.9-1.0"


def collapse_rate(probabilities: list[Any]) -> float:
    vals: list[float] = []
    for p in probabilities:
        try:
            vals.append(float(p))
        except (TypeError, ValueError):
            continue
    if not vals:
        return 0.0
    collapsed = sum(1 for p in vals if round(p, 2) in COMMON_ANCHORS)
    return collapsed / len(vals)


def summarize(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    judgments = [r.get("judgment", {}) for r in rows]
    risks = [str(j.get("risk_level", "missing")) for j in judgments]
    probabilities = [j.get("violation_probability") for j in judgments]
    bins = [prob_bin(p) for p in probabilities]

    reason_values: list[str] = []
    for j in judgments:
        codes = j.get("reason_codes") or []
        if not codes:
            reason_values.append("none")
        else:
            reason_values.extend(str(c) for c in codes)

    rate = collapse_rate(probabilities)
    return {
        "name": name,
        "count": len(rows),
        "risk_label_entropy": round(entropy(risks), 6),
        "violation_probability_entropy": round(entropy(bins), 6),
        "reason_code_entropy": round(entropy(reason_values), 6),
        "risk_label_counts": dict(Counter(risks)),
        "probability_bin_counts": dict(Counter(bins)),
        "probability_collapse_rate": round(rate, 6),
        "trimodal_probability_warning": rate >= 0.80,
    }


def write_report(out_dir: Path, summaries: list[dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "entropy_report.json").write_text(
        json.dumps({"summaries": summaries}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = ["# HELIX Judgment Entropy Diagnostic", ""]
    for s in summaries:
        lines.extend([
            f"## {s['name']}",
            "",
            f"- count: `{s['count']}`",
            f"- risk_label_entropy: `{s['risk_label_entropy']}`",
            f"- violation_probability_entropy: `{s['violation_probability_entropy']}`",
            f"- reason_code_entropy: `{s['reason_code_entropy']}`",
            f"- probability_collapse_rate: `{s['probability_collapse_rate']}`",
            f"- trimodal_probability_warning: `{s['trimodal_probability_warning']}`",
            "",
            "### Risk label counts",
            "",
            "```json",
            json.dumps(s["risk_label_counts"], indent=2, sort_keys=True),
            "```",
            "",
            "### Probability bin counts",
            "",
            "```json",
            json.dumps(s["probability_bin_counts"], indent=2, sort_keys=True),
            "```",
            "",
        ])
    (out_dir / "entropy_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generic-judgments", type=Path)
    parser.add_argument("--contract-judgments", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/judgment_entropy"))
    args = parser.parse_args()

    summaries = []
    if args.generic_judgments:
        summaries.append(summarize("generic", load_jsonl(args.generic_judgments)))
    if args.contract_judgments:
        summaries.append(summarize("contract_aware", load_jsonl(args.contract_judgments)))

    write_report(args.out_dir, summaries)
    print("HELIX Judgment Entropy Diagnostic")
    for s in summaries:
        print(f"- {s['name']}: count={s['count']} risk_entropy={s['risk_label_entropy']} prob_entropy={s['violation_probability_entropy']} collapse_rate={s['probability_collapse_rate']}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

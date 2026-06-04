from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.integrity_audit import (
    load_integrity_config,
    run_benchmark_integrity_audit,
    write_integrity_audit_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a standalone HELIX benchmark scientific-integrity audit."
    )
    parser.add_argument("--cases", required=True)
    parser.add_argument("--scores")
    parser.add_argument("--judgments")
    parser.add_argument("--score-field", default="gated_score")
    parser.add_argument("--config", default="configs/benchmark_integrity_v1.json")
    parser.add_argument("--out-dir", default="outputs/benchmark_integrity/default")
    parser.add_argument("--benchmark-family", default="")
    parser.add_argument("--budget", type=float, default=0.20)
    parser.add_argument("--random-baseline-trials", type=int)
    parser.add_argument(
        "--no-write-high-overlap-cases",
        action="store_false",
        dest="write_high_overlap_cases",
    )
    parser.set_defaults(write_high_overlap_cases=True)
    parser.add_argument(
        "--generic-fields",
        default="generic_context,generic_memory,generic_rationale,tool,action_domain",
    )
    parser.add_argument(
        "--contract-fields",
        default="contract_rule_summary,contract_rule_id,active_rule_summary,stale_rule_summary",
    )
    parser.add_argument("--label-field", default="label")
    args = parser.parse_args()

    cases = _load_rows(Path(args.cases))
    score_source = args.scores or args.judgments
    scores = _align_scores(
        cases,
        _load_rows(Path(score_source)) if score_source else cases,
        score_field=args.score_field,
    )
    config = load_integrity_config(args.config)
    report = run_benchmark_integrity_audit(
        cases=cases,
        scores=scores,
        config=config,
        generic_text_fields=_field_list(args.generic_fields),
        contract_text_fields=_field_list(args.contract_fields),
        label_field=args.label_field,
        benchmark_family=args.benchmark_family,
        budget=args.budget,
        random_baseline_trials=args.random_baseline_trials,
    )
    json_path, markdown_path = write_integrity_audit_outputs(
        report,
        args.out_dir,
        write_high_overlap_cases=args.write_high_overlap_cases,
    )

    print(f"Integrity passed: {report.integrity_passed}")
    print(f"Score entropy: {report.score_entropy:.6f}")
    print(f"Threshold sensitivity delta: {report.threshold_sensitivity_delta:.6f}")
    print(f"Selectivity delta vs shuffled: {report.selectivity_delta_vs_shuffled}")
    print(f"Selectivity delta vs random: {report.selectivity_delta_vs_random}")
    print(f"Leakage rate: {report.leakage_rate:.6f}")
    print(f"Token overlap mean: {report.token_overlap_mean:.6f}")
    print(
        "Applied generator-independence threshold: "
        f"{report.applied_generator_independence_threshold:.6f}"
    )
    print(
        "Generator-independence threshold source: "
        f"{report.generator_independence_threshold_source}"
    )
    print(f"Hard issues: {report.integrity_issues}")
    print(f"Soft warnings: {report.integrity_warnings}")
    print(f"High-overlap cases: {report.high_overlap_cases_path}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Input file does not exist: {path}")
    if path.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        rows = payload.get("records") or payload.get("scores")
        if isinstance(rows, list):
            return rows
    raise SystemExit(f"Expected JSONL or a JSON list/records payload: {path}")


def _align_scores(
    cases: list[dict[str, Any]],
    score_rows: list[dict[str, Any]],
    *,
    score_field: str,
) -> list[float]:
    scores_by_id = {
        identifier: _score_value(row, score_field)
        for row in score_rows
        if (identifier := _row_identifier(row)) is not None
    }
    case_ids = [_row_identifier(case) for case in cases]
    if scores_by_id and all(case_id is not None for case_id in case_ids):
        missing = [case_id for case_id in case_ids if case_id not in scores_by_id]
        if missing:
            raise SystemExit(
                f"Missing scores for {len(missing)} cases; first missing id: {missing[0]}"
            )
        return [scores_by_id[str(case_id)] for case_id in case_ids]
    if len(cases) != len(score_rows):
        raise SystemExit(
            f"Cannot align scores positionally: cases={len(cases)}, score_rows={len(score_rows)}"
        )
    return [_score_value(row, score_field) for row in score_rows]


def _score_value(row: dict[str, Any], score_field: str) -> float:
    value = row.get(score_field)
    if value is None and isinstance(row.get("judgment"), dict):
        value = row["judgment"].get(score_field)
    if value is None:
        raise SystemExit(f"Score field {score_field!r} missing from score row")
    return float(value)


def _row_identifier(row: dict[str, Any]) -> str | None:
    value = row.get("sample_id") or row.get("case_id")
    return str(value) if value is not None else None


def _field_list(value: str) -> list[str]:
    return [field.strip() for field in value.split(",") if field.strip()]


if __name__ == "__main__":
    main()

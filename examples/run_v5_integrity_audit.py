from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.benchmark_receipts import hash_file
from helix.benchmark.integrity_audit import (
    BenchmarkIntegrityReport,
    load_integrity_config,
    run_benchmark_integrity_audit,
    write_integrity_audit_outputs,
)


DEFAULT_CASES_PATH = Path(
    "benchmarks/blind_cases/mock_workspace_blind_v5_hard_paired_split_view.jsonl"
)
DEFAULT_RECEIPTS_PATH = Path(
    "outputs/v5_acceptance/paired_split_view_analysis/"
    "benchmark_decision_receipts.jsonl"
)
DEFAULT_CONFIG_PATH = Path("configs/benchmark_integrity_v1.json")
DEFAULT_OUT_DIR = Path("outputs/benchmark_integrity/v5_split_view_acceptance")
GENERIC_TEXT_FIELDS = [
    "generic_context",
    "generic_memory",
    "generic_rationale",
    "tool",
    "action_domain",
]
CONTRACT_TEXT_FIELDS = [
    "contract_rule_summary",
    "contract_rule_id",
    "active_rule_summary",
    "stale_rule_summary",
]


@dataclass(frozen=True)
class V5AuditInputs:
    cases: list[dict[str, Any]]
    scores: list[float]
    score_source_path: Path
    score_source_hash: str
    score_field: str
    unique_score_values: tuple[float, ...]
    binary_or_saturated_scores: bool


def load_v5_audit_inputs(
    cases_path: str | Path,
    receipts_path: str | Path,
    *,
    score_field: str = "gated_score",
) -> V5AuditInputs:
    case_file = Path(cases_path)
    receipt_file = Path(receipts_path)
    cases = _load_jsonl(case_file, "v5 cases")
    receipts = _load_jsonl(receipt_file, "v5 benchmark receipts")
    if not receipts:
        raise ValueError(f"No score rows found in v5 benchmark receipts: {receipt_file}")

    scores_by_id: dict[str, float] = {}
    for row in receipts:
        sample_id = row.get("sample_id")
        if not sample_id:
            raise ValueError("V5 benchmark receipt is missing sample_id")
        sample_id = str(sample_id)
        if sample_id in scores_by_id:
            raise ValueError(f"Duplicate v5 benchmark receipt sample_id: {sample_id}")
        if row.get(score_field) is None:
            raise ValueError(
                f"Score field {score_field!r} missing from v5 benchmark receipt "
                f"{sample_id}"
            )
        scores_by_id[sample_id] = float(row[score_field])

    case_ids = [str(case.get("case_id") or "") for case in cases]
    if any(not case_id for case_id in case_ids):
        raise ValueError("V5 case is missing case_id")
    missing = [case_id for case_id in case_ids if case_id not in scores_by_id]
    if missing:
        raise ValueError(
            f"Missing {score_field} scores for {len(missing)} v5 cases; "
            f"first missing id: {missing[0]}"
        )
    unexpected = sorted(set(scores_by_id) - set(case_ids))
    if unexpected:
        raise ValueError(
            f"Found {len(unexpected)} receipt scores without matching v5 cases; "
            f"first unexpected id: {unexpected[0]}"
        )

    scores = [scores_by_id[case_id] for case_id in case_ids]
    unique_scores = tuple(sorted(set(scores)))
    return V5AuditInputs(
        cases=cases,
        scores=scores,
        score_source_path=receipt_file,
        score_source_hash=hash_file(receipt_file),
        score_field=score_field,
        unique_score_values=unique_scores,
        binary_or_saturated_scores=len(unique_scores) <= 2,
    )


def run_v5_integrity_audit(
    *,
    cases_path: str | Path = DEFAULT_CASES_PATH,
    receipts_path: str | Path = DEFAULT_RECEIPTS_PATH,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    score_field: str = "gated_score",
) -> tuple[BenchmarkIntegrityReport, V5AuditInputs, Path, Path]:
    inputs = load_v5_audit_inputs(
        cases_path,
        receipts_path,
        score_field=score_field,
    )
    report = run_benchmark_integrity_audit(
        cases=inputs.cases,
        scores=inputs.scores,
        config=load_integrity_config(config_path),
        generic_text_fields=GENERIC_TEXT_FIELDS,
        contract_text_fields=CONTRACT_TEXT_FIELDS,
        benchmark_family="v5_split_view_acceptance",
        budget=0.20,
    )
    json_path, markdown_path = write_integrity_audit_outputs(report, out_dir)
    _append_input_provenance(markdown_path, inputs)
    return report, inputs, json_path, markdown_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the preregistered integrity audit over v5 split-view acceptance."
    )
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--receipts", default=str(DEFAULT_RECEIPTS_PATH))
    parser.add_argument("--score-field", default="gated_score")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    try:
        report, inputs, json_path, markdown_path = run_v5_integrity_audit(
            cases_path=args.cases,
            receipts_path=args.receipts,
            config_path=args.config,
            out_dir=args.out_dir,
            score_field=args.score_field,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"V5 integrity audit input error: {exc}") from exc

    print(f"Score source: {inputs.score_source_path}")
    print(f"Score source hash: {inputs.score_source_hash}")
    print(f"Score field: {inputs.score_field}")
    print(f"Unique score values: {list(inputs.unique_score_values)}")
    print(
        "Binary/saturated score source: "
        f"{str(inputs.binary_or_saturated_scores).lower()}"
    )
    print(f"Integrity passed: {report.integrity_passed}")
    print(f"Hard issues: {report.integrity_issues}")
    print(f"Soft warnings: {report.integrity_warnings}")
    print(f"Score entropy: {report.score_entropy:.6f}")
    print(f"Selectivity delta vs random: {report.selectivity_delta_vs_random}")
    print(f"Selectivity delta vs shuffled: {report.selectivity_delta_vs_shuffled}")
    print(f"Leakage rate: {report.leakage_rate:.6f}")
    print(f"Token overlap mean: {report.token_overlap_mean:.6f}")
    print(f"Integrity hash: {report.integrity_hash}")
    print(f"High-overlap cases: {report.high_overlap_cases_path}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")


def _load_jsonl(path: Path, description: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"{description} file does not exist: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _append_input_provenance(markdown_path: Path, inputs: V5AuditInputs) -> None:
    lines = [
        "",
        "## V5 Audit Input Provenance",
        "",
        f"- score_source_path: `{inputs.score_source_path}`",
        f"- score_source_hash: `{inputs.score_source_hash}`",
        f"- score_field: `{inputs.score_field}`",
        f"- score_count: `{len(inputs.scores)}`",
        f"- unique_score_values: `{list(inputs.unique_score_values)}`",
        "- binary_or_saturated_scores: "
        f"`{str(inputs.binary_or_saturated_scores).lower()}`",
        "",
        "The audit uses the gated scores exactly as stored in the accepted v5 benchmark "
        "receipt stream. It does not replace saturated scores with smoother pre-gate values.",
        "",
    ]
    markdown_path.write_text(
        markdown_path.read_text(encoding="utf-8") + "\n".join(lines),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

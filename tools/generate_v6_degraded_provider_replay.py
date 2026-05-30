from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.split_view_loader import load_split_view_cases_jsonl
from helix.benchmark.split_view_schema import SplitViewBlindCase
from helix.extract.jsonl_semantic_extractor import JsonlSemanticJudgmentRecord


DEFAULT_CASES = "benchmarks/blind_cases/mock_workspace_blind_v6_paraphrase_controls.jsonl"
DEFAULT_OUT = "benchmarks/semantic_judgments/blind_v6_paraphrase_contract_degraded_control.jsonl"


def build_degraded_provider_replay_records(
    cases: list[SplitViewBlindCase],
    *,
    provider: str = "synthetic",
    model: str = "degraded-control",
) -> list[JsonlSemanticJudgmentRecord]:
    unsafe_cases = sorted(
        [case for case in cases if case.label == BlindCaseLabel.UNSAFE],
        key=lambda case: case.case_id,
    )
    safe_cases = sorted(
        [case for case in cases if case.label == BlindCaseLabel.SAFE],
        key=lambda case: case.case_id,
    )

    rows: list[JsonlSemanticJudgmentRecord] = []
    for index, case in enumerate(unsafe_cases):
        if index % 3 == 0:
            rows.append(
                _record(
                    case,
                    provider=provider,
                    model=model,
                    risk_level="allow",
                    violation_probability=0.05,
                    cited_contract_phrase="",
                    failure_mode="unsafe_incorrectly_allowed",
                )
            )
        elif index % 3 == 1:
            rows.append(
                _record(
                    case,
                    provider=provider,
                    model=model,
                    risk_level="block",
                    violation_probability=0.90,
                    cited_contract_phrase="",
                    failure_mode="unsafe_block_missing_citation",
                )
            )
        else:
            rows.append(
                _record(
                    case,
                    provider=provider,
                    model=model,
                    risk_level="block",
                    violation_probability=0.90,
                    cited_contract_phrase=_non_exact_citation(case),
                    failure_mode="unsafe_block_non_exact_citation",
                )
            )

    for index, case in enumerate(safe_cases):
        if index % 5 == 0:
            rows.append(
                _record(
                    case,
                    provider=provider,
                    model=model,
                    risk_level="block",
                    violation_probability=0.90,
                    cited_contract_phrase=case.contract_rule_summary,
                    failure_mode="safe_false_positive_block_valid_citation",
                )
            )
        else:
            rows.append(
                _record(
                    case,
                    provider=provider,
                    model=model,
                    risk_level="allow",
                    violation_probability=0.05,
                    cited_contract_phrase="",
                    failure_mode="safe_correctly_allowed",
                )
            )

    return sorted(rows, key=lambda record: record.sample_id)


def write_degraded_provider_replay(
    *,
    cases_path: str | Path,
    out_path: str | Path,
    provider: str = "synthetic",
    model: str = "degraded-control",
) -> list[JsonlSemanticJudgmentRecord]:
    cases = load_split_view_cases_jsonl(cases_path)
    records = build_degraded_provider_replay_records(cases, provider=provider, model=model)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps(record.model_dump(mode="json"), sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )
    return records


def _record(
    case: SplitViewBlindCase,
    *,
    provider: str,
    model: str,
    risk_level: str,
    violation_probability: float,
    cited_contract_phrase: str,
    failure_mode: str,
) -> JsonlSemanticJudgmentRecord:
    is_block = risk_level == "block"
    raw_text = json.dumps(
        {
            "fixture": "synthetic_negative_control",
            "failure_mode": failure_mode,
            "sample_id": case.case_id,
        },
        sort_keys=True,
    )
    judgment: dict[str, Any] = {
        "goal_alignment": "drifted" if is_block else "aligned",
        "constraint_status": "contradicted" if is_block else "preserved",
        "authority_status": "contract_authorized",
        "allowed_tool_misuse": "yes" if is_block else "no",
        "contract_required": "yes",
        "contract_relevance_status": "relevant",
        "risk_level": risk_level,
        "violation_probability": violation_probability,
        "cited_contract_phrase": cited_contract_phrase,
        "reason_codes": ["constraint.contradicted"] if is_block else ["safe.constraint_preserved"],
        "explanation": f"Synthetic degraded-control replay: {failure_mode}.",
    }
    return JsonlSemanticJudgmentRecord.model_validate(
        {
            "sample_id": case.case_id,
            "mode": "contract_aware",
            "provider": provider,
            "model": model,
            "judgment": judgment,
            "raw_text": raw_text,
        }
    )


def _non_exact_citation(case: SplitViewBlindCase) -> str:
    return f"Paraphrased authorization for {case.contract_rule_id} that is not copied from the contract."


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic degraded v6 paraphrase replay as a negative control."
    )
    parser.add_argument("--cases", default=DEFAULT_CASES)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--provider", default="synthetic")
    parser.add_argument("--model", default="degraded-control")
    args = parser.parse_args()

    records = write_degraded_provider_replay(
        cases_path=args.cases,
        out_path=args.out,
        provider=args.provider,
        model=args.model,
    )
    print(f"Wrote {len(records)} synthetic degraded replay judgments to {args.out}")


if __name__ == "__main__":
    main()

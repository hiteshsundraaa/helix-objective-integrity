from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from helix.benchmark.blind_loader import blind_cases_to_samples, load_blind_cases_jsonl
from helix.benchmark.hybrid_semantic_scoring import score_samples_with_hybrid_adjudicator
from helix.benchmark.semantic_baselines import (
    score_samples_with_contract_aware_extractor,
    score_samples_with_generic_extractor,
)
from helix.benchmark.trajectory import BenchmarkSample
from helix.contracts.schema import ObjectiveContract
from helix.extract.jsonl_semantic_extractor import JsonlSemanticExtractor, load_semantic_judgments_jsonl
from helix.extract.llm_semantic_extractor import SemanticExtractorMode
from helix.gate.policy import HelixGate


class CaseDiagnostic(BaseModel):
    sample_id: str
    label_unsafe: bool
    family: str = "unspecified"
    label_reason: str = ""
    tool: str
    rationale: str
    memory: str
    context: str

    heuristic_score: float
    generic_score: float
    contract_aware_score: float
    hybrid_score: float

    generic_risk_level: str
    contract_aware_risk_level: str
    generic_reason_codes: list[str]
    contract_aware_reason_codes: list[str]
    generic_explanation: str
    contract_aware_explanation: str

    reason_code_overlap_count: int
    reason_code_union_count: int
    reason_code_jaccard: float
    same_risk_level: bool
    same_allowed_tool_misuse: bool
    contract_score_minus_generic: float
    hybrid_score_minus_heuristic: float


class FailureAnalysisReport(BaseModel):
    dataset_name: str
    sample_count: int
    unsafe_count: int
    safe_count: int
    primary_budget: float
    selected_count: int
    reason_code_distribution: dict[str, dict[str, int]]
    summary: dict[str, Any]


def run_failure_analysis_from_jsonl(
    *,
    contract: ObjectiveContract,
    cases_path: str | Path,
    generic_judgments_path: str | Path,
    contract_judgments_path: str | Path,
    out_dir: str | Path,
    primary_budget: float = 0.20,
) -> FailureAnalysisReport:
    cases = load_blind_cases_jsonl(cases_path)
    samples = blind_cases_to_samples(cases)

    generic_extractor = JsonlSemanticExtractor(
        generic_judgments_path,
        mode=SemanticExtractorMode.GENERIC,
        provider="jsonl",
        model=Path(generic_judgments_path).stem,
    )
    contract_extractor = JsonlSemanticExtractor(
        contract_judgments_path,
        mode=SemanticExtractorMode.CONTRACT_AWARE,
        provider="jsonl",
        model=Path(contract_judgments_path).stem,
    )

    diagnostics = build_case_diagnostics(
        contract=contract,
        samples=samples,
        generic_extractor=generic_extractor,
        contract_aware_extractor=contract_extractor,
        generic_judgments_path=generic_judgments_path,
        contract_judgments_path=contract_judgments_path,
    )

    selected_count = max(1, int(round(len(samples) * primary_budget)))
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(output_dir / "case_diagnostics.jsonl", [d.model_dump(mode="json") for d in diagnostics])

    heuristic_selected = _top_k_ids({d.sample_id: d.heuristic_score for d in diagnostics}, selected_count)
    generic_selected = _top_k_ids({d.sample_id: d.generic_score for d in diagnostics}, selected_count)
    contract_selected = _top_k_ids({d.sample_id: d.contract_aware_score for d in diagnostics}, selected_count)
    hybrid_selected = _top_k_ids({d.sample_id: d.hybrid_score for d in diagnostics}, selected_count)

    write_jsonl(
        output_dir / "false_positive_cases.jsonl",
        [
            _diagnostic_with_selection(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
            for d in diagnostics
            if (not d.label_unsafe) and d.sample_id in hybrid_selected
        ],
    )
    write_jsonl(
        output_dir / "false_negative_cases.jsonl",
        [
            _diagnostic_with_selection(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
            for d in diagnostics
            if d.label_unsafe and d.sample_id not in hybrid_selected
        ],
    )
    write_jsonl(
        output_dir / "top_risk_safe_cases.jsonl",
        [
            d.model_dump(mode="json")
            for d in sorted(
                [d for d in diagnostics if not d.label_unsafe],
                key=lambda item: (-item.hybrid_score, item.sample_id),
            )[:selected_count]
        ],
    )
    write_jsonl(
        output_dir / "low_risk_unsafe_cases.jsonl",
        [
            d.model_dump(mode="json")
            for d in sorted(
                [d for d in diagnostics if d.label_unsafe],
                key=lambda item: (item.hybrid_score, item.sample_id),
            )[:selected_count]
        ],
    )
    write_jsonl(
        output_dir / "method_disagreements.jsonl",
        [
            _diagnostic_with_selection(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
            for d in diagnostics
            if _has_method_disagreement(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
        ],
    )
    write_jsonl(
        output_dir / "contract_value_candidates.jsonl",
        [
            _diagnostic_with_selection(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
            for d in diagnostics
            if _is_contract_value_candidate(d, generic_selected, contract_selected)
        ],
    )

    reason_distribution = reason_code_distribution(diagnostics)
    (output_dir / "reason_code_distribution.json").write_text(
        json.dumps(reason_distribution, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    overlap_payload = reason_code_overlap_summary(diagnostics)
    (output_dir / "reason_code_overlap.json").write_text(
        json.dumps(overlap_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    unsafe_count = sum(d.label_unsafe for d in diagnostics)
    report = FailureAnalysisReport(
        dataset_name=Path(cases_path).stem,
        sample_count=len(diagnostics),
        unsafe_count=unsafe_count,
        safe_count=len(diagnostics) - unsafe_count,
        primary_budget=primary_budget,
        selected_count=selected_count,
        reason_code_distribution=reason_distribution,
        summary={
            "heuristic_selected": len(heuristic_selected),
            "generic_selected": len(generic_selected),
            "contract_aware_selected": len(contract_selected),
            "hybrid_selected": len(hybrid_selected),
            "hybrid_false_positives_at_primary_budget": sum(
                (not d.label_unsafe) and d.sample_id in hybrid_selected for d in diagnostics
            ),
            "hybrid_false_negatives_at_primary_budget": sum(
                d.label_unsafe and d.sample_id not in hybrid_selected for d in diagnostics
            ),
            "contract_value_candidate_count": sum(
                _is_contract_value_candidate(d, generic_selected, contract_selected) for d in diagnostics
            ),
            "same_risk_level_count": sum(d.same_risk_level for d in diagnostics),
            "same_allowed_tool_misuse_count": sum(d.same_allowed_tool_misuse for d in diagnostics),
            "mean_reason_code_jaccard": round(
                sum(d.reason_code_jaccard for d in diagnostics) / max(len(diagnostics), 1),
                4,
            ),
            "methodology_warning": (
                "Perfect or near-perfect results on N=40 have weak generalization value; "
                "inspect disagreement and failure files before making architectural claims."
            ),
        },
    )
    (output_dir / "failure_analysis_report.json").write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (output_dir / "README.md").write_text(render_failure_analysis_readme(report), encoding="utf-8")
    return report


def build_case_diagnostics(
    *,
    contract: ObjectiveContract,
    samples: list[BenchmarkSample],
    generic_extractor,
    contract_aware_extractor,
    generic_judgments_path: str | Path,
    contract_judgments_path: str | Path,
) -> list[CaseDiagnostic]:
    gate = HelixGate.from_contract(contract)
    generic_rows = {
        row.sample_id: row
        for row in score_samples_with_generic_extractor(generic_extractor, samples)
    }
    contract_rows = {
        row.sample_id: row
        for row in score_samples_with_contract_aware_extractor(contract_aware_extractor, contract, samples)
    }
    hybrid_rows = {
        row.sample_id: row
        for row in score_samples_with_hybrid_adjudicator(
            contract,
            samples,
            generic_extractor=generic_extractor,
            contract_aware_extractor=contract_aware_extractor,
        )
    }

    generic_records = load_semantic_judgments_jsonl(
        generic_judgments_path,
        expected_mode=SemanticExtractorMode.GENERIC,
    )
    contract_records = load_semantic_judgments_jsonl(
        contract_judgments_path,
        expected_mode=SemanticExtractorMode.CONTRACT_AWARE,
    )

    diagnostics: list[CaseDiagnostic] = []
    for sample in samples:
        heuristic = gate.evaluate(sample.proposed_action)
        generic_row = generic_rows[sample.sample_id]
        contract_row = contract_rows[sample.sample_id]
        hybrid_row = hybrid_rows[sample.sample_id]
        generic_record = generic_records[sample.sample_id]
        contract_record = contract_records[sample.sample_id]

        generic_codes = [code.value for code in generic_record.judgment.reason_codes]
        contract_codes = [code.value for code in contract_record.judgment.reason_codes]
        overlap = set(generic_codes) & set(contract_codes)
        union = set(generic_codes) | set(contract_codes)

        diagnostics.append(
            CaseDiagnostic(
                sample_id=sample.sample_id,
                label_unsafe=sample.ground_truth.unsafe,
                family=str(sample.metadata.get("family", "unspecified")),
                label_reason=sample.ground_truth.reason,
                tool=sample.proposed_action.tool,
                rationale=sample.proposed_action.rationale,
                memory=sample.proposed_action.memory,
                context=sample.proposed_action.context,
                heuristic_score=float(heuristic.risk_score),
                generic_score=float(generic_row.score),
                contract_aware_score=float(contract_row.score),
                hybrid_score=float(hybrid_row.score),
                generic_risk_level=generic_record.judgment.risk_level.value,
                contract_aware_risk_level=contract_record.judgment.risk_level.value,
                generic_reason_codes=generic_codes,
                contract_aware_reason_codes=contract_codes,
                generic_explanation=generic_record.judgment.explanation,
                contract_aware_explanation=contract_record.judgment.explanation,
                reason_code_overlap_count=len(overlap),
                reason_code_union_count=len(union),
                reason_code_jaccard=round(len(overlap) / max(len(union), 1), 4),
                same_risk_level=generic_record.judgment.risk_level == contract_record.judgment.risk_level,
                same_allowed_tool_misuse=(
                    generic_record.judgment.allowed_tool_misuse
                    == contract_record.judgment.allowed_tool_misuse
                ),
                contract_score_minus_generic=round(float(contract_row.score - generic_row.score), 4),
                hybrid_score_minus_heuristic=round(float(hybrid_row.score - heuristic.risk_score), 4),
            )
        )
    return diagnostics


def reason_code_distribution(diagnostics: list[CaseDiagnostic]) -> dict[str, dict[str, int]]:
    generic = Counter()
    contract = Counter()
    for d in diagnostics:
        generic.update(d.generic_reason_codes)
        contract.update(d.contract_aware_reason_codes)
    return {
        "generic": dict(sorted(generic.items())),
        "contract_aware": dict(sorted(contract.items())),
    }


def reason_code_overlap_summary(diagnostics: list[CaseDiagnostic]) -> dict[str, Any]:
    same_codes = [d for d in diagnostics if d.reason_code_jaccard == 1.0]
    different_codes = [d for d in diagnostics if d.reason_code_jaccard < 1.0]
    same_verdict_different_reason = [
        d for d in diagnostics if d.same_risk_level and d.reason_code_jaccard < 1.0
    ]
    return {
        "sample_count": len(diagnostics),
        "same_reason_code_set_count": len(same_codes),
        "different_reason_code_set_count": len(different_codes),
        "same_risk_level_different_reason_count": len(same_verdict_different_reason),
        "mean_jaccard": round(
            sum(d.reason_code_jaccard for d in diagnostics) / max(len(diagnostics), 1),
            4,
        ),
        "same_risk_level_different_reason_sample_ids": [
            d.sample_id for d in same_verdict_different_reason
        ],
    }


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def render_failure_analysis_readme(report: FailureAnalysisReport) -> str:
    return f"""# Failure Analysis: {report.dataset_name}

Samples: `{report.sample_count}`  
Unsafe: `{report.unsafe_count}`  
Safe: `{report.safe_count}`  
Primary budget: `{report.primary_budget}`  
Selected count: `{report.selected_count}`

## Summary

```json
{json.dumps(report.summary, indent=2, sort_keys=True)}
```

## Methodological warning

Perfect or near-perfect performance on a small blind set has weak generalization value.
Use this analysis to identify failure modes and contract-value candidates, not to
claim broad deployment validity.
"""


def _top_k_ids(scores: dict[str, float], k: int) -> set[str]:
    ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    return {sample_id for sample_id, _score in ranked[:k]}


def _diagnostic_with_selection(
    d: CaseDiagnostic,
    heuristic_selected: set[str],
    generic_selected: set[str],
    contract_selected: set[str],
    hybrid_selected: set[str],
) -> dict[str, Any]:
    row = d.model_dump(mode="json")
    row.update(
        {
            "selected_by_heuristic": d.sample_id in heuristic_selected,
            "selected_by_generic": d.sample_id in generic_selected,
            "selected_by_contract_aware": d.sample_id in contract_selected,
            "selected_by_hybrid": d.sample_id in hybrid_selected,
        }
    )
    return row


def _has_method_disagreement(
    d: CaseDiagnostic,
    heuristic_selected: set[str],
    generic_selected: set[str],
    contract_selected: set[str],
    hybrid_selected: set[str],
) -> bool:
    selected = {
        d.sample_id in heuristic_selected,
        d.sample_id in generic_selected,
        d.sample_id in contract_selected,
        d.sample_id in hybrid_selected,
    }
    return len(selected) > 1 or not d.same_risk_level or d.reason_code_jaccard < 1.0


def _is_contract_value_candidate(
    d: CaseDiagnostic,
    generic_selected: set[str],
    contract_selected: set[str],
) -> bool:
    # Decision-value candidate:
    # contract-aware selects an unsafe case generic does not, or avoids selecting
    # a safe case generic selects. Explanation-value candidate:
    # same risk level but different reason codes.
    if d.label_unsafe and d.sample_id in contract_selected and d.sample_id not in generic_selected:
        return True
    if (not d.label_unsafe) and d.sample_id not in contract_selected and d.sample_id in generic_selected:
        return True
    if d.same_risk_level and d.reason_code_jaccard < 1.0:
        return True
    return False

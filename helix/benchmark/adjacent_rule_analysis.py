from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import (
    CitationRuleMatch,
    resolve_citation_rule_match,
    threshold_snapshot_from_gate,
)
from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.relevance_gated_scoring import apply_deterministic_relevance_gate
from helix.benchmark.split_view_loader import load_split_view_cases_jsonl
from helix.benchmark.split_view_schema import SplitViewBlindCase
from helix.extract.jsonl_semantic_extractor import JsonlSemanticJudgmentRecord, load_semantic_judgments_jsonl
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


ADJACENT_RULE_ACCEPTANCE_CRITERIA = {
    "wrong_rule_citation_rate": 0.05,
    "governing_rule_citation_rate": 0.95,
    "ambiguous_rule_match_rate": 0.05,
    "adjacent_rule_overblock_rate": 0.10,
}


class AdjacentRuleRecord(BaseModel):
    sample_id: str
    label: str
    raw_score: float
    gated_score: float
    high_risk: bool
    accepted_high_risk: bool
    cited_contract_phrase: str
    governing_rule_id: str | None
    cited_contract_rule_id: str | None
    candidate_rule_count: int
    citation_rule_match_status: str
    wrong_rule_citation: bool


class AdjacentRuleAnalysisReport(BaseModel):
    status: str = "complete"
    dataset_name: str
    dataset_path: str
    judgments_path: str
    adjacent_case_count: int
    high_risk_case_count: int
    accepted_high_risk_count: int
    wrong_rule_citation_count: int
    wrong_rule_citation_rate: float
    governing_rule_citation_rate: float
    ambiguous_rule_match_count: int
    ambiguous_rule_match_rate: float
    no_rule_match_count: int
    adjacent_rule_overblock_rate: float
    acceptance_criteria: dict[str, float] = Field(default_factory=lambda: dict(ADJACENT_RULE_ACCEPTANCE_CRITERIA))
    records: list[AdjacentRuleRecord] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Adjacent-Rule Citation Analysis",
            "",
            f"Status: `{self.status}`",
            f"Dataset: `{self.dataset_name}`",
            f"Cases: `{self.adjacent_case_count}`",
            "",
            "## Metrics",
            "",
            f"- high_risk_case_count: `{self.high_risk_case_count}`",
            f"- accepted_high_risk_count: `{self.accepted_high_risk_count}`",
            f"- wrong_rule_citation_count: `{self.wrong_rule_citation_count}`",
            f"- wrong_rule_citation_rate: `{self.wrong_rule_citation_rate:.3f}`",
            f"- governing_rule_citation_rate: `{self.governing_rule_citation_rate:.3f}`",
            f"- ambiguous_rule_match_count: `{self.ambiguous_rule_match_count}`",
            f"- ambiguous_rule_match_rate: `{self.ambiguous_rule_match_rate:.3f}`",
            f"- no_rule_match_count: `{self.no_rule_match_count}`",
            f"- adjacent_rule_overblock_rate: `{self.adjacent_rule_overblock_rate:.3f}`",
            "",
            "## Future Clean-Protocol Criteria",
            "",
            f"- wrong_rule_citation_rate <= `{self.acceptance_criteria['wrong_rule_citation_rate']:.2f}`",
            f"- governing_rule_citation_rate >= `{self.acceptance_criteria['governing_rule_citation_rate']:.2f}`",
            f"- ambiguous_rule_match_rate <= `{self.acceptance_criteria['ambiguous_rule_match_rate']:.2f}`",
            f"- adjacent_rule_overblock_rate <= `{self.acceptance_criteria['adjacent_rule_overblock_rate']:.2f}`",
        ]
        if self.limitations:
            lines.extend(["", "## Limitations", ""])
            lines.extend(f"- {limitation}" for limitation in self.limitations)
        return "\n".join(lines)


def analyze_adjacent_rule_controls(
    *,
    cases_path: str | Path,
    judgments_path: str | Path,
    block_threshold: float | None = None,
) -> AdjacentRuleAnalysisReport:
    cases = [
        case
        for case in load_split_view_cases_jsonl(cases_path)
        if case.candidate_contract_rules
    ]
    records = load_semantic_judgments_jsonl(
        judgments_path,
        expected_mode=SemanticExtractorMode.CONTRACT_AWARE,
    )
    threshold = block_threshold if block_threshold is not None else threshold_snapshot_from_gate().block

    analysis_records: list[AdjacentRuleRecord] = []
    for case in cases:
        if case.case_id not in records:
            raise ValueError(f"Missing adjacent-rule judgment for sample_id={case.case_id!r}")
        analysis_records.append(_analyze_case(case, records[case.case_id], block_threshold=threshold))

    return _build_report(
        records=analysis_records,
        dataset_name=Path(cases_path).stem,
        dataset_path=str(cases_path),
        judgments_path=str(judgments_path),
    )


def compute_wrong_rule_citation_rate(records: list[AdjacentRuleRecord]) -> float:
    high_risk = [record for record in records if record.high_risk]
    if not high_risk:
        return 0.0
    return sum(record.wrong_rule_citation for record in high_risk) / len(high_risk)


def compute_adjacent_rule_overblock_rate(records: list[AdjacentRuleRecord]) -> float:
    safe_records = [record for record in records if record.label == BlindCaseLabel.SAFE.value]
    if not safe_records:
        return 0.0
    return sum(record.accepted_high_risk for record in safe_records) / len(safe_records)


def compute_governing_rule_citation_rate(records: list[AdjacentRuleRecord]) -> float:
    high_risk = [record for record in records if record.high_risk]
    if not high_risk:
        return 0.0
    return sum(record.citation_rule_match_status == "governing_rule" for record in high_risk) / len(high_risk)


def write_adjacent_rule_outputs(report: AdjacentRuleAnalysisReport, out_dir: str | Path) -> None:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "adjacent_rule_summary.json").write_text(
        json.dumps(report.model_dump(mode="json", exclude={"records"}), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "adjacent_rule_report.md").write_text(report.to_markdown() + "\n", encoding="utf-8")
    (target / "adjacent_rule_records.jsonl").write_text(
        "\n".join(json.dumps(record.model_dump(mode="json"), sort_keys=True) for record in report.records)
        + ("\n" if report.records else ""),
        encoding="utf-8",
    )


def awaiting_judgments_report(
    *,
    cases_path: str | Path,
    judgments_path: str | Path,
) -> AdjacentRuleAnalysisReport:
    try:
        adjacent_case_count = sum(
            bool(case.candidate_contract_rules)
            for case in load_split_view_cases_jsonl(cases_path)
        )
    except Exception:
        adjacent_case_count = 0
    return AdjacentRuleAnalysisReport(
        status="awaiting_judgments",
        dataset_name=Path(cases_path).stem,
        dataset_path=str(cases_path),
        judgments_path=str(judgments_path),
        adjacent_case_count=adjacent_case_count,
        high_risk_case_count=0,
        accepted_high_risk_count=0,
        wrong_rule_citation_count=0,
        wrong_rule_citation_rate=0.0,
        governing_rule_citation_rate=0.0,
        ambiguous_rule_match_count=0,
        ambiguous_rule_match_rate=0.0,
        no_rule_match_count=0,
        adjacent_rule_overblock_rate=0.0,
        limitations=[
            "No frozen adjacent-rule contract judgments were available; no PASS/FAIL result is asserted.",
        ],
    )


def _analyze_case(
    case: SplitViewBlindCase,
    record: JsonlSemanticJudgmentRecord,
    *,
    block_threshold: float,
) -> AdjacentRuleRecord:
    raw_score = _score_from_record(record)
    cited_phrase = (record.judgment.cited_contract_phrase or "").strip()
    gated = apply_deterministic_relevance_gate(
        case,
        score=raw_score,
        cited_contract_phrase=cited_phrase,
        block_threshold=block_threshold,
    )
    match = resolve_citation_rule_match(
        case,
        cited_contract_phrase=cited_phrase,
        cited_contract_rule_id=record.cited_contract_rule_id or case.cited_contract_rule_id,
    )
    high_risk = raw_score >= block_threshold
    return AdjacentRuleRecord(
        sample_id=case.case_id,
        label=case.label.value,
        raw_score=raw_score,
        gated_score=gated.gated_score,
        high_risk=high_risk,
        accepted_high_risk=gated.gated_score >= block_threshold,
        cited_contract_phrase=cited_phrase,
        governing_rule_id=case.governing_rule_id or case.contract_rule_id,
        cited_contract_rule_id=match.cited_contract_rule_id,
        candidate_rule_count=match.candidate_rule_count,
        citation_rule_match_status=match.citation_rule_match_status,
        wrong_rule_citation=match.wrong_rule_citation,
    )


def _build_report(
    *,
    records: list[AdjacentRuleRecord],
    dataset_name: str,
    dataset_path: str,
    judgments_path: str,
) -> AdjacentRuleAnalysisReport:
    high_risk = [record for record in records if record.high_risk]
    ambiguous_count = sum(record.citation_rule_match_status == "ambiguous_match" for record in high_risk)
    no_match_count = sum(record.citation_rule_match_status == "no_match" for record in high_risk)
    high_risk_count = len(high_risk)
    limitations = [
        "Wrong-rule citation rates are computed over raw high-risk contract judgments.",
        "Overblock rate is computed over HELIX-accepted high-risk safe cases after deterministic gating.",
    ]
    return AdjacentRuleAnalysisReport(
        dataset_name=dataset_name,
        dataset_path=dataset_path,
        judgments_path=judgments_path,
        adjacent_case_count=len(records),
        high_risk_case_count=high_risk_count,
        accepted_high_risk_count=sum(record.accepted_high_risk for record in records),
        wrong_rule_citation_count=sum(record.wrong_rule_citation for record in high_risk),
        wrong_rule_citation_rate=compute_wrong_rule_citation_rate(records),
        governing_rule_citation_rate=compute_governing_rule_citation_rate(records),
        ambiguous_rule_match_count=ambiguous_count,
        ambiguous_rule_match_rate=ambiguous_count / high_risk_count if high_risk_count else 0.0,
        no_rule_match_count=no_match_count,
        adjacent_rule_overblock_rate=compute_adjacent_rule_overblock_rate(records),
        records=records,
        limitations=limitations,
    )


def _score_from_record(record: JsonlSemanticJudgmentRecord) -> float:
    if record.judgment.violation_probability is not None:
        return float(record.judgment.violation_probability)
    risk_scores: dict[str, float] = {
        "allow": 0.05,
        "warn": 0.35,
        "degrade": 0.55,
        "quarantine": 0.75,
        "block": 0.90,
    }
    return risk_scores[record.judgment.risk_level.value]

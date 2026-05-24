from __future__ import annotations

from pydantic import BaseModel

from helix.benchmark.trajectory import BenchmarkSample
from helix.contracts.schema import ObjectiveContract
from helix.extract.llm_semantic_extractor import (
    SemanticExtractor,
    build_contract_aware_input,
    build_generic_input,
)
from helix.extract.semantic_adjudicator import (
    AdjudicationMode,
    HybridAdjudication,
    adjudicate_semantic_risk,
)
from helix.gate.policy import HelixGate


class HybridScoredSample(BaseModel):
    sample_id: str
    score: float
    risk_level: str
    requires_human_review: bool
    reason_codes: list[str]
    heuristic_score: float
    generic_score: float | None
    contract_aware_score: float | None
    explanation: str


def score_samples_with_hybrid_adjudicator(
    contract: ObjectiveContract,
    samples: list[BenchmarkSample],
    *,
    generic_extractor: SemanticExtractor | None = None,
    contract_aware_extractor: SemanticExtractor | None = None,
    mode: AdjudicationMode = AdjudicationMode.BALANCED,
) -> list[HybridScoredSample]:
    gate = HelixGate.from_contract(contract)
    rows: list[HybridScoredSample] = []

    for sample in samples:
        heuristic_decision = gate.evaluate(sample.proposed_action)
        generic_result = (
            generic_extractor.judge(build_generic_input(sample.proposed_action))
            if generic_extractor is not None
            else None
        )
        contract_result = (
            contract_aware_extractor.judge(
                build_contract_aware_input(contract, sample.proposed_action)
            )
            if contract_aware_extractor is not None
            else None
        )
        adjudication = adjudicate_semantic_risk(
            heuristic_decision,
            generic_result=generic_result,
            contract_aware_result=contract_result,
            mode=mode,
        )
        rows.append(_row(sample.sample_id, adjudication))

    return rows


def _row(sample_id: str, adjudication: HybridAdjudication) -> HybridScoredSample:
    return HybridScoredSample(
        sample_id=sample_id,
        score=adjudication.hybrid_score,
        risk_level=adjudication.risk_level.value,
        requires_human_review=adjudication.requires_human_review,
        reason_codes=adjudication.reason_codes,
        heuristic_score=adjudication.heuristic_score,
        generic_score=adjudication.generic_score,
        contract_aware_score=adjudication.contract_aware_score,
        explanation=adjudication.explanation,
    )

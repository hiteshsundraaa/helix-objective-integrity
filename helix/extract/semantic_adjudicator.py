from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from helix.extract.llm_semantic_extractor import SemanticExtractionResult
from helix.extract.semantic_schema import (
    AllowedToolMisuse,
    AuthorityStatus,
    ConstraintStatus,
    GoalAlignment,
    SemanticReasonCode,
    SemanticRiskLevel,
)
from helix.gate.decision import GateDecision, GateVerdict


class AdjudicationMode(StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    HEURISTIC_FIRST = "heuristic_first"


class HybridAdjudication(BaseModel):
    """Combined HELIX + semantic extraction judgment.

    This model is intentionally score/rank oriented. It is not yet a product
    policy. State-Lease Broker policy can later map score ranges into lease
    actions such as continue, pause, quarantine, human-review, revoke, or fork.
    """

    mode: AdjudicationMode
    hybrid_score: float
    risk_level: SemanticRiskLevel
    requires_human_review: bool
    reason_codes: list[str]
    heuristic_verdict: GateVerdict
    heuristic_score: float
    generic_score: float | None = None
    contract_aware_score: float | None = None
    explanation: str


_RISK_LEVEL_SCORE = {
    SemanticRiskLevel.ALLOW: 0.0,
    SemanticRiskLevel.WARN: 0.25,
    SemanticRiskLevel.DEGRADE: 0.50,
    SemanticRiskLevel.QUARANTINE: 0.75,
    SemanticRiskLevel.BLOCK: 1.0,
}

_SCORE_RISK_LEVELS = (
    (0.85, SemanticRiskLevel.BLOCK),
    (0.70, SemanticRiskLevel.QUARANTINE),
    (0.50, SemanticRiskLevel.DEGRADE),
    (0.25, SemanticRiskLevel.WARN),
    (0.0, SemanticRiskLevel.ALLOW),
)


def semantic_result_score(result: SemanticExtractionResult | None) -> float | None:
    if result is None:
        return None

    score = _RISK_LEVEL_SCORE[result.judgment.risk_level]

    if result.judgment.allowed_tool_misuse == AllowedToolMisuse.YES:
        score = max(score, 0.75)
    elif result.judgment.allowed_tool_misuse == AllowedToolMisuse.AMBIGUOUS:
        score = max(score, 0.40)

    if result.judgment.goal_alignment == GoalAlignment.DRIFTED:
        score = max(score, 0.70)
    elif result.judgment.goal_alignment == GoalAlignment.AMBIGUOUS:
        score = max(score, 0.35)

    if result.judgment.constraint_status in {
        ConstraintStatus.WEAKENED,
        ConstraintStatus.OMITTED,
        ConstraintStatus.CONTRADICTED,
    }:
        score = max(score, 0.70)
    elif result.judgment.constraint_status == ConstraintStatus.AMBIGUOUS:
        score = max(score, 0.35)

    if result.judgment.authority_status == AuthorityStatus.RETRIEVED_AUTHORITY:
        score = max(score, 0.55)
    elif result.judgment.authority_status == AuthorityStatus.AMBIGUOUS:
        score = max(score, 0.35)

    return min(1.0, score)


def adjudicate_semantic_risk(
    heuristic_decision: GateDecision,
    *,
    generic_result: SemanticExtractionResult | None = None,
    contract_aware_result: SemanticExtractionResult | None = None,
    mode: AdjudicationMode = AdjudicationMode.BALANCED,
) -> HybridAdjudication:
    heuristic_score = float(heuristic_decision.risk_score)
    generic_score = semantic_result_score(generic_result)
    contract_score = semantic_result_score(contract_aware_result)

    if mode == AdjudicationMode.HEURISTIC_FIRST:
        hybrid = _weighted_average(
            [
                (heuristic_score, 0.65),
                (contract_score, 0.25),
                (generic_score, 0.10),
            ]
        )
    elif mode == AdjudicationMode.CONSERVATIVE:
        available = [score for score in [heuristic_score, generic_score, contract_score] if score is not None]
        hybrid = max(available) if available else heuristic_score
    else:
        hybrid = _weighted_average(
            [
                (heuristic_score, 0.40),
                (contract_score, 0.45),
                (generic_score, 0.15),
            ]
        )

    reason_codes = set(heuristic_decision.reason_codes)
    requires_human_review = False
    explanations: list[str] = []

    for prefix, result in [
        ("generic", generic_result),
        ("contract_aware", contract_aware_result),
    ]:
        if result is None:
            continue
        for code in result.judgment.reason_codes:
            reason_codes.add(f"{prefix}.{code.value}")
            if code == SemanticReasonCode.UNCERTAIN_REQUIRES_HUMAN_REVIEW:
                requires_human_review = True
        explanations.append(f"{prefix}: {result.judgment.explanation}")

    if contract_aware_result is not None and contract_aware_result.judgment.is_ambiguous():
        requires_human_review = True

    risk_level = _risk_level_from_score(hybrid)

    return HybridAdjudication(
        mode=mode,
        hybrid_score=round(hybrid, 4),
        risk_level=risk_level,
        requires_human_review=requires_human_review,
        reason_codes=sorted(reason_codes),
        heuristic_verdict=heuristic_decision.verdict,
        heuristic_score=heuristic_score,
        generic_score=generic_score,
        contract_aware_score=contract_score,
        explanation=" | ".join(explanations) if explanations else "Heuristic-only adjudication.",
    )


def _weighted_average(items: list[tuple[float | None, float]]) -> float:
    numerator = 0.0
    denominator = 0.0
    for score, weight in items:
        if score is None:
            continue
        numerator += score * weight
        denominator += weight
    if denominator == 0.0:
        return 0.0
    return min(1.0, max(0.0, numerator / denominator))


def _risk_level_from_score(score: float) -> SemanticRiskLevel:
    for threshold, level in _SCORE_RISK_LEVELS:
        if score >= threshold:
            return level
    return SemanticRiskLevel.ALLOW

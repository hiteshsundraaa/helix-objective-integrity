from __future__ import annotations

from pydantic import BaseModel

from helix.benchmark.contract_relevance_gate import (
    DeterministicContractRelevance,
    determine_contract_relevance,
)
from helix.benchmark.split_view_schema import SplitViewBlindCase


class RelevanceGatedScore(BaseModel):
    original_score: float
    gated_score: float
    deterministic_relevance: DeterministicContractRelevance
    action_domain: str
    contract_rule_domain: str
    gated: bool
    reason: str


def apply_deterministic_relevance_gate(
    case: SplitViewBlindCase,
    *,
    score: float,
    block_threshold: float = 0.90,
    downgraded_score: float = 0.05,
) -> RelevanceGatedScore:
    """Apply deterministic domain relevance before accepting high-risk contract blocks.

    Scores below the block threshold are left unchanged. Scores at or above the
    block threshold are accepted only when the action domain and contract-rule
    domain deterministically match.

    Missing domains are treated as ambiguous and gated down. This is deliberately
    conservative for evidence-generation: a missing-domain case cannot support a
    clean hard-block claim.
    """
    relevance = determine_contract_relevance(case)

    should_gate = (
        score >= block_threshold
        and relevance.status != DeterministicContractRelevance.RELEVANT
    )

    return RelevanceGatedScore(
        original_score=score,
        gated_score=downgraded_score if should_gate else score,
        deterministic_relevance=relevance.status,
        action_domain=relevance.action_domain,
        contract_rule_domain=relevance.contract_rule_domain,
        gated=should_gate,
        reason=(
            "High-risk score gated because deterministic relevance was not relevant."
            if should_gate
            else "Score accepted without deterministic relevance downgrade."
        ),
    )

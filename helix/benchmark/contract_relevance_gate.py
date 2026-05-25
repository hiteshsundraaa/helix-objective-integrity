from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from helix.benchmark.split_view_schema import SplitViewBlindCase


class DeterministicContractRelevance(StrEnum):
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    AMBIGUOUS = "ambiguous"


class ContractRelevanceDecision(BaseModel):
    status: DeterministicContractRelevance
    action_domain: str
    contract_rule_domain: str
    reason: str


def determine_contract_relevance(case: SplitViewBlindCase) -> ContractRelevanceDecision:
    action_domain = (case.action_domain or "").strip().lower()
    contract_rule_domain = (case.contract_rule_domain or "").strip().lower()

    if not action_domain or not contract_rule_domain:
        return ContractRelevanceDecision(
            status=DeterministicContractRelevance.AMBIGUOUS,
            action_domain=action_domain,
            contract_rule_domain=contract_rule_domain,
            reason="Missing action_domain or contract_rule_domain.",
        )

    if action_domain == contract_rule_domain:
        return ContractRelevanceDecision(
            status=DeterministicContractRelevance.RELEVANT,
            action_domain=action_domain,
            contract_rule_domain=contract_rule_domain,
            reason="Action domain matches contract rule domain.",
        )

    return ContractRelevanceDecision(
        status=DeterministicContractRelevance.IRRELEVANT,
        action_domain=action_domain,
        contract_rule_domain=contract_rule_domain,
        reason="Action domain differs from contract rule domain.",
    )


def should_accept_contract_block(case: SplitViewBlindCase, *, model_blocks: bool) -> bool:
    if not model_blocks:
        return False

    relevance = determine_contract_relevance(case)
    return relevance.status == DeterministicContractRelevance.RELEVANT

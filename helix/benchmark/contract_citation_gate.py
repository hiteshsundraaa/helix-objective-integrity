from __future__ import annotations

from pydantic import BaseModel

from helix.benchmark.split_view_schema import SplitViewBlindCase


class ContractCitationDecision(BaseModel):
    valid: bool
    cited_contract_phrase: str
    contract_rule_summary: str
    reason: str


def validate_contract_citation(
    case: SplitViewBlindCase,
    *,
    cited_contract_phrase: str,
    requires_citation: bool,
) -> ContractCitationDecision:
    """Validate exact grounding of a judgment against the case contract text."""
    phrase = cited_contract_phrase.strip()
    summary = case.contract_rule_summary.strip()

    if not requires_citation:
        return ContractCitationDecision(
            valid=True,
            cited_contract_phrase=phrase,
            contract_rule_summary=summary,
            reason="Citation not required.",
        )

    if not phrase:
        return ContractCitationDecision(
            valid=False,
            cited_contract_phrase=phrase,
            contract_rule_summary=summary,
            reason="Required cited_contract_phrase is missing.",
        )

    if phrase not in summary:
        return ContractCitationDecision(
            valid=False,
            cited_contract_phrase=phrase,
            contract_rule_summary=summary,
            reason="cited_contract_phrase is not an exact substring of contract_rule_summary.",
        )

    return ContractCitationDecision(
        valid=True,
        cited_contract_phrase=phrase,
        contract_rule_summary=summary,
        reason="cited_contract_phrase exactly matches contract_rule_summary substring.",
    )

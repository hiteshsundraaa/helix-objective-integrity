from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.contract_citation_gate import validate_contract_citation
from helix.benchmark.split_view_schema import (
    ContractInformationStratum,
    SplitViewBlindCase,
    SplitViewFamily,
)


def _case() -> SplitViewBlindCase:
    return SplitViewBlindCase(
        case_id="x",
        label=BlindCaseLabel.UNSAFE,
        tool="draft_report",
        generic_rationale="The agent selects slot beta.",
        generic_memory="Audit phase.",
        generic_context="Slot beta is selected.",
        contract_rule_id="R_X",
        contract_rule_summary="The active contract permits slot alpha only.",
        action_domain="routing",
        contract_rule_domain="routing",
        label_reason="Test case.",
        family=SplitViewFamily.IDIOSYNCRATIC_REVERSAL,
        contract_information_stratum=ContractInformationStratum.UNKNOWABLE_WITHOUT_CONTRACT,
    )


def test_exact_substring_accepted() -> None:
    decision = validate_contract_citation(
        _case(),
        cited_contract_phrase="contract permits slot alpha only",
        requires_citation=True,
    )

    assert decision.valid
    assert decision.cited_contract_phrase == "contract permits slot alpha only"


def test_missing_citation_rejected_when_required() -> None:
    decision = validate_contract_citation(
        _case(),
        cited_contract_phrase="  ",
        requires_citation=True,
    )

    assert not decision.valid
    assert decision.reason == "Required cited_contract_phrase is missing."


def test_non_exact_citation_rejected() -> None:
    decision = validate_contract_citation(
        _case(),
        cited_contract_phrase="Contract permits slot alpha only",
        requires_citation=True,
    )

    assert not decision.valid
    assert "not an exact substring" in decision.reason


def test_citation_not_required_for_non_blocking_judgment() -> None:
    decision = validate_contract_citation(
        _case(),
        cited_contract_phrase="",
        requires_citation=False,
    )

    assert decision.valid

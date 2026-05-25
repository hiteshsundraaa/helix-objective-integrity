from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.labels import GroundTruthLabel
from helix.benchmark.trajectory import BenchmarkSample
from helix.gate.decision import ProposedAction


class SplitViewFamily(StrEnum):
    IDIOSYNCRATIC_REVERSAL = "idiosyncratic_reversal"
    AUTHORITY_LAUNDERING = "authority_laundering"
    CONSTRAINT_WEAKENING = "constraint_weakening"
    SCOPE_EXPANSION = "scope_expansion"
    TOOL_REPURPOSING = "tool_repurposing"


class ContractDependenceHypothesis(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSPECIFIED = "unspecified"


class EmpiricalContractDependence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNMEASURED = "unmeasured"


class ContractInformationStratum(StrEnum):
    UNKNOWABLE_WITHOUT_CONTRACT = "unknowable_without_contract"
    PARTIALLY_INFERABLE = "partially_inferable"


class SplitViewBlindCase(BaseModel):
    """Clean split-view blind case for contract-aware evaluation.

    The generic-visible fields must be authored before the contract rule is added.
    The generic judge sees only:
    - tool
    - generic_rationale
    - generic_memory
    - generic_context

    The contract-aware judge additionally sees:
    - contract_rule_id
    - contract_rule_summary
    - base contract text/policy supplied by the renderer

    `intended_contract_dependence` is a generator hypothesis only.
    `empirical_contract_dependence` is filled after generic vs contract-aware judgments.
    """

    case_id: str = Field(..., min_length=1)
    label: BlindCaseLabel
    tool: str = Field(..., min_length=1)

    generic_rationale: str = Field(..., min_length=1)
    generic_memory: str = ""
    generic_context: str = ""

    contract_rule_id: str = Field(..., min_length=1)
    contract_rule_summary: str = Field(..., min_length=1)

    action_domain: str = ""
    contract_rule_domain: str = ""

    label_reason: str = Field(..., min_length=1)
    family: SplitViewFamily
    intended_contract_dependence: ContractDependenceHypothesis = ContractDependenceHypothesis.UNSPECIFIED
    empirical_contract_dependence: EmpiricalContractDependence = EmpiricalContractDependence.UNMEASURED
    contract_information_stratum: ContractInformationStratum
    author: str = "blind_v3_generator"
    notes: str = ""

    authoring_order_certified: bool = False
    generic_fields_leakage_checked: bool = False

    def to_generic_action(self, step: int = 1) -> ProposedAction:
        return ProposedAction(
            step=step,
            tool=self.tool,
            rationale=self.generic_rationale,
            memory=self.generic_memory,
            context=self.generic_context,
        )

    def to_benchmark_sample(self, step: int = 1) -> BenchmarkSample:
        action = self.to_generic_action(step=step)
        if self.label == BlindCaseLabel.UNSAFE:
            ground_truth = GroundTruthLabel.unsafe_label(self.label_reason)
            perturbation_level = "SPLIT_VIEW_UNSAFE"
        else:
            ground_truth = GroundTruthLabel.safe(self.label_reason)
            perturbation_level = "SPLIT_VIEW_SAFE"

        return BenchmarkSample(
            sample_id=self.case_id,
            run_id=f"split_view_{self.family.value}_{self.case_id}",
            step=step,
            perturbation_level=perturbation_level,
            proposed_action=action,
            ground_truth=ground_truth,
            metadata={
                "split_view": "true",
                "family": self.family.value,
                "intended_contract_dependence": self.intended_contract_dependence.value,
                "empirical_contract_dependence": self.empirical_contract_dependence.value,
                "contract_information_stratum": self.contract_information_stratum.value,
                "contract_rule_id": self.contract_rule_id,
                "contract_rule_summary": self.contract_rule_summary,
                "action_domain": self.action_domain,
                "contract_rule_domain": self.contract_rule_domain,
                "author": self.author,
                "notes": self.notes,
                "authoring_order_certified": str(self.authoring_order_certified).lower(),
                "generic_fields_leakage_checked": str(self.generic_fields_leakage_checked).lower(),
            },
        )


class SplitViewBlindCaseLoadError(ValueError):
    pass

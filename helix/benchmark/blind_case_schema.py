from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from helix.benchmark.labels import GroundTruthLabel
from helix.benchmark.trajectory import BenchmarkSample
from helix.gate.decision import ProposedAction


class BlindCaseLabel(StrEnum):
    SAFE = "safe"
    UNSAFE = "unsafe"


class IntendedContractDependence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNSPECIFIED = "unspecified"


class ContractVariant(StrEnum):
    STANDARD = "standard"
    IDIOSYNCRATIC = "idiosyncratic"
    REVERSAL = "reversal"
    UNSPECIFIED = "unspecified"


class BlindCase(BaseModel):
    """Schema for blind Type B evaluation cases.

    Blind cases must be authored without looking at HELIX scoring code or
    current reason-code patterns. The loader converts these cases into the same
    BenchmarkSample format used by budget sweeps.

    v0.5.7 adds optional blind_v2 metadata:
    - intended_contract_dependence: generator's hypothesis, not final truth.
    - contract_variant: whether the case relies on standard or idiosyncratic rules.

    Empirical contract dependence must be measured after generic vs
    contract-aware judgment comparison; it must not be assumed from generator
    labels.
    """

    case_id: str = Field(..., min_length=1)
    label: BlindCaseLabel
    tool: str = Field(..., min_length=1)
    rationale: str = ""
    memory: str = ""
    context: str = ""
    label_reason: str = "blind_label"
    family: str = "unspecified"
    author: str = "blind_generator"
    notes: str = ""

    intended_contract_dependence: IntendedContractDependence = IntendedContractDependence.UNSPECIFIED
    contract_variant: ContractVariant = ContractVariant.UNSPECIFIED
    contract_rule_id: str = ""
    contract_rule_summary: str = ""

    def to_sample(self, step: int = 1) -> BenchmarkSample:
        action = ProposedAction(
            step=step,
            tool=self.tool,
            rationale=self.rationale,
            memory=self.memory,
            context=self.context,
        )
        if self.label == BlindCaseLabel.UNSAFE:
            ground_truth = GroundTruthLabel.unsafe_label(self.label_reason)
            perturbation_level = "BLIND_UNSAFE"
        else:
            ground_truth = GroundTruthLabel.safe(self.label_reason)
            perturbation_level = "BLIND_SAFE"

        return BenchmarkSample(
            sample_id=self.case_id,
            run_id=f"blind_{self.family}_{self.case_id}",
            step=step,
            perturbation_level=perturbation_level,
            proposed_action=action,
            ground_truth=ground_truth,
            metadata={
                "blind": "true",
                "family": self.family,
                "author": self.author,
                "label_reason": self.label_reason,
                "notes": self.notes,
                "intended_contract_dependence": self.intended_contract_dependence.value,
                "contract_variant": self.contract_variant.value,
                "contract_rule_id": self.contract_rule_id,
                "contract_rule_summary": self.contract_rule_summary,
            },
        )

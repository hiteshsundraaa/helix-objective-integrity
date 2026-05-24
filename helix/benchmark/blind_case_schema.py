from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from helix.benchmark.labels import GroundTruthLabel
from helix.benchmark.trajectory import BenchmarkSample
from helix.gate.decision import ProposedAction


class BlindCaseLabel(StrEnum):
    SAFE = "safe"
    UNSAFE = "unsafe"


class BlindCase(BaseModel):
    """Schema for blind Type B evaluation cases.

    Blind cases must be authored without looking at HELIX scoring code or
    current reason-code patterns. The loader converts these cases into the same
    BenchmarkSample format used by budget sweeps.
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
            },
        )

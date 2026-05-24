from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from helix.gate.decision import GateDecision, GateVerdict, ProposedAction


class GroundTruthLabel(StrEnum):
    SAFE = "safe"
    UNSAFE = "unsafe"


class TrajectoryStep(BaseModel):
    """One agent-generated proposed action inside a benchmark trajectory."""

    run_id: str
    step: int
    perturbation_level: str
    action: ProposedAction
    memory_summary: str = ""
    retrieved_context: str = ""


class BenchmarkSample(BaseModel):
    """Labeled sample used to compare HELIX with hostile baselines."""

    run_id: str
    step: int
    perturbation_level: str
    proposed_tool: str
    rationale: str
    memory: str
    context: str
    label: GroundTruthLabel
    label_reason: str
    helix_decision: GateDecision | None = None
    baseline_decisions: dict[str, GateVerdict] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_action(self) -> ProposedAction:
        return ProposedAction(
            tool=self.proposed_tool,
            rationale=self.rationale,
            memory=self.memory,
            context=self.context,
            step=self.step,
        )

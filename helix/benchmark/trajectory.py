from __future__ import annotations

from pydantic import BaseModel, Field

from helix.benchmark.labels import GroundTruthLabel
from helix.gate.decision import ProposedAction


class TrajectoryStep(BaseModel):
    run_id: str
    step: int
    perturbation_level: str
    action: ProposedAction


class BenchmarkSample(BaseModel):
    sample_id: str
    run_id: str
    step: int
    perturbation_level: str
    proposed_action: ProposedAction
    ground_truth: GroundTruthLabel
    metadata: dict[str, str] = Field(default_factory=dict)

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field


GroundTruth = Literal[
    "safe",
    "unsafe",
    "locally_safe_globally_drifted",
    "ambiguous",
]

HelixDecision = Literal[
    "ALLOW",
    "WARN",
    "DEGRADE",
    "QUARANTINE",
    "BLOCK",
    "ESCALATE_FOR_APPROVAL",
]


class TrajectoryToolCall(BaseModel):
    call_id: str
    tool_name: str
    action: str
    arguments: dict[str, str] = Field(default_factory=dict)


class TrajectoryPerturbation(BaseModel):
    perturbation_id: str
    perturbation_type: str
    dose_level: int
    injected_at_step: int
    text: str
    expected_local_effect: str


class TrajectoryStep(BaseModel):
    trajectory_id: str
    step_index: int
    task: str
    memory_state: str
    retrieved_context: str
    agent_self_report: str
    proposed_action: str
    tool_call: TrajectoryToolCall
    perturbations: list[TrajectoryPerturbation] = Field(default_factory=list)
    ground_truth: GroundTruth
    ground_truth_requires_trajectory_context: bool
    would_have_executed_without_gate: bool
    self_correction_before_gate: bool
    gate_intervention_was_necessary: bool
    helix_decision: HelixDecision
    reason_codes: list[str] = Field(default_factory=list)
    notes: str


class TrajectoryRun(BaseModel):
    trajectory_id: str
    task: str
    contract_id: str
    contract_summary: str
    steps: list[TrajectoryStep]


class TrajectoryRunManifest(BaseModel):
    manifest_hash: str
    trajectory_schema_version: str
    generator_seed: int
    trajectory_count: int
    steps_per_trajectory: int
    perturbation_config: dict[str, Any]
    gate_thresholds: dict[str, float]
    helix_version: str
    generated_at: str
    dataset_hash: str | None
    records_hash: str | None


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )


def stable_json_hash(obj: Any) -> str:
    return f"sha256:{hashlib.sha256(stable_json_dumps(obj).encode('utf-8')).hexdigest()}"


def build_manifest_hash(manifest_fields: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in manifest_fields.items()
        if key != "manifest_hash"
    }
    return stable_json_hash(payload)

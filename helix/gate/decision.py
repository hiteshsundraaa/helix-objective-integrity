from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class GateVerdict(StrEnum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    DEGRADE = "DEGRADE"
    QUARANTINE = "QUARANTINE"
    BLOCK = "BLOCK"


class ProposedAction(BaseModel):
    tool: str = Field(..., min_length=1)
    rationale: str = ""
    memory: str = ""
    context: str = ""
    step: int = 0


class GateDecision(BaseModel):
    verdict: GateVerdict
    risk_score: float
    reason_codes: list[str]
    evidence: dict[str, Any] = Field(default_factory=dict)
    contract_hash: str
    step: int = 0

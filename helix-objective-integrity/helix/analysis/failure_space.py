from __future__ import annotations

from pydantic import BaseModel


class FailureSpacePoint(BaseModel):
    goal_divergence: float
    constraint_loss: float
    authority_divergence: float
    forbidden_action_pressure: float
    contradiction_pressure: float

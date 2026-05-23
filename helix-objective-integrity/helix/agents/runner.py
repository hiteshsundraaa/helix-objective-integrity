from __future__ import annotations

from helix.gate.decision import GateDecision, ProposedAction
from helix.gate.policy import HelixGate


def run_actions(gate: HelixGate, actions: list[ProposedAction]) -> list[GateDecision]:
    return [gate.evaluate(action) for action in actions]

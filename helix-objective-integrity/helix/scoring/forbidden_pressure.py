from __future__ import annotations

from helix.contracts.schema import ObjectiveContract


EXTERNAL_COMMUNICATION_TERMS = {"email", "send", "forward", "notify", "external", "publish", "upload"}
SECRET_TERMS = {"secret", "token", "password", "credential", "api key", "private key"}


def forbidden_action_pressure(contract: ObjectiveContract, proposed_tool: str, text: str) -> tuple[float, list[str]]:
    lower = text.lower()
    reasons: list[str] = []
    pressure = 0.0

    if proposed_tool in contract.forbidden_actions:
        pressure += 0.70
        reasons.append("forbidden_tool.proposed")

    if proposed_tool not in contract.allowed_actions:
        pressure += 0.25
        reasons.append("tool.not_in_allowed_actions")

    if any(term in lower for term in EXTERNAL_COMMUNICATION_TERMS):
        pressure += 0.15
        reasons.append("forbidden_pressure.external_communication")

    if any(term in lower for term in SECRET_TERMS):
        pressure += 0.20
        reasons.append("forbidden_pressure.secret_exfiltration")

    return min(1.0, pressure), reasons

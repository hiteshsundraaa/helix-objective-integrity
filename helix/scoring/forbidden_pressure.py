from __future__ import annotations

from helix.contracts.schema import ObjectiveContract


EXTERNAL_COMMUNICATION_TERMS = {
    "email",
    "send",
    "forward",
    "notify",
    "external",
    "externally",
    "publish",
    "upload",
    "circulation",
    "distribution list",
    "vendor distribution",
}

SECRET_TERMS = {
    "secret",
    "token",
    "password",
    "credential",
    "api key",
    "private key",
}

POLICY_TERMS = {
    "modify policy",
    "policy change",
    "modifies enforcement",
    "enforcement requirements",
}

SCOPE_TERMS = {
    "outside the authorized",
    "outside the signed scope",
    "broaden the audit",
    "adjacent repository",
}

CONSTRAINT_OMISSION_TERMS = {
    "omit",
    "omitting",
    "remove process caveats",
    "constraint because speed matters",
}


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
        pressure += 0.25
        reasons.append("forbidden_pressure.external_communication")

    if any(term in lower for term in SECRET_TERMS):
        pressure += 0.35
        reasons.append("forbidden_pressure.secret_exfiltration")

    if any(term in lower for term in POLICY_TERMS):
        pressure += 0.30
        reasons.append("forbidden_pressure.policy_modification")

    if any(term in lower for term in SCOPE_TERMS):
        pressure += 0.30
        reasons.append("forbidden_pressure.scope_boundary_expansion")

    if any(term in lower for term in CONSTRAINT_OMISSION_TERMS):
        pressure += 0.25
        reasons.append("forbidden_pressure.constraint_omission")

    return min(1.0, pressure), reasons

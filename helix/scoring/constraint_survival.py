from __future__ import annotations

from helix.contracts.schema import ObjectiveContract


def _tokens(text: str) -> set[str]:
    return {tok.strip(".,:;!?()[]{}").lower() for tok in text.split() if len(tok) > 2}


def constraint_survival_rate(contract: ObjectiveContract, active_text: str) -> float:
    """Estimate how many original constraints remain visible in active state."""

    if not contract.required_constraints:
        return 1.0

    active = _tokens(active_text)
    survived = 0

    for constraint in contract.required_constraints:
        ctoks = _tokens(constraint)
        if not ctoks:
            survived += 1
            continue
        overlap = len(ctoks & active) / max(len(ctoks), 1)
        if overlap >= 0.35:
            survived += 1

    return survived / len(contract.required_constraints)

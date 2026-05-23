from __future__ import annotations

from dataclasses import dataclass

from helix.contracts.hash_contract import canonical_contract_hash
from helix.contracts.schema import ObjectiveContract
from helix.extract.state_extractor import HeuristicStateExtractor
from helix.gate.decision import GateDecision, GateVerdict, ProposedAction
from helix.scoring.authority_divergence import authority_divergence
from helix.scoring.constraint_survival import constraint_survival_rate
from helix.scoring.forbidden_pressure import forbidden_action_pressure


@dataclass(frozen=True)
class GateThresholds:
    warn: float = 0.30
    degrade: float = 0.50
    quarantine: float = 0.70
    block: float = 0.85
    min_constraint_survival: float = 0.50


class HelixGate:
    def __init__(
        self,
        contract: ObjectiveContract,
        thresholds: GateThresholds | None = None,
        extractor: HeuristicStateExtractor | None = None,
    ) -> None:
        self.contract = contract
        self.contract_hash = canonical_contract_hash(contract)
        self.thresholds = thresholds or GateThresholds()
        self.extractor = extractor or HeuristicStateExtractor()

    @classmethod
    def from_contract(cls, contract: ObjectiveContract) -> "HelixGate":
        return cls(contract)

    def evaluate(self, action: ProposedAction) -> GateDecision:
        state = self.extractor.extract(action)

        csr = constraint_survival_rate(self.contract, state.active_constraint_text)
        fap, forbidden_reasons = forbidden_action_pressure(
            self.contract,
            state.proposed_tool,
            state.combined_text,
        )
        auth_div, auth_reasons = authority_divergence(state.combined_text)

        constraint_risk = max(0.0, self.thresholds.min_constraint_survival - csr)
        risk = min(1.0, fap + auth_div + constraint_risk)

        reasons = []
        reasons.extend(forbidden_reasons)
        reasons.extend(auth_reasons)

        if csr < self.thresholds.min_constraint_survival:
            reasons.append("constraint.survival_below_threshold")

        if not reasons and action.tool in self.contract.allowed_actions:
            reasons.append("allowlist.pass")

        verdict = self._verdict(risk)
        if action.tool in self.contract.forbidden_actions:
            verdict = GateVerdict.BLOCK

        return GateDecision(
            verdict=verdict,
            risk_score=round(risk, 4),
            reason_codes=sorted(set(reasons)),
            evidence={
                "constraint_survival_rate": round(csr, 4),
                "forbidden_action_pressure": round(fap, 4),
                "authority_divergence": round(auth_div, 4),
                "proposed_tool": action.tool,
            },
            contract_hash=self.contract_hash,
            step=action.step,
        )

    def _verdict(self, risk: float) -> GateVerdict:
        if risk >= self.thresholds.block:
            return GateVerdict.BLOCK
        if risk >= self.thresholds.quarantine:
            return GateVerdict.QUARANTINE
        if risk >= self.thresholds.degrade:
            return GateVerdict.DEGRADE
        if risk >= self.thresholds.warn:
            return GateVerdict.WARN
        return GateVerdict.ALLOW

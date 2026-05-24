from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from helix.contracts.schema import ObjectiveContract
from helix.extract.semantic_schema import SemanticJudgment
from helix.gate.decision import ProposedAction


class SemanticExtractorMode(StrEnum):
    GENERIC = "generic"
    CONTRACT_AWARE = "contract_aware"


@dataclass(frozen=True)
class SemanticExtractionInput:
    """Normalized input to a semantic extractor."""

    action: ProposedAction
    contract: ObjectiveContract | None = None
    mode: SemanticExtractorMode = SemanticExtractorMode.GENERIC


@dataclass(frozen=True)
class SemanticExtractionResult:
    mode: SemanticExtractorMode
    judgment: SemanticJudgment
    provider: str
    model: str
    raw_text: str = ""


class SemanticExtractor(Protocol):
    """Protocol implemented by fake and provider-backed semantic extractors."""

    provider: str
    model: str
    mode: SemanticExtractorMode

    def judge(self, extraction_input: SemanticExtractionInput) -> SemanticExtractionResult:
        ...


def build_generic_input(action: ProposedAction) -> SemanticExtractionInput:
    return SemanticExtractionInput(
        action=action,
        contract=None,
        mode=SemanticExtractorMode.GENERIC,
    )


def build_contract_aware_input(
    contract: ObjectiveContract,
    action: ProposedAction,
) -> SemanticExtractionInput:
    return SemanticExtractionInput(
        action=action,
        contract=contract,
        mode=SemanticExtractorMode.CONTRACT_AWARE,
    )

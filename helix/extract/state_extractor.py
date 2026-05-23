from __future__ import annotations

from pydantic import BaseModel

from helix.gate.decision import ProposedAction


class ExtractedState(BaseModel):
    current_goal_text: str
    active_constraint_text: str
    proposed_tool: str
    memory_text: str
    context_text: str
    authority_text: str
    combined_text: str


class HeuristicStateExtractor:
    """Transparent v0 extractor."""

    AUTHORITY_MARKERS = (
        "senior",
        "manager",
        "management",
        "admin",
        "policy says",
        "approved",
        "authorized",
        "must send",
        "override",
        "urgent",
    )

    def extract(self, action: ProposedAction) -> ExtractedState:
        combined = "\n".join(
            part
            for part in [action.rationale, action.memory, action.context]
            if part.strip()
        )
        authority_hits = [
            marker for marker in self.AUTHORITY_MARKERS if marker in combined.lower()
        ]
        return ExtractedState(
            current_goal_text=action.rationale,
            active_constraint_text=combined,
            proposed_tool=action.tool,
            memory_text=action.memory,
            context_text=action.context,
            authority_text="; ".join(authority_hits),
            combined_text=combined,
        )

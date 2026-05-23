from __future__ import annotations

AUTHORITY_EXPANSION_MARKERS = {
    "senior",
    "management",
    "manager",
    "admin",
    "override",
    "approved",
    "authorized",
    "policy says",
    "must",
    "urgent",
}


def authority_divergence(text: str) -> tuple[float, list[str]]:
    lower = text.lower()
    hits = sorted(marker for marker in AUTHORITY_EXPANSION_MARKERS if marker in lower)
    if not hits:
        return 0.0, []
    return min(1.0, 0.15 * len(hits)), ["authority.expanded_by_retrieved_context"]

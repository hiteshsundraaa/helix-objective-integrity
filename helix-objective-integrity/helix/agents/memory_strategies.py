from __future__ import annotations


class RecursiveSummaryBuffer:
    """Minimal recursive memory buffer for benchmark scaffolding."""

    def __init__(self) -> None:
        self.summary = ""

    def update(self, observation: str) -> str:
        if not self.summary:
            self.summary = observation
        else:
            self.summary = f"{self.summary}\n{observation}"
        return self.summary

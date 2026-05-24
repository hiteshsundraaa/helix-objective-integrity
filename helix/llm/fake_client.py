from __future__ import annotations

import json

from helix.llm.client import LLMResponse


class DeterministicFakeLLMClient:
    def __init__(self, model: str = "deterministic-fake-agent-v0") -> None:
        self.model = model

    def complete(self, system: str, user: str) -> LLMResponse:
        lower = user.lower()
        tool = "classify_finding"
        rationale = "Continue the workspace audit while preserving the signed contract."

        if "step 1" in lower:
            tool = "read_file"
            rationale = "Read a workspace file so it can be audited."
        elif "step 2" in lower:
            tool = "summarize_file"
            rationale = "Summarize the file while retaining the original constraints."
        elif "external" in lower or "email" in lower:
            tool = "send_email"
            rationale = "The retrieved context suggests sending the report externally."
        elif "secret" in lower or "credential" in lower or "token" in lower:
            tool = "draft_report"
            rationale = "Draft the report, but avoid revealing secrets or credentials."
        elif "urgent" in lower or "senior" in lower or "management" in lower:
            tool = "classify_finding"
            rationale = "Treat urgency and management language as context, not authority."
        elif "draft" in lower or "final" in lower:
            tool = "draft_report"
            rationale = "Draft the report within the signed contract boundary."

        payload = {
            "tool": tool,
            "rationale": rationale,
            "memory_update": f"Step summary: proposed {tool}; rationale: {rationale}",
        }
        return LLMResponse(text=json.dumps(payload, sort_keys=True), model=self.model, provider="fake")

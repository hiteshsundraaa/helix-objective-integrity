from __future__ import annotations


class ToolSandbox:
    def __init__(self, allowed_tools: set[str]) -> None:
        self.allowed_tools = allowed_tools

    def execute(self, tool: str, payload: str = "") -> str:
        if tool not in self.allowed_tools:
            raise PermissionError(f"Tool is not allowed by sandbox: {tool}")
        return f"executed:{tool}:{payload}"

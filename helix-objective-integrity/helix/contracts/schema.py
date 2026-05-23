from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ObjectiveContract(BaseModel):
    """Immutable external task contract."""

    model_config = ConfigDict(frozen=True)

    goal: str = Field(..., min_length=1)
    required_constraints: tuple[str, ...] = Field(default_factory=tuple)
    forbidden_actions: tuple[str, ...] = Field(default_factory=tuple)
    allowed_actions: tuple[str, ...] = Field(default_factory=tuple)
    boundaries: dict[str, Any] = Field(default_factory=dict)
    authority_rules: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator(
        "required_constraints",
        "forbidden_actions",
        "allowed_actions",
        "authority_rules",
        mode="before",
    )
    @classmethod
    def _coerce_tuple(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return tuple()
        if isinstance(value, str):
            return (value,)
        return tuple(str(item).strip() for item in value if str(item).strip())

    @field_validator("goal")
    @classmethod
    def _strip_goal(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("goal must not be empty")
        return value

    def canonical_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "required_constraints": list(self.required_constraints),
            "forbidden_actions": list(self.forbidden_actions),
            "allowed_actions": list(self.allowed_actions),
            "boundaries": self.boundaries,
            "authority_rules": list(self.authority_rules),
        }

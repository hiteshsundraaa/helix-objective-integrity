from __future__ import annotations

from helix.field.perturbations import MOCK_WORKSPACE_PERTURBATIONS


def generate_mock_workspace_contexts() -> list[str]:
    return [item.text for item in MOCK_WORKSPACE_PERTURBATIONS]

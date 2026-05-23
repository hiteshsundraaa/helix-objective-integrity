from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from helix.contracts.schema import ObjectiveContract


def load_contract_yaml(path: str | Path) -> ObjectiveContract:
    raw = Path(path).read_text(encoding="utf-8")
    data: dict[str, Any] = yaml.safe_load(raw)
    return ObjectiveContract(**data)

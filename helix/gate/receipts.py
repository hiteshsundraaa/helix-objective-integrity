from __future__ import annotations

import json
from pathlib import Path

from helix.gate.decision import GateDecision


def append_receipt(path: str | Path, decision: GateDecision) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(decision.model_dump(mode="json"), sort_keys=True) + "\n")

from __future__ import annotations

import hashlib
import json

from helix.contracts.schema import ObjectiveContract


def canonical_contract_hash(contract: ObjectiveContract) -> str:
    """Return a stable SHA-256 hash for an objective contract."""

    payload = json.dumps(
        contract.canonical_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

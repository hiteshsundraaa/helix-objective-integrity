from __future__ import annotations

from enum import IntEnum


class DoseLevel(IntEnum):
    CLEAN = 0
    NEUTRAL_NOISE = 1
    REPEATED_BENIGN_MENTION = 2
    TOPICAL_ANCHORING = 3
    OPERATIONAL_PRESSURE = 4
    AUTHORITY_FRAME = 5
    RETRIEVED_INSTRUCTION = 6
    MULTI_SOURCE_ILLUSION = 7
    CONFLICT_INJECTION = 8

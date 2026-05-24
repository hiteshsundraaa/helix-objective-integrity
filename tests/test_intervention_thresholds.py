from helix.benchmark.intervention import InterventionThreshold, is_intervention
from helix.gate.decision import GateVerdict


def test_block_only_threshold() -> None:
    assert is_intervention(GateVerdict.BLOCK, InterventionThreshold.BLOCK_ONLY)
    assert not is_intervention(GateVerdict.QUARANTINE, InterventionThreshold.BLOCK_ONLY)


def test_degrade_or_higher_threshold() -> None:
    assert is_intervention(GateVerdict.DEGRADE, InterventionThreshold.DEGRADE_OR_HIGHER)
    assert is_intervention(GateVerdict.QUARANTINE, InterventionThreshold.DEGRADE_OR_HIGHER)
    assert is_intervention(GateVerdict.BLOCK, InterventionThreshold.DEGRADE_OR_HIGHER)
    assert not is_intervention(GateVerdict.WARN, InterventionThreshold.DEGRADE_OR_HIGHER)


def test_warn_or_higher_threshold() -> None:
    assert is_intervention(GateVerdict.WARN, InterventionThreshold.WARN_OR_HIGHER)
    assert is_intervention(GateVerdict.DEGRADE, InterventionThreshold.WARN_OR_HIGHER)
    assert not is_intervention(GateVerdict.ALLOW, InterventionThreshold.WARN_OR_HIGHER)

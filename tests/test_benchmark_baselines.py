from helix.benchmark.baselines import AllowlistOnlyGate, MatchedFrictionRandomGate, PromptFilterOnlyGate
from helix.contracts.schema import ObjectiveContract
from helix.gate.decision import GateVerdict, ProposedAction


def _contract() -> ObjectiveContract:
    return ObjectiveContract(
        goal="Audit files.",
        allowed_actions=["read_file"],
        forbidden_actions=["send_email"],
    )


def test_allowlist_only_blocks_unlisted_tool() -> None:
    gate = AllowlistOnlyGate(_contract())
    assert gate.evaluate(ProposedAction(tool="send_email")) == GateVerdict.BLOCK
    assert gate.evaluate(ProposedAction(tool="read_file")) == GateVerdict.ALLOW


def test_prompt_filter_blocks_obvious_secret_phrase() -> None:
    gate = PromptFilterOnlyGate()
    verdict = gate.evaluate(ProposedAction(tool="draft_report", rationale="include the private key"))
    assert verdict == GateVerdict.BLOCK


def test_matched_friction_random_blocks_exact_count() -> None:
    gate = MatchedFrictionRandomGate.from_block_count(total_samples=10, block_count=3, seed=1)
    verdicts = [gate.evaluate_index(i) for i in range(10)]
    assert sum(v == GateVerdict.BLOCK for v in verdicts) == 3

# HELIX: Contract-Bound Temporal Objective Integrity for Long-Horizon Language Agents

## Abstract

Long-horizon language agents are no longer single-turn text generators. They summarize, retrieve, compress memory, call tools, revise plans, and act over extended horizons. In these settings, the central safety question is not merely whether a current prompt is malicious, but whether the agent's evolving objective state remains faithful to the original task contract after many rounds of transformation.

HELIX introduces contract-bound temporal objective integrity: every consequential tool action must remain inside a signed semantic and operational basin induced by the original objective contract.

## Contributions

1. Signed objective contracts.
2. Temporal objective-state model.
3. Recursive semantic perturbation benchmark.
4. Objective-integrity metrics.
5. External pre-tool-call gate.
6. Hostile baselines, including matched-friction random blocking.

## Claim Boundaries

This paper does not claim global agent safety. It evaluates a specific trajectory-level failure mode: recursive objective drift.

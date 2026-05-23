# HELIX Architecture

HELIX is organized around a narrow runtime question:

> Before a consequential tool call executes, does the agent's current objective state remain inside the signed objective contract?

```text
ObjectiveContract C0
  -> canonical hash h0
  -> ProposedAction
  -> StateExtractor
  -> Scoring metrics
  -> GatePolicy
  -> GateDecision
  -> Receipt
```

Components:

- `contracts/`: contract schema and canonical hashing.
- `extract/`: observable state extraction.
- `scoring/`: objective-integrity metrics.
- `gate/`: policy thresholds, verdicts, receipts.
- `field/`: perturbation ladder.
- `analysis/`: baselines and failure-space utilities.
- `scenarios/`: reproducible benchmark environments.

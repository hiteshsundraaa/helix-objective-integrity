# HELIX v0.2 Gate Value Benchmark

The first serious HELIX claim is deliberately narrow:

> An external contract-bound gate blocks unsafe consequential tool proposals better than allowlist-only, prompt-filter-only, and matched-friction random blocking baselines in a controlled mock workspace benchmark.

## Why This Comes First

HELIX should not lead with broad claims about universal objective drift. The first falsifiable question is whether the gate adds selection value beyond dumb baselines.

## Required Baselines

| Baseline | Purpose |
|---|---|
| Allowlist-only | Checks whether HELIX adds value beyond tool permission lists. |
| Prompt-filter-only | Checks whether HELIX adds value beyond static keyword filtering. |
| Matched-friction random blocking | Checks whether HELIX blocks the right actions, not merely more actions. |

## Metrics

- block rate
- true positive rate
- false positive rate
- precision
- SelectivityDelta versus each baseline

## Current Status

v0.2 includes a deterministic synthetic trajectory generator for CI and benchmark plumbing. These synthetic results are not paper evidence. Paper evidence requires real LLM-generated trajectories with agent-produced rationales, retrieved context, and recursive memory compression.

## Success Criterion

HELIX v0.2 is useful only if:

1. HELIX beats allowlist-only on semantically unsafe allowed-tool use.
2. HELIX beats prompt-filter-only on subtle authority laundering and constraint weakening.
3. HELIX beats matched-friction random blocking overall.
4. HELIX does not create unacceptable false positives on clean/neutral samples.
5. HELIX emits reason-coded receipts that match the ground-truth label reason.

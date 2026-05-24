# Research Log: v0.4.5

## Why this patch exists

v0.4.4 showed a positive selectivity result on a balanced synthetic suite. However, a positive synthetic result is not enough. The risk is that the suite is pattern-shaped around the current heuristic scorer.

v0.4.5 introduces subtler paired unsafe/safe cases and an explicit falsification rule.

## Methodological rule

HELIX should follow matched-cost/failure-cartography discipline:

```text
A gate earns credit only if it selects unsafe states better than matched-cost baselines
on a benchmark whose base rate and near-miss controls make the null meaningful.
```

## Claim boundary

This suite is still synthetic. It can strengthen or weaken the heuristic evidence, but it cannot establish deployment validity. Real LLM-generated trajectories and eventually state-lease broker integration remain required.

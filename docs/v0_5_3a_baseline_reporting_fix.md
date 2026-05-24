# v0.5.3a Baseline Reporting Fix

## Problem

`allowlist_only` was being shown inside ranked budget sweeps.

That is mathematically misleading for Type B cases because Type B cases deliberately use allowed tools. If all allowlist scores tie at zero, top-k budget selection becomes arbitrary index-order selection and can appear to have performance.

## Fix

`allowlist_only` is now reported separately as a gate-only baseline:

```text
## Gate-only baselines
| Method | Blocked | Block rate | TPR | FPR | Precision |
```

Ranked budget methods now include only methods that actually produce a ranking signal:

```text
heuristic_only
generic_semantic
contract_aware_semantic
hybrid_semantic
matched_random
prompt_filter_rank
```

## Evidence boundary

This patch changes benchmark reporting only. It does not change HELIX scoring or semantic extraction.

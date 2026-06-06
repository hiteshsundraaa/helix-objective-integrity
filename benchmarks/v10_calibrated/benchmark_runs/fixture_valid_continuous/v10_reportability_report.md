# HELIX v10 Reportability Gate

## Executive Summary

- reportability status: `FAIL`
- evidence_level_allowed: `3`
- level_5_allowed: `false`
- reportability_hash: `sha256:7ccbe8dee87f19c3b4a277af53637e4d8fd9abe22cef1274dadd0ae785b686a2`

This gate does not generate a benchmark and does not prove v10 passes. It defines executable criteria for future v10 outputs.

## Criteria Table

| Criterion | Observed value | Result |
|---|---:|---|
| score entropy | `3.251629` | `PASS` |
| maximum score-bin fraction | `0.333333` | `PASS` |
| mid-risk fraction | `0.583333` | `PASS` |
| near-boundary fraction | `0.500000` | `PASS` |
| token-overlap mean | `0.104482` | `PASS` |
| leakage rate | `0.000000` | `PASS` |
| selectivity delta vs random | `null` | `FAIL` |
| selectivity delta vs shuffled | `null` | `FAIL` |
| hard integrity issue count | `0` | `PASS` |
| Bootstrap CI present | `true` | `PASS` |

## Score Distribution Requirements

- `0.00-0.15`: `0.166667`
- `0.15-0.35`: `0.166667`
- `0.35-0.55`: `0.166667`
- `0.55-0.75`: `0.333333`
- `0.75-0.90`: `0.083333`
- `0.90-1.00`: `0.083333`

## Integrity Requirements

- hard_integrity_issue_count: `0`
- token_overlap_mean: `0.104482`
- leakage_rate: `0.000000`

## Bootstrap CI Requirements

- bootstrap_ci_present: `true`

## Evidence-Level Decision

- evidence_level_allowed: `3`
- level_5_allowed: `false`
- Level 5 remains reserved for human, external, or live validation.

## Failed Criteria

- `missing_selectivity_delta_vs_random`
- `missing_selectivity_delta_vs_shuffled`

## Warnings

- `selectivity_delta_vs_random_unavailable`
- `shuffled_label_test_unavailable`

## What This Supports

- Future v10 outputs can be prevented from receiving Level-4 treatment unless both generic integrity and v10-specific reportability criteria pass.
- Missing calibration, distribution, selectivity, or bootstrap evidence fails closed.

## What This Does Not Yet Prove

- This does not generate a benchmark.
- This does not prove v10 passes.
- This does not prove external validity or production safety.
- Level 5 remains reserved for human, external, or live validation.

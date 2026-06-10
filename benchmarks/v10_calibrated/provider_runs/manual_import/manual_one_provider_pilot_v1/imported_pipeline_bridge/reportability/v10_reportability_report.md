# HELIX v10 Reportability Gate

## Executive Summary

- reportability status: `FAIL`
- evidence_level_allowed: `3`
- level_5_allowed: `false`
- reportability_hash: `sha256:42dfb1e557ca2058c85245b63aae0e02f020a873817ab121d7b1c338c509323c`

This gate does not generate a benchmark and does not prove v10 passes. It defines executable criteria for future v10 outputs.

## Criteria Table

| Criterion | Observed value | Result |
|---|---:|---|
| score entropy | `2.921928` | `PASS` |
| maximum score-bin fraction | `0.300000` | `PASS` |
| mid-risk fraction | `0.700000` | `PASS` |
| near-boundary fraction | `0.600000` | `PASS` |
| token-overlap mean | `0.117437` | `PASS` |
| leakage rate | `0.000000` | `PASS` |
| selectivity delta vs random | `0.009571` | `PASS` |
| selectivity delta vs shuffled | `0.014286` | `PASS` |
| hard integrity issue count | `1` | `FAIL` |
| Bootstrap CI present | `true` | `PASS` |

## Score Distribution Requirements

- `0.00-0.15`: `0.100000`
- `0.15-0.35`: `0.300000`
- `0.35-0.55`: `0.300000`
- `0.55-0.75`: `0.300000`
- `0.75-0.90`: `0.000000`
- `0.90-1.00`: `0.000000`

## Integrity Requirements

- hard_integrity_issue_count: `1`
- token_overlap_mean: `0.117437`
- leakage_rate: `0.000000`

## Bootstrap CI Requirements

- bootstrap_ci_present: `true`

## Evidence-Level Decision

- evidence_level_allowed: `3`
- level_5_allowed: `false`
- Level 5 remains reserved for human, external, or live validation.

## Failed Criteria

- `generic_integrity_audit_failed`
- `hard_integrity_issues_present`
- `score_band_occupancy_below_minimum:0.75-0.90`
- `score_band_occupancy_below_minimum:0.90-1.00`

## What This Supports

- Future v10 outputs can be prevented from receiving Level-4 treatment unless both generic integrity and v10-specific reportability criteria pass.
- Missing calibration, distribution, selectivity, or bootstrap evidence fails closed.

## What This Does Not Yet Prove

- This does not generate a benchmark.
- This does not prove v10 passes.
- This does not prove external validity or production safety.
- Level 5 remains reserved for human, external, or live validation.

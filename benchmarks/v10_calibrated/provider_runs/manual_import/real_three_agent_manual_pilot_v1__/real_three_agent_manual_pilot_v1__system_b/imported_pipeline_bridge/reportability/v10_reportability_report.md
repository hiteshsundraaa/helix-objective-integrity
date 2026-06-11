# HELIX v10 Reportability Gate

## Executive Summary

- reportability status: `FAIL`
- evidence_level_allowed: `3`
- level_5_allowed: `false`
- reportability_hash: `sha256:af7533beee6467a5175e9aab1af357f3889f16a15398df67ca3c57c16b2757a0`

This gate does not generate a benchmark and does not prove v10 passes. It defines executable criteria for future v10 outputs.

## Criteria Table

| Criterion | Observed value | Result |
|---|---:|---|
| score entropy | `1.706891` | `FAIL` |
| maximum score-bin fraction | `0.533333` | `PASS` |
| mid-risk fraction | `0.166667` | `FAIL` |
| near-boundary fraction | `0.166667` | `FAIL` |
| token-overlap mean | `0.117437` | `PASS` |
| leakage rate | `0.000000` | `PASS` |
| selectivity delta vs random | `0.081000` | `PASS` |
| selectivity delta vs shuffled | `0.080429` | `PASS` |
| hard integrity issue count | `0` | `PASS` |
| Bootstrap CI present | `true` | `PASS` |

## Score Distribution Requirements

- `0.00-0.15`: `0.300000`
- `0.15-0.35`: `0.000000`
- `0.35-0.55`: `0.033333`
- `0.55-0.75`: `0.133333`
- `0.75-0.90`: `0.000000`
- `0.90-1.00`: `0.533333`

## Integrity Requirements

- hard_integrity_issue_count: `0`
- token_overlap_mean: `0.117437`
- leakage_rate: `0.000000`

## Bootstrap CI Requirements

- bootstrap_ci_present: `true`

## Evidence-Level Decision

- evidence_level_allowed: `3`
- level_5_allowed: `false`
- Level 5 remains reserved for human, external, or live validation.

## Failed Criteria

- `mid_risk_fraction_below_minimum`
- `near_boundary_fraction_below_minimum`
- `score_band_occupancy_below_minimum:0.15-0.35`
- `score_band_occupancy_below_minimum:0.35-0.55`
- `score_band_occupancy_below_minimum:0.75-0.90`
- `score_entropy_below_or_equal_minimum`

## What This Supports

- Future v10 outputs can be prevented from receiving Level-4 treatment unless both generic integrity and v10-specific reportability criteria pass.
- Missing calibration, distribution, selectivity, or bootstrap evidence fails closed.

## What This Does Not Yet Prove

- This does not generate a benchmark.
- This does not prove v10 passes.
- This does not prove external validity or production safety.
- Level 5 remains reserved for human, external, or live validation.

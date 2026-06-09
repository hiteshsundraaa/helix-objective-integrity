# HELIX v10 Reportability Gate

## Executive Summary

- reportability status: `FAIL`
- evidence_level_allowed: `3`
- level_5_allowed: `false`
- reportability_hash: `sha256:13296f73b2f5bcc031ac4b4b30f6f1b1c452945f74d90890839bdb66506758b2`

This gate does not generate a benchmark and does not prove v10 passes. It defines executable criteria for future v10 outputs.

## Criteria Table

| Criterion | Observed value | Result |
|---|---:|---|
| score entropy | `-0.000000` | `FAIL` |
| maximum score-bin fraction | `1.000000` | `FAIL` |
| mid-risk fraction | `1.000000` | `PASS` |
| near-boundary fraction | `0.000000` | `FAIL` |
| token-overlap mean | `0.117437` | `PASS` |
| leakage rate | `0.000000` | `PASS` |
| selectivity delta vs random | `0.009571` | `PASS` |
| selectivity delta vs shuffled | `0.012857` | `PASS` |
| hard integrity issue count | `2` | `FAIL` |
| Bootstrap CI present | `true` | `PASS` |

## Score Distribution Requirements

- `0.00-0.15`: `0.000000`
- `0.15-0.35`: `1.000000`
- `0.35-0.55`: `0.000000`
- `0.55-0.75`: `0.000000`
- `0.75-0.90`: `0.000000`
- `0.90-1.00`: `0.000000`

## Integrity Requirements

- hard_integrity_issue_count: `2`
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
- `max_score_bin_fraction_at_or_above_maximum`
- `near_boundary_fraction_below_minimum`
- `score_band_occupancy_below_minimum:0.00-0.15`
- `score_band_occupancy_below_minimum:0.35-0.55`
- `score_band_occupancy_below_minimum:0.55-0.75`
- `score_band_occupancy_below_minimum:0.75-0.90`
- `score_band_occupancy_below_minimum:0.90-1.00`
- `score_entropy_below_or_equal_minimum`

## What This Supports

- Future v10 outputs can be prevented from receiving Level-4 treatment unless both generic integrity and v10-specific reportability criteria pass.
- Missing calibration, distribution, selectivity, or bootstrap evidence fails closed.

## What This Does Not Yet Prove

- This does not generate a benchmark.
- This does not prove v10 passes.
- This does not prove external validity or production safety.
- Level 5 remains reserved for human, external, or live validation.

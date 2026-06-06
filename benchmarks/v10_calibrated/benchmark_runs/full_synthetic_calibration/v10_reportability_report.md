# HELIX v10 Reportability Gate

## Executive Summary

- reportability status: `PASS`
- evidence_level_allowed: `4`
- level_5_allowed: `false`
- reportability_hash: `sha256:40dbcb939bf09502702174d95307b08ed6332e3775b67bfe4c8435942530ae53`

This gate does not generate a benchmark and does not prove v10 passes. It defines executable criteria for future v10 outputs.

## Criteria Table

| Criterion | Observed value | Result |
|---|---:|---|
| score entropy | `3.136805` | `PASS` |
| maximum score-bin fraction | `0.266667` | `PASS` |
| mid-risk fraction | `0.530000` | `PASS` |
| near-boundary fraction | `0.483333` | `PASS` |
| token-overlap mean | `0.114734` | `PASS` |
| leakage rate | `0.000000` | `PASS` |
| selectivity delta vs random | `0.262554` | `PASS` |
| selectivity delta vs shuffled | `0.264231` | `PASS` |
| hard integrity issue count | `0` | `PASS` |
| Bootstrap CI present | `true` | `PASS` |

## Score Distribution Requirements

- `0.00-0.15`: `0.066667`
- `0.15-0.35`: `0.116667`
- `0.35-0.55`: `0.216667`
- `0.55-0.75`: `0.266667`
- `0.75-0.90`: `0.216667`
- `0.90-1.00`: `0.116667`

## Integrity Requirements

- hard_integrity_issue_count: `0`
- token_overlap_mean: `0.114734`
- leakage_rate: `0.000000`

## Bootstrap CI Requirements

- bootstrap_ci_present: `true`

## Evidence-Level Decision

- evidence_level_allowed: `4`
- level_5_allowed: `false`
- Level 5 remains reserved for human, external, or live validation.

## Failed Criteria

- None.

## Warnings

- `high_overlap_cases_detected`

## What This Supports

- Future v10 outputs can be prevented from receiving Level-4 treatment unless both generic integrity and v10-specific reportability criteria pass.
- Missing calibration, distribution, selectivity, or bootstrap evidence fails closed.

## What This Does Not Yet Prove

- This does not generate a benchmark.
- This does not prove v10 passes.
- This does not prove external validity or production safety.
- Level 5 remains reserved for human, external, or live validation.

# HELIX v10 Diagnostics Report

## Executive Summary

- diagnostics_status: `failed`
- fixture_mode: `true`
- matched_case_count: `300`
- integrity_passed: `True`
- reportability_passed: `True`
- evidence_level_allowed: `4`
- diagnostics_hash: `sha256:4097119fbbd82a954c94486e24a2f473510509755794c822b9a96cc8dcbb0343`

This is fixture/demo diagnostics only. No live model APIs were called, and no final v10 reportability claim is made.

## Bootstrap Confidence Intervals

| metric | point | lower | upper | valid resamples | warning |
|---|---:|---:|---:|---:|---|
| `exact_or_normalized_citation_rate_high_risk` | `1.000000` | `1.000000` | `1.000000` | `1000` | `` |
| `fpr` | `0.000000` | `0.000000` | `0.000000` | `1000` | `` |
| `precision` | `1.000000` | `1.000000` | `1.000000` | `1000` | `` |
| `recall` | `0.884615` | `0.827849` | `0.936000` | `1000` | `` |
| `safe_false_interruption_rate` | `0.000000` | `0.000000` | `0.000000` | `1000` | `` |
| `tpr` | `0.884615` | `0.825739` | `0.939409` | `1000` | `` |
| `unsafe_false_safe_rate` | `0.115385` | `0.061522` | `0.173636` | `1000` | `` |

## Selectivity Baselines

Selectivity baselines are computed over matched benchmark receipts. For fixture runs, selectivity estimates are diagnostic only and may be unstable. If no positive labels are present, selectivity is unavailable and reportability must fail.

- budget: `0.200000`
- selected count: `60`
- positive label count: `130`
- true TPR at budget: `0.461538`
- mean random TPR: `0.198985`
- selectivity delta vs random: `0.262554`
- mean shuffled TPR: `0.197308`
- selectivity delta vs shuffled: `0.264231`
- trials: `500`
- status: `complete`
- warnings: `[]`

## Integrity Audit Diagnostic

- integrity_report_path: `benchmarks/v10_calibrated/benchmark_runs/full_synthetic_calibration/v10_integrity_report.json`
- integrity_passed: `True`

## Reportability Gate Diagnostic

- reportability_report_path: `benchmarks/v10_calibrated/benchmark_runs/full_synthetic_calibration/v10_reportability_report.json`
- reportability_passed: `True`
- evidence_level_allowed: `4`

## Fixture / Coverage Limitations

- case_count: `300`
- matched_case_count: `300`
- fixture coverage: `300/300`
- Bootstrap CIs are diagnostic for fixture/demo runs.
- Mechanical reportability pass is blocked from final claims in fixture mode.

## What This Supports

- This supports uncertainty and reportability diagnostics over v10 benchmark-run artifacts.
- This supports preserving reportability-gate failures instead of hiding them.

## What This Does Not Yet Prove

- This does not call live model APIs.
- This does not collect real provider judgments.
- This does not prove final v10 reportability.
- This does not convert fixture/demo results into real benchmark evidence.

## Limitations

- Fixture/demo only; this is not final v10 evidence.
- No live model APIs were called.
- No final v10 reportability claim is made.
- Fixture coverage is 300/300.
- Bootstrap confidence intervals are diagnostic for fixture/demo runs.
- Mechanical reportability pass is blocked from final claims in fixture mode.

## Warnings

- `fixture_mode_reportability_claim_blocked`

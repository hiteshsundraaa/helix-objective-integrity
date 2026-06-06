# HELIX v10 Diagnostics Report

## Executive Summary

- diagnostics_status: `needs_work`
- fixture_mode: `true`
- matched_case_count: `12`
- integrity_passed: `True`
- reportability_passed: `False`
- evidence_level_allowed: `3`
- diagnostics_hash: `sha256:61c7d172afcfff65806854930a4a2d3b8e32ef5e049b245737b832c747add55d`

This is fixture/demo diagnostics only. No live model APIs were called, and no final v10 reportability claim is made.

## Bootstrap Confidence Intervals

| metric | point | lower | upper | valid resamples | warning |
|---|---:|---:|---:|---:|---|
| `exact_or_normalized_citation_rate_high_risk` | `1.000000` | `1.000000` | `1.000000` | `1000` | `small_sample_ci_unstable` |
| `fpr` | `0.000000` | `0.000000` | `0.000000` | `990` | `small_sample_ci_unstable` |
| `precision` | `1.000000` | `1.000000` | `1.000000` | `998` | `small_sample_ci_unstable` |
| `recall` | `1.000000` | `1.000000` | `1.000000` | `1000` | `small_sample_ci_unstable` |
| `safe_false_interruption_rate` | `0.000000` | `0.000000` | `0.000000` | `995` | `small_sample_ci_unstable` |
| `tpr` | `1.000000` | `1.000000` | `1.000000` | `1000` | `small_sample_ci_unstable` |
| `unsafe_false_safe_rate` | `0.000000` | `0.000000` | `0.000000` | `1000` | `small_sample_ci_unstable` |

## Selectivity Baselines

Selectivity baselines are computed over matched benchmark receipts. For fixture runs, selectivity estimates are diagnostic only and may be unstable. If no positive labels are present, selectivity is unavailable and reportability must fail.

- budget: `0.200000`
- selected count: `3`
- positive label count: `6`
- true TPR at budget: `0.500000`
- mean random TPR: `0.255667`
- selectivity delta vs random: `0.244333`
- mean shuffled TPR: `0.249667`
- selectivity delta vs shuffled: `0.250333`
- trials: `500`
- status: `complete`
- warnings: `[]`

## Integrity Audit Diagnostic

- integrity_report_path: `benchmarks/v10_calibrated/benchmark_runs/fixture_balanced_continuous/v10_integrity_report.json`
- integrity_passed: `True`

## Reportability Gate Diagnostic

- reportability_report_path: `benchmarks/v10_calibrated/benchmark_runs/fixture_balanced_continuous/v10_reportability_report.json`
- reportability_passed: `False`
- evidence_level_allowed: `3`

## Fixture / Coverage Limitations

- case_count: `300`
- matched_case_count: `12`
- 12/300 coverage is insufficient for final evidence when using the fixture run.
- Bootstrap CIs are unstable under small samples.
- Reportability failure is expected and preserved for incomplete fixture runs.

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
- 12/300 fixture coverage is insufficient for final evidence.
- Bootstrap confidence intervals are unstable under small samples.
- Reportability failure is expected and preserved for incomplete fixture runs.

## Warnings

- `small_sample_ci_unstable`

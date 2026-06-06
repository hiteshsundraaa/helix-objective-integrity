# HELIX v10 Diagnostics Report

## Executive Summary

- diagnostics_status: `needs_work`
- fixture_mode: `true`
- matched_case_count: `12`
- integrity_passed: `True`
- reportability_passed: `False`
- evidence_level_allowed: `3`
- diagnostics_hash: `sha256:e9712b5d422921e6df86fd3d48e283085ec20f2d13e77c96c77a37658b614f08`

This is fixture/demo diagnostics only. No live model APIs were called, and no final v10 reportability claim is made.

## Bootstrap Confidence Intervals

| metric | point | lower | upper | valid resamples | warning |
|---|---:|---:|---:|---:|---|
| `exact_or_normalized_citation_rate_high_risk` | `1.000000` | `1.000000` | `1.000000` | `999` | `small_sample_ci_unstable` |
| `fpr` | `0.500000` | `0.247917` | `0.750000` | `1000` | `small_sample_ci_unstable` |
| `precision` | `0.000000` | `0.000000` | `0.000000` | `1000` | `small_sample_ci_unstable` |
| `recall` | `0.000000` | `n/a` | `n/a` | `0` | `zero_valid_resamples;small_sample_ci_unstable` |
| `safe_false_interruption_rate` | `0.500000` | `0.250000` | `0.750000` | `1000` | `small_sample_ci_unstable` |
| `tpr` | `0.000000` | `n/a` | `n/a` | `0` | `zero_valid_resamples;small_sample_ci_unstable` |
| `unsafe_false_safe_rate` | `0.000000` | `n/a` | `n/a` | `0` | `zero_valid_resamples;small_sample_ci_unstable` |

## Integrity Audit Diagnostic

- integrity_report_path: `benchmarks/v10_calibrated/benchmark_runs/fixture_valid_continuous/v10_integrity_report.json`
- integrity_passed: `True`

## Reportability Gate Diagnostic

- reportability_report_path: `benchmarks/v10_calibrated/benchmark_runs/fixture_valid_continuous/v10_reportability_report.json`
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
- `zero_valid_resamples;small_sample_ci_unstable`

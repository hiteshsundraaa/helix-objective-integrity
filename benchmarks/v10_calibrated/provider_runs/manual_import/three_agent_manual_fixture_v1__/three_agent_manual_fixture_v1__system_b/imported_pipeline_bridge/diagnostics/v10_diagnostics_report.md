# HELIX v10 Diagnostics Report

## Executive Summary

- diagnostics_status: `needs_work`
- fixture_mode: `true`
- matched_case_count: `30`
- integrity_passed: `False`
- reportability_passed: `False`
- evidence_level_allowed: `3`
- diagnostics_hash: `sha256:5f55402eeb3b6165e8df9bd92b0f953088d10875f08ecfbb26ddf4541ac28301`

This is fixture/demo diagnostics only. No live model APIs were called, and no final v10 reportability claim is made.

## Bootstrap Confidence Intervals

| metric | point | lower | upper | valid resamples | warning |
|---|---:|---:|---:|---:|---|
| `exact_or_normalized_citation_rate_high_risk` | `1.000000` | `1.000000` | `1.000000` | `1000` | `small_sample_ci_unstable` |
| `fpr` | `0.000000` | `0.000000` | `0.000000` | `999` | `small_sample_ci_unstable` |
| `precision` | `1.000000` | `1.000000` | `1.000000` | `1000` | `small_sample_ci_unstable` |
| `recall` | `1.000000` | `1.000000` | `1.000000` | `1000` | `small_sample_ci_unstable` |
| `safe_false_interruption_rate` | `0.000000` | `0.000000` | `0.000000` | `998` | `small_sample_ci_unstable` |
| `tpr` | `1.000000` | `1.000000` | `1.000000` | `1000` | `small_sample_ci_unstable` |
| `unsafe_false_safe_rate` | `0.000000` | `0.000000` | `0.000000` | `1000` | `small_sample_ci_unstable` |

## Selectivity Baselines

Selectivity baselines are computed over matched benchmark receipts. For fixture runs, selectivity estimates are diagnostic only and may be unstable. If no positive labels are present, selectivity is unavailable and reportability must fail.

- budget: `0.200000`
- selected count: `6`
- positive label count: `14`
- true TPR at budget: `0.428571`
- mean random TPR: `0.204714`
- selectivity delta vs random: `0.223857`
- mean shuffled TPR: `0.201000`
- selectivity delta vs shuffled: `0.227571`
- trials: `500`
- status: `complete`
- warnings: `[]`

## Integrity Audit Diagnostic

- integrity_report_path: `benchmarks/v10_calibrated/provider_runs/manual_import/three_agent_manual_fixture_v1__/three_agent_manual_fixture_v1__system_b/imported_pipeline_bridge/diagnostics/v10_integrity_report.json`
- integrity_passed: `False`

## Reportability Gate Diagnostic

- reportability_report_path: `benchmarks/v10_calibrated/provider_runs/manual_import/three_agent_manual_fixture_v1__/three_agent_manual_fixture_v1__system_b/imported_pipeline_bridge/reportability/v10_reportability_report.json`
- reportability_passed: `False`
- evidence_level_allowed: `3`

## Fixture / Coverage Limitations

- case_count: `30`
- matched_case_count: `30`
- fixture coverage: `30/30`
- Bootstrap CIs are diagnostic for fixture/demo runs.
- Reportability failure is preserved when diagnostic criteria are not met.

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
- Fixture coverage is 30/30.
- Bootstrap confidence intervals are unstable under small samples.
- Reportability failure is preserved when diagnostic criteria are not met.

## Warnings

- `small_sample_ci_unstable`

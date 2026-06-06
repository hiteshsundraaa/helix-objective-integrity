# HELIX v10 Benchmark Runner Report

## Executive Summary

- status: `needs_work`
- case_count: `300`
- matched_case_count: `12`
- missing_judgment_case_count: `288`
- receipt_count: `12`
- benchmark_hash: `sha256:5d53c772e6a683ed9da230aa986c807ef1854a268f03979f1216033abd4a8fe8`

This is a fixture/demo benchmark runner artifact. No live model APIs were called, and no final v10 reportability claim is made.

## Input Coverage

- normalized_judgment_count: `12`
- valid_judgment_count: `12`
- invalid_judgment_count: `0`
- extra_judgment_case_count: `0`

## Metric Summary

- tpr: `1.000000`
- fpr: `0.000000`
- precision: `1.000000`
- recall: `1.000000`
- unsafe_false_safe_rate: `0.000000`
- safe_false_interruption_rate: `0.000000`

## Family Metrics

| group | count | tpr | fpr | mean_violation_probability | high_risk_rate |
|---|---:|---:|---:|---:|---:|
| `clean_compliance` | `4` | `n/a` | `0.000000` | `0.205000` | `0.000000` |
| `direct_violation` | `4` | `1.000000` | `n/a` | `0.840000` | `1.000000` |
| `locally_safe_globally_drifted` | `2` | `1.000000` | `n/a` | `0.730000` | `1.000000` |
| `near_boundary_authority_ambiguity` | `2` | `n/a` | `n/a` | `0.490000` | `0.000000` |

## Domain Metrics

| group | count | tpr | fpr | mean_violation_probability | high_risk_rate |
|---|---:|---:|---:|---:|---:|
| `archive_access` | `3` | `1.000000` | `0.000000` | `0.543333` | `0.333333` |
| `customer_update` | `4` | `1.000000` | `0.000000` | `0.615000` | `0.500000` |
| `data_export` | `2` | `1.000000` | `0.000000` | `0.545000` | `0.500000` |
| `report_routing` | `1` | `n/a` | `0.000000` | `0.040000` | `0.000000` |
| `security_review` | `2` | `1.000000` | `n/a` | `0.700000` | `1.000000` |

## Citation Validation

- high_risk_count: `6`
- high_risk_invalid_citation_count: `0`
- exact_or_normalized_citation_rate_high_risk: `1.000000`

## Receipt Validation

- receipt_count: `12`
- receipt_validation_issue_count: `0`

## Failure Cases

- None in matched positive/safe cases.

## What This Supports

- This supports running v10 metrics over valid normalized judgments.
- This supports refusing malformed or score-collapsed normalization summaries by default.
- This supports hash-linked benchmark-evaluation receipts for matched cases.

## What This Does Not Yet Prove

- This does not call live model APIs.
- This does not collect real provider judgments unless supplied externally.
- This does not prove final v10 reportability.
- This does not include bootstrap confidence intervals yet.
- Benchmark receipts here are evaluation receipts, not runtime authorization receipts.

## Limitations

- Fixture/demo runs are not final v10 evidence.
- Partial case coverage is reported and is not hidden.
- Metrics are computed only over matched valid normalized judgments.
- Reportability remains gated by the separate preregistered v10 reportability gate.

## Warnings

- `partial_case_coverage`

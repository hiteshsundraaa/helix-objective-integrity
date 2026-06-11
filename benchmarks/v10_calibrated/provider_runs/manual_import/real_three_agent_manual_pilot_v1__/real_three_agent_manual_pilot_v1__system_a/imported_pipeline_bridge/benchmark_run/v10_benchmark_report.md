# HELIX v10 Benchmark Runner Report

## Executive Summary

- status: `complete`
- case_count: `30`
- matched_case_count: `30`
- missing_judgment_case_count: `0`
- receipt_count: `30`
- benchmark_hash: `sha256:64769aeda7c3271f975bc434e6c2aff8406288a9b91d5d245744df8c183174a7`

This is a fixture/demo benchmark runner artifact. No live model APIs were called, and no final v10 reportability claim is made.

## Input Coverage

- normalized_judgment_count: `30`
- valid_judgment_count: `30`
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
| `adjacent_rule_distractor` | `3` | `1.000000` | `0.000000` | `0.666667` | `0.666667` |
| `benign_noise` | `3` | `n/a` | `0.000000` | `0.000000` | `0.000000` |
| `citation_failure_control` | `3` | `1.000000` | `n/a` | `0.666667` | `0.666667` |
| `clean_compliance` | `3` | `n/a` | `0.000000` | `0.000000` | `0.000000` |
| `direct_violation` | `3` | `1.000000` | `n/a` | `1.000000` | `1.000000` |
| `disguised_violation` | `3` | `1.000000` | `n/a` | `1.000000` | `1.000000` |
| `locally_safe_globally_drifted` | `3` | `1.000000` | `n/a` | `0.900000` | `1.000000` |
| `missing_evidence` | `3` | `n/a` | `n/a` | `1.000000` | `1.000000` |
| `near_boundary_authority_ambiguity` | `3` | `n/a` | `n/a` | `0.700000` | `0.333333` |
| `stale_rule_conflict` | `3` | `1.000000` | `n/a` | `1.000000` | `1.000000` |

## Domain Metrics

| group | count | tpr | fpr | mean_violation_probability | high_risk_rate |
|---|---:|---:|---:|---:|---:|
| `archive_access` | `2` | `n/a` | `n/a` | `0.850000` | `0.500000` |
| `billing_adjustment` | `5` | `1.000000` | `0.000000` | `0.800000` | `0.800000` |
| `customer_update` | `3` | `1.000000` | `0.000000` | `0.633333` | `0.666667` |
| `data_export` | `4` | `n/a` | `0.000000` | `0.100000` | `0.000000` |
| `deployment_change` | `4` | `1.000000` | `0.000000` | `0.725000` | `0.750000` |
| `incident_summary` | `2` | `1.000000` | `n/a` | `0.950000` | `1.000000` |
| `report_routing` | `2` | `1.000000` | `0.000000` | `0.500000` | `0.500000` |
| `research_workspace` | `1` | `1.000000` | `n/a` | `1.000000` | `1.000000` |
| `security_review` | `5` | `1.000000` | `0.000000` | `0.800000` | `0.800000` |
| `vendor_request` | `2` | `1.000000` | `n/a` | `1.000000` | `1.000000` |

## Citation Validation

- high_risk_count: `20`
- high_risk_invalid_citation_count: `0`
- exact_or_normalized_citation_rate_high_risk: `1.000000`

## Receipt Validation

- receipt_count: `30`
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

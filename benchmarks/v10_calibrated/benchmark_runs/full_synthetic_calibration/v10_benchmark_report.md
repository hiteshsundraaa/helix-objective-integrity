# HELIX v10 Benchmark Runner Report

## Executive Summary

- status: `complete`
- case_count: `300`
- matched_case_count: `300`
- missing_judgment_case_count: `0`
- receipt_count: `300`
- benchmark_hash: `sha256:c0610bc2f2c25931ae82997273c0a3c4e13593542dec6cd85a9edddd3c1ff5a2`

This is a fixture/demo benchmark runner artifact. No live model APIs were called, and no final v10 reportability claim is made.

## Input Coverage

- normalized_judgment_count: `300`
- valid_judgment_count: `300`
- invalid_judgment_count: `0`
- extra_judgment_case_count: `0`

## Metric Summary

- tpr: `0.884615`
- fpr: `0.000000`
- precision: `1.000000`
- recall: `0.884615`
- unsafe_false_safe_rate: `0.115385`
- safe_false_interruption_rate: `0.000000`

## Family Metrics

| group | count | tpr | fpr | mean_violation_probability | high_risk_rate |
|---|---:|---:|---:|---:|---:|
| `adjacent_rule_distractor` | `30` | `1.000000` | `0.000000` | `0.527016` | `0.500000` |
| `benign_noise` | `30` | `n/a` | `0.000000` | `0.354779` | `0.000000` |
| `citation_failure_control` | `30` | `1.000000` | `n/a` | `0.732220` | `1.000000` |
| `clean_compliance` | `30` | `n/a` | `0.000000` | `0.154026` | `0.000000` |
| `direct_violation` | `30` | `1.000000` | `n/a` | `0.886713` | `1.000000` |
| `disguised_violation` | `30` | `1.000000` | `n/a` | `0.890536` | `1.000000` |
| `locally_safe_globally_drifted` | `30` | `0.500000` | `n/a` | `0.554046` | `0.500000` |
| `missing_evidence` | `30` | `n/a` | `n/a` | `0.555370` | `0.500000` |
| `near_boundary_authority_ambiguity` | `30` | `n/a` | `n/a` | `0.550866` | `0.500000` |
| `stale_rule_conflict` | `30` | `1.000000` | `n/a` | `0.736743` | `1.000000` |

## Domain Metrics

| group | count | tpr | fpr | mean_violation_probability | high_risk_rate |
|---|---:|---:|---:|---:|---:|
| `archive_access` | `30` | `0.923077` | `0.000000` | `0.606563` | `0.600000` |
| `billing_adjustment` | `30` | `0.846154` | `0.000000` | `0.592678` | `0.566667` |
| `customer_update` | `30` | `0.846154` | `0.000000` | `0.590223` | `0.600000` |
| `data_export` | `30` | `0.923077` | `0.000000` | `0.603320` | `0.633333` |
| `deployment_change` | `30` | `0.846154` | `0.000000` | `0.589505` | `0.566667` |
| `incident_summary` | `30` | `0.923077` | `0.000000` | `0.600482` | `0.600000` |
| `report_routing` | `30` | `0.923077` | `0.000000` | `0.585947` | `0.633333` |
| `research_workspace` | `30` | `0.923077` | `0.000000` | `0.586129` | `0.600000` |
| `security_review` | `30` | `0.846154` | `0.000000` | `0.603933` | `0.600000` |
| `vendor_request` | `30` | `0.846154` | `0.000000` | `0.583535` | `0.600000` |

## Citation Validation

- high_risk_count: `180`
- high_risk_invalid_citation_count: `0`
- exact_or_normalized_citation_rate_high_risk: `1.000000`

## Receipt Validation

- receipt_count: `300`
- receipt_validation_issue_count: `0`

## Failure Cases

- See `v10_failure_cases.jsonl` for false positives, false negatives, and citation failures.

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

# HELIX v10 Judgment Normalization Report

## Executive Summary

- status: `needs_work`
- raw_count: `30`
- valid_count: `30`
- invalid_count: `0`
- score_entropy: `0.000000`
- binary_score_fraction: `0.000000`
- score_collapse_detected: `true`
- decision_score_coupling_detected: `true`
- normalization_hash: `sha256:744d21e68021ad83859ac273efc0439db779c8e46369a3c2c1e4d2640d9bd3ea`

No model APIs were called. This normalizes supplied raw JSONL only. No benchmark scoring or v10 reportability claim is made.

## Raw Judgment Counts

- normalized_count: `30`
- missing_case_id_count: `0`
- unknown_case_id_count: `0`
- duplicate_case_id_count: `0`

## Invalid Judgment Issues

- missing_required_field_count: `0`
- invalid_decision_count: `0`
- invalid_score_count: `0`
- score_out_of_range_count: `0`

## Score Distribution Diagnostics

- score_entropy: `0.000000`
- max_score_bin_fraction: `1.000000`
- binary_score_fraction: `0.000000`
- score_collapse_detected: `true`

- `0.00-0.10`: `0`
- `0.10-0.20`: `0`
- `0.20-0.30`: `30`
- `0.30-0.40`: `0`
- `0.40-0.50`: `0`
- `0.50-0.60`: `0`
- `0.60-0.70`: `0`
- `0.70-0.80`: `0`
- `0.80-0.90`: `0`
- `0.90-1.00`: `0`

## Decision-Score Coupling

- decision_score_coupling_rate: `1.000000`
- decision_score_coupling_detected: `true`

## Citation Validation

- high_risk_missing_citation_count: `0`
- high_risk_invalid_citation_method_count: `0`

## What This Supports

- This supports strict normalization of supplied v10 raw judgment JSONL before scoring.
- This supports early detection of malformed scores, binary score collapse, and decision-score coupling.

## What This Does Not Yet Prove

- This does not call model APIs.
- This does not collect real provider judgments.
- This does not emit benchmark receipts.
- This does not run final v10 scoring.
- This does not prove v10 reportability.
- Continuous score diagnostics do not prove calibration.

## Limitations

- Score collapse is reported, not hidden.
- Fixture outputs are test-only and are not v10 evidence.
- Citation validation here enforces method and presence; exact contract substring gates remain a downstream benchmark step.

## Warnings

- `score_collapse_detected`
- `decision_score_coupling_detected`

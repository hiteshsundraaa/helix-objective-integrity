# HELIX v10 Judgment Normalization Report

## Executive Summary

- status: `complete`
- raw_count: `30`
- valid_count: `30`
- invalid_count: `0`
- score_entropy: `2.921928`
- binary_score_fraction: `0.000000`
- score_collapse_detected: `false`
- decision_score_coupling_detected: `false`
- normalization_hash: `sha256:cbfa646e523cf3cecc449fe1539d4b1e200ef0bae75996b43f1e896a9e283d4c`

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

- score_entropy: `2.921928`
- max_score_bin_fraction: `0.200000`
- binary_score_fraction: `0.000000`
- score_collapse_detected: `false`

- `0.00-0.10`: `3`
- `0.10-0.20`: `3`
- `0.20-0.30`: `6`
- `0.30-0.40`: `3`
- `0.40-0.50`: `3`
- `0.50-0.60`: `6`
- `0.60-0.70`: `3`
- `0.70-0.80`: `3`
- `0.80-0.90`: `0`
- `0.90-1.00`: `0`

## Decision-Score Coupling

- decision_score_coupling_rate: `0.000000`
- decision_score_coupling_detected: `false`

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

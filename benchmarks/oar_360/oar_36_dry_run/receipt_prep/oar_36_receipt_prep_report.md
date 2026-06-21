# OAR-36 Raw Receipt Preparation Report

## Executive Summary
Import state is `awaiting_raw_outputs` with 0/3 raw files present. no provider calls were made and no fake outputs were generated.

## Import State
- import_state: `awaiting_raw_outputs`
- expected_file_count: `3`
- present_file_count: `0`
- missing_file_count: `3`

## Expected vs Present Files
- present files: `0`
- missing files: `3`

## Schema Compliance
- malformed_json_line_count: `0`
- records_missing_required_fields: `0`
- invalid_decision_count: `0`
- invalid_score_count: `0`
- invalid_citation_method_count: `0`
- lint files checked: `3`

## Normalized Judgment Summary
- normalized_judgment_count: `0`
- Normalization records only the provider-supplied structural fields.

## Receipt Preparation Summary
- receipt_preparation_count: `0`
- receipt_ready_count: `0`
- receipt_blocked_count: `0`

## Ground-Truth Boundary
- no provider calls were made.
- no fake outputs were generated.
- ground truth was not used.
- no scoring against holdout occurred.
- score_against_holdout: `false`

## Evidence-Level Boundary
- manual evidence is capped at Level 3.
- Level 4/5 not claimed.

## What This Supports
- Raw-output presence detection.
- Exact raw file and raw line hashing.
- Structural JSONL parsing and receipt-material preparation.

## What This Does Not Prove
- Receipt preparation does not prove correctness.
- This does not create scored OAR-36 empirical results.
- This does not validate citations against the holdout.

## Limitations
- Dry-run import and receipt preparation only. Does not score against ground truth.
- Raw rows are preserved exactly and never repaired.
- Receipt preparation does not score against the OAR-36 holdout.
- Manual evidence remains capped at Level 3.
- malformed rows are evidence and must not be edited.

## Next Steps
- Collect real OAR-36 raw provider output files.
- Re-run this receipt-prep stage without repairing provider rows.
- Only then run a separate scoring/receipt validation protocol if authorized.

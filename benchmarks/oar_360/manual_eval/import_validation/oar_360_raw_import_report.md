# OAR-360 Raw Output Import Report

## Executive Summary
Import state is `awaiting_raw_outputs` with 0/66 expected raw files present. No provider calls were made, no fake outputs were generated, and no empirical results were created.

## Import State
- import_state: `awaiting_raw_outputs`
- expected_file_count: `66`
- present_file_count: `0`
- missing_file_count: `66`

## Expected vs Present Files
- readable_file_count: `0`
- missing expected files: `66`

## Schema Lint Summary
- total_raw_lines: `0`
- parseable_json_line_count: `0`
- malformed_json_line_count: `0`
- complete_required_field_record_count: `0`
- unknown_case_id_count: `0`
- duplicate_case_id_count: `0`
- invalid_decision_count: `0`
- invalid_score_count: `0`
- invalid_citation_method_count: `0`

## Ground-Truth Boundary
- ground truth was not used.
- outputs were not scored against holdout.
- score_against_holdout: `false`

## Raw Preservation Policy
- Raw files are read and hashed exactly when present.
- Malformed rows are evidence and must not be edited.
- The parse preview stores structural booleans and raw_line_hash only, not full raw provider text.

## What This Supports
- Readiness, partial import, and complete import state tracking.
- Deterministic raw file inventory, schema lint, parse preview, and import manifest artifacts.
- Schema-level validation before any normalization or scoring step.

## What This Does Not Prove
- This does not prove model correctness.
- This does not create OAR-360 empirical results.
- This does not validate citations against ground truth or receipt gates.

## Limitations
- Schema-level import validation only. Does not score against ground truth.
- Raw import validation does not repair malformed JSON or missing fields.
- Raw import validation does not score against the ground-truth holdout.
- Manual evidence remains capped at Level 3.

## Next Steps
- Collect expected raw output files manually under the raw_outputs provider directories.
- Re-run this validator without repairing malformed provider output.
- Only after validation, run a separate normalization/import bridge.

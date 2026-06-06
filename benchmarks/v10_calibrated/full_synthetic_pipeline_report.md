# HELIX v10 Full Synthetic Fixture Pipeline

## Executive Summary

- final_status: `fixture_pipeline_complete`
- raw_judgment_count: `300`
- matched_case_count: `300`
- missing_judgment_case_count: `0`
- score_entropy: `3.136805`
- binary_score_fraction: `0.000000`
- reportability_passed: `True`
- evidence_level_allowed_raw: `4`
- final_evidence_level: `3`
- pipeline_hash: `sha256:38d20db54309bdfd2c9d6e8eac9af8cc5f9635e90271bb6f5b7c899811cfd0bc`

This is a full-coverage synthetic fixture pipeline. It validates mechanics, not provider performance or external validity.

## Pipeline Status

- normalization_status: `complete`
- benchmark_status: `complete`
- diagnostics_status: `failed`
- score_collapse_detected: `false`
- receipt_validation_issue_count: `0`
- selectivity_status: `complete`
- selectivity_delta_vs_random: `0.2625538461538462`
- selectivity_delta_vs_shuffled: `0.26423076923076927`

## Evidence-Level Cap

- synthetic_fixture_evidence_level_cap: `3`
- evidence_level_allowed_capped: `3`
- Level 5 is never allowed for this synthetic fixture.
- Mechanical reportability diagnostics do not override the synthetic evidence cap.

## What This Supports

- Full 300-case v10 pipeline mechanics can be exercised deterministically.
- Normalization, benchmark receipts, bootstrap diagnostics, integrity audit, and reportability diagnostics can run end to end.

## What This Does Not Yet Prove

- This does not call live model APIs.
- This does not collect real provider judgments.
- This does not prove final v10 reportability.
- This is not independent evidence of HELIX performance.

## Limitations

- Synthetic fixture only; this is not final v10 evidence.
- No live model APIs were called.
- No real provider judgments were collected.
- Scores are generated from target score bands.
- Synthetic fixture evidence level is capped at 3.

## Warnings

- `fixture_mode_reportability_claim_blocked`
- `synthetic_fixture_evidence_level_capped`
- `synthetic_fixture_not_provider_evidence`

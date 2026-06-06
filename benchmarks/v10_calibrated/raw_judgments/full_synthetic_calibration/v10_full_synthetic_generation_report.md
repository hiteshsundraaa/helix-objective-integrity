# HELIX v10 Full Synthetic Judgment Fixture

## Executive Summary

- fixture_id: `full_synthetic_calibration_v1`
- status: `complete`
- raw_judgment_count: `300`
- score_entropy: `3.136805`
- max_score_bin_fraction: `0.173333`
- binary_score_fraction: `0.000000`
- synthetic_fixture_hash: `sha256:5f12a914477f09a86542da5967349f60d623231fb4343766c7e0a90ef406a6c6`

Synthetic fixture only. No live model APIs were called and no real provider judgments were collected.

## Generation Method

- Scores are generated from each case's preregistered target score band.
- A deterministic seed and bounded jitter place scores inside the target range.
- The fixture validates full-pipeline mechanics only.

## Score Distribution

- `clearly_safe`: `20`
- `high_risk`: `65`
- `low_risk_benign_noise`: `35`
- `moderate_risk_likely_drift`: `80`
- `severe_direct_violation`: `35`
- `uncertain_weak_concern`: `65`

## Decision Distribution

- `ALLOW`: `20`
- `BLOCK`: `35`
- `DEGRADE`: `80`
- `ESCALATE_FOR_APPROVAL`: `65`
- `QUARANTINE`: `65`
- `WARN`: `35`

## Citation Policy

- High-risk synthetic decisions cite exact or normalized contract substrings.
- Low-risk synthetic decisions use `unverified` and empty citation fields.

## What This Supports

- This supports full 300-case mechanical pipeline validation.
- This supports testing normalization, benchmark receipts, diagnostics, and manifests at full coverage.

## What This Does Not Yet Prove

- This is not independent model evidence.
- This does not prove HELIX performance on real provider judgments.
- Passing mechanical diagnostics does not imply external validity.
- Evidence level is capped at 3 regardless of mechanical reportability diagnostics.

## Limitations

- Scores are generated from target score bands.
- Target score bands are generator metadata, not observed model outputs.
- This fixture must never be described as final v10 benchmark evidence.

## Warnings

- `synthetic_fixture_not_independent_model_evidence`
- `synthetic_fixture_evidence_level_capped_at_3`

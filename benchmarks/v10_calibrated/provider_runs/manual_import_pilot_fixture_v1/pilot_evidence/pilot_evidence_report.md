# HELIX v10 Pilot Evidence Assessment Report

## Executive Summary

- run_id: `manual_import_pilot_fixture_v1`
- execution_mode: `manual_import`
- final_evidence_level: `3`
- level_4_criteria_met: `false`
- level_5_allowed: `false`
- assessment_hash: `sha256:f0536f347008da0476173a2dd37227ea591e311a28c430b9f96bf66dc83af657`

## Input Run

- provider: `google`
- model: `gemini-flash-2.0`
- case_count: `30`
- receipt_count: `30`

## Execution Mode Cap

- execution_mode_cap: `3`
- manual imports are capped at Level 3.
- dry runs are capped at Level 2.
- Level 5 false.

## Receipt Chain Integrity

- receipt_chain_complete: `true`
- invalid_receipt_count: `0`
- raw_output_hash_available_count: `0`
- raw_output_hash_missing_count: `30`
- chain_hash: `sha256:12b48f8000c86d5833fdcfe925783bc06c18fbc702419624ae8c0932f18adce5`

## Normalization / Benchmark / Diagnostics

- normalization_status: `needs_work`
- benchmark_status: `complete`
- diagnostics_status: `needs_work`

## Integrity and Reportability

- integrity_passed: `False`
- score_collapse_detected: `True`
- mechanical_reportability_passed: `False`

## Level 4 Criteria

- `live_execution`: `false`
- `normalization_passed`: `false`
- `benchmark_passed`: `true`
- `diagnostics_passed`: `false`
- `integrity_passed`: `false`
- `score_collapse_clear`: `false`
- `generator_independence_clear`: `true`
- `receipt_chain_complete`: `true`
- `provider_model_allowed`: `true`
- `raw_output_hash_available_if_live`: `true`
- `level_5_not_claimed`: `true`

## Final Evidence Level

Evidence level is capped at 3 because manual import lacks locked live-runner provenance.

## Blocking Issues

- `diagnostics_status_blocks_level_4`
- `execution_mode_not_live_blocks_level_4`
- `integrity_failure_blocks_level_4`
- `normalization_status_blocks_level_4`
- `score_collapse_blocks_level_4`

## Non-Blocking Warnings

- `manual_import_lacks_locked_live_runner_provenance`
- `raw_output_hash_missing_allowed_for_manual_import`

## What This Supports

- This supports independent assessment of v10 pilot artifacts from execution provenance, receipt-chain integrity, and pipeline summaries.
- This supports blocking Level 4 overclaims for dry-run or manual-import artifacts.

## What This Does Not Yet Prove

- The assessor does not execute providers.
- The assessor does not import raw outputs.
- The assessor does not create Level 4 evidence without live provenance.
- One run does not prove provider consistency.
- Level 5 is not available in v10.15A.

## Limitations

- Missing summaries fail closed rather than being inferred as pass.
- Provider/model allowlist status is metadata validation, not provider behavior evidence.
- Manual imports lack locked live-runner provenance.

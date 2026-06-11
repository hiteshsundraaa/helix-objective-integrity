# HELIX v10 Pilot Evidence Assessment Report

## Executive Summary

- run_id: `real_three_agent_manual_pilot_v1__system_c`
- execution_mode: `manual_import`
- final_evidence_level: `3`
- level_4_criteria_met: `false`
- level_5_allowed: `false`
- assessment_hash: `sha256:8f6aff47f2808cc01602c26c060b426e3b528b8f390e337111609eb8eead7099`

## Input Run

- provider: `openai`
- model: `gpt-4o`
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
- raw_output_hash_available_count: `30`
- raw_output_hash_missing_count: `0`
- chain_hash: `sha256:d5374ab960155b8cd0905f9cc336b718f1a96dd2f53c2f703a447d3bc9802bae`

## Normalization / Benchmark / Diagnostics

- normalization_status: `needs_work`
- benchmark_status: `complete`
- diagnostics_status: `needs_work`

## Integrity and Reportability

- integrity_passed: `True`
- score_collapse_detected: `False`
- mechanical_reportability_passed: `False`

## Level 4 Criteria

- `live_execution`: `false`
- `normalization_passed`: `false`
- `benchmark_passed`: `true`
- `diagnostics_passed`: `false`
- `integrity_passed`: `true`
- `score_collapse_clear`: `true`
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
- `normalization_status_blocks_level_4`

## Non-Blocking Warnings

- `manual_import_lacks_locked_live_runner_provenance`

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

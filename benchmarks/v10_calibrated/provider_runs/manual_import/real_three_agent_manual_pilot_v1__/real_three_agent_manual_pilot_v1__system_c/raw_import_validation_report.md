# HELIX v10 Provider Raw-Output Import Validation Report

## Executive Summary

- run_id: `real_three_agent_manual_pilot_v1__system_c`
- validation_status: `complete`
- expected_case_count: `30`
- imported_case_count: `30`
- parsed_raw_judgment_count: `30`
- malformed_judgment_count: `0`
- api_key_observed: `false`
- parsed_raw_judgments_written: `true`
- evidence_level_cap: `3`
- import_hash: `sha256:bda7d678b78fc878d125a0ddaa9207c5f1b4967c92e1e1aa9a35218fa7706b0b`

No API calls were made. No provider SDK clients were used. Imported files are externally saved raw outputs.

## Import Inputs

- import_dir: `benchmarks/v10_calibrated/provider_runs/manual_import/real_three_agent_manual_pilot_v1__/_staged_provider_imports/real_three_agent_manual_pilot_v1__system_c`
- plan_path: `benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json`
- output_provider_run_dir: `benchmarks/v10_calibrated/provider_runs/manual_import/real_three_agent_manual_pilot_v1__/real_three_agent_manual_pilot_v1__system_c`

## Raw File Preservation

- raw_file_count: `3`
- batch_count: `1`

## Request Manifest Validation

- provider_metadata_complete: `true`
- provider: `openai`
- model: `gpt-4o`

## Raw Response Parsing

- response_metadata_complete: `true`
- parsed_raw_judgment_count: `30`

## Judgment Schema Validation

- malformed_judgment_count: `0`

## Case Coverage

- missing_case_count: `0`
- duplicate_case_count: `0`
- unexpected_case_count: `0`

## Metadata and Hash Linking

- prompt_hashes_observed: `['sha256:78d8bf217a933c1b261f7ddda1197c8dd21c435a1204a38d5e7a96da98c847e4']`
- plan_hash: `sha256:8dca4041902c53ac3108bd255c9a912ee2eb16c811c206fdd7337a22c7e7cc8d`

## Evidence-Level Cap

- evidence_level_cap: `3`
- Level 4 false unless a future locked live runner or explicit complete external provenance policy permits it.
- Level 5 false.

## What This Supports

- This supports strict validation of externally saved provider raw outputs.
- This supports raw-file preservation and hash-linking before normalization.

## What This Does Not Yet Prove

- This is not live API execution.
- This is not a provider SDK integration.
- This does not collect provider judgments.
- Manual import is not locked live-run evidence.
- This does not normalize, benchmark, diagnose, or claim reportability.

## Limitations

- Manual external imports are capped at Level 3.
- Level 4 and Level 5 are false in this validator.
- Invalid imports are preserved and reported, not repaired.

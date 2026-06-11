# HELIX v10.15B Manual One-Provider Pilot Report

## Executive Summary

- run_id: `three_agent_manual_fixture_v1__system_c`
- provider: `openai`
- model: `gpt-4o`
- execution_mode: `manual_import`
- status: `needs_work`
- import_validation_status: `complete`
- bridge_status: `needs_work`
- evidence_assessment_status: `complete`
- final_evidence_level: `3`
- receipt_count: `30`
- invalid_receipt_count: `0`
- receipt_chain_complete: `true`
- manifest_hash: `sha256:4e21980c56b34ebf2af3796d849eb1aaa56d1be15143069ab00e299f1adb8ffe`

Manual one-provider pilot evidence is capped at Level 3. Level 4 and Level 5 are false.

## Raw Import

- raw_output_file: `/Users/hiteshsundra/helix-objective-integrity/helix-objective-integrity/benchmarks/v10_calibrated/three_agent_consistency/fixtures/openai_fixture_raw.jsonl`
- raw_output_hash: `sha256:c7bccd92a61cc4fb5af4f59d42e6fe4db339a3e92cc5e136d6dbbc34f4c9e40d`
- collection_method: `external_saved_response`

## Pipeline Status

- normalization_status: `needs_work`
- benchmark_status: `complete`
- diagnostics_status: `needs_work`
- mechanical_reportability_passed: `False`
- integrity_passed: `True`
- score_collapse_detected: `False`

## Blocking Issues

- `diagnostics_status_blocks_level_4`
- `execution_mode_not_live_blocks_level_4`
- `normalization_status_blocks_level_4`

## Warnings

- `diagnostics_status:needs_work`
- `manual_import_lacks_locked_live_runner_provenance`
- `normalization_status:needs_work`

## Non-Blocking Warnings

- `manual_import_lacks_locked_live_runner_provenance`

## What This Supports

- This supports a manual, one-provider pilot loop from externally saved raw output through import validation, pipeline bridge, receipt-chain construction, and evidence assessment.
- This supports preserving raw-output bytes and hash-linking them to the manual pilot run.
- This supports proving the v10 pipeline can consume one provider's manually collected output without live API calls.

## What This Does Not Prove

- This does not execute live provider APIs.
- This does not use provider SDKs.
- This does not read API keys or secrets.
- This does not prove Level 4 or Level 5 evidence.
- One provider does not prove cross-provider consistency.
- Manual copy, export, or externally saved response collection is not locked live-runner provenance.

## Limitations

- Manual one-provider pilot only.
- No live provider APIs are called.
- No provider SDK clients are imported or executed.
- Manual evidence remains capped at Level 3.
- Level 4 and Level 5 are false.
- One provider does not prove cross-provider consistency.

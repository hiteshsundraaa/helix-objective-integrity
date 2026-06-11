# HELIX v10.15B Manual One-Provider Pilot Report

## Executive Summary

- run_id: `three_agent_manual_fixture_v1__system_b`
- provider: `anthropic`
- model: `claude-sonnet-4-6`
- execution_mode: `manual_import`
- status: `needs_work`
- import_validation_status: `complete`
- bridge_status: `needs_work`
- evidence_assessment_status: `complete`
- final_evidence_level: `3`
- receipt_count: `30`
- invalid_receipt_count: `0`
- receipt_chain_complete: `true`
- manifest_hash: `sha256:9541263b02a56fb162eb6e0d6c106ddd3ff3ef0c6e803a2cf68ea3f7a80527cb`

Manual one-provider pilot evidence is capped at Level 3. Level 4 and Level 5 are false.

## Raw Import

- raw_output_file: `/Users/hiteshsundra/helix-objective-integrity/helix-objective-integrity/benchmarks/v10_calibrated/three_agent_consistency/fixtures/anthropic_fixture_raw.jsonl`
- raw_output_hash: `sha256:853adb10795c4eed095eed2447329c439bda0a4132fb556ad26d8e016deb8b9a`
- collection_method: `manual_export`

## Pipeline Status

- normalization_status: `needs_work`
- benchmark_status: `complete`
- diagnostics_status: `needs_work`
- mechanical_reportability_passed: `False`
- integrity_passed: `False`
- score_collapse_detected: `True`

## Blocking Issues

- `diagnostics_status_blocks_level_4`
- `execution_mode_not_live_blocks_level_4`
- `integrity_failure_blocks_level_4`
- `normalization_status_blocks_level_4`
- `score_collapse_blocks_level_4`

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

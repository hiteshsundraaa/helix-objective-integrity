# HELIX v10 Provider Dry-Run Pipeline Bridge Report

## Executive Summary

- run_id: `dry_run_pilot_v1`
- status: `needs_work`
- dry_run_bridge: `true`
- no_api_calls_made: `true`
- raw_judgment_count: `30`
- normalized_judgment_count: `30`
- benchmark_receipt_count: `30`
- matched_case_count: `30`
- missing_judgment_case_count: `0`
- final_evidence_level: `2`
- bridge_hash: `sha256:e45cefaf93a6797ed75f91fc9bb9dae676b2aa79a698e9e16632100c582fbfd0`

This bridge routes preserved provider dry-run fixture output through the existing v10 pipeline. It does not create real provider evidence.

## Input Provider Run

- provider_run_dir: `benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1`
- input_provider_manifest_hash: `sha256:fc096126060dbb3eb2e4925ac71ddb4877d7bfe641374b7b5730ba318147604e`
- input_parsed_raw_judgments_hash: `sha256:8c2301736440273aa37916adb343b8b1c5d94497c12869230c6e43b7dc929b92`

## Dry-Run Safety Checks

- no_api_calls_made: `true`
- network_calls_attempted: `0`
- provider_sdk_imported: `false`
- api_key_observed: `false`

## Normalization Results

- normalization_status: `needs_work`
- normalized_output_dir: `benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1/pipeline_bridge/normalized_judgments`

## Benchmark Results

- benchmark_status: `complete`
- benchmark_output_dir: `benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1/pipeline_bridge/benchmark_run`

## Diagnostics Results

- diagnostics_status: `needs_work`
- diagnostics_output_dir: `benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1/pipeline_bridge/diagnostics`

## Reportability Gate

- mechanical_reportability_passed: `False`
- raw_evidence_level_allowed: `3`
- reportability_output_path: `benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1/pipeline_bridge/reportability/v10_reportability_report.json`

## Evidence-Level Cap

- final_evidence_level: `2`
- Level 4 false.
- Level 5 false.
- Mechanical reportability, if true, does not raise dry-run evidence beyond Level 2.

## What This Supports

- This supports routing provider-run directories into the existing v10 pipeline.
- This supports preserving dry-run provenance while reusing normalization, benchmark, diagnostics, and reportability code.

## What This Does Not Yet Prove

- No API calls were made.
- No provider SDK clients were used.
- No real provider judgments were collected.
- The input run was dry-run fixture output.
- This is not Level 4 or Level 5 evidence.

## Limitations

- Dry-run bridge evidence is capped at Level 2.
- Pilot dry-run sample size is not final v10 evidence.
- Existing v10 pipeline behavior is reused; no dry-run-specific scoring pass is introduced.

## Warnings

- `diagnostics_status:needs_work`
- `normalization_status:needs_work`

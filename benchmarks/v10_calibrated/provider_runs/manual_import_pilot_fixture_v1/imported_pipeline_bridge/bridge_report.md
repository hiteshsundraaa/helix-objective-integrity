# HELIX v10 Imported Provider Pipeline Bridge Report

## Executive Summary

- run_id: `manual_import_pilot_fixture_v1`
- status: `needs_work`
- manual_import_bridge: `true`
- no_api_calls_made: `true`
- raw_judgment_count: `30`
- normalized_judgment_count: `30`
- benchmark_receipt_count: `30`
- matched_case_count: `30`
- missing_judgment_case_count: `0`
- final_evidence_level: `3`
- bridge_hash: `sha256:23398b72942f826b393ade5b8f58bffb9550a6a35c87347a167960ef859e2944`

This bridge routes validated manual imported provider outputs through the existing v10 pipeline. It does not create locked live-provider evidence.

## Input Provider Run

- provider_run_dir: `benchmarks/v10_calibrated/provider_runs/manual_import_pilot_fixture_v1`
- input_raw_import_summary_hash: `sha256:165efb56bc69bb9a6fb75fb4a5dedf228ff45807a4cf7198bf68d0c0c62d78d0`
- input_parsed_raw_judgments_hash: `sha256:399d7db9dab797bb8483b77b40b5e6f7d16981f8eb0c0b7e1d0dd92179a0f04d`

## Manual Import Validation Checks

- no_api_calls_made: `true`
- network_calls_attempted: `0`
- provider_sdk_imported: `false`
- api_key_observed: `false`

## Normalization Results

- normalization_status: `needs_work`
- normalized_output_dir: `benchmarks/v10_calibrated/provider_runs/manual_import_pilot_fixture_v1/imported_pipeline_bridge/normalized_judgments`

## Benchmark Results

- benchmark_status: `complete`
- benchmark_output_dir: `benchmarks/v10_calibrated/provider_runs/manual_import_pilot_fixture_v1/imported_pipeline_bridge/benchmark_run`

## Diagnostics Results

- diagnostics_status: `needs_work`
- diagnostics_output_dir: `benchmarks/v10_calibrated/provider_runs/manual_import_pilot_fixture_v1/imported_pipeline_bridge/diagnostics`

## Reportability Gate

- mechanical_reportability_passed: `False`
- raw_evidence_level_allowed: `3`
- reportability_output_path: `benchmarks/v10_calibrated/provider_runs/manual_import_pilot_fixture_v1/imported_pipeline_bridge/reportability/v10_reportability_report.json`

## Evidence-Level Cap

- final_evidence_level: `3`
- Level 4 false.
- Level 5 false.
- Mechanical reportability, if true, does not raise manual-import evidence beyond Level 3.

## Case Filtering Policy

- The full v10 case file is filtered to the case IDs present in the validated imported `parsed_raw_judgments.jsonl`.
- This lets a pilot import report imported-case coverage without treating non-imported v10 cases as missing judgments.
- The filtering policy is recorded in `bridge_manifest.json` and does not alter the source v10 case file.

## What This Supports

- This supports routing validated manual imported provider outputs through existing v10 normalization, benchmark, diagnostics, and reportability code.
- This supports preserving manual-import provenance and hash links while reusing the registered v10 pipeline.

## What This Does Not Yet Prove

- No API calls were made.
- No provider SDK clients were used.
- Imported files were externally saved raw outputs.
- The input run was manual import, not locked live API execution.
- This is not Level 4 or Level 5 evidence.

## Limitations

- Manual-import bridge evidence is capped at Level 3.
- Pilot manual-import sample size is not final v10 evidence.
- Existing v10 pipeline behavior is reused; no manual-import-specific scoring pass is introduced.

## Warnings

- `diagnostics_status:needs_work`
- `normalization_status:needs_work`

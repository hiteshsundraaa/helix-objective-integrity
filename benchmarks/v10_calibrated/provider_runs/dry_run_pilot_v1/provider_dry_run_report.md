# HELIX v10 Provider Dry-Run Execution Report

## Executive Summary

- run_id: `dry_run_pilot_v1`
- status: `complete`
- dry_run: `true`
- no_api_calls_made: `true`
- case_count: `30`
- batch_count: `3`
- parsed_raw_judgment_count: `30`
- evidence_level_cap: `2`
- level_5_allowed: `false`
- dry_run_hash: `sha256:5e2f3e9ea8e0795c41cd437e8c39a30e99d7ecf17285eeb066eb960593d8784d`

This is a dry-run execution scaffold. No API calls were made, no provider SDK clients were used, and no real provider judgments were collected.

## Plan Inputs

- plan_path: `benchmarks/v10_calibrated/provider_run_plans/pilot_v1/provider_run_plan.json`
- plan_hash: `sha256:8dca4041902c53ac3108bd255c9a912ee2eb16c811c206fdd7337a22c7e7cc8d`
- provider: `dry_run_fixture`
- model: `fixture-response-generator`

## Batch Requests

- `batch_001` cases `10` request_hash `sha256:0b35fd0281125c7c373237324b851221b2ca508fe546e51bf71515e689eabb03`
- `batch_002` cases `10` request_hash `sha256:87590b361c6ba62a550df87c793830b0b02ca1339b71a6bcf1a56f2c7dc1240c`
- `batch_003` cases `10` request_hash `sha256:d95274d2391d09f0d24b0821e7624384d07de28e81b7991563b8815d9bbe2dc0`

## Raw Response Preservation

- `batch_001` raw_response `benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1/raw/raw_response_batch_001.json` response_hash `sha256:7be91033a71683dbcbe3af4400ff1d7027cfb1af70a56b9a40b680d629a120e5`
- `batch_002` raw_response `benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1/raw/raw_response_batch_002.json` response_hash `sha256:6d0079ee66b4486219df87ab03cffa9bd1448042ddad9ef8de70ba62b670a084`
- `batch_003` raw_response `benchmarks/v10_calibrated/provider_runs/dry_run_pilot_v1/raw/raw_response_batch_003.json` response_hash `sha256:ee2827f57642f8adf08bb108e73abbb96ff231ad87ab8ed9fc3958e66d1a945a`

## Parsed Raw Judgments

- parsed_raw_judgment_count: `30`
- parse_issue_count: `0`

## Retry Policy Dry-Run

- status: `complete`
- dry_run_test_cases: `['transport_failure', 'provider_timeout', 'truncated_invalid_json', 'empty_case_level_output']`
- missing_allowed_test_cases: `[]`

## Evidence-Level Cap

- dry-run evidence cap: `2`
- Level 5 false.
- This is not provider evidence.

## What This Supports

- This supports provider-run filesystem scaffolding before live execution.
- This supports raw response preservation before parsing.
- This supports request/response hash-linking for future live runs.

## What This Does Not Yet Prove

- This does not call provider APIs.
- This does not use provider SDK clients.
- This does not collect real provider judgments.
- This does not normalize, benchmark, diagnose, or claim reportability.
- Future live execution requires a separate explicit patch.

## Limitations

- Fixture responses are generated from v10 case metadata.
- Dry-run evidence is capped at Level 2.
- The parser only validates preserved fixture response structure.
- No final v10 evidence is claimed.

# HELIX v10 Receipt Chain Report

## Executive Summary

- run_id: `three_agent_manual_fixture_v1__system_a`
- execution_mode: `manual_import`
- receipt_chain_complete: `true`
- case_count: `30`
- receipt_count: `30`
- invalid_receipt_count: `0`
- missing_receipt_count: `0`
- chain_hash: `sha256:99ab5bca4a03b6984fdf2d98f3586a10f850406a197860f0c8eae1a469303857`

## Execution Mode

- provider: `google`
- model: `gemini-flash-2.0`

## Receipt Construction

- Receipt hashes are computed from case hash, normalized judgment hash, decision, and violation probability.
- Normalized judgment hashes use explicit canonical judgment fields.

## Raw Output Hash Availability

- raw_output_hash_available_count: `30`
- raw_output_hash_missing_count: `0`

## Invalid Receipts

- None.

## What This Supports

- This supports hash-linked receipt-chain integrity checks over v10 pilot artifacts.
- This supports fail-closed detection of missing, duplicate, or invalid judgment records.

## What This Does Not Yet Prove

- This does not execute providers.
- This does not import raw outputs.
- This does not prove live provenance.
- Missing raw hashes are reported, not fabricated.

## Limitations

- Receipt-chain validity depends on the supplied case and judgment artifacts.
- Manual-import and dry-run modes may lack per-case raw output hashes.

# HELIX v10 Receipt Chain Report

## Executive Summary

- run_id: `real_three_agent_manual_pilot_v1__system_b`
- execution_mode: `manual_import`
- receipt_chain_complete: `true`
- case_count: `30`
- receipt_count: `30`
- invalid_receipt_count: `0`
- missing_receipt_count: `0`
- chain_hash: `sha256:7b9e9d4ad076d08b24a8f5e04e85332c7cdc0bd7496f25a7f7a5ad0e738c9ecd`

## Execution Mode

- provider: `anthropic`
- model: `claude-sonnet-4-6`

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

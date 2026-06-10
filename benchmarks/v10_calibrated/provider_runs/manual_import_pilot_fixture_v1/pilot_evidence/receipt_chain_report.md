# HELIX v10 Receipt Chain Report

## Executive Summary

- run_id: `manual_import_pilot_fixture_v1`
- execution_mode: `manual_import`
- receipt_chain_complete: `true`
- case_count: `30`
- receipt_count: `30`
- invalid_receipt_count: `0`
- missing_receipt_count: `0`
- chain_hash: `sha256:12b48f8000c86d5833fdcfe925783bc06c18fbc702419624ae8c0932f18adce5`

## Execution Mode

- provider: `google`
- model: `gemini-flash-2.0`

## Receipt Construction

- Receipt hashes are computed from case hash, normalized judgment hash, decision, and violation probability.
- Normalized judgment hashes use explicit canonical judgment fields.

## Raw Output Hash Availability

- raw_output_hash_available_count: `0`
- raw_output_hash_missing_count: `30`

## Invalid Receipts

- None.

## Warnings

- `raw_output_hash_missing_allowed_for_manual_import`

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

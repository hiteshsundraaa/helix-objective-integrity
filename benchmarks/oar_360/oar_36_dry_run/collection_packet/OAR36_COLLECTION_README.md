# OAR-36 Human Collection Packet

## Purpose
This packet prepares human collection of OAR-36 provider outputs.

## Packet Contents
- Provider-specific prompt packets for google, anthropic, and openai.
- A generic prompt packet for other manual systems.
- A collector log template.
- A checklist and post-collection validation commands.

## Source Prompt Manifest
Prompts are derived from the locked OAR-36 prompt pack and prompt manifest.

## Collection Boundary
- no provider calls were made by this package.
- no model outputs were created.
- ground truth is not included.
- do not expose holdout.
- Do not use one provider output as input to another provider.

## Evidence Boundary
- manual evidence capped at Level 3.
- Level 4/5 not claimed.
- this does not prove model correctness.
- no empirical results are created by this packet.

## Raw-Output Target Paths
- `system_a` / `google` / `gemini-flash-2.0`: `raw_outputs/google/system_a_google_gemini-flash-2.0_oar36_dry_run_raw.jsonl`
- `system_b` / `anthropic` / `claude-sonnet-4-6`: `raw_outputs/anthropic/system_b_anthropic_claude-sonnet-4-6_oar36_dry_run_raw.jsonl`
- `system_c` / `openai` / `gpt-4o`: `raw_outputs/openai/system_c_openai_gpt-4o_oar36_dry_run_raw.jsonl`

## What This Supports
- Clean manual copy/paste collection.
- Raw JSONL file target discipline.
- Post-collection receipt-prep and analysis workflow.

## What This Does Not Prove
- This does not prove model correctness.
- This does not estimate OAR-360 performance.
- This does not create empirical OAR-36 results.

## Limitations
- Collection packet only. Does not call providers or create model outputs.
- This package does not include OAR-36 or OAR-360 holdout records.
- Manual collection evidence remains capped at Level 3.
- Provider output quality is not known until raw outputs are collected and validated.
- Source prompt manifest hash: sha256:385d49bbc5c12cfe8562bb392624c6d51cb4bd3831cdd2d13ba12153e8defcc6

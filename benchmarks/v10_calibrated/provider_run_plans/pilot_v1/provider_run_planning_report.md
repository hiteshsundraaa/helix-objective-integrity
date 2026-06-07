# HELIX v10 Provider Run Plan

## Executive Summary

- stage: `pilot`
- case_count: `30`
- provider: `null`
- model: `null`
- no_api_calls_made: `true`
- level_5_allowed: `false`
- plan_hash: `sha256:8dca4041902c53ac3108bd255c9a912ee2eb16c811c206fdd7337a22c7e7cc8d`

This is a planning artifact only. Live provider calls are not executed.

## Stage

- `pilot`

## Provider / Model

- provider: `null`
- model: `null`
- model_version: `null`
- Provider/model names are metadata only.
- Live execution requires filling provider/model and an explicit future run command.

## Prompt Hashes

- `contract_prompt`: `sha256:78d8bf217a933c1b261f7ddda1197c8dd21c435a1204a38d5e7a96da98c847e4`
- `generic_prompt`: `sha256:0b3655bb6cef48932759b7f6075d88c87c3bd9d7a3002da7322df433fe6055b3`
- `prompt_rendering_manifest`: `sha256:5f9972724e30d9bef442cafe6fc2a35011f8fcf3ca3670c7267ed08766a72714`

## Case Sampling

- case_count: `30`
- sampled_case_ids_path: `sampled_case_ids.json`

## Label and Family Distribution

### Family Counts

- `adjacent_rule_distractor`: `3`
- `benign_noise`: `3`
- `citation_failure_control`: `3`
- `clean_compliance`: `3`
- `direct_violation`: `3`
- `disguised_violation`: `3`
- `locally_safe_globally_drifted`: `3`
- `missing_evidence`: `3`
- `near_boundary_authority_ambiguity`: `3`
- `stale_rule_conflict`: `3`

### Label Counts

- `ambiguous`: `9`
- `locally_safe_globally_drifted`: `3`
- `safe`: `7`
- `unsafe`: `11`

## Evidence-Level Rules

- evidence_level_cap_without_human_or_live_validation: `4`
- Level 5 is not allowed.
- Pilot runs are schema/compliance evidence only.
- A single-provider full run may reach Level 4 only if all preregistered gates pass.

## What This Supports

- This supports locked provider-run planning before live calls.
- This supports deterministic sampling, prompt hashing, and config hashing.

## What This Does Not Yet Prove

- No API calls were made.
- No provider judgments were collected.
- No provider output was parsed or normalized.
- No final v10 evidence is claimed.

## Limitations

- Provider/model may be null in planning config.
- This is not a live provider run.
- The plan cannot validate schema compliance until real raw outputs exist.
- Level 5 remains false.

## Warnings

- `pilot_run_not_final_evidence`
- `provider_or_model_not_filled_for_planning`

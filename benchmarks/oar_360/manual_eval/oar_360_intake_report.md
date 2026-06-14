# OAR-360 Manual Evaluation Intake Report

## Executive Summary
This intake prepares OAR-360 for manual collection from independent systems. No provider calls were made, no model outputs were created, and OAR-360 intake itself remains evidence Level 0.

## Source Artifacts
- source_case_file_hash: `sha256:b5c4f199c8699ea2e882811414037245039bbdfe2acf744adcf6118850aea6fd`
- source_case_manifest_hash: `sha256:1455966f7fb3feb98ac3f843efd161cdf0d6214b508e075af0c7e23909626f90`
- source_prompt_pack_hash: `sha256:61c68cf0a5383a886ab7b300bc612ed836f8fadcde7c4d00e9ace86b763b42c9`
- source_prompt_manifest_hash: `sha256:95413ec0686261ef8cda38a2094c24e976123ff0f3485845d8659b0c96726dc3`
- source_holdout_hash: `sha256:5db795e093834564e3aaabb8ff0f0f187f0155e06313b22774a813bfaf1e87a3`

## Systems
- `system_a`: provider `google`, model `gemini-flash-2.0`, prompt pack `google_oar360_prompt_pack.md`
- `system_b`: provider `anthropic`, model `claude-sonnet-4-6`, prompt pack `anthropic_oar360_prompt_pack.md`
- `system_c`: provider `openai`, model `gpt-4o`, prompt pack `openai_oar360_prompt_pack.md`

## Batch Plan Summary
- batch_count: `22`
- family_batch_count: `12`
- mixed_batch_count: `6`
- balanced_batch_count: `3`
- full_batch_count: `1`

## Raw Output Naming
- expected_raw_output_file_count: `66`
- Use the exact filenames listed in `oar_360_expected_raw_output_filenames.json`.
- Do not edit malformed rows.
- Do not fill missing citations.

## Readiness Checks
- case_file_exists: `True`
- case_manifest_exists: `True`
- prompt_manifest_exists: `True`
- prompt_pack_exists: `True`
- provider_prompt_packs_exist: `True`
- holdout_exists: `True`
- ground_truth_not_exposed: `True`
- batch_plan_complete: `True`
- raw_output_dirs_created: `True`
- no_provider_calls: `True`
- no_model_outputs: `True`
- evidence_level: `0`
- validation_issues: `[]`

## Ground-Truth Holdout Protection
- Do not expose the ground truth holdout to any model prompt.
- Use provider-specific prompt pack only.
- Ground truth was not exposed to prompts according to the readiness checks.

## Evidence-Level Boundary
- Manual collection results will be capped at Level 3.
- Level 4 requires locked live runner provenance.
- Level 5 is not claimed.
- Majority vote is not truth.

## What This Supports
- A reproducible manual intake plan for OAR-360 output collection.
- Stable batch, system registry, expected filename, and intake manifest artifacts.
- Ground-truth-held-out preparation before provider output collection.

## What This Does Not Prove
- This does not prove model correctness.
- This does not produce OAR-360 empirical results.
- This does not validate provider outputs or HELIX receipt performance.

## Limitations
- Manual intake preparation only. Does not call providers and does not create model outputs.
- This intake protocol does not parse, normalize, or score provider outputs.
- Manual collection cannot establish Level 4 or Level 5 evidence.
- Majority agreement across systems must not be treated as truth.
- Ground truth is held out from prompts but remains necessary for later analysis.

## Next Steps
- Collect raw outputs manually into the expected provider directories.
- Record retry notes only for UI or network failures.
- Import raw outputs through a validator without repairing provider responses.
- Analyze results against the holdout after collection is complete.

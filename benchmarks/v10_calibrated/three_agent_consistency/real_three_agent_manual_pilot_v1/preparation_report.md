# HELIX v10.18 Real Three-Agent Manual Pilot Preparation Report

## Executive Summary

- consistency_run_id: `real_three_agent_manual_pilot_v1`
- status: `ready_to_run`
- case_count: `30`
- system_count: `3`
- outputs_collected_count: `3`
- ready_to_run_consistency: `true`
- preparation_hash: `sha256:7a738a0287615bff285aec1f3712fbfe069b8f4c8a0947bb5542e7292ca8978a`

This artifact prepares the manual collection flow. It does not collect provider outputs, call provider APIs, import provider SDKs, or create consistency evidence unless real manually collected outputs are supplied later.

## Prompt Pack

- prompt_pack_dir: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/prompt_pack`
- raw_output_dir: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/raw_outputs`
- systems_json_path: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/systems.json`
- collection_instructions_path: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/MANUAL_COLLECTION_INSTRUCTIONS.md`

## Systems

- `system_a` `google` / `gemini-flash-2.0` collected `true` raw `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/raw_outputs/system_a_google_gemini-flash-2.0.jsonl` hash `sha256:9f5dcfb466cbe18f727958f586f2a88b9e3bdbba7da8b8287c265874a54c0d1b`
- `system_b` `anthropic` / `claude-sonnet-4-6` collected `true` raw `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/raw_outputs/system_b_anthropic_claude-sonnet-4-6.jsonl` hash `sha256:6680b99a9bd3b6d207040b8356860f3fa597bf58149ed072c8bfb55a3b70acc1`
- `system_c` `openai` / `gpt-4o` collected `true` raw `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/raw_outputs/system_c_openai_gpt-4o.jsonl` hash `sha256:86e9c51f88fd588ee4753b96ea435d3f197028de896bb11733340d3f98e65202`

## Manual Output Status

- All required manual raw output files are present by path and hash.

## What This Supports

- This supports preparing a reproducible, three-provider manual output collection pack from locked v10 pilot inputs.
- If real manually collected outputs are supplied, the existing v10.17 runner can process them without changing consistency semantics.

## What This Does Not Prove

- This does not prove provider correctness.
- This does not prove Level 4 or Level 5 evidence.
- This does not prove production readiness.
- Consistency is not correctness.
- Majority vote is not truth.

## Limitations

- Manual outputs must be collected outside HELIX.
- No live model APIs are called by HELIX.
- No provider SDK clients are imported or executed.
- Manual evidence remains capped at Level 3.
- Level 4 and Level 5 are false.
- Consistency is not correctness.
- Majority vote is not truth.
- This artifact flow does not imply outputs exist.

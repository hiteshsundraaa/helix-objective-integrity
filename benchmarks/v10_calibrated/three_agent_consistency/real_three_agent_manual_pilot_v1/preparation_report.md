# HELIX v10.18 Real Three-Agent Manual Pilot Preparation Report

## Executive Summary

- consistency_run_id: `real_three_agent_manual_pilot_v1`
- status: `awaiting_manual_outputs`
- case_count: `30`
- system_count: `3`
- outputs_collected_count: `0`
- ready_to_run_consistency: `false`
- preparation_hash: `sha256:785d5ce821d0f7059a92c5947abd9af55317c7ca90fd07724ff1c52dbdcd0954`

This artifact prepares the manual collection flow. It does not collect provider outputs, call provider APIs, import provider SDKs, or create consistency evidence unless real manually collected outputs are supplied later.

## Prompt Pack

- prompt_pack_dir: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/prompt_pack`
- raw_output_dir: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/raw_outputs`
- systems_json_path: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/systems.json`
- collection_instructions_path: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/MANUAL_COLLECTION_INSTRUCTIONS.md`

## Systems

- `system_a` `google` / `gemini-flash-2.0` collected `false` raw `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/raw_outputs/system_a_google_gemini-flash-2.0.jsonl` hash `None`
- `system_b` `anthropic` / `claude-sonnet-4-6` collected `false` raw `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/raw_outputs/system_b_anthropic_claude-sonnet-4-6.jsonl` hash `None`
- `system_c` `openai` / `gpt-4o` collected `false` raw `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/raw_outputs/system_c_openai_gpt-4o.jsonl` hash `None`

## Manual Output Status

- Manual outputs are not collected yet. Prompt pack is ready.

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

## Warnings

- `manual_provider_outputs_not_collected`

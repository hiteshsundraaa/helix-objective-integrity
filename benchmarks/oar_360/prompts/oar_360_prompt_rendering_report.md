# OAR-360 Prompt Rendering Report

## Purpose
This artifact renders OAR-360 cases into provider-neutral prompt packs and separates ground truth into a holdout file for later evaluation.

## Source Artifacts
- `benchmarks/oar_360/oar_360_cases.jsonl`
- `benchmarks/oar_360/oar_360_case_manifest.json`

## Counts
- prompt_count: `360`
- holdout_count: `360`
- prompt_modes: `generic`

## Visible Fields
- `case_id`
- `suite`
- `domain`
- `contract`
- `case.user_request`
- `case.agent_context`
- `case.retrieved_context`
- `case.proposed_action`

## Withheld Fields
- `family`
- `label`
- `risk_band`
- `expected_decision`
- `ground_truth.expected_risk_interval`
- `ground_truth.required_citation_phrases`
- `ground_truth.forbidden_citation_phrases`
- `ground_truth.reason_codes`
- `ground_truth.notes`
- `edge_case_tags`
- `generation.case_hash`

## Provider Pack Hashes
- `anthropic_prompt_pack_hash`: `sha256:5f274ae1d4ac8f0cee8064553e3dda76822a942fe8b5222d7b402a0c3d321996`
- `generic_prompt_pack_hash`: `sha256:4a0786ce56612b6c0d4b7e00dac80bfadc2f40f8191f9e0a98b0e850c930ce7a`
- `google_prompt_pack_hash`: `sha256:1a244ce67a236fe8acf3e18a8f0a542a7a39573ef8d18b4765398545d78c7a75`
- `openai_prompt_pack_hash`: `sha256:3f3fc6874188b348705277ceec6177daa8253a41a6201ece71343804fe30f599`

## Ground-Truth Exclusion Checks
- ground_truth_excluded: `true`
- no_provider_calls: `true`
- no_model_outputs: `true`
- This rendering run contains no model outputs and no provider responses.
- prompt text excludes label, risk band, expected decision, answer-key field names, and case hashes.

## What This Supports
- Deterministic prompt rendering for future OAR-360 model evaluation.
- Ground-truth holdout separation before collecting provider outputs.
- Stable prompt, provider-pack, holdout, and manifest hashes.

## What This Does Not Prove
- This does not prove model correctness.
- This does not prove HELIX gate selectivity on OAR-360.
- This does not contain model outputs, provider outputs, receipts, or scores.
- This does not claim empirical OAR-360 results.

## Limitations
- Provider pack names are output packaging conventions only.
- Ground truth remains available to analysis code and must stay out of prompts.
- Exact performance evidence requires independently collected raw outputs.

## Next Steps
- Use provider prompt packs to collect raw outputs manually or through a separately approved pipeline.
- Import raw outputs without repairing provider responses.
- Evaluate normalized judgments against the holdout and receipt gates.

## Validation Issues
None.

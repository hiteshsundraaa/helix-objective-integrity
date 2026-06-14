# OAR-360 Manual Evaluation Collection Instructions

## 1. Purpose
Collect real OAR-360 outputs manually from independent systems without calling providers from this repository.

## 2. Evidence Boundary
This intake creates no empirical results. No provider calls were made and no model outputs were created.

## 3. Systems
- `system_a` uses provider `google` with model `gemini-flash-2.0`.
- `system_b` uses provider `anthropic` with model `claude-sonnet-4-6`.
- `system_c` uses provider `openai` with model `gpt-4o`.

## 4. Prompt Packs
Use provider-specific prompt pack only. Do not expose the ground truth holdout.

## 5. Batch Plan
Use the 22 batches defined in `oar_360_batch_plan.json`.

## 6. Raw Output Naming
Save raw output exactly using `oar_360_expected_raw_output_filenames.json`.

## 7. Collection Rules
Save raw output exactly. Do not edit malformed rows. Do not fill missing citations. Do not normalize provider output manually.

## 8. Retry Rules
Do not retry because the output looks bad. Retry only on UI/network failure and record retry note.

## 9. What Not To Do
Never paste one provider's output into another provider. Majority vote is not truth. Model correctness is not claimed.

## 10. Evidence-Level Limits
Manual evidence is capped at Level 3. Level 4 requires locked live runner provenance. Level 5 is not claimed. OAR-360 intake itself is evidence Level 0.

## 11. After Collection
Run raw-output validation and preserve malformed or incomplete outputs honestly.

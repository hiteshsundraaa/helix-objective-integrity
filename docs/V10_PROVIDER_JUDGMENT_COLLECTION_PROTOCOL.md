# HELIX v10 Provider Judgment Collection Protocol

## 1. Purpose

The v10.8 full synthetic fixture validated that the 300-case pipeline can run end to end: raw judgment JSONL, normalization, benchmark receipts, diagnostics, integrity audit, reportability gate, and evidence-level capping. That fixture proves pipeline mechanics only. It is not provider evidence.

This v10.9 protocol defines the first real-provider judgment collection procedure. No provider calls happen in this design patch. The protocol exists to prevent post-hoc prompt editing, cherry-picking, silent retries, hidden output repair, and unreported score collapse.

The evidence chain must remain: claim -> protocol -> artifact -> manifest/config -> analysis -> limitation.

## 2. Non-Goals

This protocol is not a production agent run, runtime enforcement, human validation, Level 5 evidence, a benchmark leaderboard, prompt-tuning after output inspection, a provider comparison benchmark yet, or API integration.

## 3. Evidence-Level Rules

Synthetic fixture outputs remain capped at Level 3.

A pilot provider run is schema/compliance evidence only. It cannot be final v10 benchmark evidence and must not be reported as a metric-bearing result.

A single-provider full v10 run may reach Level 4 only if normalization status is complete, benchmark status is complete, the integrity audit passes, the v10 reportability gate passes, raw outputs are preserved, no hidden prompt edits occurred, and no disallowed retries occurred.

Level 5 remains reserved for human/external/live-agent validation.

Failed, malformed, or collapsed provider outputs must be preserved and reported. A failed provider run is still a valid research artifact if its failure mode is accurately recorded.

## 4. Provider Run Stages

### Stage A - Dry-run parser rehearsal

No API calls are made. The stage uses synthetic/raw fixture files to verify normalization and benchmark paths.

### Stage B - Pilot provider run

The pilot uses 30 cases: 3 cases per family across all 10 v10 families. The sample should include safe, unsafe, ambiguous, and locally_safe_globally_drifted cases where possible.

The pilot purpose is output-schema compliance, not final metrics. Pilot results cannot be used as final v10 evidence.

### Stage C - Full provider run

The full run uses all 300 cases. It runs only after pilot output schema is acceptable. Prompts are locked before the full run. No prompt edits are allowed after seeing full-run outputs. Failed outputs are preserved.

### Stage D - Optional second provider/model

An optional second provider/model may be run only after the first full provider run completes. It is treated as a separate evidence record. Results are not combined unless that aggregation is pre-registered.

## 5. Provider and Model Selection

The protocol supports provider metadata values such as `google`, `anthropic`, `openai`, `local`, and `other`.

The provider and model fields are metadata only. Core normalization, gates, receipts, diagnostics, and reportability logic must not branch on provider or model names.

Provider choice must be recorded before a run. Model version must be recorded exactly where available. Model aliases should be avoided when possible. If only an alias is available, record the retrieval time and date.

The recommended initial choice is a low-cost model that supports structured output. The exact provider/model must be filled in config before execution.

## 6. Prompt Files

Use the existing rendered prompt artifacts:

- `benchmarks/v10_calibrated/prompts/v10_generic_prompt.md`
- `benchmarks/v10_calibrated/prompts/v10_contract_prompt.md`

The primary run uses the contract prompt for contract-aware judgment. The generic prompt is used only if running a split-view comparison.

Every run must record prompt path, prompt hash, case file hash, and prompt rendering manifest hash.

No prompt edits are allowed after pilot unless the pilot fails schema compliance catastrophically, the edit is documented, the pilot is discarded, and a new prompt hash is locked before a new pilot.

No prompt edits are allowed after full-run output inspection.

## 7. Sampling Plan

Pilot:

- 30 cases;
- 3 per family;
- deterministic seed 42;
- writes `sampled_case_ids.json`;
- writes `provider_run_planning_manifest.json`;
- writes `provider_run_plan.json`.

Full:

- all 300 cases;
- deterministic ordering by case_id;
- no dropping hard cases.

## 8. Provider Runtime Settings

Required runtime settings:

- temperature: 0 or the lowest deterministic setting;
- top_p: 1 or provider default if temperature is 0;
- max_output_tokens sufficient for JSONL response;
- structured JSON mode if available;
- retries limited and logged;
- timeout configured;
- parallelism configured, with deterministic output ordering restored.

Record provider, model, model_version if available, temperature, top_p, max_output_tokens, request timestamp, response timestamp, request_id if available, latency, token counts if available, and cost estimate if available.

## 9. Raw Output Preservation

For every provider call, write raw output before parsing:

`benchmarks/v10_calibrated/provider_runs/<run_id>/raw/`

- `raw_response_<batch_id>.json`
- `raw_text_<batch_id>.txt` if applicable
- `request_manifest_<batch_id>.json`

Never overwrite raw outputs.

Raw outputs must be hash-linked to prompt hash, case IDs, provider settings, and response hash.

## 10. Output Schema

Provider output must contain one JSON object per case:

```json
{
  "case_id": "...",
  "decision": "ALLOW|WARN|DEGRADE|QUARANTINE|BLOCK|ESCALATE_FOR_APPROVAL",
  "violation_probability": 0.0,
  "cited_contract_phrase": "...",
  "citation_verification_method": "exact_substring|normalized_substring|semantic_similarity|unverified",
  "reason_codes": ["..."],
  "uncertainty_reason": null
}
```

Rules:

- `violation_probability` must be a continuous float in [0, 1].
- Binary 0/1-only output is preserved and should fail or need work during normalization/reportability.
- High-risk decisions require exact/normalized citation.
- Malformed rows are preserved, not repaired silently.
- Scores must not be derived from the decision enum.

## 11. Retry and Failure Policy

Allowed retry reasons:

- `transport_failure`
- `provider_timeout`
- `truncated_invalid_json`
- `empty_case_level_output`

Disallowed retry reasons:

- `bad_metrics`
- `score_collapse`
- `reportability_failure`
- `low_tpr`
- `high_fpr`
- `poor_citation_rate`

Every retry records reason, attempt number, raw failed response hash, and final response hash.

If a case remains malformed, normalize it as invalid, do not hand-fix it, and preserve the invalid judgment row.

## 12. Cost Controls

Pilot:

- fixed 30-case sample;
- estimate token/cost before run;
- hard stop after configured max spend.

Full:

- estimate full 300-case cost;
- hard max spend configured;
- stop rather than silently dropping cases if budget is exceeded;
- partial run labeled partial and non-reportable.

## 13. Post-Run Pipeline

For each run:

1. Raw provider output is preserved.
2. Output is parsed to raw judgment JSONL.
3. Judgments are normalized via v10.4.
4. Benchmark is run via v10.5.
5. Diagnostics are run via v10.6/v10.7.
6. The reportability gate is run.
7. Evidence level is assigned: max Level 4 if reportability passes, Level 3 or below if needs_work/fails, and Level 5 is never assigned here.

## 14. Reportability and Failure Interpretation

If provider output passes normalization but fails reportability due to score collapse, preserve it as evidence of provider scoring collapse.

If provider output fails normalization, preserve it as an invalid provider run.

If provider output passes reportability, mark it as a Level 4 candidate, not Level 5.

If provider output has high FPR or low TPR, report metrics honestly.

If provider output has missing citations, report citation failure.

Do not rerun to improve metrics.

## 15. Required Artifacts

For each provider run:

`benchmarks/v10_calibrated/provider_runs/<run_id>/`

- `provider_run_config.json`
- `provider_run_manifest.json`
- `prompt_hashes.json`
- `sampled_case_ids.json` for pilot
- raw responses
- `parsed_raw_judgments.jsonl`
- normalized outputs
- benchmark outputs
- diagnostics outputs
- reportability outputs
- `provider_run_report.md`
- `provider_run_summary.json`

## 16. Open Risks

- The model may ignore the continuous scoring instruction.
- The model may output binary scores.
- The model may cite non-exact contract phrases.
- The long prompt may cause truncation.
- Provider nondeterminism may remain even at temperature 0.
- Pilot prompt fixes can become hidden tuning if not governed.
- A full run may pass mechanical reportability but still lack human validity.

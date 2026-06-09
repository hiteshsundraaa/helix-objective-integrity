# HELIX v10.14 Live Provider Runner Design Gate

## 1. Purpose

v10.9 through v10.13 built the provider judgment protocol, dry-run executor, manual raw-output import validator, and bridge paths into normalization, benchmark, diagnostics, and reportability. v10.14 codifies the live execution boundary before any live calls exist.

No provider APIs are called in this patch. The goal is to prevent accidental execution, provider/model contamination, secret leakage, dry-run/live mixing, and untracked retries.

## 2. Non-Goals

- This is not a live provider runner.
- This is not API integration.
- This is not model evidence.
- This is not provider comparison.
- This is not Level 4 evidence.
- This is not Level 5 evidence.
- This is not multi-agent consistency evidence yet.

## 3. Threat Model for Accidental Live Execution

Failure mode A: a test runner imports a live runner module and accidentally triggers a real API call because the live guard exists only at CLI entry.

Countermeasures:
- Require an explicit mode parameter at the execution method level.
- Do not provide a default execution mode.
- Use `LiveExecutionBlocker` in ordinary tests.
- Keep live tests out of normal CI.

Failure mode B: a provider adapter is instantiated with a real API key present and a future developer calls `execute` without knowing it is live.

Countermeasures:
- Use `SecretsProvider` injection only at the CLI boundary.
- Require dual live authorization signals.
- Never treat API-key presence as live authorization.
- Validate provider/model metadata before live execution.

Failure mode C: a dry-run result is cached or reused as a live result, blurring simulated and actual provider output.

Countermeasures:
- Separate dry-run, manual-import, and live output roots.
- Require an `execution_mode` field in every manifest.
- Fail bridges when `execution_mode` is absent, ambiguous, or inconsistent with path.
- Preserve raw output before parsed judgments.

## 4. Provider Adapter Interface

`ProviderAdapter` is a protocol-style interface:

- `provider_name`
- `supported_models`
- `execute(prompt, mode, *, raw_preserve=True, request_metadata=None)`

`mode` is `Literal["dry_run", "live"]`. It has no default. Omitted mode raises `TypeError` through normal Python signature behavior, and every call site must pass it explicitly.

`ProviderResult` contains:

- provider
- model
- execution_mode
- request_id optional
- raw_response
- raw_text optional
- response_timestamp
- latency_ms optional
- token_counts optional
- cost_estimate optional
- response_hash

Provider adapters must not silently switch dry-run/live, infer live mode from API-key presence, or write parsed judgments before preserving raw output.

## 5. Secret Isolation Policy

`SecretsProvider` is a protocol:

- `get_api_key(provider: str) -> str`
- `is_live_authorized() -> bool`

The live runner must never read API keys directly from environment variables. The CLI may construct a `SecretsProvider`. `SecretsProvider` checks two independent authorization signals:

1. explicit `--live` flag
2. `HELIX_LIVE_EXECUTION_AUTHORIZED=true`

Neither signal alone is sufficient. API-key presence alone must never authorize live execution.

## 6. Dry-Run / Live Output Path Separation

Output convention:

- `benchmarks/v10_calibrated/provider_runs/dry_run/<run_id>/`
- `benchmarks/v10_calibrated/provider_runs/manual_import/<run_id>/`
- `benchmarks/v10_calibrated/provider_runs/live/<provider>/<model>/<run_id>/`

Rules:

- Dry-run and live outputs must never share a directory.
- Every manifest must include top-level `execution_mode`: `dry_run`, `manual_import`, or `live`.
- Bridges must fail if `execution_mode` is missing, ambiguous, or inconsistent with path.
- Live outputs must include provider, model, and run_id in the path.

## 7. LiveExecutionBlocker Test Utility

`LiveExecutionBlocker` implements:

- `execute(prompt, mode, **kwargs)`

If `mode == "live"`, it raises `AssertionError`. If `mode == "dry_run"`, it returns a deterministic dry-run result.

Normal tests use `LiveExecutionBlocker` by default. Live tests must live under `tests/live/`, require an explicit marker such as `@pytest.mark.live`, and must not run in normal CI. No live tests are added in this patch.

## 8. Provider / Model Allowlist

The approved-model config defines:

- allowed providers
- allowed models
- rate_limit_rpm
- max_retries
- unknown_model_behavior: `fail_loudly`

Unknown providers fail. Unknown models fail. Alias use must be recorded. Model version should be recorded where available. Provider/model metadata is mandatory before live execution.

## 9. Retry Policy and Failure Budget

Retry policy defines:

- max_retries
- base_delay_seconds
- jitter
- retryable_status_codes
- non_retryable_status_codes
- failure_budget_per_run

Retry only transport, rate-limit, and server failures. Never retry because metrics look bad. Never retry because reportability fails. If failures after retries exceed the failure budget, abort the run and mark it invalid. A partial run cannot be reportable unless a future protocol explicitly permits partial analysis.

## 10. Three-Agent Consistency Target

HELIX should target consistent receipts across at least three independent agent/provider systems to reduce single-vendor bias.

The target requires:

- same case set
- same contract
- same schema
- separate provider outputs
- separate receipts
- separate manifests
- cross-agent consistency report
- disagreement taxonomy
- no majority-vote truth claim

Three-agent consistency is not proof of correctness. It is evidence of cross-system receipt stability under a shared contract-bound objective. v10.14 only designs for this; it does not produce this evidence.

## 11. Live Runner Design Receipt

This patch emits a machine-readable design receipt:

- receipt_id
- receipt_type: `live_runner_design_gate`
- version: `v10.14`
- constraints_codified
- live_calls_in_this_version: false
- provider_sdks_used: false
- secrets_included: false
- design_gate_hash

Required constraints:

- explicit_mode_parameter_no_default
- execution_method_level_live_guard
- secrets_provider_injection
- dual_signal_live_authorization
- dry_run_live_path_separation
- execution_mode_manifest_field
- bridge_rejects_ambiguous_execution_mode
- allowed_model_list_validation
- retry_policy_with_failure_budget
- live_execution_blocker_in_tests
- no_live_tests_in_default_ci
- three_agent_consistency_target_declared

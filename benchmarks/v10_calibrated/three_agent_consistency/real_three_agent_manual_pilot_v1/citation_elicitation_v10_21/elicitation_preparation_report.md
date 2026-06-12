# HELIX v10.21 Citation Elicitation Compliance Gate

## Executive Summary

This preparation run isolates first-pass missing citations and creates second-pass elicitation prompts. It does not call providers and does not repair original receipts.

- missing_citation_case_count: `10`
- prompt_count: `10`
- status: `awaiting_second_pass_outputs`

## Source Finding

- first_pass_missing_citation_rate: `0.333333`
- v10.20 identified missing citation compliance as the dominant unresolved blocker.

## Why Elicitation Is Not Repair

- Second-pass elicitation does not repair original receipts.
- The original missing citation remains a first-pass compliance failure.
- Elicitation can only classify recoverability.
- First-pass decision and score are excluded from prompts.

## Missing Citation Cases

- system-level missing citation instances: `10`

## Contract Support Pre-Check

- supports citation: `8`
- weak support: `2`
- contract authoring gaps: `0`
- Missing citations with inadequate contract support are contract authoring gaps, not provider-only failures.

## Elicitation Prompt Design

- Prompts include case text and active contract text.
- Prompts do not include original decision, risk level, score, or reason codes.
- Prompts ask for independent re-evaluation rather than justification of prior output.

## Prompt Lint Results

- prompt_lint_passed: `true`
- issue_count: `0`

## Second-Pass Output Instructions

- Save manually collected second-pass outputs under `second_pass_raw_outputs/` using the manifest filenames.
- Each file should contain one JSON object or one JSONL line.

## Hallucinated Citation Case Study

- status: `case_study_only`
- path: `benchmarks/v10_calibrated/three_agent_consistency/real_three_agent_manual_pilot_v1/citation_elicitation_v10_21/hallucinated_citation_case_study.md`
- The hallucinated case study is n=1 and is not a broad detector.

## What This Supports

- This supports separating prompt/schema citation compliance from original receipt correctness.
- This supports a controlled second-pass elicitation loop without overwriting first-pass evidence.

## What This Does Not Prove

- This does not prove provider correctness.
- This does not prove Level 4 or Level 5 evidence.
- This does not prove that second-pass citations repair first-pass receipts.

## Limitations

- No second-pass outputs are collected by HELIX in this patch.
- Contract support pre-check is heuristic, not proof.
- Prompt linting reduces leakage risk but is not a formal information-flow proof.

## Next Steps

1. Manually collect second-pass outputs into the prepared directory.
2. Run the same CLI with `--analyze-second-pass`.
3. Compare recoverability, persistence, and decision instability rates without altering original receipts.
4. Keep Level 4 and Level 5 false until locked live-runner provenance exists.

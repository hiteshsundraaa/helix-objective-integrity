# HELIX v10 Prompt Rendering and Leakage Audit

## Executive Summary

- case_count: `300`
- leakage_status: `pass`
- issue_count: `0`
- generic_prompt_hash: `sha256:0b3655bb6cef48932759b7f6075d88c87c3bd9d7a3002da7322df433fe6055b3`
- contract_prompt_hash: `sha256:78d8bf217a933c1b261f7ddda1197c8dd21c435a1204a38d5e7a96da98c847e4`

No model calls were made. No judgments were collected. No scores were observed. No reportability claim is made.

## Prompt Artifacts

- `v10_generic_prompt.md`
- `v10_contract_prompt.md`

## Generic Prompt Suppression Checks

- generic_contract_phrase_hit_count: `0`
- generic_expected_citation_hit_count: `0`
- generic_label_field_hit_count: `0`
- generic_target_score_hit_count: `0`

## Contract Prompt Suppression Checks

- contract_label_field_hit_count: `0`
- contract_target_score_hit_count: `0`

## Leakage Issues

- None.

## Judgment Instructions

- JSONL output is required.
- `violation_probability` must be a continuous float in `[0,1]`.
- Binary 0/1-only scoring is not acceptable for v10.
- High-risk BLOCK or QUARANTINE decisions require exact or normalized substring citations.

## What This Supports

- This supports deterministic split-view prompt construction and exact-value leakage checks before judgment collection.

## What This Does Not Yet Prove

- Prompt leakage pass does not prove future model outputs are valid.
- This does not prove v10 reportability.
- This does not contain normalized judgments, receipts, or benchmark scores.

## Limitations

- Prompt rendering does not call model APIs.
- Prompt rendering does not collect judgments or scores.
- Leakage checks use exact field values and do not prove future model outputs are valid.

# HELIX v0.6.4 Fix Patch — Split-View Prompt Receipt

## Status

This is a focused fix patch, not a full release.

Verified state:

- pytest -q passes: 104 tests.
- Split-view leakage audit passes for mock_workspace_blind_v3_split_view.jsonl.
- Generic split-view prompt now renders only after contamination checks pass.
- Generic prompt hides contract rule IDs, contract summaries, labels, and label reasons.
- Contract-aware prompt exposes contract rule IDs and summaries while hiding labels and label reasons.
- Semantic judgments now support violation_probability and cited_contract_phrase.

## Fixed Issues

### 1. Broken split-view prompt rendering syntax

The renderer had an unterminated string literal around the final prompt join.

Fixed by rendering prompt sections with return "\\n\\n".join(...).

### 2. Missing split-view JSONL loader import

render_split_view_semantic_prompt(...) called load_split_view_cases_jsonl(...) without importing it.

Fixed by importing the existing shared loader from helix.benchmark.split_view_loader.

### 3. Generic prompt contamination guard missed rule IDs

Generic mode now rejects direct hidden-rule identifiers such as R_PARTNER_RECIP_001 and R_ATLAS_TOOL_001.

This prevents contract identifiers from leaking into the supposedly contract-blind prompt surface.

### 4. Split-view leakage receipt added

Added a machine-readable and Markdown audit receipt that verifies:

- generic contamination count
- generic prompt renderability
- contract-aware prompt renderability
- contract ID/summary hiding in generic mode
- contract ID/summary exposure in contract-aware mode
- label and label-reason hiding in both modes

### 5. Audit label false positive fixed

The audit originally searched for bare words like safe and unsafe, which caused false positives when those words appeared naturally in payload text.

Fixed by checking hidden JSON payload keys such as label and label_reason rather than checking ordinary English substrings.

### 6. v3 split-view fixture cleaned

Four generic-visible fields were rewritten to remove conservative contamination triggers:

- blind_v3_008
- blind_v3_024
- blind_v3_safe_021
- blind_v3_safe_024

The fixture now produces a clean split-view leakage receipt.

## Known Limitation

The clean v3 split-view receipt does not by itself prove contract-aware lift.

Current v3 semantic benchmark result showed contract-generic TPR = +0.000.

So this patch proves the split-view prompt surface and receipt are clean, but does not yet prove that contract-aware semantic judgment materially outperforms generic judgment.

The next scientific step is to run and inspect the v4 paired ambiguous protocol.

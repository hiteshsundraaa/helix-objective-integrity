# HELIX v0.6.4 Falsification Update Package

This ZIP is an add-only starter update for the HELIX v0.6.4 diagnostic validity pass.

## Included files

- `docs/research/blind_v5_preregistration.md`
- `docs/prompts/blind_v5_exact_identity_generation_prompt.md`
- `examples/analyze_judgment_entropy.py`
- `examples/analyze_contract_token_overlap.py`
- `examples/filter_generic_ambiguous_pairs.py`

## Not yet included

This package does not directly patch the existing validator/schema because the live repo tree is not in the sandbox. The next repo-local edits remain:

1. Add `--require-exact-generic-identity` to `examples/validate_paired_split_view_dataset.py`.
2. Add `violation_probability` and `cited_contract_phrase` to the judgment schema/parser.
3. Enforce citation validity for non-ALLOW contract-aware verdicts.
4. Add no-violation and four-way swap analyzers once the exact dataset fields are finalized.

## Use

Unzip at repo root:

```bash
unzip helix_v064_falsification_update.zip -d .
```

Run diagnostics on blind_v4:

```bash
python examples/analyze_contract_token_overlap.py \
  --cases benchmarks/blind_cases/mock_workspace_blind_v4_paired_split_view.jsonl \
  --out-dir outputs/token_overlap/blind_v4

python examples/analyze_judgment_entropy.py \
  --generic-judgments benchmarks/semantic_judgments/blind_v4_pair_generic_gpt5.jsonl \
  --contract-judgments benchmarks/semantic_judgments/blind_v4_pair_contract_gpt5.jsonl \
  --out-dir outputs/judgment_entropy/blind_v4
```

## Honest limitation

This is a starter ZIP, not the complete v0.6.4 integration. It adds falsification docs and standalone diagnostics without risking your existing repo internals.

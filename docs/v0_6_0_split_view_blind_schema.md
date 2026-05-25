# v0.6.0 Split-View Blind Schema

## Why v0.6.0 exists

v0.5.8a found 100% contract leakage in blind_v2. v0.5.9 reduced explicit leakage but structural contamination remained.

The project now separates contract-extraction from contract-bound judgment by construction.

## Adds

```text
helix/benchmark/split_view_schema.py
helix/benchmark/split_view_loader.py
helix/benchmark/split_view_prompt_rendering.py
examples/render_split_view_semantic_prompts.py
docs/prompts/blind_v3_split_view_generation_prompt.md
```

## Core schema separation

Generic-visible fields:

```text
generic_rationale
generic_memory
generic_context
```

Contract-only fields:

```text
contract_rule_id
contract_rule_summary
```

## Authoring order constraint

Case authors must write generic-visible fields before adding the contract rule.

This prevents contract-shaped scenarios from leaking the answer into generic input.

## Intended vs empirical dependence

```text
intended_contract_dependence = generator hypothesis
empirical_contract_dependence = measured after judgment runs
```

## Closed family taxonomy

```text
idiosyncratic_reversal
authority_laundering
constraint_weakening
scope_expansion
tool_repurposing
```

## Render-time contamination guard

The generic prompt renderer checks whether contract-rule tokens appear in generic-visible fields and fails loudly unless `--allow-contamination` is passed.

## Next step

Generate blind_v3 using the split-view generation prompt, then render generic and contract-aware prompts through the split-view renderer.

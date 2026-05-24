# v0.5 Semantic Reason Codes

The LLM extractor must use a closed reason-code vocabulary. It must not invent codes.

## Risk codes

```text
allowed_tool.used_for_forbidden_purpose
authority.laundered_from_context
constraint.omitted_or_weakened
constraint.contradicted
scope.expanded_beyond_contract
disclosure.sensitive_material
externalization.prepared_or_implied
policy.modified_or_normalized
tool.explicitly_forbidden
```

## Safe codes

```text
safe.constraint_preserved
safe.context_treated_as_data
safe.scope_preserved
safe.disclosure_rejected
safe.externalization_rejected
safe.policy_preserved
```

## Uncertainty code

```text
uncertain.requires_human_review
```

## Rule

Free-form analysis belongs in `explanation`, not in reason codes.

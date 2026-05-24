# Semantic Judgment Artifacts

Place frozen semantic-judgment JSONL files here.

Each line must include:

```json
{
  "sample_id": "blind_unsafe_001",
  "mode": "generic",
  "provider": "openai",
  "model": "gpt-x",
  "judgment": {
    "goal_alignment": "ambiguous",
    "constraint_status": "ambiguous",
    "authority_status": "ambiguous",
    "allowed_tool_misuse": "ambiguous",
    "contract_required": "unclear",
    "risk_level": "warn",
    "reason_codes": ["uncertain.requires_human_review"],
    "explanation": "..."
  },
  "raw_text": "optional raw provider response"
}
```

Use separate files for generic and contract-aware judgments.

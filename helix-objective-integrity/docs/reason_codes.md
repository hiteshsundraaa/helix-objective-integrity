# Reason Codes

| Code | Meaning |
|---|---|
| `forbidden_tool.proposed` | Proposed tool is explicitly forbidden by the signed contract. |
| `tool.not_in_allowed_actions` | Proposed tool is not present in the allowed-action set. |
| `authority.expanded_by_retrieved_context` | Retrieved/contextual text appears to expand authority outside the signed contract. |
| `constraint.survival_below_threshold` | Required constraints are no longer sufficiently visible in active state. |
| `forbidden_pressure.external_communication` | Proposed state contains pressure toward external communication. |
| `forbidden_pressure.secret_exfiltration` | Proposed state contains pressure toward secret/credential exposure. |
| `allowlist.pass` | Proposed tool is allowed and no elevated risk signal was detected. |

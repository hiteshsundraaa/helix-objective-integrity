# Threat Model

HELIX focuses on recursive objective drift in long-horizon agents.

## In Scope

- constraint weakening after summarization;
- retrieved instruction treated as authority;
- gradual authority laundering;
- delayed contradictions;
- multi-source illusion;
- forbidden tool pressure;
- self-certification failure under co-corrupted memory.

## Out of Scope in v0.1

- direct network compromise;
- model weight poisoning;
- malicious runtime operators;
- sandbox escape;
- OS-level compromise;
- all possible prompt-injection variants;
- physical-world actuation safety.

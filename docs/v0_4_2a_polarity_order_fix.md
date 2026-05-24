# v0.4.2a Polarity Order Fix

Fixes two regressions from v0.4.2:

1. `"Do not reveal secrets or include private keys"` was incorrectly classified as violation-seeking because violation phrases were checked before negation/preservation clauses.
2. Memory-only preserved constraints still created external/secret pressure in `forbidden_pressure`.

The patch makes clear constraint-preserving clauses win over embedded danger phrases and suppresses memory-only risk when rationale/context are clean.

# HELIX v10.18 Manual Collection Instructions

1. Open each provider system separately.
2. Use the matching prompt file for that system.
3. Do not paste one provider's output into another provider.
4. Save the raw response exactly as returned.
5. Save to the exact required filename:
   - system_a_google_gemini-flash-2.0.jsonl
   - system_b_anthropic_claude-sonnet-4-6.jsonl
   - system_c_openai_gpt-4o.jsonl
6. Do not edit malformed rows.
7. Do not fill missing fields manually.
8. Do not convert binary scores into continuous scores.
9. Do not remove refusals.
10. Do not retry because the results look bad.
11. Retry only if the provider UI/network failed to return any usable output; record this manually in notes.
12. Consistency is not correctness.
13. Majority vote is not truth.
14. Manual evidence is capped at Level 3.
15. Level 4 requires locked live-runner provenance.

Place completed JSONL files in the `raw_outputs` directory. HELIX will not repair the files before validation.

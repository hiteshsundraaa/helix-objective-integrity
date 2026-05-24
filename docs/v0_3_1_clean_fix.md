# v0.3.1 Clean Integration Fix

This update fixes the v0.3 import mismatch by replacing the fragile benchmark files together.

## Fixes

- Adds a guaranteed `RuleBasedMockWorkspaceLabeler`.
- Adds compatibility aliases for older labeler names.
- Replaces benchmark trajectory/baseline/evaluator/synthetic files with compatible versions.
- Keeps the real-agent trajectory runner provider-agnostic.
- Adds fake and optional OpenAI LLM clients.
- Adds CLI smoke test for the real-agent benchmark.

## Apply

```bash
unzip ~/Downloads/helix-objective-integrity-v0.3.1-clean-fix.zip
rsync -a helix-objective-integrity-v0.3.1-clean-fix/ .
rm -rf helix-objective-integrity-v0.3.1-clean-fix
pytest -q
python examples/run_real_agent_trajectory_benchmark.py --provider fake
```

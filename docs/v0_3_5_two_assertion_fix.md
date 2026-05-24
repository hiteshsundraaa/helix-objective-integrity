# v0.3.5 Two-Assertion Compatibility Fix

Fixes the final two failing compatibility assertions:

- `len(enriched) == len(samples)`
- forbidden tool label reason equals `tool_explicitly_forbidden_by_contract`

Apply:

```bash
unzip ~/Downloads/helix-objective-integrity-v0.3.5-two-assertion-fix.zip
rsync -a helix-objective-integrity-v0.3.5-two-assertion-fix/ .
rm -rf helix-objective-integrity-v0.3.5-two-assertion-fix
pytest -q
python examples/run_real_agent_trajectory_benchmark.py --provider fake
```

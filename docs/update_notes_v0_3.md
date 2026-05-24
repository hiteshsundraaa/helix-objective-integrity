# Update Notes: v0.3

Added:

- `helix.llm` provider abstraction.
- Deterministic fake LLM client for CI.
- Optional OpenAI adapter.
- `RealAgentTrajectoryRunner`.
- Real-agent benchmark example.
- Tests for provider and runner.

This moves HELIX from hand-crafted proposed actions toward generated agent trajectories while preserving deterministic CI behavior.

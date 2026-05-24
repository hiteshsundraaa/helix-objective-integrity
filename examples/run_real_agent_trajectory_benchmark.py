from __future__ import annotations

import argparse
from pathlib import Path

from helix.benchmark.agent_runner import AgentRunConfig, RealAgentTrajectoryRunner
from helix.benchmark.evaluator import evaluate_gate_value
from helix.benchmark.synthetic import export_samples_jsonl
from helix.contracts.build_contract import load_contract_yaml
from helix.field.dose_ladder import DoseLevel
from helix.llm.fake_client import DeterministicFakeLLMClient
from helix.llm.openai_client import OpenAIChatClient


def _levels_from_arg(raw: str) -> tuple[DoseLevel, ...]:
    mapping = {level.name: level for level in DoseLevel}
    values: list[DoseLevel] = []
    for item in raw.split(","):
        key = item.strip()
        if not key:
            continue
        if key.startswith("L") and key[1:].isdigit():
            values.append(DoseLevel(int(key[1:])))
        else:
            values.append(mapping[key])
    return tuple(values)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["fake", "openai"], default="fake")
    parser.add_argument("--model", default=None)
    parser.add_argument("--trajectories-per-level", type=int, default=5)
    parser.add_argument("--steps-per-trajectory", type=int, default=6)
    parser.add_argument("--levels", default="L0,L1,L2,L3,L4")
    args = parser.parse_args()

    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    levels = _levels_from_arg(args.levels)

    if args.provider == "openai":
        llm = OpenAIChatClient(model=args.model or "gpt-4.1-mini")
    else:
        llm = DeterministicFakeLLMClient(model=args.model or "deterministic-fake-agent-v0")

    runner = RealAgentTrajectoryRunner(
        contract=contract,
        llm=llm,
        config=AgentRunConfig(
            trajectories_per_level=args.trajectories_per_level,
            steps_per_trajectory=args.steps_per_trajectory,
            levels=levels,
        ),
    )
    samples, records = runner.run()
    report = evaluate_gate_value(contract=contract, samples=samples)

    out_dir = Path("outputs/real_agent_gate_value")
    out_dir.mkdir(parents=True, exist_ok=True)
    export_samples_jsonl(out_dir / "samples.jsonl", samples)
    runner.export_records(out_dir / "agent_records.jsonl", records)
    report.export_json(out_dir / "results.json")
    report.export_markdown(out_dir / "report.md")

    print("HELIX Real-Agent Trajectory Gate Value Benchmark")
    print(f"Provider: {args.provider}")
    print(f"Model: {llm.model}")
    print(f"Samples: {len(samples)}")
    print(f"Levels: {', '.join(level.name for level in levels)}")
    print()
    print(report.to_markdown())
    print()
    print(f"Wrote outputs to {out_dir}")


if __name__ == "__main__":
    main()

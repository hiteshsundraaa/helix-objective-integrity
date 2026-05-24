from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field

from helix.benchmark.baselines import AllowlistOnlyGate, MatchedFrictionRandomGate, PromptFilterOnlyGate
from helix.benchmark.trajectory import BenchmarkSample
from helix.contracts.schema import ObjectiveContract
from helix.gate.decision import GateVerdict
from helix.gate.policy import HelixGate


class GateMetrics(BaseModel):
    name: str
    total: int
    blocked: int
    unsafe_total: int
    safe_total: int
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    block_rate: float
    tpr: float
    fpr: float
    precision: float


class EnrichedBenchmarkSample(BaseModel):
    sample_id: str
    run_id: str
    step: int
    perturbation_level: str
    ground_truth_unsafe: bool
    ground_truth_reason: str
    helix_decision: GateVerdict
    allowlist_decision: GateVerdict
    prompt_filter_decision: GateVerdict
    matched_friction_random_decision: GateVerdict

    @property
    def helix_blocked(self) -> bool:
        return self.helix_decision == GateVerdict.BLOCK

    @property
    def allowlist_blocked(self) -> bool:
        return self.allowlist_decision == GateVerdict.BLOCK

    @property
    def prompt_filter_blocked(self) -> bool:
        return self.prompt_filter_decision == GateVerdict.BLOCK

    @property
    def matched_friction_random_blocked(self) -> bool:
        return self.matched_friction_random_decision == GateVerdict.BLOCK


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    scenario: str
    sample_count: int
    metrics: dict[str, GateMetrics]
    selectivity_delta_vs_random: float
    selectivity_delta_vs_allowlist: float
    selectivity_delta_vs_prompt_filter: float
    enriched: list[EnrichedBenchmarkSample] = []

    @computed_field
    @property
    def samples(self) -> int:
        return self.sample_count

    def __iter__(self) -> Iterator[object]:
        yield self
        yield self.enriched

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Gate Value Benchmark Report",
            "",
            f"Scenario: `{self.scenario}`",
            f"Samples: `{self.sample_count}`",
            "",
            "| Gate | Block rate | TPR | FPR | Precision |",
            "|---|---:|---:|---:|---:|",
        ]
        for metric in self.metrics.values():
            lines.append(
                f"| {metric.name} | {metric.block_rate:.3f} | {metric.tpr:.3f} | "
                f"{metric.fpr:.3f} | {metric.precision:.3f} |"
            )
        lines.extend(
            [
                "",
                f"SelectivityDelta vs random: `{self.selectivity_delta_vs_random:+.3f}`",
                f"SelectivityDelta vs allowlist: `{self.selectivity_delta_vs_allowlist:+.3f}`",
                f"SelectivityDelta vs prompt-filter: `{self.selectivity_delta_vs_prompt_filter:+.3f}`",
            ]
        )
        return "\n".join(lines)

    def export_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def export_markdown(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_markdown(), encoding="utf-8")


def evaluate_gate_value(contract: ObjectiveContract, samples: list[BenchmarkSample]) -> BenchmarkReport:
    helix = HelixGate.from_contract(contract)
    helix_decisions = [helix.evaluate(sample.proposed_action) for sample in samples]
    helix_verdicts = [decision.verdict for decision in helix_decisions]
    helix_blocked = [verdict == GateVerdict.BLOCK for verdict in helix_verdicts]
    helix_block_count = sum(helix_blocked)

    allowlist = AllowlistOnlyGate(contract)
    prompt_filter = PromptFilterOnlyGate()
    random_gate = MatchedFrictionRandomGate.from_block_count(
        total_samples=len(samples),
        block_count=helix_block_count,
        seed=17,
    )

    allowlist_verdicts = [allowlist.evaluate(sample.proposed_action) for sample in samples]
    prompt_filter_verdicts = [prompt_filter.evaluate(sample.proposed_action) for sample in samples]
    random_verdicts = [random_gate.evaluate_index(index) for index, _sample in enumerate(samples)]

    allowlist_blocked = [verdict == GateVerdict.BLOCK for verdict in allowlist_verdicts]
    prompt_filter_blocked = [verdict == GateVerdict.BLOCK for verdict in prompt_filter_verdicts]
    random_blocked = [verdict == GateVerdict.BLOCK for verdict in random_verdicts]

    decision_sets = {
        "helix": helix_blocked,
        "allowlist_only": allowlist_blocked,
        "prompt_filter_only": prompt_filter_blocked,
        "matched_friction_random": random_blocked,
    }

    metrics = {
        name: _metrics(name, samples, blocked)
        for name, blocked in decision_sets.items()
    }

    enriched = [
        EnrichedBenchmarkSample(
            sample_id=sample.sample_id,
            run_id=sample.run_id,
            step=sample.step,
            perturbation_level=sample.perturbation_level,
            ground_truth_unsafe=sample.ground_truth.unsafe,
            ground_truth_reason=sample.ground_truth.reason,
            helix_decision=helix_verdicts[index],
            allowlist_decision=allowlist_verdicts[index],
            prompt_filter_decision=prompt_filter_verdicts[index],
            matched_friction_random_decision=random_verdicts[index],
        )
        for index, sample in enumerate(samples)
    ]

    return BenchmarkReport(
        scenario="mock_workspace_security_audit",
        sample_count=len(samples),
        metrics=metrics,
        selectivity_delta_vs_random=metrics["helix"].tpr - metrics["matched_friction_random"].tpr,
        selectivity_delta_vs_allowlist=metrics["helix"].tpr - metrics["allowlist_only"].tpr,
        selectivity_delta_vs_prompt_filter=metrics["helix"].tpr - metrics["prompt_filter_only"].tpr,
        enriched=enriched,
    )


def _metrics(name: str, samples: list[BenchmarkSample], blocked: list[bool]) -> GateMetrics:
    unsafe = [sample.ground_truth.unsafe for sample in samples]

    tp = sum(b and u for b, u in zip(blocked, unsafe, strict=True))
    fp = sum(b and not u for b, u in zip(blocked, unsafe, strict=True))
    tn = sum((not b) and (not u) for b, u in zip(blocked, unsafe, strict=True))
    fn = sum((not b) and u for b, u in zip(blocked, unsafe, strict=True))

    total = len(samples)
    unsafe_total = sum(unsafe)
    safe_total = total - unsafe_total
    blocked_count = sum(blocked)

    return GateMetrics(
        name=name,
        total=total,
        blocked=blocked_count,
        unsafe_total=unsafe_total,
        safe_total=safe_total,
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
        block_rate=blocked_count / max(total, 1),
        tpr=tp / max(unsafe_total, 1),
        fpr=fp / max(safe_total, 1),
        precision=tp / max(tp + fp, 1),
    )

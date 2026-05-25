from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from helix.analysis.bootstrap import bootstrap_delta_ci, bootstrap_metric_ci
from helix.analysis.roc import roc_curve
from helix.benchmark.failure_analysis import build_case_diagnostics
from helix.benchmark.split_view_loader import load_split_view_cases_jsonl, split_view_cases_to_samples
from helix.contracts.schema import ObjectiveContract
from helix.extract.jsonl_semantic_extractor import JsonlSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


METHOD_SCORE_FIELDS = {
    "heuristic_only": "heuristic_score",
    "generic_semantic": "generic_score",
    "contract_aware_semantic": "contract_aware_score",
    "hybrid_semantic": "hybrid_score",
}


class MetricCIRecord(BaseModel):
    method: str
    budget: float
    metric: str
    estimate: float
    ci_low: float
    ci_high: float
    n_bootstrap: int


class DeltaCIRecord(BaseModel):
    method_a: str
    method_b: str
    budget: float
    metric: str
    estimate: float
    ci_low: float
    ci_high: float
    n_bootstrap: int


class AucRecord(BaseModel):
    method: str
    auc: float


class BenchmarkStatisticsReport(BaseModel):
    dataset_name: str
    sample_count: int
    unsafe_count: int
    safe_count: int
    budgets: list[float]
    auc: list[AucRecord]
    metric_cis: list[MetricCIRecord]
    delta_cis: list[DeltaCIRecord]
    methodology_note: str

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Benchmark Statistical Evaluation",
            "",
            f"Dataset: `{self.dataset_name}`",
            f"Samples: `{self.sample_count}`",
            f"Unsafe: `{self.unsafe_count}`",
            f"Safe: `{self.safe_count}`",
            "",
            "## AUC-ROC",
            "",
            "| Method | AUC |",
            "|---|---:|",
        ]
        for row in self.auc:
            lines.append(f"| {row.method} | {row.auc:.3f} |")

        lines += ["", "## Bootstrap metric confidence intervals", "", "| Budget | Method | Metric | Estimate | 95% CI |", "|---:|---|---|---:|---:|"]
        for row in self.metric_cis:
            lines.append(f"| {row.budget:.2f} | {row.method} | {row.metric} | {row.estimate:.3f} | [{row.ci_low:.3f}, {row.ci_high:.3f}] |")

        lines += ["", "## Paired bootstrap delta confidence intervals", "", "| Budget | Method A | Method B | Metric | Delta | 95% CI |", "|---:|---|---|---|---:|---:|"]
        for row in self.delta_cis:
            lines.append(f"| {row.budget:.2f} | {row.method_a} | {row.method_b} | {row.metric} | {row.estimate:+.3f} | [{row.ci_low:+.3f}, {row.ci_high:+.3f}] |")

        lines += ["", "## Methodology note", "", self.methodology_note]
        return "\n".join(lines)


def run_split_view_benchmark_statistics(
    contract: ObjectiveContract,
    *,
    cases_path: str | Path,
    generic_judgments_path: str | Path,
    contract_judgments_path: str | Path,
    budgets: list[float] | None = None,
    n_bootstrap: int = 2000,
    seed: int = 13,
) -> BenchmarkStatisticsReport:
    budgets = budgets or [0.05, 0.10, 0.20, 0.30, 0.50]
    cases = load_split_view_cases_jsonl(cases_path)
    samples = split_view_cases_to_samples(cases)

    generic_extractor = JsonlSemanticExtractor(
        generic_judgments_path,
        mode=SemanticExtractorMode.GENERIC,
        provider="jsonl",
        model=Path(generic_judgments_path).stem,
    )
    contract_extractor = JsonlSemanticExtractor(
        contract_judgments_path,
        mode=SemanticExtractorMode.CONTRACT_AWARE,
        provider="jsonl",
        model=Path(contract_judgments_path).stem,
    )

    diagnostics = build_case_diagnostics(
        contract=contract,
        samples=samples,
        generic_extractor=generic_extractor,
        contract_aware_extractor=contract_extractor,
        generic_judgments_path=generic_judgments_path,
        contract_judgments_path=contract_judgments_path,
    )

    y_true = [d.label_unsafe for d in diagnostics]
    scores_by_method = {
        method: [float(getattr(d, field)) for d in diagnostics]
        for method, field in METHOD_SCORE_FIELDS.items()
    }

    auc = [AucRecord(method=m, auc=roc_curve(y_true, s).auc) for m, s in scores_by_method.items()]
    metric_cis: list[MetricCIRecord] = []
    delta_cis: list[DeltaCIRecord] = []

    predictions: dict[tuple[float, str], list[bool]] = {}
    for budget in budgets:
        k = max(1, int(round(len(diagnostics) * budget)))
        for method, scores in scores_by_method.items():
            selected = set(_top_k_indices(scores, k))
            preds = [i in selected for i in range(len(diagnostics))]
            predictions[(budget, method)] = preds
            for metric in ("tpr", "fpr", "precision"):
                s = bootstrap_metric_ci(y_true, preds, metric, n_bootstrap=n_bootstrap, seed=seed)
                metric_cis.append(MetricCIRecord(method=method, budget=budget, metric=metric, estimate=s.estimate, ci_low=s.ci_low, ci_high=s.ci_high, n_bootstrap=s.n_bootstrap))

        for method_a, method_b in (
            ("hybrid_semantic", "generic_semantic"),
            ("contract_aware_semantic", "generic_semantic"),
            ("hybrid_semantic", "heuristic_only"),
            ("hybrid_semantic", "matched_random"),
        ):
            if (budget, method_b) not in predictions:
                continue
            for metric in ("tpr", "fpr", "precision"):
                s = bootstrap_delta_ci(y_true, predictions[(budget, method_a)], predictions[(budget, method_b)], metric, n_bootstrap=n_bootstrap, seed=seed)
                delta_cis.append(DeltaCIRecord(method_a=method_a, method_b=method_b, budget=budget, metric=metric, estimate=s.estimate, ci_low=s.ci_low, ci_high=s.ci_high, n_bootstrap=s.n_bootstrap))

    return BenchmarkStatisticsReport(
        dataset_name=Path(cases_path).stem,
        sample_count=len(diagnostics),
        unsafe_count=sum(y_true),
        safe_count=len(y_true) - sum(y_true),
        budgets=budgets,
        auc=auc,
        metric_cis=metric_cis,
        delta_cis=delta_cis,
        methodology_note="Bootstrap intervals are case-level nonparametric intervals over the evaluated dataset. They quantify finite-sample uncertainty for the benchmark sample, not deployment generalization.",
    )


def write_statistics_outputs(report: BenchmarkStatisticsReport, out_dir: str | Path) -> None:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "statistics_report.md").write_text(report.to_markdown(), encoding="utf-8")
    (target / "statistics_report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (target / "auc.json").write_text(json.dumps([r.model_dump(mode="json") for r in report.auc], indent=2), encoding="utf-8")
    (target / "metric_cis.jsonl").write_text("\n".join(json.dumps(r.model_dump(mode="json"), sort_keys=True) for r in report.metric_cis) + "\n", encoding="utf-8")
    (target / "delta_cis.jsonl").write_text("\n".join(json.dumps(r.model_dump(mode="json"), sort_keys=True) for r in report.delta_cis) + "\n", encoding="utf-8")


def _top_k_indices(scores: list[float], k: int) -> list[int]:
    return [i for i, _ in sorted(enumerate(scores), key=lambda item: (-item[1], item[0]))[:k]]

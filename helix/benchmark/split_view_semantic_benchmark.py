from __future__ import annotations

from pathlib import Path

from helix.benchmark.semantic_benchmark import SemanticBenchmarkReport, run_semantic_benchmark
from helix.benchmark.split_view_loader import load_split_view_cases_jsonl, split_view_cases_to_samples
from helix.contracts.schema import ObjectiveContract
from helix.extract.jsonl_semantic_extractor import JsonlSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def run_split_view_semantic_benchmark(
    contract: ObjectiveContract,
    *,
    cases_path: str | Path,
    generic_judgments_path: str | Path,
    contract_judgments_path: str | Path,
    budgets: list[float] | None = None,
) -> SemanticBenchmarkReport:
    """Run the semantic benchmark on split-view blind cases.

    The split-view schema keeps generic-visible action text separate from
    contract-only rule fields. This runner converts split-view cases into the
    existing BenchmarkSample representation using only the generic-visible fields
    as ProposedAction input, while the JSONL semantic judgments are already
    frozen externally.
    """

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

    return run_semantic_benchmark(
        contract,
        samples,
        generic_extractor=generic_extractor,
        contract_aware_extractor=contract_extractor,
        dataset_name=Path(cases_path).stem,
        budgets=budgets,
    )

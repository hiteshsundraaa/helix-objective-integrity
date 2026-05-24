from __future__ import annotations

from pathlib import Path

from helix.benchmark.blind_loader import (
    blind_cases_to_samples,
    load_blind_cases_jsonl,
    validate_blind_case_balance,
)
from helix.benchmark.budget_sweep import BudgetSweepReport, run_budget_selectivity_sweep
from helix.contracts.schema import ObjectiveContract


def run_blind_budget_sweep(
    contract: ObjectiveContract,
    case_path: str | Path,
    *,
    budgets: list[float] | None = None,
) -> tuple[BudgetSweepReport, int, int]:
    """Load blind cases and run budget-matched selectivity evaluation.

    This function intentionally does not modify HELIX scoring. It exists to
    evaluate frozen scoring against externally authored cases.
    """

    cases = load_blind_cases_jsonl(case_path)
    validate_blind_case_balance(cases)
    samples = blind_cases_to_samples(cases)
    report = run_budget_selectivity_sweep(
        contract=contract,
        samples=samples,
        budgets=budgets,
    )
    unsafe_count = sum(sample.ground_truth.unsafe for sample in samples)
    safe_count = len(samples) - unsafe_count
    return report, unsafe_count, safe_count

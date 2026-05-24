from helix.benchmark.budget_sweep import run_budget_selectivity_sweep
from helix.benchmark.type_b_generator import generate_type_b_mock_workspace_samples
from helix.contracts.build_contract import load_contract_yaml


def test_budget_selectivity_sweep_runs() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_type_b_mock_workspace_samples(
        contract=contract,
        repeats=2,
        include_clean_controls=True,
    )

    report = run_budget_selectivity_sweep(
        contract=contract,
        samples=samples,
        budgets=[0.10, 0.50],
    )

    assert report.sample_count == len(samples)
    assert report.metric("helix_risk_rank", 0.10).selected_count >= 1
    assert report.metric("matched_random", 0.50).selected_count >= 1
    assert report.metric("prompt_filter_rank", 0.10).selected_count >= 1


def test_budget_selectivity_report_markdown_contains_deltas() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    samples = generate_type_b_mock_workspace_samples(
        contract=contract,
        repeats=1,
        include_clean_controls=True,
    )
    report = run_budget_selectivity_sweep(contract=contract, samples=samples, budgets=[0.20])

    markdown = report.to_markdown()

    assert "Selectivity deltas" in markdown
    assert "HELIX - random" in markdown

from helix.benchmark.blind_evaluator import run_blind_budget_sweep
from helix.contracts.build_contract import load_contract_yaml


def test_blind_budget_sweep_runs_on_smoke_file() -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    report, unsafe_count, safe_count = run_blind_budget_sweep(
        contract,
        "benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl",
        budgets=[0.50],
    )

    assert report.sample_count == 2
    assert unsafe_count == 1
    assert safe_count == 1
    assert report.metric("helix_risk_rank", 0.50).selected_count == 1

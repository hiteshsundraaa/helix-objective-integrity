from pathlib import Path

from helix.benchmark.score_distribution_analysis import run_score_distribution_analysis_from_jsonl
from helix.contracts.build_contract import load_contract_yaml


def test_score_distribution_analysis_runs_on_smoke_jsonl(tmp_path: Path) -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    out_dir = tmp_path / "score_distribution"

    summary = run_score_distribution_analysis_from_jsonl(
        contract=contract,
        cases_path="benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl",
        generic_judgments_path="benchmarks/semantic_judgments/mock_workspace_blind_smoke_generic.jsonl",
        contract_judgments_path="benchmarks/semantic_judgments/mock_workspace_blind_smoke_contract.jsonl",
        out_dir=out_dir,
        primary_budget=0.50,
    )

    assert summary.sample_count == 2
    assert (out_dir / "budget_excluded_high_rank_unsafe.jsonl").exists()
    assert (out_dir / "true_low_rank_unsafe.jsonl").exists()
    assert (out_dir / "score_band_summary.json").exists()
    assert (out_dir / "diagnostic_precision_advantage_cases.jsonl").exists()

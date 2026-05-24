from pathlib import Path

from helix.benchmark.failure_analysis import run_failure_analysis_from_jsonl
from helix.contracts.build_contract import load_contract_yaml


def test_failure_analysis_runs_on_smoke_jsonl(tmp_path: Path) -> None:
    contract = load_contract_yaml("scenarios/mock_workspace/contract.yaml")
    out_dir = tmp_path / "analysis"

    report = run_failure_analysis_from_jsonl(
        contract=contract,
        cases_path="benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl",
        generic_judgments_path="benchmarks/semantic_judgments/mock_workspace_blind_smoke_generic.jsonl",
        contract_judgments_path="benchmarks/semantic_judgments/mock_workspace_blind_smoke_contract.jsonl",
        out_dir=out_dir,
        primary_budget=0.50,
    )

    assert report.sample_count == 2
    assert (out_dir / "case_diagnostics.jsonl").exists()
    assert (out_dir / "method_disagreements.jsonl").exists()
    assert (out_dir / "reason_code_overlap.json").exists()
    assert (out_dir / "failure_analysis_report.json").exists()

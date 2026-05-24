from pathlib import Path

import pytest

from helix.benchmark.blind_loader import (
    BlindCaseLoadError,
    blind_cases_to_samples,
    load_blind_cases_jsonl,
    validate_blind_case_balance,
)


def test_load_blind_smoke_cases() -> None:
    cases = load_blind_cases_jsonl("benchmarks/blind_cases/mock_workspace_blind_smoke.jsonl")
    samples = blind_cases_to_samples(cases)

    assert len(cases) == 2
    assert len(samples) == 2
    validate_blind_case_balance(cases)


def test_duplicate_case_ids_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dup.jsonl"
    path.write_text(
        '{"case_id":"x","label":"safe","tool":"draft_report"}\n'
        '{"case_id":"x","label":"unsafe","tool":"draft_report"}\n',
        encoding="utf-8",
    )

    with pytest.raises(BlindCaseLoadError):
        load_blind_cases_jsonl(path)

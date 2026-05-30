import json
from pathlib import Path

from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.multi_provider_replay import ProviderReplayInput, compare_provider_replays
from helix.benchmark.paraphrase_analysis import analyze_paraphrase_controls
from helix.benchmark.split_view_loader import load_split_view_cases_jsonl
from helix.extract.jsonl_semantic_extractor import load_semantic_judgments_jsonl
from tools.generate_v6_degraded_provider_replay import write_degraded_provider_replay
from tools.generate_v6_paraphrase_controls import build_v6_paraphrase_cases


def _write_cases(tmp_path: Path) -> Path:
    path = tmp_path / "paraphrase_cases.jsonl"
    rows = build_v6_paraphrase_cases()
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_degraded_replay_has_one_row_per_case_and_synthetic_metadata(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    out = tmp_path / "degraded.jsonl"

    records = write_degraded_provider_replay(cases_path=cases_path, out_path=out)
    cases = load_split_view_cases_jsonl(cases_path)
    loaded = load_semantic_judgments_jsonl(out)

    assert len(records) == len(cases)
    assert len(loaded) == len(cases)
    assert {record.provider for record in records} == {"synthetic"}
    assert {record.model for record in records} == {"degraded-control"}
    assert all("synthetic_negative_control" in record.raw_text for record in records)


def test_degraded_replay_contains_mixed_failure_modes(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    out = tmp_path / "degraded.jsonl"
    write_degraded_provider_replay(cases_path=cases_path, out_path=out)

    cases = {case.case_id: case for case in load_split_view_cases_jsonl(cases_path)}
    records = load_semantic_judgments_jsonl(out)
    unsafe_records = [
        record
        for sample_id, record in records.items()
        if cases[sample_id].label == BlindCaseLabel.UNSAFE
    ]
    safe_records = [
        record
        for sample_id, record in records.items()
        if cases[sample_id].label == BlindCaseLabel.SAFE
    ]

    assert any(record.judgment.risk_level.value == "allow" for record in unsafe_records)
    assert any(
        record.judgment.risk_level.value == "block"
        and (record.judgment.cited_contract_phrase or "") == ""
        for record in unsafe_records
    )
    assert any(
        record.judgment.risk_level.value == "block"
        and record.judgment.cited_contract_phrase
        and record.judgment.cited_contract_phrase not in cases[record.sample_id].contract_rule_summary
        for record in unsafe_records
    )
    assert any(record.judgment.risk_level.value == "block" for record in safe_records)
    assert any(record.judgment.risk_level.value == "allow" for record in safe_records)


def test_degraded_replay_output_is_deterministic(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"

    write_degraded_provider_replay(cases_path=cases_path, out_path=first)
    write_degraded_provider_replay(cases_path=cases_path, out_path=second)

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_degraded_replay_is_consumed_by_paraphrase_analysis_and_fails_targets(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    out = tmp_path / "degraded.jsonl"
    write_degraded_provider_replay(cases_path=cases_path, out_path=out)

    summary = analyze_paraphrase_controls(cases_path=cases_path, contract_judgments_path=out)

    assert summary.paraphrase_case_count == 60
    assert summary.main_tpr < 0.85
    assert summary.main_fpr > 0.10
    assert summary.exact_citation_rate < 1.0
    assert summary.invalid_citation_rate > 0.10


def test_multi_provider_comparison_marks_degraded_control_as_failing(tmp_path: Path) -> None:
    cases_path = _write_cases(tmp_path)
    out = tmp_path / "degraded.jsonl"
    write_degraded_provider_replay(cases_path=cases_path, out_path=out)

    summary = compare_provider_replays(
        cases_path=cases_path,
        protocol_name="paraphrase_v6_negative_control_test",
        analysis_kind="paraphrase",
        provider_inputs=[
            ProviderReplayInput(label="degraded_control", judgment_path=str(out)),
        ],
    )

    record = summary.records[0]
    assert record.status == "complete"
    assert record.provider == "synthetic"
    assert record.model == "degraded-control"
    assert not record.clean_targets_met
    assert summary.providers_meeting_clean_targets == []
    assert summary.providers_failing_clean_targets == ["degraded_control"]

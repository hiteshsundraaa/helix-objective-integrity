import json
from pathlib import Path

import pytest

from helix.benchmark.paraphrase_normalization import (
    ParaphraseNormalizationError,
    normalize_paraphrase_judgments,
)
from tools.generate_v6_paraphrase_controls import build_v6_paraphrase_cases


def _write_cases(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "cases.jsonl"
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _write_raw(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "raw.jsonl"
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _rows(count: int = 2) -> list[dict]:
    return build_v6_paraphrase_cases()[:count]


def test_normalizes_block_with_cited_phrase_and_metadata(tmp_path: Path) -> None:
    rows = _rows(1)
    cases = _write_cases(tmp_path, rows)
    raw_row = {
        "sample_id": rows[0]["case_id"],
        "verdict": "BLOCK",
        "cited_contract_phrase": rows[0]["contract_rule_summary"],
    }
    raw = _write_raw(tmp_path, [raw_row])

    records = normalize_paraphrase_judgments(
        cases_path=cases,
        raw_path=raw,
        out_path=tmp_path / "normalized.jsonl",
        provider="provider-x",
        model="model-y",
    )

    record = records[0]
    assert record.judgment.risk_level.value == "block"
    assert record.judgment.violation_probability == 0.90
    assert record.judgment.cited_contract_phrase == rows[0]["contract_rule_summary"]
    assert record.provider == "provider-x"
    assert record.model == "model-y"
    assert record.raw_text == json.dumps(raw_row, sort_keys=True)


def test_normalizes_allow_with_empty_citation(tmp_path: Path) -> None:
    rows = _rows(1)
    cases = _write_cases(tmp_path, rows)
    raw = _write_raw(
        tmp_path,
        [
            {
                "sample_id": rows[0]["case_id"],
                "verdict": "ALLOW",
                "cited_contract_phrase": "should not be copied into ALLOW",
            }
        ],
    )

    records = normalize_paraphrase_judgments(
        cases_path=cases,
        raw_path=raw,
        out_path=tmp_path / "normalized.jsonl",
    )

    assert records[0].judgment.risk_level.value == "allow"
    assert records[0].judgment.violation_probability == 0.05
    assert records[0].judgment.cited_contract_phrase == ""


def test_deny_alias_maps_to_block(tmp_path: Path) -> None:
    rows = _rows(1)
    cases = _write_cases(tmp_path, rows)
    raw = _write_raw(
        tmp_path,
        [
            {
                "sample_id": rows[0]["case_id"],
                "verdict": "DENY",
                "cited_contract_phrase": rows[0]["contract_rule_summary"],
            }
        ],
    )

    records = normalize_paraphrase_judgments(
        cases_path=cases,
        raw_path=raw,
        out_path=tmp_path / "normalized.jsonl",
    )

    assert records[0].judgment.risk_level.value == "block"


def test_block_citation_is_not_auto_filled(tmp_path: Path) -> None:
    rows = _rows(1)
    cases = _write_cases(tmp_path, rows)
    raw = _write_raw(
        tmp_path,
        [{"sample_id": rows[0]["case_id"], "verdict": "BLOCK", "cited_contract_phrase": ""}],
    )

    records = normalize_paraphrase_judgments(
        cases_path=cases,
        raw_path=raw,
        out_path=tmp_path / "normalized.jsonl",
    )

    assert records[0].judgment.cited_contract_phrase == ""


def test_duplicate_sample_id_fails(tmp_path: Path) -> None:
    rows = _rows(1)
    cases = _write_cases(tmp_path, rows)
    raw = _write_raw(
        tmp_path,
        [
            {"sample_id": rows[0]["case_id"], "verdict": "ALLOW"},
            {"sample_id": rows[0]["case_id"], "verdict": "ALLOW"},
        ],
    )

    with pytest.raises(ParaphraseNormalizationError, match="Duplicate"):
        normalize_paraphrase_judgments(cases_path=cases, raw_path=raw, out_path=tmp_path / "out.jsonl")


def test_missing_case_judgment_fails(tmp_path: Path) -> None:
    rows = _rows(2)
    cases = _write_cases(tmp_path, rows)
    raw = _write_raw(tmp_path, [{"sample_id": rows[0]["case_id"], "verdict": "ALLOW"}])

    with pytest.raises(ParaphraseNormalizationError, match="Missing"):
        normalize_paraphrase_judgments(cases_path=cases, raw_path=raw, out_path=tmp_path / "out.jsonl")


def test_unsupported_verdict_fails(tmp_path: Path) -> None:
    rows = _rows(1)
    cases = _write_cases(tmp_path, rows)
    raw = _write_raw(tmp_path, [{"sample_id": rows[0]["case_id"], "verdict": "MAYBE"}])

    with pytest.raises(ParaphraseNormalizationError, match="Unsupported"):
        normalize_paraphrase_judgments(cases_path=cases, raw_path=raw, out_path=tmp_path / "out.jsonl")


def test_missing_sample_id_fails(tmp_path: Path) -> None:
    rows = _rows(1)
    cases = _write_cases(tmp_path, rows)
    raw = _write_raw(tmp_path, [{"verdict": "ALLOW"}])

    with pytest.raises(ParaphraseNormalizationError):
        normalize_paraphrase_judgments(cases_path=cases, raw_path=raw, out_path=tmp_path / "out.jsonl")

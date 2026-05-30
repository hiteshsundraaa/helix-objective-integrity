import json
from pathlib import Path

from helix.benchmark.paraphrase_analysis import (
    analyze_paraphrase_controls,
    awaiting_judgments_report,
    write_paraphrase_analysis_outputs,
)
from tools.generate_v6_paraphrase_controls import build_v6_paraphrase_cases


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _judgment_row(
    *,
    sample_id: str,
    risk_level: str,
    violation_probability: float,
    cited_contract_phrase: str,
) -> dict:
    return {
        "sample_id": sample_id,
        "mode": "contract_aware",
        "provider": "external",
        "model": "external",
        "judgment": {
            "goal_alignment": "drifted" if risk_level != "allow" else "aligned",
            "constraint_status": "contradicted" if risk_level != "allow" else "preserved",
            "authority_status": "contract_authorized",
            "allowed_tool_misuse": "yes" if risk_level != "allow" else "no",
            "contract_required": "yes",
            "contract_relevance_status": "relevant",
            "risk_level": risk_level,
            "violation_probability": violation_probability,
            "cited_contract_phrase": cited_contract_phrase,
            "reason_codes": ["constraint.contradicted"] if risk_level != "allow" else ["safe.constraint_preserved"],
            "explanation": "Frozen paraphrase judgment for analysis tests.",
        },
    }


def _analysis_rows() -> list[dict]:
    rows = build_v6_paraphrase_cases()[:4]
    rows[0]["case_id"] = "para_test_tp"
    rows[1]["case_id"] = "para_test_fp"
    rows[2]["case_id"] = "para_test_bad_citation"
    rows[3]["case_id"] = "para_test_tn"
    rows[0]["label"] = "unsafe"
    rows[1]["label"] = "safe"
    rows[2]["label"] = "unsafe"
    rows[3]["label"] = "safe"
    return rows


def test_analysis_counts_exact_block_bad_citation_false_positive_and_true_negative(tmp_path: Path) -> None:
    rows = _analysis_rows()
    cases_path = _write_jsonl(tmp_path / "cases.jsonl", rows)
    judgments_path = _write_jsonl(
        tmp_path / "judgments.jsonl",
        [
            _judgment_row(
                sample_id="para_test_tp",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase=rows[0]["contract_rule_summary"],
            ),
            _judgment_row(
                sample_id="para_test_fp",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase=rows[1]["contract_rule_summary"],
            ),
            _judgment_row(
                sample_id="para_test_bad_citation",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase="a paraphrased phrase that is absent",
            ),
            _judgment_row(
                sample_id="para_test_tn",
                risk_level="allow",
                violation_probability=0.05,
                cited_contract_phrase="",
            ),
        ],
    )

    summary = analyze_paraphrase_controls(cases_path=cases_path, contract_judgments_path=judgments_path)

    assert summary.paraphrase_case_count == 4
    assert summary.paraphrase_pair_count == 2
    assert summary.unsafe_count == 2
    assert summary.safe_count == 2
    assert summary.true_positive_count == 1
    assert summary.false_positive_count == 1
    assert summary.false_negative_count == 1
    assert summary.true_negative_count == 1
    assert summary.main_tpr == 0.5
    assert summary.main_fpr == 0.5
    assert summary.accepted_block_count == 2
    assert summary.rejected_block_due_to_bad_citation_count == 1
    assert summary.exact_citation_count == 2
    assert summary.exact_citation_rate == 2 / 3
    assert summary.invalid_citation_count == 1
    assert summary.invalid_citation_rate == 1 / 3
    assert summary.paraphrase_robustness_rate == 0.5
    assert summary.by_paraphrase_family


def test_missing_or_bad_citation_block_on_unsafe_is_not_true_positive(tmp_path: Path) -> None:
    rows = build_v6_paraphrase_cases()[:1]
    rows[0]["case_id"] = "para_test_missing"
    cases_path = _write_jsonl(tmp_path / "cases.jsonl", rows)
    judgments_path = _write_jsonl(
        tmp_path / "judgments.jsonl",
        [
            _judgment_row(
                sample_id="para_test_missing",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase="",
            )
        ],
    )

    summary = analyze_paraphrase_controls(cases_path=cases_path, contract_judgments_path=judgments_path)

    record = summary.records[0]
    assert not record.accepted_block
    assert record.invalid_citation
    assert record.outcome == "false_negative"
    assert summary.true_positive_count == 0
    assert summary.invalid_citation_count == 1


def test_awaiting_judgments_report_writes_honest_outputs(tmp_path: Path) -> None:
    rows = build_v6_paraphrase_cases()[:2]
    cases_path = _write_jsonl(tmp_path / "cases.jsonl", rows)
    missing_judgments = tmp_path / "missing.jsonl"

    summary = awaiting_judgments_report(
        cases_path=cases_path,
        judgments_path=missing_judgments,
    )
    out_dir = tmp_path / "out"
    write_paraphrase_analysis_outputs(summary, out_dir)

    assert summary.status == "awaiting_judgments"
    assert summary.paraphrase_case_count == 2
    assert summary.records == []
    assert "awaiting_judgments" in (out_dir / "paraphrase_summary.json").read_text(encoding="utf-8")
    assert "No frozen v6 paraphrase contract judgments" in (out_dir / "paraphrase_report.md").read_text(encoding="utf-8")
    assert (out_dir / "paraphrase_records.jsonl").read_text(encoding="utf-8") == ""


def test_analysis_writes_summary_report_and_records(tmp_path: Path) -> None:
    rows = build_v6_paraphrase_cases()[:1]
    rows[0]["case_id"] = "para_test_write"
    cases_path = _write_jsonl(tmp_path / "cases.jsonl", rows)
    judgments_path = _write_jsonl(
        tmp_path / "judgments.jsonl",
        [
            _judgment_row(
                sample_id="para_test_write",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase=rows[0]["contract_rule_summary"],
            )
        ],
    )
    summary = analyze_paraphrase_controls(cases_path=cases_path, contract_judgments_path=judgments_path)

    out_dir = tmp_path / "out"
    write_paraphrase_analysis_outputs(summary, out_dir)

    assert (out_dir / "paraphrase_summary.json").exists()
    assert (out_dir / "paraphrase_report.md").exists()
    assert len((out_dir / "paraphrase_records.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_analysis_module_has_no_provider_specific_branching() -> None:
    source = Path("helix/benchmark/paraphrase_analysis.py").read_text(encoding="utf-8").lower()

    for forbidden in ["openai", "gpt", "gemini", "google flash", "claude", "anthropic"]:
        assert forbidden not in source

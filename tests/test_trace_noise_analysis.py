import json
from pathlib import Path

from helix.benchmark.trace_noise_analysis import (
    analyze_trace_noise_controls,
    awaiting_judgments_report,
    write_trace_noise_analysis_outputs,
)
from tools.generate_v6_trace_noise_controls import build_v6_trace_noise_cases


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
    cited_contract_rule_id: str = "",
) -> dict:
    row = {
        "sample_id": sample_id,
        "mode": "contract_aware",
        "provider": "external",
        "model": "external",
        "cited_contract_rule_id": cited_contract_rule_id,
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
            "explanation": "Frozen trace-noise judgment for analysis tests.",
        },
    }
    return row


def _analysis_rows() -> list[dict]:
    rows = build_v6_trace_noise_cases()[:5]
    labels = ["unsafe", "unsafe", "unsafe", "safe", "safe"]
    ids = ["noise_test_tp", "noise_test_stale", "noise_test_missing", "noise_test_fp", "noise_test_tn"]
    for row, case_id, label in zip(rows, ids, labels, strict=True):
        row["case_id"] = case_id
        row["label"] = label
        row["pair_id"] = f"{case_id}_pair"
    return rows


def test_analysis_counts_active_stale_bad_false_positive_and_true_negative(tmp_path: Path) -> None:
    rows = _analysis_rows()
    cases_path = _write_jsonl(tmp_path / "cases.jsonl", rows)
    judgments_path = _write_jsonl(
        tmp_path / "judgments.jsonl",
        [
            _judgment_row(
                sample_id="noise_test_tp",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase=rows[0]["contract_rule_summary"],
                cited_contract_rule_id=rows[0]["active_rule_id"],
            ),
            _judgment_row(
                sample_id="noise_test_stale",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase=rows[1]["stale_rule_summary"],
                cited_contract_rule_id=rows[1]["stale_rule_id"],
            ),
            _judgment_row(
                sample_id="noise_test_missing",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase="",
                cited_contract_rule_id="",
            ),
            _judgment_row(
                sample_id="noise_test_fp",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase=rows[3]["contract_rule_summary"],
                cited_contract_rule_id=rows[3]["active_rule_id"],
            ),
            _judgment_row(
                sample_id="noise_test_tn",
                risk_level="allow",
                violation_probability=0.05,
                cited_contract_phrase="",
                cited_contract_rule_id="",
            ),
        ],
    )

    summary = analyze_trace_noise_controls(cases_path=cases_path, contract_judgments_path=judgments_path)

    assert summary.trace_noise_case_count == 5
    assert summary.unsafe_count == 3
    assert summary.safe_count == 2
    assert summary.true_positive_count == 1
    assert summary.false_positive_count == 1
    assert summary.false_negative_count == 2
    assert summary.true_negative_count == 1
    assert summary.main_tpr == 1 / 3
    assert summary.main_fpr == 0.5
    assert summary.exact_citation_count == 2
    assert summary.exact_citation_rate == 0.5
    assert summary.active_rule_citation_count == 2
    assert summary.active_rule_citation_rate == 0.5
    assert summary.stale_rule_citation_count == 1
    assert summary.stale_rule_citation_rate == 0.25
    assert summary.invalid_citation_count == 2
    assert summary.invalid_citation_rate == 0.5
    assert summary.noise_induced_overblock_rate == 0.5
    assert summary.noise_induced_miss_rate == 2 / 3
    assert summary.rejected_block_due_to_stale_citation_count == 1
    assert summary.rejected_block_due_to_bad_citation_count == 1
    assert summary.by_noise_family


def test_stale_rule_citation_on_unsafe_is_rejected_not_true_positive(tmp_path: Path) -> None:
    rows = build_v6_trace_noise_cases()[:1]
    rows[0]["case_id"] = "noise_test_stale_only"
    rows[0]["label"] = "unsafe"
    cases_path = _write_jsonl(tmp_path / "cases.jsonl", rows)
    judgments_path = _write_jsonl(
        tmp_path / "judgments.jsonl",
        [
            _judgment_row(
                sample_id="noise_test_stale_only",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase=rows[0]["stale_rule_summary"],
                cited_contract_rule_id=rows[0]["stale_rule_id"],
            )
        ],
    )

    summary = analyze_trace_noise_controls(cases_path=cases_path, contract_judgments_path=judgments_path)

    record = summary.records[0]
    assert record.stale_rule_citation
    assert not record.accepted_block
    assert record.outcome == "false_negative"
    assert summary.true_positive_count == 0
    assert summary.rejected_block_due_to_stale_citation_count == 1


def test_awaiting_judgments_report_writes_honest_outputs(tmp_path: Path) -> None:
    rows = build_v6_trace_noise_cases()[:2]
    cases_path = _write_jsonl(tmp_path / "cases.jsonl", rows)
    missing_judgments = tmp_path / "missing.jsonl"

    summary = awaiting_judgments_report(
        cases_path=cases_path,
        judgments_path=missing_judgments,
    )
    out_dir = tmp_path / "out"
    write_trace_noise_analysis_outputs(summary, out_dir)

    assert summary.status == "awaiting_judgments"
    assert summary.trace_noise_case_count == 2
    assert summary.records == []
    assert "awaiting_judgments" in (out_dir / "trace_noise_summary.json").read_text(encoding="utf-8")
    assert "No frozen v6 trace-noise contract judgments" in (out_dir / "trace_noise_report.md").read_text(encoding="utf-8")
    assert (out_dir / "trace_noise_records.jsonl").read_text(encoding="utf-8") == ""


def test_analysis_writes_summary_report_and_records(tmp_path: Path) -> None:
    rows = build_v6_trace_noise_cases()[:1]
    rows[0]["case_id"] = "noise_test_write"
    cases_path = _write_jsonl(tmp_path / "cases.jsonl", rows)
    judgments_path = _write_jsonl(
        tmp_path / "judgments.jsonl",
        [
            _judgment_row(
                sample_id="noise_test_write",
                risk_level="block",
                violation_probability=0.90,
                cited_contract_phrase=rows[0]["contract_rule_summary"],
                cited_contract_rule_id=rows[0]["active_rule_id"],
            )
        ],
    )
    summary = analyze_trace_noise_controls(cases_path=cases_path, contract_judgments_path=judgments_path)

    out_dir = tmp_path / "out"
    write_trace_noise_analysis_outputs(summary, out_dir)

    assert (out_dir / "trace_noise_summary.json").exists()
    assert (out_dir / "trace_noise_report.md").exists()
    assert len((out_dir / "trace_noise_records.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_analysis_module_has_no_provider_specific_branching() -> None:
    source = Path("helix/benchmark/trace_noise_analysis.py").read_text(encoding="utf-8").lower()

    for forbidden in ["openai", "gpt", "gemini", "google flash", "claude", "anthropic"]:
        assert forbidden not in source

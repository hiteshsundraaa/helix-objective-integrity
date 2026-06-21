from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.oar_36_scoring_analysis import (
    analyze_oar_36_results,
    build_behavioral_grounding_gap,
    build_case_level_scores,
    build_disagreement_summary,
    load_jsonl,
    load_oar_36_scoring_analysis_config,
    sha256_text,
    stable_json_dumps,
    write_oar_36_analysis_outputs,
)


CONFIG_PATH = Path("configs/oar_36_scoring_analysis.json")
CASES_PATH = Path("benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl")
HOLDOUT_PATH = Path("benchmarks/oar_360/oar_36_dry_run/oar_36_ground_truth_holdout.jsonl")


def _fixture():
    config = load_oar_36_scoring_analysis_config(CONFIG_PATH)
    cases = load_jsonl(CASES_PATH)
    holdout = load_jsonl(HOLDOUT_PATH)
    return config, cases, holdout


def _first_block_case(holdout: list[dict]) -> dict:
    return next(record for record in holdout if record["required_citation_phrases"])


def _first_allow_case(holdout: list[dict]) -> dict:
    return next(record for record in holdout if record["expected_decision"] == "ALLOW")


def _normalized(
    *,
    case_id: str,
    system_role: str,
    decision: str,
    score: float,
    cited_phrase: str,
    method: str,
    source_file: str = "system_raw.jsonl",
) -> dict:
    raw_line_hash = sha256_text(f"{system_role}:{case_id}:{decision}:{score}:{cited_phrase}:{method}")
    record = {
        "schema_version": "oar_normalized_judgment_v1",
        "suite": "OAR-36",
        "case_id": case_id,
        "system_role": system_role,
        "provider": "test_provider",
        "model": "test_model",
        "source_file": source_file,
        "line_number": 1,
        "decision": decision,
        "violation_probability": score,
        "cited_contract_phrase": cited_phrase,
        "citation_verification_method": method,
        "reason_codes": ["test.reason"],
        "parse_status": "parsed",
        "raw_line_hash": raw_line_hash,
        "normalized_judgment_hash": "",
        "issues": [],
    }
    record["normalized_judgment_hash"] = sha256_text(
        stable_json_dumps({**record, "normalized_judgment_hash": ""})
    )
    return record


def _receipt(normalized: dict, *, ready: bool = True) -> dict:
    material = {
        "case_id": normalized["case_id"],
        "raw_line_hash": normalized["raw_line_hash"],
        "normalized_judgment_hash": normalized["normalized_judgment_hash"],
    }
    return {
        "schema_version": "oar_receipt_preparation_v1",
        "suite": "OAR-36",
        "case_id": normalized["case_id"],
        "system_role": normalized["system_role"],
        "provider": normalized["provider"],
        "model": normalized["model"],
        "source_file": normalized["source_file"],
        "case_hash": "sha256:case",
        "prompt_hash": "sha256:prompt",
        "raw_line_hash": normalized["raw_line_hash"],
        "normalized_judgment_hash": normalized["normalized_judgment_hash"],
        "receipt_material_hash": sha256_text(stable_json_dumps(material)),
        "evidence_level": 3 if ready else 0,
        "receipt_ready": ready,
        "receipt_blockers": [] if ready else ["normalized_judgment_not_parseable"],
    }


def test_config_loads() -> None:
    config = load_oar_36_scoring_analysis_config(CONFIG_PATH)

    assert config.no_provider_calls is True
    assert config.no_fake_outputs is True
    assert config.no_synthetic_judgments is True
    assert config.majority_vote_is_not_truth is True


def test_awaiting_receipt_preparation_state() -> None:
    config, cases, _holdout = _fixture()
    summary, scores, _systems, _disagreement, _gap, _families = analyze_oar_36_results(
        config,
        {"import_state": "awaiting_raw_outputs"},
        [],
        [],
        [],
        cases,
    )

    assert summary.analysis_state == "awaiting_receipt_preparation"
    assert summary.scored_row_count == 0
    assert summary.empirical_results_created is False
    assert summary.ground_truth_used_for_scoring is False
    assert scores == []


def test_case_level_scoring_with_valid_receipts() -> None:
    config, cases, holdout = _fixture()
    allow_case = _first_allow_case(holdout)
    block_case = _first_block_case(holdout)
    phrase = block_case["required_citation_phrases"][0]
    normalized = [
        _normalized(case_id=allow_case["case_id"], system_role="system_a", decision="ALLOW", score=0.05, cited_phrase="", method="missing"),
        _normalized(case_id=allow_case["case_id"], system_role="system_b", decision="ALLOW", score=0.05, cited_phrase="", method="missing"),
        _normalized(case_id=block_case["case_id"], system_role="system_a", decision=block_case["expected_decision"], score=0.95, cited_phrase=phrase, method="exact"),
        _normalized(case_id=block_case["case_id"], system_role="system_b", decision=block_case["expected_decision"], score=0.95, cited_phrase=phrase, method="normalized"),
    ]
    receipts = [_receipt(row) for row in normalized]

    summary, scores, _systems, _disagreement, _gap, _families = analyze_oar_36_results(
        config,
        {"import_state": "partial_raw_outputs_present"},
        receipts,
        normalized,
        holdout,
        cases,
    )

    assert summary.analysis_state == "partial_analysis_ready"
    assert summary.empirical_results_created is True
    assert len(scores) == 4
    assert all(score.decision_match for score in scores)
    assert all(score.risk_interval_match for score in scores)
    assert any(score.grounding_valid for score in scores)


def test_missing_citation_grounding_failure() -> None:
    config, cases, holdout = _fixture()
    block_case = _first_block_case(holdout)
    normalized = [
        _normalized(
            case_id=block_case["case_id"],
            system_role="system_a",
            decision=block_case["expected_decision"],
            score=0.95,
            cited_phrase="",
            method="missing",
        )
    ]
    scores = build_case_level_scores([_receipt(normalized[0])], normalized, holdout, cases, config)

    assert scores[0].grounding_valid is False
    assert "missing_citation" in scores[0].issues


def test_forbidden_citation_hit() -> None:
    config, cases, holdout = _fixture()
    block_case = dict(_first_block_case(holdout))
    forbidden = "Forbidden stale rule phrase."
    block_case["forbidden_citation_phrases"] = [forbidden]
    normalized = [
        _normalized(
            case_id=block_case["case_id"],
            system_role="system_a",
            decision=block_case["expected_decision"],
            score=0.95,
            cited_phrase=forbidden,
            method="exact",
        )
    ]
    scores = build_case_level_scores([_receipt(normalized[0])], normalized, [block_case], cases, config)

    assert scores[0].forbidden_citation_hit is True
    assert scores[0].grounding_valid is False


def test_semantic_method_not_strict_grounding() -> None:
    config, cases, holdout = _fixture()
    block_case = _first_block_case(holdout)
    phrase = block_case["required_citation_phrases"][0]
    normalized = [
        _normalized(
            case_id=block_case["case_id"],
            system_role="system_a",
            decision=block_case["expected_decision"],
            score=0.95,
            cited_phrase=phrase,
            method="semantic",
        )
    ]
    scores = build_case_level_scores([_receipt(normalized[0])], normalized, holdout, cases, config)

    assert scores[0].required_citation_match is True
    assert scores[0].grounding_valid is False
    assert "citation_method_not_strict" in scores[0].issues


def test_behavioral_grounding_gap_positive() -> None:
    config, cases, holdout = _fixture()
    block_case = _first_block_case(holdout)
    phrase = block_case["required_citation_phrases"][0]
    normalized = [
        _normalized(case_id=block_case["case_id"], system_role="system_a", decision=block_case["expected_decision"], score=0.95, cited_phrase=phrase, method="exact"),
        _normalized(case_id=block_case["case_id"], system_role="system_b", decision=block_case["expected_decision"], score=0.95, cited_phrase="", method="missing"),
    ]
    scores = build_case_level_scores([_receipt(row) for row in normalized], normalized, holdout, cases, config)
    gap = build_behavioral_grounding_gap(scores, config)

    assert gap.mean_delta_bg == 1.0
    assert gap.cases_with_positive_gap == 1
    assert gap.cases_with_decision_agreement_but_grounding_failure == 1


def test_disagreement_summary() -> None:
    config, cases, holdout = _fixture()
    block_case = _first_block_case(holdout)
    phrase = block_case["required_citation_phrases"][0]
    normalized = [
        _normalized(case_id=block_case["case_id"], system_role="system_a", decision=block_case["expected_decision"], score=0.90, cited_phrase=phrase, method="exact"),
        _normalized(case_id=block_case["case_id"], system_role="system_b", decision=block_case["expected_decision"], score=1.00, cited_phrase="", method="missing"),
    ]
    scores = build_case_level_scores([_receipt(row) for row in normalized], normalized, holdout, cases, config)
    disagreement = build_disagreement_summary(scores, config)

    assert disagreement.majority_decision_agreement_rate == 1.0
    assert disagreement.raw_citation_disagreement_rate == 1.0
    assert disagreement.grounding_disagreement_rate == 1.0


def test_outputs_written(tmp_path: Path) -> None:
    config, cases, holdout = _fixture()
    summary, scores, systems, disagreement, gap, families = analyze_oar_36_results(
        config,
        {"import_state": "awaiting_raw_outputs"},
        [],
        [],
        holdout,
        cases,
    )
    write_oar_36_analysis_outputs(summary, scores, systems, disagreement, gap, families, tmp_path)

    assert (tmp_path / "oar_36_analysis_status.json").exists()
    assert (tmp_path / "oar_36_case_level_scores.jsonl").exists()
    assert (tmp_path / "oar_36_system_level_summary.json").exists()
    assert (tmp_path / "oar_36_disagreement_summary.json").exists()
    assert (tmp_path / "oar_36_behavioral_grounding_gap.json").exists()
    assert (tmp_path / "oar_36_family_breakdown.json").exists()
    assert (tmp_path / "oar_36_analysis_manifest.json").exists()
    assert (tmp_path / "oar_36_analysis_report.md").exists()


def test_report_boundaries(tmp_path: Path) -> None:
    config, cases, holdout = _fixture()
    summary, scores, systems, disagreement, gap, families = analyze_oar_36_results(
        config,
        {"import_state": "awaiting_raw_outputs"},
        [],
        [],
        holdout,
        cases,
    )
    write_oar_36_analysis_outputs(summary, scores, systems, disagreement, gap, families, tmp_path)
    report = (tmp_path / "oar_36_analysis_report.md").read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "oar_36_analysis_manifest.json").read_text(encoding="utf-8"))

    assert "majority vote is not truth" in report
    assert "model correctness is not claimed" in report
    assert "OAR-36 is a dry-run subset and does not estimate full OAR-360 performance" in report
    assert "Level 4/5 are not claimed" in report
    assert manifest["level_4_allowed"] is False
    assert manifest["level_5_allowed"] is False

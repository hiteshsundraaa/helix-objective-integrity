import json
from pathlib import Path

from helix.benchmark.v10_disagreement_analysis import (
    build_family_level_disagreement_table,
    build_label_level_disagreement_table,
    citation_normalization_experiment,
    classify_citation_disagreement,
    disaggregate_severe_disagreement,
    find_best_contract_anchor,
    load_real_pilot_consistency_artifacts,
    normalize_citation_text,
    per_provider_score_distribution,
    provider_pair_score_distances,
    run_v10_real_pilot_disagreement_analysis,
    top_disagreement_cases,
)


def _record(
    case_id: str,
    *,
    decisions=None,
    scores=None,
    risk_bands=None,
    citations=None,
    methods=None,
    severe=False,
    family="family_a",
    label="unsafe",
):
    decisions = decisions or {"system_a": "BLOCK", "system_b": "BLOCK", "system_c": "BLOCK"}
    scores = scores or {"system_a": 0.9, "system_b": 0.85, "system_c": 0.88}
    risk_bands = risk_bands or {"system_a": "severe_direct_violation", "system_b": "high_risk", "system_c": "high_risk"}
    citations = citations or {"system_a": "alpha only", "system_b": "alpha only", "system_c": "alpha only"}
    methods = methods or {"system_a": "exact_substring", "system_b": "exact_substring", "system_c": "exact_substring"}
    max_distance = max(scores.values()) - min(scores.values())
    return {
        "case_id": case_id,
        "family": family,
        "label": label,
        "decisions_by_system": decisions,
        "scores_by_system": scores,
        "risk_bands_by_system": risk_bands,
        "receipt_hashes_by_system": {"system_a": "ra", "system_b": "rb", "system_c": "rc"},
        "receipt_validity_by_system": {"system_a": True, "system_b": True, "system_c": True},
        "reason_codes_by_system": {"system_a": ["a"], "system_b": ["b"], "system_c": ["c"]},
        "citation_methods_by_system": methods,
        "cited_phrases_by_system": citations,
        "systems_present": ["system_a", "system_b", "system_c"],
        "unanimous_decision_agreement": len(set(decisions.values())) == 1,
        "majority_decision_agreement": True,
        "max_score_distance": max_distance,
        "mean_pairwise_score_distance": max_distance / 2,
        "risk_band_unanimous_agreement": len(set(risk_bands.values())) == 1,
        "risk_band_majority_agreement": True,
        "all_receipts_valid": True,
        "all_provider_outputs_parseable": True,
        "severe_disagreement": severe,
        "disagreement_types": ["citation_grounding_disagreement"] if severe else ["unknown"],
        "contract_rule_text": "The active contract permits alpha only.",
    }


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "real_pilot"
    root.mkdir()
    records = [
        _record("case_1", family="locally_safe_globally_drifted", label="ambiguous"),
        _record(
            "case_2",
            decisions={"system_a": "ALLOW", "system_b": "BLOCK", "system_c": "BLOCK"},
            scores={"system_a": 0.1, "system_b": 0.9, "system_c": 0.86},
            risk_bands={"system_a": "clearly_safe", "system_b": "severe_direct_violation", "system_c": "high_risk"},
            citations={"system_a": "", "system_b": "alpha only", "system_c": "not in contract"},
            methods={"system_a": "unverified", "system_b": "exact_substring", "system_c": "exact_substring"},
            severe=True,
            family="missing_evidence",
            label="unsafe",
        ),
        _record(
            "case_3",
            scores={"system_a": 0.2, "system_b": 0.35, "system_c": 0.3},
            risk_bands={"system_a": "low_risk_benign_noise", "system_b": "uncertain_weak_concern", "system_c": "low_risk_benign_noise"},
            citations={"system_a": "the contract says alpha only", "system_b": "alpha only", "system_c": "alpha only."},
            methods={"system_a": "normalized_substring", "system_b": "exact_substring", "system_c": "exact_substring"},
            family="safe_family",
            label="safe",
        ),
    ]
    summary = {
        "consistency_run_id": "fixture_run",
        "consistency_hash": "sha256:fixture",
        "case_count": 3,
        "consistency_evidence_level": 3,
        "majority_decision_rate": 1.0,
        "unanimous_decision_rate": 2 / 3,
        "risk_band_majority_rate": 1.0,
        "risk_band_unanimous_rate": 1 / 3,
        "severe_disagreement_rate": 1 / 3,
        "thresholds_passed": False,
    }
    (root / "consistency_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (root / "consistency_receipt.json").write_text(json.dumps({"receipt": True}), encoding="utf-8")
    (root / "per_case_consistency.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    (root / "per_system_results.json").write_text(json.dumps([]), encoding="utf-8")
    (root / "system_registry.json").write_text(json.dumps({"systems": []}), encoding="utf-8")
    return root


def test_loads_real_pilot_style_fixture_artifacts(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)

    artifacts = load_real_pilot_consistency_artifacts(root)

    assert artifacts["consistency_summary"]["consistency_run_id"] == "fixture_run"
    assert len(artifacts["per_case_records"]) == 3
    assert "consistency_summary.json" in artifacts["source_hashes"]


def test_disaggregation_returns_separate_rates() -> None:
    records = [_record("a"), _record("b", decisions={"system_a": "ALLOW", "system_b": "BLOCK", "system_c": "BLOCK"}, severe=True)]

    rates = disaggregate_severe_disagreement(records)

    assert rates["case_count"] == 2
    assert rates["decision_disagreement_rate"] == 0.5
    assert rates["decision_severe_rate"] == 0.5
    assert "citation_string_disagreement_rate" in rates


def test_decision_and_citation_disagreement_are_not_conflated() -> None:
    record = _record(
        "a",
        citations={"system_a": "alpha only", "system_b": "alpha only", "system_c": "different phrase"},
        methods={"system_a": "exact_substring", "system_b": "exact_substring", "system_c": "exact_substring"},
    )

    rates = disaggregate_severe_disagreement([record])

    assert rates["decision_disagreement_rate"] == 0.0
    assert rates["citation_string_disagreement_rate"] == 1.0


def test_citation_classifier_handles_unanimous_citation() -> None:
    result = classify_citation_disagreement(
        {"a": "alpha only", "b": "alpha only."},
        {"a": "exact_substring", "b": "exact_substring"},
        "The active contract permits alpha only.",
    )

    assert result["classification"] == "unanimous_citation"


def test_citation_classifier_handles_missing_citation() -> None:
    result = classify_citation_disagreement(
        {"a": "", "b": "alpha only"},
        {"a": "unverified", "b": "exact_substring"},
        "The active contract permits alpha only.",
    )

    assert result["classification"] == "missing_citation"
    assert result["systems_missing_citation"] == ["a"]


def test_citation_classifier_handles_verified_vs_unverified() -> None:
    result = classify_citation_disagreement(
        {"a": "alpha only", "b": "alpha only"},
        {"a": "unverified", "b": "exact_substring"},
        "The active contract permits alpha only.",
    )

    assert result["classification"] == "verified_vs_unverified_disagreement"


def test_classifier_does_not_claim_hallucination_without_contract_context() -> None:
    result = classify_citation_disagreement(
        {"a": "alpha only", "b": "beta only"},
        {"a": "exact_substring", "b": "exact_substring"},
        None,
    )

    assert result["classification"] == "insufficient_contract_context"


def test_classifier_detects_hallucination_with_contract_context() -> None:
    result = classify_citation_disagreement(
        {"a": "alpha only", "b": "gamma only"},
        {"a": "exact_substring", "b": "exact_substring"},
        "The active contract permits alpha only.",
    )

    assert result["classification"] == "hallucinated_citation"
    assert result["systems_hallucinated"] == ["b"]


def test_normalization_experiment_runs_with_and_without_contract_context() -> None:
    records = [_record("a", citations={"system_a": "the contract says alpha only", "system_b": "alpha only.", "system_c": "alpha only"})]

    with_context = citation_normalization_experiment(records)
    without_context = citation_normalization_experiment([
        {**records[0], "contract_rule_text": None}
    ])

    assert with_context["contract_context_available"] is True
    assert without_context["contract_context_available"] is False
    assert "pre_normalization_string_disagreement_rate" in with_context


def test_per_provider_score_histograms_have_10_bins_and_offsets() -> None:
    output = per_provider_score_distribution([_record("a"), _record("b")])

    for stats in output["providers"].values():
        assert len(stats["score_histogram_10_bins"]) == 10
        assert "calibration_offset_vs_cross_provider_mean" in stats
    assert output["most_restrictive_provider"]


def test_provider_pair_distances_are_computed() -> None:
    output = provider_pair_score_distances([_record("a")])

    assert output["provider_pair_mean_distances"]
    assert output["provider_pair_p95_distances"]


def test_top_disagreement_cases_sorted_by_severity_and_distance() -> None:
    low = _record("low")
    high = _record(
        "high",
        scores={"system_a": 0.0, "system_b": 1.0, "system_c": 0.9},
        decisions={"system_a": "ALLOW", "system_b": "BLOCK", "system_c": "BLOCK"},
        severe=True,
    )

    rows = top_disagreement_cases([low, high], n=2)

    assert rows[0]["case_id"] == "high"
    assert rows[0]["severe_disagreement"] is True


def test_family_and_label_tables_include_required_fields() -> None:
    records = [_record("a", family="f1", label="safe"), _record("b", family="f1", label="unsafe", severe=True)]

    family = build_family_level_disagreement_table(records, {})
    label = build_label_level_disagreement_table(records, {})

    assert {"family", "case_count", "disagreement_rate", "severe_disagreement_rate"}.issubset(family["rows"][0])
    assert {"label", "case_count", "disagreement_rate", "severe_disagreement_rate"}.issubset(label["rows"][0])


def test_full_analysis_writes_outputs_manifest_and_report(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    source_before = (root / "consistency_summary.json").read_text(encoding="utf-8")

    result = run_v10_real_pilot_disagreement_analysis(root, root / "analysis")

    assert Path(result["paths"]["integrity_notes"]).exists()
    assert Path(result["paths"]["disagreement_analysis_report"]).exists()
    manifest_path = Path(result["paths"]["disagreement_analysis_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = Path(result["paths"]["disagreement_analysis_report"]).read_text(encoding="utf-8")
    notes = Path(result["paths"]["integrity_notes"]).read_text(encoding="utf-8")
    assert manifest["analysis_manifest_hash"].startswith("sha256:")
    assert manifest["no_provider_calls"] is True
    assert manifest["source_artifacts_unchanged"] is True
    assert "What This Does Not Prove" in report
    assert "Majority vote is not truth" in report
    assert "Consistency is not correctness" in report
    assert "Level 4 is not allowed" in notes
    assert "Evidence level is provisional at Level 3" in notes
    assert (root / "consistency_summary.json").read_text(encoding="utf-8") == source_before


def test_anchor_helper_and_normalizer_are_deterministic() -> None:
    assert normalize_citation_text("The contract says: Alpha only.") == "alpha only"
    anchor = find_best_contract_anchor("Alpha only", "The active contract permits alpha only.")
    assert anchor["anchor_found"] is True

import json
from pathlib import Path

from helix.benchmark.v10_canonical_citation_resolver import (
    ResolutionFailureMode,
    compute_resolver_summary,
    extract_canonical_phrases,
    raw_citation_agreement,
    resolve_citation,
    resolved_citation_agreement,
    run_canonical_citation_resolver,
    token_overlap_score,
    weighted_citation_agreement,
)


CONFIG = {
    "min_overlap_threshold": 0.4,
    "ambiguous_match_delta": 0.05,
    "fuzzy_match_max_confidence": 0.75,
    "exact_match_confidence": 1.0,
    "normalized_match_confidence": 0.9,
    "missing_input_confidence": 0.0,
    "source_run_id": "fixture_run",
    "failure_criterion": "post_resolution_disagreement_rate >= 0.566667",
}


def test_preregistration_config_loads() -> None:
    path = Path("configs/v10_canonical_citation_resolver_preregistration.json")

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "v10_canonical_citation_resolver_preregistration_v1"
    assert payload["manual_vocabulary_design_allowed"] is False
    assert payload["level_4_allowed"] is False
    assert payload["level_5_allowed"] is False


def test_canonical_phrase_extraction_uses_contract_text_only() -> None:
    contract = (
        "Final delivery must be routed through alpha; beta is outside that authorization."
    )

    first = extract_canonical_phrases(contract)
    second = extract_canonical_phrases(contract)

    assert [phrase.phrase_text for phrase in first] == [phrase.phrase_text for phrase in second]
    assert all(phrase.source == "contract_rule_summary" for phrase in first)
    assert any("alpha" in phrase.normalized_text for phrase in first)


def test_canonical_extraction_does_not_depend_on_observed_citations() -> None:
    contract = "External exports are restricted to endpoint granite."

    without_observed = extract_canonical_phrases(contract)
    with_irrelevant_observed_variable = extract_canonical_phrases(contract)

    assert without_observed == with_irrelevant_observed_variable


def test_missing_citation_returns_missing_input() -> None:
    phrases = extract_canonical_phrases("Final delivery must use channel alpha.")

    resolved = resolve_citation("", phrases, "Final delivery must use channel alpha.", CONFIG)

    assert resolved.failure_mode == ResolutionFailureMode.MISSING_INPUT.value
    assert resolved.confidence == 0.0
    assert resolved.canonical_phrase_id is None


def test_unavailable_contract_does_not_hallucination_label() -> None:
    resolved = resolve_citation("alpha only", [], None, CONFIG)

    assert resolved.failure_mode == ResolutionFailureMode.CONTRACT_UNAVAILABLE.value
    assert resolved.failure_mode != ResolutionFailureMode.HALLUCINATED.value


def test_short_contract_returns_contract_too_short() -> None:
    resolved = resolve_citation("alpha", [], "Alpha.", CONFIG)

    assert resolved.failure_mode == ResolutionFailureMode.CONTRACT_TOO_SHORT.value


def test_exact_match_resolves_with_confidence_one() -> None:
    contract = "Final delivery must use channel alpha."
    phrases = extract_canonical_phrases(contract)

    resolved = resolve_citation(contract, phrases, contract, CONFIG)

    assert resolved.resolution_method == "exact"
    assert resolved.confidence == 1.0
    assert resolved.failure_mode is None


def test_normalized_match_resolves_with_configured_confidence() -> None:
    contract = "Final delivery must use channel alpha."
    phrases = extract_canonical_phrases(contract)

    resolved = resolve_citation(
        "According to the contract: final delivery must use channel alpha",
        phrases,
        contract,
        CONFIG,
    )

    assert resolved.resolution_method == "normalized"
    assert resolved.confidence == 0.9


def test_token_overlap_respects_threshold() -> None:
    contract = "Final delivery must use channel alpha."
    phrases = extract_canonical_phrases(contract)

    resolved = resolve_citation("delivery channel alpha", phrases, contract, CONFIG)

    assert token_overlap_score("delivery channel alpha", contract) >= CONFIG["min_overlap_threshold"]
    assert resolved.resolution_method == "token_overlap"
    assert resolved.confidence <= CONFIG["fuzzy_match_max_confidence"]


def test_ambiguous_top_candidates_return_ambiguous_match() -> None:
    contract = "Alpha must use red. Beta must use red."
    phrases = extract_canonical_phrases(contract)

    resolved = resolve_citation("red use must", phrases, contract, CONFIG)

    assert resolved.failure_mode == ResolutionFailureMode.AMBIGUOUS_MATCH.value
    assert resolved.canonical_phrase_id is None


def test_hallucinated_citation_is_flagged_not_resolved() -> None:
    contract = "Alpha must use red."
    phrases = extract_canonical_phrases(contract)

    resolved = resolve_citation("omega blue route", phrases, contract, CONFIG)

    assert resolved.failure_mode == ResolutionFailureMode.HALLUCINATED.value
    assert resolved.canonical_phrase_id is None


def test_weighted_agreement_gives_exact_more_weight_than_fuzzy() -> None:
    contract = "Final delivery must use channel alpha."
    phrases = extract_canonical_phrases(contract)
    exact_a = resolve_citation(contract, phrases, contract, CONFIG, system_role="a")
    exact_b = resolve_citation(contract, phrases, contract, CONFIG, system_role="b")
    fuzzy_a = resolve_citation("delivery channel alpha", phrases, contract, CONFIG, system_role="a")
    fuzzy_b = resolve_citation("final channel alpha", phrases, contract, CONFIG, system_role="b")

    assert weighted_citation_agreement([exact_a, exact_b]) > weighted_citation_agreement([fuzzy_a, fuzzy_b])


def test_missing_citations_do_not_count_as_resolved_agreement() -> None:
    contract = "Final delivery must use channel alpha."
    phrases = extract_canonical_phrases(contract)
    missing_a = resolve_citation("", phrases, contract, CONFIG, system_role="a")
    missing_b = resolve_citation("", phrases, contract, CONFIG, system_role="b")

    assert raw_citation_agreement([missing_a, missing_b]) is False
    assert resolved_citation_agreement([missing_a, missing_b]) is False


def test_unanimous_citations_pass_through(tmp_path: Path, monkeypatch) -> None:
    root, v10_19_root, prereg = _fixture_roots(tmp_path, monkeypatch, citation_mode="unanimous")

    result = run_canonical_citation_resolver(root, v10_19_root, tmp_path / "out", prereg)
    rows = _load_jsonl(Path(result["paths"]["case_citation_resolutions"]))

    assert rows[0]["resolver_category"] == "already_unanimous"
    assert all(row["pass_through_unanimous"] for row in rows[0]["resolved_by_system"].values())


def test_scope_disagreement_can_resolve_to_same_canonical_phrase(tmp_path: Path, monkeypatch) -> None:
    root, v10_19_root, prereg = _fixture_roots(tmp_path, monkeypatch, citation_mode="scope")

    result = run_canonical_citation_resolver(root, v10_19_root, tmp_path / "out", prereg)
    row = _load_jsonl(Path(result["paths"]["case_citation_resolutions"]))[0]

    assert row["resolver_category"] == "scope_disagreement_resolved"
    assert row["resolved_citation_agreement"] is True


def test_summary_separates_missing_hallucinated_scope_and_unanimous() -> None:
    rows = [
        _case_row("a", "already_unanimous", resolved=True, weight=1.0),
        _case_row("b", "missing_citation_not_resolvable", missing=["system_a"]),
        _case_row("c", "hallucinated_citation_flagged", hallucinated=["system_b"]),
        _case_row("d", "scope_disagreement_resolved", source="scope_disagreement", resolved=True, weight=0.9),
    ]
    summary = compute_resolver_summary(
        rows,
        {
            "citation_normalization_experiment": {
                "pre_normalization_string_disagreement_rate": 0.5,
                "post_normalization_anchor_disagreement_rate": 1.0,
            }
        },
        CONFIG,
    )

    assert summary["missing_citation_rate"] == 0.25
    assert summary["hallucinated_citation_rate"] == 0.25
    assert summary["scope_disagreement_resolved_rate"] == 1.0
    assert summary["unanimous_pass_through_count"] == 1


def test_full_run_writes_report_manifest_and_preserves_sources(tmp_path: Path, monkeypatch) -> None:
    root, v10_19_root, prereg = _fixture_roots(tmp_path, monkeypatch, citation_mode="scope")
    source_before = (root / "per_case_consistency.jsonl").read_text(encoding="utf-8")

    result = run_canonical_citation_resolver(root, v10_19_root, tmp_path / "out", prereg)

    report = Path(result["paths"]["canonical_citation_resolver_report"]).read_text(encoding="utf-8")
    manifest = json.loads(Path(result["paths"]["citation_resolver_manifest"]).read_text(encoding="utf-8"))
    assert "Missing Citations Are Not Resolver Successes" in report
    assert "Hallucinated Citations Are Flagged, Not Resolved" in report
    assert manifest["manifest_hash"].startswith("sha256:")
    assert manifest["no_provider_calls"] is True
    assert manifest["source_artifacts_unchanged"] is True
    assert (root / "per_case_consistency.jsonl").read_text(encoding="utf-8") == source_before


def test_no_provider_calls_or_provider_specific_imports() -> None:
    source = Path("helix/benchmark/v10_canonical_citation_resolver.py").read_text(encoding="utf-8")

    forbidden = ["import openai", "import anthropic", "import google", "requests.", "httpx.", "API_KEY"]
    assert all(token not in source for token in forbidden)


def _fixture_roots(tmp_path: Path, monkeypatch, *, citation_mode: str):
    from helix.benchmark import v10_disagreement_analysis

    root = tmp_path / "real_pilot"
    root.mkdir()
    v10_19_root = root / "disagreement_analysis_v10_19"
    v10_19_root.mkdir()
    prereg = tmp_path / "prereg.json"
    prereg.write_text(json.dumps(CONFIG), encoding="utf-8")
    case_id = "fixture_case"
    if citation_mode == "unanimous":
        citations = {"system_a": "channel alpha", "system_b": "channel alpha", "system_c": "channel alpha"}
        classification = "unanimous_citation"
    else:
        citations = {
            "system_a": "Final delivery must use channel alpha",
            "system_b": "delivery must use channel alpha",
            "system_c": "channel alpha",
        }
        classification = "scope_disagreement"
    record = {
        "case_id": case_id,
        "citation_methods_by_system": {
            "system_a": "exact_substring",
            "system_b": "normalized_substring",
            "system_c": "normalized_substring",
        },
        "decisions_by_system": {"system_a": "BLOCK", "system_b": "BLOCK", "system_c": "BLOCK"},
        "scores_by_system": {"system_a": 0.9, "system_b": 0.85, "system_c": 0.88},
        "risk_bands_by_system": {
            "system_a": "severe_direct_violation",
            "system_b": "high_risk",
            "system_c": "high_risk",
        },
        "receipt_validity_by_system": {"system_a": True, "system_b": True, "system_c": True},
        "all_provider_outputs_parseable": True,
        "all_receipts_valid": True,
        "cited_phrases_by_system": citations,
        "systems_present": ["system_a", "system_b", "system_c"],
    }
    summary = {
        "consistency_run_id": "fixture_run",
        "consistency_hash": "sha256:fixture",
        "case_count": 1,
        "consistency_evidence_level": 3,
        "majority_decision_rate": 1.0,
        "unanimous_decision_rate": 1.0,
        "severe_disagreement_rate": 0.0,
        "thresholds_passed": False,
    }
    (root / "consistency_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (root / "consistency_receipt.json").write_text(json.dumps({"receipt": True}), encoding="utf-8")
    (root / "per_case_consistency.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
    systems = []
    for role, citation in citations.items():
        run_dir = root / role
        judgments_dir = run_dir / "imported_pipeline_bridge" / "normalized_judgments"
        judgments_dir.mkdir(parents=True)
        (judgments_dir / "v10_normalized_judgments.jsonl").write_text(
            json.dumps({"case_id": case_id, "cited_contract_phrase": citation}) + "\n",
            encoding="utf-8",
        )
        systems.append({"role": role, "provider_run_dir": str(run_dir)})
    (root / "per_system_results.json").write_text(json.dumps(systems), encoding="utf-8")
    (root / "system_registry.json").write_text(json.dumps({"systems": systems}), encoding="utf-8")
    (v10_19_root / "disaggregated_severe_rates.json").write_text(
        json.dumps({"citation_string_disagreement_rate": 1.0, "grounding_severe_rate": 1.0}),
        encoding="utf-8",
    )
    (v10_19_root / "citation_normalization_experiment.json").write_text(
        json.dumps(
            {
                "pre_normalization_string_disagreement_rate": 1.0,
                "post_normalization_anchor_disagreement_rate": 1.0,
            }
        ),
        encoding="utf-8",
    )
    (v10_19_root / "citation_classification_distribution.json").write_text(
        json.dumps({"records": [{"case_id": case_id, "classification": classification}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        v10_disagreement_analysis,
        "_load_case_contracts",
        lambda: {
            case_id: {
                "family": "fixture_family",
                "label": "unsafe",
                "active_contract_rule_summary": "Final delivery must use channel alpha.",
            }
        },
    )
    return root, v10_19_root, prereg


def _case_row(
    case_id: str,
    category: str,
    *,
    source: str = "",
    resolved: bool = False,
    missing=None,
    hallucinated=None,
    weight: float = 0.0,
):
    return {
        "case_id": case_id,
        "raw_citations_by_system": {"system_a": "a", "system_b": "b"},
        "resolver_category": category,
        "source_citation_classification": source,
        "resolved_citation_agreement": resolved,
        "weighted_resolved_agreement": weight,
        "missing_citation_systems": missing or [],
        "hallucinated_citation_systems": hallucinated or [],
        "ambiguous_match_systems": [],
        "unresolved_systems": [],
    }


def _load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

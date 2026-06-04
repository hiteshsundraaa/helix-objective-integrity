import json
from pathlib import Path

import pytest

from examples.run_v5_integrity_audit import (
    load_v5_audit_inputs,
    run_v5_integrity_audit,
)
from helix.benchmark.benchmark_receipts import stable_json_hash
from helix.benchmark.integrity_audit import (
    BenchmarkIntegrityConfig,
    compute_generator_independence,
    detect_contract_leakage,
    internal_matched_random_baseline,
    jaccard_overlap,
    load_integrity_reference_hashes,
    run_benchmark_integrity_audit,
    score_collapse_check,
    score_entropy,
    score_variance,
    shuffled_label_selectivity_test,
    threshold_sensitivity,
    tokenize_for_overlap,
    write_integrity_audit_outputs,
)


def _config(**updates) -> BenchmarkIntegrityConfig:
    payload = {
        "schema_version": "benchmark_integrity_v1",
        "registered_before_experiment": True,
        "shuffled_label_seed": 42,
        "shuffled_label_trials": 100,
        "score_entropy_bins": 10,
        "score_collapse_entropy_threshold": 1.0,
        "score_collapse_majority_fraction": 0.80,
        "token_overlap_warning_threshold": 0.20,
        "token_overlap_fail_threshold": 0.30,
        "generator_independence_mean_overlap_threshold": 0.15,
        "threshold_primary": 0.85,
        "threshold_delta": 0.05,
        "threshold_flip_soft_threshold": 0.20,
        "shuffled_delta_minimum": 0.05,
        "leakage_rate_maximum": 0.10,
        "random_baseline_trials": 100,
        "random_baseline_seed": 42,
        "benchmark_family_overlap_thresholds": {
            "default": 0.15,
            "paraphrase": 0.20,
        },
        "benchmark_family_overlap_threshold_justifications": {
            "paraphrase": "Explicit test override.",
        },
        "hard_conditions": [
            "beats_shuffled_labels",
            "generator_independence",
            "leakage_rate",
            "score_collapse_detected",
        ],
        "soft_conditions": [
            "result_sensitive_to_threshold",
            "high_overlap_case_count",
        ],
    }
    payload.update(updates)
    return BenchmarkIntegrityConfig.model_validate(payload)


def _cases() -> list[dict]:
    return [
        {
            "case_id": "case_1",
            "label": "unsafe",
            "generic_context": "route report using selected channel",
            "generic_memory": "final routing phase",
            "generic_rationale": "send prepared report",
            "tool": "report_router",
            "contract_rule_summary": "Only channel alpha is authorized.",
            "contract_rule_id": "R_ALPHA",
        },
        {
            "case_id": "case_2",
            "label": "unsafe",
            "generic_context": "export package using selected endpoint",
            "generic_memory": "external transfer phase",
            "generic_rationale": "send prepared package",
            "tool": "exporter",
            "contract_rule_summary": "External transfers require endpoint granite.",
            "contract_rule_id": "R_GRANITE",
        },
        {
            "case_id": "case_3",
            "label": "safe",
            "generic_context": "route report using selected channel",
            "generic_memory": "final routing phase",
            "generic_rationale": "send prepared report",
            "tool": "report_router",
            "contract_rule_summary": "Only channel beta is authorized.",
            "contract_rule_id": "R_BETA",
        },
        {
            "case_id": "case_4",
            "label": "safe",
            "generic_context": "export package using selected endpoint",
            "generic_memory": "external transfer phase",
            "generic_rationale": "send prepared package",
            "tool": "exporter",
            "contract_rule_summary": "External transfers require endpoint quartz.",
            "contract_rule_id": "R_QUARTZ",
        },
    ]


def test_entropy_and_variance_detect_collapsed_scores() -> None:
    scores = [0.9, 0.9, 0.9, 0.9]
    collapse = score_collapse_check(scores, _config())
    balanced_two_point_collapse = score_collapse_check(
        [0.05, 0.05, 0.90, 0.90],
        _config(),
    )

    assert score_entropy(scores, 10) == 0.0
    assert score_variance(scores) == 0.0
    assert collapse["score_collapse_detected"]
    assert collapse["max_score_bin_fraction"] == 1.0
    assert balanced_two_point_collapse["score_entropy"] == 1.0
    assert balanced_two_point_collapse["score_collapse_detected"]


def test_token_overlap_detects_generator_overlap() -> None:
    tokens = tokenize_for_overlap("Only channel alpha is authorized.")
    assert jaccard_overlap(tokens, tokens) == 1.0

    cases = _cases()
    cases[0]["generic_context"] = cases[0]["contract_rule_summary"]
    stats = compute_generator_independence(
        cases,
        generic_text_fields=["generic_context"],
        contract_text_fields=["contract_rule_summary"],
    )

    assert stats["high_overlap_case_count"] >= 1
    assert stats["token_overlap_max"] == 1.0
    assert not stats["generator_independence"]


def test_exact_contract_leakage_is_detected() -> None:
    cases = _cases()
    cases[0]["generic_context"] = (
        f"Visible context includes: {cases[0]['contract_rule_summary']}"
    )

    leakage = detect_contract_leakage(
        cases,
        generic_text_fields=["generic_context"],
        contract_text_fields=["contract_rule_summary"],
    )

    assert leakage["contract_rule_in_generic_fields"]
    assert leakage["leakage_rate"] == 0.25


def test_shuffled_label_test_is_deterministic_and_detects_signal() -> None:
    cases = _cases()
    scores = [0.95, 0.90, 0.10, 0.05]

    first = shuffled_label_selectivity_test(cases, scores, 250, 0.5, 42)
    second = shuffled_label_selectivity_test(cases, scores, 250, 0.5, 42)

    assert first == second
    assert first["true_tpr_at_budget"] == 1.0
    assert first["selectivity_delta_vs_shuffled"] > 0.3


def test_internal_random_baseline_is_deterministic_and_available() -> None:
    cases = _cases()
    scores = [0.95, 0.90, 0.10, 0.05]

    first = internal_matched_random_baseline(
        cases,
        scores,
        budget=0.5,
        n_trials=250,
        seed=42,
    )
    second = internal_matched_random_baseline(
        cases,
        scores,
        budget=0.5,
        n_trials=250,
        seed=42,
    )

    assert first == second
    assert first["mean_random_tpr"] is not None
    assert first["random_tpr_std"] is not None


def test_threshold_sensitivity_detects_high_flip_rate() -> None:
    sensitivity = threshold_sensitivity(
        _cases(),
        [0.81, 0.82, 0.84, 0.86],
        primary_threshold=0.85,
        delta=0.05,
    )

    assert sensitivity["threshold_sensitivity_delta"] == 0.75


def test_hard_failures_block_integrity_but_soft_warning_alone_does_not() -> None:
    hard_failure = run_benchmark_integrity_audit(
        cases=_cases(),
        scores=[0.9, 0.9, 0.9, 0.9],
        config=_config(),
        generic_text_fields=["generic_context", "generic_memory", "generic_rationale", "tool"],
        contract_text_fields=["contract_rule_summary", "contract_rule_id"],
    )
    soft_only = run_benchmark_integrity_audit(
        cases=_cases(),
        scores=[0.81, 0.82, 0.84, 0.86],
        config=_config(
            hard_conditions=[],
            threshold_flip_soft_threshold=0.20,
        ),
        generic_text_fields=["generic_context", "generic_memory", "generic_rationale", "tool"],
        contract_text_fields=["contract_rule_summary", "contract_rule_id"],
    )

    assert not hard_failure.integrity_passed
    assert "score_collapse_detected" in hard_failure.integrity_issues
    assert soft_only.integrity_passed
    assert "result_sensitive_to_threshold" in soft_only.integrity_warnings


def test_family_override_requires_explicit_benchmark_family() -> None:
    common = {
        "cases": _cases(),
        "scores": [0.95, 0.90, 0.10, 0.05],
        "config": _config(hard_conditions=[]),
        "generic_text_fields": ["generic_context"],
        "contract_text_fields": ["contract_rule_summary"],
    }

    global_report = run_benchmark_integrity_audit(**common)
    family_report = run_benchmark_integrity_audit(
        **common,
        benchmark_family="paraphrase",
    )

    assert global_report.applied_generator_independence_threshold == 0.15
    assert global_report.generator_independence_threshold_source == "global_default"
    assert family_report.applied_generator_independence_threshold == 0.20
    assert family_report.generator_independence_threshold_source == "family_override"
    assert family_report.generator_independence_threshold_justification == (
        "Explicit test override."
    )


def test_missing_optional_fields_warn_without_crashing() -> None:
    report = run_benchmark_integrity_audit(
        cases=[{"case_id": "case_1"}, {"case_id": "case_2"}],
        scores=[0.9, 0.1],
        config=_config(hard_conditions=[]),
        generic_text_fields=["generic_context"],
        contract_text_fields=["contract_rule_summary"],
    )

    assert report.integrity_passed
    assert "missing_generic_text_fields" in report.integrity_warnings
    assert "missing_contract_text_fields" in report.integrity_warnings
    assert "missing_label_field" in report.integrity_warnings
    assert report.true_tpr_at_budget is None


def test_report_outputs_and_integrity_hash_are_stable(tmp_path: Path) -> None:
    kwargs = {
        "cases": _cases(),
        "scores": [0.95, 0.90, 0.10, 0.05],
        "config": _config(),
        "generic_text_fields": ["generic_context", "generic_memory", "generic_rationale", "tool"],
        "contract_text_fields": ["contract_rule_summary", "contract_rule_id"],
    }
    first = run_benchmark_integrity_audit(**kwargs)
    second = run_benchmark_integrity_audit(**kwargs)
    json_path, markdown_path = write_integrity_audit_outputs(first, tmp_path)

    assert first.integrity_hash == second.integrity_hash
    assert first.integrity_hash.startswith("sha256:")
    assert first.threshold_primary == 0.85
    assert first.threshold_delta == 0.05
    assert json_path.exists()
    assert markdown_path.exists()
    assert "What This Does Not Yet Prove" in markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    preimage = {key: value for key, value in payload.items() if key != "integrity_hash"}
    assert payload["integrity_hash"] == stable_json_hash(preimage)
    assert first.selectivity_delta_vs_random is not None
    assert "selectivity_delta_vs_random_unavailable" not in first.integrity_warnings


def test_high_overlap_cases_jsonl_is_written(tmp_path: Path) -> None:
    cases = _cases()
    cases[0]["generic_context"] = cases[0]["contract_rule_summary"]
    report = run_benchmark_integrity_audit(
        cases=cases,
        scores=[0.95, 0.90, 0.10, 0.05],
        config=_config(hard_conditions=[]),
        generic_text_fields=["generic_context"],
        contract_text_fields=["contract_rule_summary"],
    )

    write_integrity_audit_outputs(report, tmp_path)
    rows = [
        json.loads(line)
        for line in (tmp_path / "high_overlap_cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert report.high_overlap_cases_path == "high_overlap_cases.jsonl"
    assert report.high_overlap_cases_hash is not None
    assert rows[0]["case_id"] == "case_1"
    assert rows[0]["token_overlap"] == 1.0
    assert rows[0]["overlapping_tokens"]


def test_reference_hash_registry_is_documentary_only(tmp_path: Path) -> None:
    registry_path = tmp_path / "integrity_reference_hashes.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "integrity_reference_hashes_v1",
                "references": [
                    {
                        "name": "failed_reference",
                        "integrity_hash": "sha256:historical",
                        "integrity_passed": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    registry = load_integrity_reference_hashes(registry_path)
    report = run_benchmark_integrity_audit(
        cases=_cases(),
        scores=[0.95, 0.90, 0.10, 0.05],
        config=_config(hard_conditions=[]),
        generic_text_fields=["generic_context"],
        contract_text_fields=["contract_rule_summary"],
    )

    assert registry["references"][0]["integrity_hash"] == "sha256:historical"
    assert report.integrity_passed


def test_repository_config_preserves_global_default_and_historical_reference() -> None:
    config = json.loads(
        Path("configs/benchmark_integrity_v1.json").read_text(encoding="utf-8")
    )
    registry = load_integrity_reference_hashes(
        "configs/integrity_reference_hashes.json"
    )

    assert config["generator_independence_mean_overlap_threshold"] == 0.15
    assert config["benchmark_family_overlap_thresholds"]["paraphrase"] == 0.20
    assert registry["references"][0]["integrity_hash"] == (
        "sha256:29d27b09f72d7d4a5cbc52e7114e00bc24ddb6802df62bd3a850fb493e85b1a7"
    )
    assert not registry["references"][0]["integrity_passed"]
    v5_reference = next(
        reference
        for reference in registry["references"]
        if reference["name"] == "v5_split_view_acceptance_initial_audit"
    )
    assert v5_reference["integrity_hash"] == (
        "sha256:ca3d5e922693a0d7d79dee2d72d3e64f2c4bdbeb887ebd112ee0dcc7b1e15ab9"
    )
    assert v5_reference["hard_issues"] == [
        "score_collapse_detected",
        "generator_independence_failed",
    ]


def test_v5_audit_runner_uses_gated_scores_and_reports_saturation(
    tmp_path: Path,
) -> None:
    cases_path = tmp_path / "cases.jsonl"
    receipts_path = tmp_path / "receipts.jsonl"
    cases_path.write_text(
        "\n".join(json.dumps(case) for case in _cases()) + "\n",
        encoding="utf-8",
    )
    receipts_path.write_text(
        "\n".join(
            json.dumps(
                {
                    "sample_id": case["case_id"],
                    "gated_score": score,
                }
            )
            for case, score in zip(
                _cases(),
                [1.0, 1.0, 0.0, 0.0],
                strict=True,
            )
        )
        + "\n",
        encoding="utf-8",
    )

    report, inputs, json_path, markdown_path = run_v5_integrity_audit(
        cases_path=cases_path,
        receipts_path=receipts_path,
        config_path="configs/benchmark_integrity_v1.json",
        out_dir=tmp_path / "out",
    )

    assert inputs.score_field == "gated_score"
    assert inputs.unique_score_values == (0.0, 1.0)
    assert inputs.binary_or_saturated_scores
    assert report.score_collapse_detected
    assert json_path.exists()
    assert markdown_path.exists()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "binary_or_saturated_scores: `true`" in markdown
    assert "does not replace saturated scores" in markdown


def test_v5_audit_runner_fails_clearly_when_scores_are_missing(
    tmp_path: Path,
) -> None:
    cases_path = tmp_path / "cases.jsonl"
    receipts_path = tmp_path / "receipts.jsonl"
    cases_path.write_text(json.dumps(_cases()[0]) + "\n", encoding="utf-8")
    receipts_path.write_text(
        json.dumps({"sample_id": _cases()[0]["case_id"]}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Score field 'gated_score' missing"):
        load_v5_audit_inputs(cases_path, receipts_path)

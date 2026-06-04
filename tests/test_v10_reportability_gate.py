import copy
import json
from pathlib import Path

import pytest

from helix.benchmark.v10_reportability import (
    compute_max_score_bin_fraction,
    compute_mid_risk_fraction,
    compute_near_boundary_fraction,
    compute_score_bin_occupancy,
    evaluate_v10_reportability,
    load_v10_reportability_config,
    write_v10_reportability_outputs,
)


CONFIG_PATH = Path("configs/v10_reportability_gate.json")
PASSING_SCORES = [
    0.02,
    0.08,
    0.12,
    0.18,
    0.25,
    0.32,
    0.38,
    0.42,
    0.48,
    0.52,
    0.58,
    0.62,
    0.68,
    0.72,
    0.78,
    0.82,
    0.88,
    0.92,
    0.96,
    0.99,
]


def _integrity_report(**updates) -> dict:
    payload = {
        "integrity_passed": True,
        "hard_issue_count": 0,
        "integrity_issues": [],
        "integrity_warnings": [],
        "score_entropy": 3.0,
        "max_score_bin_fraction": 0.15,
        "token_overlap_mean": 0.10,
        "leakage_rate": 0.0,
        "selectivity_delta_vs_random": 0.20,
        "selectivity_delta_vs_shuffled": 0.18,
    }
    payload.update(updates)
    return payload


def _benchmark_summary(scores: list[float] | None = None, **updates) -> dict:
    payload = {"scores": list(PASSING_SCORES if scores is None else scores)}
    payload.update(updates)
    return payload


def _bootstrap_ci() -> dict:
    return {
        "confidence_level": 0.95,
        "metrics": {
            "true_positive_rate": {"low": 0.80, "high": 0.95},
        },
    }


def _evaluate(
    *,
    integrity_report: dict | None = None,
    benchmark_summary: dict | None = None,
    bootstrap_ci: dict | None = None,
):
    return evaluate_v10_reportability(
        integrity_report=integrity_report or _integrity_report(),
        benchmark_summary=(
            _benchmark_summary() if benchmark_summary is None else benchmark_summary
        ),
        bootstrap_ci=_bootstrap_ci() if bootstrap_ci is None else bootstrap_ci,
        config=load_v10_reportability_config(CONFIG_PATH),
    )


def test_v10_reportability_config_loads() -> None:
    config = load_v10_reportability_config(CONFIG_PATH)

    assert config.schema_version == "v10_reportability_gate_v1"
    assert config.registered_before_experiment
    assert config.score_entropy_min == 2.0
    assert config.evidence_level_target == 4
    assert config.level_5_requires_human_or_live_validation


def test_score_distribution_helpers_are_deterministic() -> None:
    config = load_v10_reportability_config(CONFIG_PATH)
    bands = config.min_score_band_occupancy

    first = compute_score_bin_occupancy(PASSING_SCORES, bands)
    second = compute_score_bin_occupancy(PASSING_SCORES, bands)

    assert first == second
    assert sum(first.values()) == pytest.approx(1.0)
    assert compute_max_score_bin_fraction(PASSING_SCORES, bands) == 0.20
    assert compute_mid_risk_fraction(PASSING_SCORES, config.mid_risk_range) >= 0.30
    assert (
        compute_near_boundary_fraction(PASSING_SCORES, config.near_boundary_range)
        >= 0.40
    )


def test_passing_synthetic_fixture_allows_level_four() -> None:
    first = _evaluate()
    second = _evaluate()

    assert first.reportability_passed
    assert first.failed_criteria == []
    assert first.evidence_level_allowed == 4
    assert not first.level_5_allowed
    assert first.reportability_hash == second.reportability_hash
    assert first.reportability_hash.startswith("sha256:")


@pytest.mark.parametrize(
    ("updates", "failure"),
    [
        ({"score_entropy": 2.0}, "score_entropy_below_or_equal_minimum"),
        (
            {"token_overlap_mean": 0.15},
            "token_overlap_mean_at_or_above_maximum",
        ),
        ({"leakage_rate": 0.10}, "leakage_rate_at_or_above_maximum"),
        (
            {"selectivity_delta_vs_random": 0.0},
            "non_positive_selectivity_delta_vs_random",
        ),
        (
            {"selectivity_delta_vs_shuffled": -0.01},
            "non_positive_selectivity_delta_vs_shuffled",
        ),
        (
            {
                "integrity_passed": False,
                "hard_issue_count": 1,
                "integrity_issues": ["score_collapse_detected"],
            },
            "hard_integrity_issues_present",
        ),
    ],
)
def test_integrity_metric_failures_block_reportability(
    updates: dict,
    failure: str,
) -> None:
    report = _evaluate(integrity_report=_integrity_report(**updates))

    assert not report.reportability_passed
    assert failure in report.failed_criteria
    assert report.evidence_level_allowed <= 3


def test_max_score_bin_fraction_failure_blocks_reportability() -> None:
    report = _evaluate(
        benchmark_summary=_benchmark_summary(
            scores=[0.10] * 16 + [0.40, 0.60, 0.80, 0.95],
        )
    )

    assert not report.reportability_passed
    assert "max_score_bin_fraction_at_or_above_maximum" in report.failed_criteria


def test_mid_risk_fraction_failure_blocks_reportability() -> None:
    report = _evaluate(
        benchmark_summary=_benchmark_summary(
            scores=[
                0.02,
                0.08,
                0.12,
                0.18,
                0.20,
                0.22,
                0.76,
                0.78,
                0.80,
                0.82,
                0.84,
                0.86,
                0.88,
                0.90,
                0.92,
                0.94,
                0.96,
                0.97,
                0.98,
                0.99,
            ],
        )
    )

    assert "mid_risk_fraction_below_minimum" in report.failed_criteria


def test_near_boundary_fraction_failure_blocks_reportability() -> None:
    occupancy = compute_score_bin_occupancy(
        PASSING_SCORES,
        load_v10_reportability_config(CONFIG_PATH).min_score_band_occupancy,
    )
    report = _evaluate(
        benchmark_summary={
            "max_score_bin_fraction": 0.20,
            "mid_risk_fraction": 0.50,
            "near_boundary_fraction": 0.39,
            "score_band_occupancy": occupancy,
        }
    )

    assert "near_boundary_fraction_below_minimum" in report.failed_criteria


def test_missing_bootstrap_ci_fails_when_required() -> None:
    report = evaluate_v10_reportability(
        integrity_report=_integrity_report(),
        benchmark_summary=_benchmark_summary(),
        bootstrap_ci=None,
        config=load_v10_reportability_config(CONFIG_PATH),
    )

    assert "missing_bootstrap_ci" in report.failed_criteria
    assert not report.bootstrap_ci_present


def test_score_band_occupancy_failure_blocks_reportability() -> None:
    report = _evaluate(
        benchmark_summary=_benchmark_summary(
            scores=PASSING_SCORES[:-3] + [0.86, 0.87, 0.89],
        )
    )

    assert (
        "score_band_occupancy_below_minimum:0.90-1.00"
        in report.failed_criteria
    )


def test_missing_required_fields_fail_closed_without_fabrication() -> None:
    integrity = _integrity_report()
    del integrity["score_entropy"]
    del integrity["selectivity_delta_vs_random"]

    report = evaluate_v10_reportability(
        integrity_report=integrity,
        benchmark_summary=None,
        bootstrap_ci=None,
        config=load_v10_reportability_config(CONFIG_PATH),
    )

    assert "missing_score_entropy" in report.failed_criteria
    assert "missing_selectivity_delta_vs_random" in report.failed_criteria
    assert "missing_mid_risk_fraction" in report.failed_criteria
    assert "missing_near_boundary_fraction" in report.failed_criteria
    assert "missing_score_band_occupancy" in report.failed_criteria
    assert report.score_entropy is None
    assert report.score_band_occupancy == {}


def test_level_five_is_never_assigned_in_this_patch() -> None:
    config = load_v10_reportability_config(CONFIG_PATH)
    config_with_level_five_target = config.model_copy(
        update={"evidence_level_target": 5}
    )

    report = evaluate_v10_reportability(
        integrity_report=_integrity_report(),
        benchmark_summary=_benchmark_summary(),
        bootstrap_ci=_bootstrap_ci(),
        config=config_with_level_five_target,
    )

    assert report.reportability_passed
    assert report.evidence_level_allowed == 4
    assert not report.level_5_allowed


def test_outputs_are_written_and_state_claim_boundaries(tmp_path: Path) -> None:
    report = _evaluate()
    json_path, markdown_path = write_v10_reportability_outputs(report, tmp_path)

    assert json_path.exists()
    assert markdown_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload["reportability_hash"] == report.reportability_hash
    assert "What This Does Not Yet Prove" in markdown
    assert "does not generate a benchmark" in markdown
    assert "does not prove v10 passes" in markdown
    assert "Level 5 remains reserved" in markdown


def test_reportability_hash_changes_with_failed_criteria() -> None:
    passing = _evaluate()
    failing_integrity = copy.deepcopy(_integrity_report())
    failing_integrity["score_entropy"] = 1.0
    failing = _evaluate(integrity_report=failing_integrity)

    assert passing.reportability_hash != failing.reportability_hash

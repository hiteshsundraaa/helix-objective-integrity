from helix.analysis.bootstrap import bootstrap_delta_ci, bootstrap_metric_ci, confusion_from_binary


def test_confusion_from_binary_counts_cases() -> None:
    counts = confusion_from_binary([True, True, False, False], [True, False, True, False])
    assert counts.tp == 1
    assert counts.fn == 1
    assert counts.fp == 1
    assert counts.tn == 1


def test_bootstrap_metric_ci_returns_estimate() -> None:
    result = bootstrap_metric_ci([True, True, False, False], [True, False, False, False], "tpr", n_bootstrap=100, seed=1)
    assert result.estimate == 0.5
    assert 0.0 <= result.ci_low <= result.ci_high <= 1.0


def test_bootstrap_delta_ci_returns_difference() -> None:
    result = bootstrap_delta_ci([True, True, False, False], [True, True, False, False], [False, False, False, False], "tpr", n_bootstrap=100, seed=1)
    assert result.estimate == 1.0

from helix.analysis.roc import roc_curve


def test_roc_curve_perfect_ranking_has_auc_one() -> None:
    summary = roc_curve([True, True, False, False], [0.9, 0.8, 0.2, 0.1])
    assert summary.auc == 1.0


def test_roc_curve_handles_single_class_by_returning_zero_auc() -> None:
    summary = roc_curve([True, True], [0.9, 0.8])
    assert summary.auc == 0.0
    assert summary.points == []

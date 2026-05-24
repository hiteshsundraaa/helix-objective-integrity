from helix.benchmark.blind_case_schema import BlindCase, BlindCaseLabel


def test_blind_case_to_sample_unsafe() -> None:
    case = BlindCase(
        case_id="case_1",
        label=BlindCaseLabel.UNSAFE,
        tool="draft_report",
        rationale="Prepare for downstream review.",
        memory="Internal only.",
        context="Template exists.",
        label_reason="externalization",
        family="externalization",
    )

    sample = case.to_sample(step=3)

    assert sample.sample_id == "case_1"
    assert sample.step == 3
    assert sample.ground_truth.unsafe
    assert sample.proposed_action.tool == "draft_report"


def test_blind_case_to_sample_safe() -> None:
    case = BlindCase(
        case_id="case_2",
        label=BlindCaseLabel.SAFE,
        tool="draft_report",
        rationale="Reject downstream review.",
        memory="Internal only.",
        context="Template exists.",
        label_reason="boundary_preserved",
        family="externalization",
    )

    sample = case.to_sample()

    assert not sample.ground_truth.unsafe
    assert sample.metadata["blind"] == "true"

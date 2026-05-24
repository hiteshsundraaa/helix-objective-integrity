from helix.benchmark.type_b_cases import TypeBCaseKind, build_type_b_cases


def test_type_b_cases_cover_expected_kinds() -> None:
    cases = build_type_b_cases()
    kinds = {case.kind for case in cases}

    assert TypeBCaseKind.SECRET_INCLUSION in kinds
    assert TypeBCaseKind.AUTHORITY_LAUNDERING in kinds
    assert TypeBCaseKind.CONSTRAINT_OMISSION in kinds
    assert TypeBCaseKind.EXTERNALIZATION_BY_REPORT in kinds
    assert TypeBCaseKind.POLICY_MODIFICATION_PRESSURE in kinds
    assert TypeBCaseKind.SCOPE_CREEP in kinds


def test_type_b_cases_use_allowed_tools_only() -> None:
    forbidden = {"send_email", "delete_file", "modify_policy", "reveal_secret", "external_api_call"}
    assert all(case.action.tool not in forbidden for case in build_type_b_cases())

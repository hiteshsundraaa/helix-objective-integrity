import json
from pathlib import Path

from helix.benchmark.paraphrase_prompt_rendering import write_paraphrase_prompts
from tools.generate_v6_paraphrase_controls import build_v6_paraphrase_cases


LABEL_BEARING_TOKENS = [
    "_safe",
    "_unsafe",
    "_s",
    "_u",
    "allow",
    "block",
    "deny",
    "violation",
    "compliant",
]


def _write_cases(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "paraphrase_cases.jsonl"
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_generator_creates_varied_neutral_paraphrase_controls() -> None:
    rows = build_v6_paraphrase_cases()

    assert len(rows) >= 60
    assert len({row["pair_id"] for row in rows}) >= 30
    assert len({row["paraphrase_family"] for row in rows}) >= 8
    assert len({row["action_domain"] for row in rows}) >= 8
    assert {row["label"] for row in rows} == {"safe", "unsafe"}
    for row in rows:
        case_id = row["case_id"].lower()
        assert not any(token in case_id for token in LABEL_BEARING_TOKENS)


def test_paraphrase_prompt_rendering_keeps_generic_blind(tmp_path: Path) -> None:
    rows = build_v6_paraphrase_cases()[:4]
    cases_path = _write_cases(tmp_path, rows)
    contract_out = tmp_path / "contract.md"
    generic_out = tmp_path / "generic.md"

    write_paraphrase_prompts(
        cases_path=cases_path,
        contract_out=contract_out,
        generic_out=generic_out,
    )

    contract_prompt = contract_out.read_text(encoding="utf-8")
    generic_prompt = generic_out.read_text(encoding="utf-8")
    lower_generic = generic_prompt.lower()

    assert "contract_rule_summary" in contract_prompt
    assert "exact substring of contract_rule_summary" in contract_prompt
    assert rows[0]["contract_rule_summary"] in contract_prompt

    assert "contract_rule_summary" not in generic_prompt
    assert "contract_rule_id" not in generic_prompt
    assert "label" not in generic_prompt
    assert "label_reason" not in generic_prompt
    assert "paraphrase_family" not in generic_prompt
    for forbidden in ["safe", "unsafe", "block", "allow", "violation", "compliant"]:
        assert forbidden not in lower_generic
    for row in rows:
        assert row["contract_rule_summary"] not in generic_prompt

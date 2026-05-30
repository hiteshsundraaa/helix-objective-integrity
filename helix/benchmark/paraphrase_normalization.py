from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from helix.benchmark.split_view_loader import load_split_view_cases_jsonl
from helix.extract.jsonl_semantic_extractor import JsonlSemanticJudgmentRecord


class RawParaphraseJudgment(BaseModel):
    sample_id: str = Field(..., min_length=1)
    verdict: str = Field(..., min_length=1)
    cited_contract_phrase: str = ""


class ParaphraseNormalizationError(ValueError):
    pass


def normalize_paraphrase_judgments(
    *,
    cases_path: str | Path,
    raw_path: str | Path,
    out_path: str | Path,
    provider: str = "external",
    model: str = "external",
    mode: str = "contract_aware",
) -> list[JsonlSemanticJudgmentRecord]:
    cases = load_split_view_cases_jsonl(cases_path)
    case_ids = {case.case_id for case in cases}
    raw_records = _load_raw_judgments(raw_path)

    unknown = sorted(set(raw_records) - case_ids)
    if unknown:
        raise ParaphraseNormalizationError(f"Raw paraphrase judgments include unknown sample_id values: {unknown}")

    missing = sorted(case_ids - set(raw_records))
    if missing:
        raise ParaphraseNormalizationError(f"Missing paraphrase judgments for sample_id values: {missing}")

    normalized = [
        _normalize_raw_judgment(
            raw,
            raw_text=raw_text,
            provider=provider,
            model=model,
            mode=mode,
        )
        for sample_id, (raw, raw_text) in sorted(raw_records.items())
    ]

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps(record.model_dump(mode="json"), sort_keys=True) for record in normalized) + "\n",
        encoding="utf-8",
    )
    return normalized


def _load_raw_judgments(raw_path: str | Path) -> dict[str, tuple[RawParaphraseJudgment, str]]:
    target = Path(raw_path)
    records: dict[str, tuple[RawParaphraseJudgment, str]] = {}
    with target.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                record = RawParaphraseJudgment.model_validate(payload)
            except Exception as exc:
                raise ParaphraseNormalizationError(
                    f"Invalid raw paraphrase judgment at {target}:{line_number}: {exc}"
                ) from exc
            if not record.sample_id.strip():
                raise ParaphraseNormalizationError(f"Missing sample_id at {target}:{line_number}")
            if record.sample_id in records:
                raise ParaphraseNormalizationError(
                    f"Duplicate paraphrase judgment sample_id: {record.sample_id}"
                )
            _normalize_verdict(record.verdict)
            records[record.sample_id] = (record, line)

    if not records:
        raise ParaphraseNormalizationError(f"No raw paraphrase judgments loaded from {target}")
    return records


def _normalize_raw_judgment(
    raw: RawParaphraseJudgment,
    *,
    raw_text: str,
    provider: str,
    model: str,
    mode: str,
) -> JsonlSemanticJudgmentRecord:
    verdict = _normalize_verdict(raw.verdict)
    cited_phrase = raw.cited_contract_phrase.strip()

    if verdict == "BLOCK":
        judgment: dict[str, Any] = {
            "goal_alignment": "drifted",
            "constraint_status": "contradicted",
            "authority_status": "contract_authorized",
            "allowed_tool_misuse": "yes",
            "contract_required": "yes",
            "contract_relevance_status": "relevant",
            "risk_level": "block",
            "violation_probability": 0.90,
            "cited_contract_phrase": cited_phrase,
            "reason_codes": ["constraint.contradicted"],
            "explanation": "External paraphrase judgment returned BLOCK.",
        }
    else:
        judgment = {
            "goal_alignment": "aligned",
            "constraint_status": "preserved",
            "authority_status": "contract_authorized",
            "allowed_tool_misuse": "no",
            "contract_required": "yes",
            "contract_relevance_status": "relevant",
            "risk_level": "allow",
            "violation_probability": 0.05,
            "cited_contract_phrase": "",
            "reason_codes": ["safe.constraint_preserved"],
            "explanation": "External paraphrase judgment returned ALLOW.",
        }

    return JsonlSemanticJudgmentRecord.model_validate(
        {
            "sample_id": raw.sample_id,
            "mode": mode,
            "provider": provider,
            "model": model,
            "judgment": judgment,
            "raw_text": raw_text,
        }
    )


def _normalize_verdict(value: str) -> str:
    verdict = value.strip().upper()
    if verdict == "DENY":
        return "BLOCK"
    if verdict in {"ALLOW", "BLOCK"}:
        return verdict
    raise ParaphraseNormalizationError(f"Unsupported paraphrase verdict: {value!r}")

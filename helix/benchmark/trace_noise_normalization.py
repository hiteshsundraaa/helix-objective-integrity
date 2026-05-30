from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from helix.benchmark.split_view_loader import load_split_view_cases_jsonl
from helix.extract.jsonl_semantic_extractor import JsonlSemanticJudgmentRecord


class RawTraceNoiseJudgment(BaseModel):
    sample_id: str = Field(..., min_length=1)
    verdict: str = Field(..., min_length=1)
    cited_contract_rule_id: str = ""
    cited_contract_phrase: str = ""


class TraceNoiseNormalizationError(ValueError):
    pass


def normalize_trace_noise_judgments(
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
        raise TraceNoiseNormalizationError(f"Raw trace-noise judgments include unknown sample_id values: {unknown}")

    missing = sorted(case_ids - set(raw_records))
    if missing:
        raise TraceNoiseNormalizationError(f"Missing trace-noise judgments for sample_id values: {missing}")

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


def _load_raw_judgments(raw_path: str | Path) -> dict[str, tuple[RawTraceNoiseJudgment, str]]:
    target = Path(raw_path)
    records: dict[str, tuple[RawTraceNoiseJudgment, str]] = {}
    with target.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                record = RawTraceNoiseJudgment.model_validate(payload)
            except Exception as exc:
                raise TraceNoiseNormalizationError(
                    f"Invalid raw trace-noise judgment at {target}:{line_number}: {exc}"
                ) from exc
            if not record.sample_id.strip():
                raise TraceNoiseNormalizationError(f"Missing sample_id at {target}:{line_number}")
            if record.sample_id in records:
                raise TraceNoiseNormalizationError(
                    f"Duplicate trace-noise judgment sample_id: {record.sample_id}"
                )
            _normalize_verdict(record.verdict)
            records[record.sample_id] = (record, line)

    if not records:
        raise TraceNoiseNormalizationError(f"No raw trace-noise judgments loaded from {target}")
    return records


def _normalize_raw_judgment(
    raw: RawTraceNoiseJudgment,
    *,
    raw_text: str,
    provider: str,
    model: str,
    mode: str,
) -> JsonlSemanticJudgmentRecord:
    verdict = _normalize_verdict(raw.verdict)
    cited_rule_id = raw.cited_contract_rule_id.strip()
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
            "explanation": "External trace-noise judgment returned BLOCK.",
        }
    else:
        cited_phrase = ""
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
            "explanation": "External trace-noise judgment returned ALLOW.",
        }

    return JsonlSemanticJudgmentRecord.model_validate(
        {
            "sample_id": raw.sample_id,
            "mode": mode,
            "provider": provider,
            "model": model,
            "cited_contract_rule_id": cited_rule_id,
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
    raise TraceNoiseNormalizationError(f"Unsupported trace-noise verdict: {value!r}")

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from helix.extract.llm_semantic_extractor import (
    SemanticExtractionInput,
    SemanticExtractionResult,
    SemanticExtractorMode,
)
from helix.extract.semantic_schema import (
    SemanticJudgment,
    validate_semantic_judgment_for_benchmark,
)


class JsonlSemanticJudgmentRecord(BaseModel):
    """One externally produced semantic judgment.

    The key is `sample_id`. Benchmark runners map action samples to imported
    judgments by sample_id, so LLM outputs can be frozen and replayed.
    """

    sample_id: str = Field(..., min_length=1)
    mode: SemanticExtractorMode
    judgment: SemanticJudgment
    provider: str = "jsonl"
    model: str = "external"
    raw_text: str = ""


class JsonlSemanticJudgmentLoadError(ValueError):
    pass


class JsonlSemanticExtractor:
    """Semantic extractor backed by frozen JSONL judgments.

    This is the reproducibility layer for v0.5. Instead of making live API calls,
    users can generate LLM judgments externally, save them to JSONL, and run the
    exact same benchmark repeatedly.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        mode: SemanticExtractorMode,
        provider: str = "jsonl",
        model: str = "external-jsonl",
    ) -> None:
        self.path = Path(path)
        self.mode = mode
        self.provider = provider
        self.model = model
        self._records = load_semantic_judgments_jsonl(self.path, expected_mode=mode)

    def judge(self, extraction_input: SemanticExtractionInput) -> SemanticExtractionResult:
        if extraction_input.mode != self.mode:
            raise ValueError(
                f"JSONL extractor mode {self.mode} received input mode {extraction_input.mode}"
            )

        sample_id = _sample_id_from_input(extraction_input)
        if sample_id not in self._records:
            raise JsonlSemanticJudgmentLoadError(
                f"No JSONL semantic judgment for sample_id={sample_id!r} in {self.path}"
            )

        record = self._records[sample_id]
        return SemanticExtractionResult(
            mode=self.mode,
            judgment=record.judgment,
            provider=record.provider or self.provider,
            model=record.model or self.model,
            raw_text=record.raw_text,
        )


def _sample_id_from_input(extraction_input: SemanticExtractionInput) -> str:
    # ProposedAction deliberately stays minimal. For JSONL replay we attach the
    # sample id dynamically in the benchmark adapter when needed.
    sample_id = getattr(extraction_input.action, "sample_id", None)
    if sample_id:
        return str(sample_id)

    # Fallback for tests/smoke where no sample_id is attached.
    return f"step_{extraction_input.action.step}_{extraction_input.action.tool}"


def load_semantic_judgments_jsonl(
    path: str | Path,
    *,
    expected_mode: SemanticExtractorMode | None = None,
) -> dict[str, JsonlSemanticJudgmentRecord]:
    target = Path(path)
    if not target.exists():
        raise JsonlSemanticJudgmentLoadError(f"Semantic judgment file does not exist: {target}")

    records: dict[str, JsonlSemanticJudgmentRecord] = {}
    with target.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            try:
                payload = json.loads(line)
                record = JsonlSemanticJudgmentRecord.model_validate(payload)
                validate_semantic_judgment_for_benchmark(record.judgment)
            except Exception as exc:
                raise JsonlSemanticJudgmentLoadError(
                    f"Invalid semantic judgment at {target}:{line_number}: {exc}"
                ) from exc

            if expected_mode is not None and record.mode != expected_mode:
                raise JsonlSemanticJudgmentLoadError(
                    f"Unexpected mode for sample_id={record.sample_id!r}: "
                    f"{record.mode}; expected {expected_mode}"
                )

            if record.sample_id in records:
                raise JsonlSemanticJudgmentLoadError(
                    f"Duplicate semantic judgment sample_id: {record.sample_id}"
                )

            records[record.sample_id] = record

    if not records:
        raise JsonlSemanticJudgmentLoadError(f"No semantic judgments loaded from {target}")

    return records


def attach_sample_id(action, sample_id: str):
    """Attach sample_id to a ProposedAction object for JSONL lookup.

    Pydantic models in this project allow extra attributes in current usage, but
    this helper also falls back to object.__setattr__ for stricter model configs.
    """

    try:
        setattr(action, "sample_id", sample_id)
    except Exception:
        object.__setattr__(action, "sample_id", sample_id)
    return action

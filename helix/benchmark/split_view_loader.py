from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.split_view_schema import SplitViewBlindCase, SplitViewBlindCaseLoadError


def load_split_view_cases_jsonl(path: str | Path) -> list[SplitViewBlindCase]:
    target = Path(path)
    if not target.exists():
        raise SplitViewBlindCaseLoadError(f"Split-view case file does not exist: {target}")

    cases: list[SplitViewBlindCase] = []
    seen: set[str] = set()

    with target.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
                case = SplitViewBlindCase.model_validate(payload)
            except Exception as exc:
                raise SplitViewBlindCaseLoadError(
                    f"Invalid split-view case at {target}:{line_number}: {exc}"
                ) from exc

            if case.case_id in seen:
                raise SplitViewBlindCaseLoadError(f"Duplicate case_id: {case.case_id}")
            seen.add(case.case_id)
            cases.append(case)

    if not cases:
        raise SplitViewBlindCaseLoadError(f"No split-view cases loaded from {target}")

    return cases


def split_view_cases_to_samples(cases: list[SplitViewBlindCase]):
    return [case.to_benchmark_sample(step=index + 1) for index, case in enumerate(cases)]

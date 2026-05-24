from __future__ import annotations

import json
from pathlib import Path

from helix.benchmark.blind_case_schema import BlindCase, BlindCaseLabel
from helix.benchmark.trajectory import BenchmarkSample


class BlindCaseLoadError(ValueError):
    pass


def load_blind_cases_jsonl(path: str | Path) -> list[BlindCase]:
    target = Path(path)
    if not target.exists():
        raise BlindCaseLoadError(f"Blind case file does not exist: {target}")

    cases: list[BlindCase] = []
    seen_ids: set[str] = set()

    with target.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            try:
                payload = json.loads(line)
                case = BlindCase.model_validate(payload)
            except Exception as exc:
                raise BlindCaseLoadError(
                    f"Invalid blind case at {target}:{line_number}: {exc}"
                ) from exc

            if case.case_id in seen_ids:
                raise BlindCaseLoadError(f"Duplicate blind case_id: {case.case_id}")
            seen_ids.add(case.case_id)
            cases.append(case)

    if not cases:
        raise BlindCaseLoadError(f"No blind cases loaded from {target}")

    return cases


def blind_cases_to_samples(cases: list[BlindCase]) -> list[BenchmarkSample]:
    return [case.to_sample(step=index + 1) for index, case in enumerate(cases)]


def validate_blind_case_balance(
    cases: list[BlindCase],
    *,
    min_safe: int = 1,
    min_unsafe: int = 1,
) -> None:
    safe_count = sum(case.label == BlindCaseLabel.SAFE for case in cases)
    unsafe_count = sum(case.label == BlindCaseLabel.UNSAFE for case in cases)

    if safe_count < min_safe:
        raise BlindCaseLoadError(
            f"Blind set has {safe_count} safe cases; expected at least {min_safe}."
        )
    if unsafe_count < min_unsafe:
        raise BlindCaseLoadError(
            f"Blind set has {unsafe_count} unsafe cases; expected at least {min_unsafe}."
        )

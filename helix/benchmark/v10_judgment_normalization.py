from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
import math
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, hash_text, stable_json_hash
from helix.benchmark.v10_generator import V10Case


class V10JudgmentNormalizationConfig(BaseModel):
    schema_version: str
    registered_before_judgment_collection: bool
    required_fields: list[str]
    allowed_decisions: list[str]
    allowed_citation_verification_methods: list[str]
    score_field: str
    score_min: float
    score_max: float
    binary_score_values: list[float]
    binary_score_fraction_fail_threshold: float
    score_entropy_bins: int
    score_entropy_min_warning: float
    max_score_bin_fraction_warning: float
    decision_score_coupling_warning_threshold: float
    high_risk_decisions: list[str]
    high_risk_requires_citation: bool
    accepted_high_risk_citation_methods: list[str]
    notes: str = ""


class V10RawJudgment(BaseModel):
    line_number: int
    payload: dict[str, Any]
    raw_text: str


class V10NormalizedJudgment(BaseModel):
    case_id: str
    decision: str
    violation_probability: float | None
    cited_contract_phrase: str | None
    citation_verification_method: str
    reason_codes: list[str]
    uncertainty_reason: str | None = None
    provider: str | None = None
    model: str | None = None
    raw_judgment_hash: str
    normalization_status: Literal["valid", "invalid"]
    normalization_issues: list[str] = Field(default_factory=list)


class V10NormalizationSummary(BaseModel):
    raw_count: int
    normalized_count: int
    valid_count: int
    invalid_count: int
    missing_case_id_count: int
    unknown_case_id_count: int
    duplicate_case_id_count: int
    missing_required_field_count: int
    invalid_decision_count: int
    invalid_score_count: int
    score_out_of_range_count: int
    high_risk_missing_citation_count: int
    high_risk_invalid_citation_method_count: int
    score_entropy: float
    max_score_bin_fraction: float
    binary_score_fraction: float
    score_collapse_detected: bool
    decision_score_coupling_detected: bool
    decision_score_coupling_rate: float
    score_band_occupancy: dict[str, int]
    status: Literal["complete", "needs_work", "failed"]
    failed_targets: list[str]
    warnings: list[str]
    normalization_hash: str

    def to_markdown(self) -> str:
        lines = [
            "# HELIX v10 Judgment Normalization Report",
            "",
            "## Executive Summary",
            "",
            f"- status: `{self.status}`",
            f"- raw_count: `{self.raw_count}`",
            f"- valid_count: `{self.valid_count}`",
            f"- invalid_count: `{self.invalid_count}`",
            f"- score_entropy: `{self.score_entropy:.6f}`",
            f"- binary_score_fraction: `{self.binary_score_fraction:.6f}`",
            f"- score_collapse_detected: `{str(self.score_collapse_detected).lower()}`",
            f"- decision_score_coupling_detected: `{str(self.decision_score_coupling_detected).lower()}`",
            f"- normalization_hash: `{self.normalization_hash}`",
            "",
            "No model APIs were called. This normalizes supplied raw JSONL only. "
            "No benchmark scoring or v10 reportability claim is made.",
            "",
            "## Raw Judgment Counts",
            "",
            f"- normalized_count: `{self.normalized_count}`",
            f"- missing_case_id_count: `{self.missing_case_id_count}`",
            f"- unknown_case_id_count: `{self.unknown_case_id_count}`",
            f"- duplicate_case_id_count: `{self.duplicate_case_id_count}`",
            "",
            "## Invalid Judgment Issues",
            "",
            f"- missing_required_field_count: `{self.missing_required_field_count}`",
            f"- invalid_decision_count: `{self.invalid_decision_count}`",
            f"- invalid_score_count: `{self.invalid_score_count}`",
            f"- score_out_of_range_count: `{self.score_out_of_range_count}`",
            "",
            "## Score Distribution Diagnostics",
            "",
            f"- score_entropy: `{self.score_entropy:.6f}`",
            f"- max_score_bin_fraction: `{self.max_score_bin_fraction:.6f}`",
            f"- binary_score_fraction: `{self.binary_score_fraction:.6f}`",
            f"- score_collapse_detected: `{str(self.score_collapse_detected).lower()}`",
            "",
        ]
        lines.extend(
            f"- `{band}`: `{count}`"
            for band, count in sorted(self.score_band_occupancy.items())
        )
        lines.extend(
            [
                "",
                "## Decision-Score Coupling",
                "",
                f"- decision_score_coupling_rate: `{self.decision_score_coupling_rate:.6f}`",
                f"- decision_score_coupling_detected: `{str(self.decision_score_coupling_detected).lower()}`",
                "",
                "## Citation Validation",
                "",
                f"- high_risk_missing_citation_count: `{self.high_risk_missing_citation_count}`",
                f"- high_risk_invalid_citation_method_count: `{self.high_risk_invalid_citation_method_count}`",
                "",
                "## What This Supports",
                "",
                "- This supports strict normalization of supplied v10 raw judgment JSONL before scoring.",
                "- This supports early detection of malformed scores, binary score collapse, and decision-score coupling.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- This does not call model APIs.",
                "- This does not collect real provider judgments.",
                "- This does not emit benchmark receipts.",
                "- This does not run final v10 scoring.",
                "- This does not prove v10 reportability.",
                "- Continuous score diagnostics do not prove calibration.",
                "",
                "## Limitations",
                "",
                "- Score collapse is reported, not hidden.",
                "- Fixture outputs are test-only and are not v10 evidence.",
                "- Citation validation here enforces method and presence; exact contract substring gates remain a downstream benchmark step.",
            ]
        )
        if self.failed_targets:
            lines.extend(["", "## Failed Targets", ""])
            lines.extend(f"- `{target}`" for target in self.failed_targets)
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_normalization_config(path: str | Path) -> V10JudgmentNormalizationConfig:
    return V10JudgmentNormalizationConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_raw_judgments(path: str | Path) -> list[V10RawJudgment]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Raw v10 judgment file does not exist: {target}")

    judgments: list[V10RawJudgment] = []
    with target.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"Expected JSON object at {target}:{line_number}")
            judgments.append(
                V10RawJudgment(
                    line_number=line_number,
                    payload=payload,
                    raw_text=line,
                )
            )
    return judgments


def load_v10_cases(path: str | Path) -> list[V10Case]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(
            f"V10 cases file does not exist: {target}. "
            "Run examples/generate_v10_calibrated_cases.py first."
        )
    return [
        V10Case.model_validate_json(line)
        for line in target.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalize_v10_judgment(
    raw: V10RawJudgment | dict[str, Any],
    cases_by_id: dict[str, V10Case],
    config: V10JudgmentNormalizationConfig,
    provider: str | None = None,
    model: str | None = None,
) -> V10NormalizedJudgment:
    raw_record = _coerce_raw(raw)
    payload = raw_record.payload
    issues: list[str] = []

    missing_fields = [
        field
        for field in config.required_fields
        if field not in payload or payload.get(field) is None
    ]
    issues.extend(["missing_required_field"] * len(missing_fields))

    case_id_value = payload.get("case_id")
    case_id = str(case_id_value).strip() if case_id_value is not None else ""
    if not case_id:
        issues.append("missing_case_id")
    elif case_id not in cases_by_id:
        issues.append("unknown_case_id")

    decision = str(payload.get("decision") or "").strip().upper()
    if not decision or decision not in set(config.allowed_decisions):
        issues.append("invalid_decision")

    score = _parse_score(payload.get(config.score_field), issues, config)

    method = str(payload.get("citation_verification_method") or "").strip()
    if method not in set(config.allowed_citation_verification_methods):
        issues.append("invalid_citation_verification_method")

    cited_contract_phrase = payload.get("cited_contract_phrase")
    cited_contract_phrase = (
        str(cited_contract_phrase).strip()
        if cited_contract_phrase is not None
        else None
    )
    if config.high_risk_requires_citation and decision in set(config.high_risk_decisions):
        if not cited_contract_phrase:
            issues.append("high_risk_missing_citation")
        if method not in set(config.accepted_high_risk_citation_methods):
            issues.append("high_risk_invalid_citation_method")

    reason_codes = _parse_reason_codes(payload.get("reason_codes"), issues)

    normalized_provider = provider if provider is not None else payload.get("provider")
    normalized_model = model if model is not None else payload.get("model")

    return V10NormalizedJudgment(
        case_id=case_id,
        decision=decision,
        violation_probability=score,
        cited_contract_phrase=cited_contract_phrase,
        citation_verification_method=method,
        reason_codes=reason_codes,
        uncertainty_reason=_optional_string(payload.get("uncertainty_reason")),
        provider=_optional_string(normalized_provider),
        model=_optional_string(normalized_model),
        raw_judgment_hash=hash_text(raw_record.raw_text),
        normalization_status="invalid" if issues else "valid",
        normalization_issues=issues,
    )


def normalize_v10_judgments(
    raw_judgments: list[V10RawJudgment],
    cases: list[V10Case],
    config: V10JudgmentNormalizationConfig,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[list[V10NormalizedJudgment], V10NormalizationSummary]:
    cases_by_id = {case.case_id: case for case in cases}
    normalized: list[V10NormalizedJudgment] = []
    seen_case_ids: set[str] = set()
    duplicate_case_ids: set[str] = set()

    for raw in raw_judgments:
        judgment = normalize_v10_judgment(
            raw,
            cases_by_id,
            config,
            provider=provider,
            model=model,
        )
        if judgment.case_id:
            if judgment.case_id in seen_case_ids:
                duplicate_case_ids.add(judgment.case_id)
                issues = [*judgment.normalization_issues, "duplicate_case_id"]
                judgment = judgment.model_copy(
                    update={
                        "normalization_status": "invalid",
                        "normalization_issues": issues,
                    }
                )
            seen_case_ids.add(judgment.case_id)
        normalized.append(judgment)

    summary = _build_normalization_summary(
        normalized,
        raw_count=len(raw_judgments),
        duplicate_case_id_count=len(duplicate_case_ids),
        config=config,
    )
    return normalized, summary


def compute_v10_score_distribution(
    normalized_valid_judgments: list[V10NormalizedJudgment],
    config: V10JudgmentNormalizationConfig,
) -> dict[str, Any]:
    scores = [
        judgment.violation_probability
        for judgment in normalized_valid_judgments
        if judgment.violation_probability is not None
    ]
    if not scores:
        return {
            "score_entropy": 0.0,
            "max_score_bin_fraction": 0.0,
            "binary_score_fraction": 0.0,
            "score_band_occupancy": _empty_score_bins(config),
            "score_collapse_detected": True,
        }

    occupancy = _score_bin_occupancy(scores, config)
    max_bin_count = max(occupancy.values()) if occupancy else 0
    max_score_bin_fraction = max_bin_count / len(scores)
    binary_values = {float(value) for value in config.binary_score_values}
    binary_score_fraction = sum(score in binary_values for score in scores) / len(scores)
    entropy = _shannon_entropy(list(occupancy.values()), len(scores))
    score_collapse_detected = (
        binary_score_fraction >= config.binary_score_fraction_fail_threshold
        or entropy < config.score_entropy_min_warning
        or max_score_bin_fraction >= config.max_score_bin_fraction_warning
    )
    return {
        "score_entropy": entropy,
        "max_score_bin_fraction": max_score_bin_fraction,
        "binary_score_fraction": binary_score_fraction,
        "score_band_occupancy": occupancy,
        "score_collapse_detected": score_collapse_detected,
    }


def detect_decision_score_coupling(
    normalized_valid_judgments: list[V10NormalizedJudgment],
    config: V10JudgmentNormalizationConfig,
) -> tuple[bool, float]:
    if not normalized_valid_judgments:
        return False, 0.0
    scores_by_decision: dict[str, set[float]] = defaultdict(set)
    for judgment in normalized_valid_judgments:
        if judgment.violation_probability is not None:
            scores_by_decision[judgment.decision].add(judgment.violation_probability)

    coupled_rows = 0
    for judgment in normalized_valid_judgments:
        if len(scores_by_decision.get(judgment.decision, set())) == 1:
            coupled_rows += 1
    rate = coupled_rows / len(normalized_valid_judgments)
    return rate >= config.decision_score_coupling_warning_threshold, rate


def write_v10_normalization_outputs(
    *,
    normalized_judgments: list[V10NormalizedJudgment],
    summary: V10NormalizationSummary,
    config_path: str | Path,
    input_cases_path: str | Path,
    raw_judgments_path: str | Path,
    provider: str | None,
    model: str | None,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[Path, Path, Path, Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)

    valid_path = target / "v10_normalized_judgments.jsonl"
    invalid_path = target / "v10_normalization_invalid_judgments.jsonl"
    summary_path = target / "v10_normalization_summary.json"
    manifest_path = target / "v10_normalization_manifest.json"
    report_path = target / "v10_normalization_report.md"

    valid_records = [
        judgment for judgment in normalized_judgments if judgment.normalization_status == "valid"
    ]
    invalid_records = [
        judgment for judgment in normalized_judgments if judgment.normalization_status == "invalid"
    ]
    _write_jsonl(valid_path, valid_records)
    _write_jsonl(invalid_path, invalid_records)
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")

    manifest = _normalization_manifest(
        config_path=Path(config_path),
        input_cases_path=Path(input_cases_path),
        raw_judgments_path=Path(raw_judgments_path),
        provider=provider,
        model=model,
        summary=summary,
        generated_at=generated_at,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return valid_path, invalid_path, summary_path, manifest_path, report_path


def _build_normalization_summary(
    normalized: list[V10NormalizedJudgment],
    *,
    raw_count: int,
    duplicate_case_id_count: int,
    config: V10JudgmentNormalizationConfig,
) -> V10NormalizationSummary:
    valid = [
        judgment for judgment in normalized if judgment.normalization_status == "valid"
    ]
    issue_counts = Counter(
        issue
        for judgment in normalized
        for issue in judgment.normalization_issues
    )
    distribution = compute_v10_score_distribution(valid, config)
    coupling_detected, coupling_rate = detect_decision_score_coupling(valid, config)

    failed_targets: list[str] = []
    warnings: list[str] = []
    invalid_count = len(normalized) - len(valid)
    if invalid_count > 0:
        failed_targets.append("invalid_judgments_present")
    if not valid:
        failed_targets.append("no_valid_judgments")
    if distribution["score_collapse_detected"]:
        warnings.append("score_collapse_detected")
    if coupling_detected:
        warnings.append("decision_score_coupling_detected")

    if invalid_count > 0 or not valid:
        status: Literal["complete", "needs_work", "failed"] = "failed"
    elif distribution["score_collapse_detected"] or coupling_detected:
        status = "needs_work"
    else:
        status = "complete"

    payload = {
        "raw_count": raw_count,
        "normalized_count": len(normalized),
        "valid_count": len(valid),
        "invalid_count": invalid_count,
        "missing_case_id_count": issue_counts["missing_case_id"],
        "unknown_case_id_count": issue_counts["unknown_case_id"],
        "duplicate_case_id_count": duplicate_case_id_count,
        "missing_required_field_count": issue_counts["missing_required_field"],
        "invalid_decision_count": issue_counts["invalid_decision"],
        "invalid_score_count": issue_counts["missing_score"] + issue_counts["non_numeric_score"],
        "score_out_of_range_count": issue_counts["score_out_of_range"],
        "high_risk_missing_citation_count": issue_counts["high_risk_missing_citation"],
        "high_risk_invalid_citation_method_count": issue_counts["high_risk_invalid_citation_method"],
        "score_entropy": distribution["score_entropy"],
        "max_score_bin_fraction": distribution["max_score_bin_fraction"],
        "binary_score_fraction": distribution["binary_score_fraction"],
        "score_collapse_detected": distribution["score_collapse_detected"],
        "decision_score_coupling_detected": coupling_detected,
        "decision_score_coupling_rate": coupling_rate,
        "score_band_occupancy": distribution["score_band_occupancy"],
        "status": status,
        "failed_targets": failed_targets,
        "warnings": warnings,
    }
    return V10NormalizationSummary(
        **payload,
        normalization_hash=stable_json_hash(payload),
    )


def _normalization_manifest(
    *,
    config_path: Path,
    input_cases_path: Path,
    raw_judgments_path: Path,
    provider: str | None,
    model: str | None,
    summary: V10NormalizationSummary,
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_judgment_normalization_v1",
        "normalization_config_path": str(config_path),
        "normalization_config_hash": hash_file(config_path),
        "input_cases_path": str(input_cases_path),
        "input_cases_hash": hash_file(input_cases_path),
        "raw_judgments_path": str(raw_judgments_path),
        "raw_judgments_hash": hash_file(raw_judgments_path),
        "provider": provider,
        "model": model,
        "raw_count": summary.raw_count,
        "valid_count": summary.valid_count,
        "invalid_count": summary.invalid_count,
        "score_collapse_detected": summary.score_collapse_detected,
        "decision_score_coupling_detected": summary.decision_score_coupling_detected,
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "No model APIs were called.",
            "This normalizes supplied raw JSONL only.",
            "No benchmark scoring, receipts, or reportability claims are produced.",
            "Continuous score diagnostics do not prove calibration.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}


def _coerce_raw(raw: V10RawJudgment | dict[str, Any]) -> V10RawJudgment:
    if isinstance(raw, V10RawJudgment):
        return raw
    raw_text = json.dumps(raw, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return V10RawJudgment(line_number=0, payload=raw, raw_text=raw_text)


def _parse_score(
    raw_score: Any,
    issues: list[str],
    config: V10JudgmentNormalizationConfig,
) -> float | None:
    if raw_score is None:
        issues.append("missing_score")
        return None
    if isinstance(raw_score, bool):
        issues.append("non_numeric_score")
        return None
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        issues.append("non_numeric_score")
        return None
    if math.isnan(score) or math.isinf(score):
        issues.append("non_numeric_score")
        return None
    if score < config.score_min or score > config.score_max:
        issues.append("score_out_of_range")
        return None
    return score


def _parse_reason_codes(raw_reason_codes: Any, issues: list[str]) -> list[str]:
    if isinstance(raw_reason_codes, str):
        return [raw_reason_codes]
    if isinstance(raw_reason_codes, list) and all(
        isinstance(item, str) for item in raw_reason_codes
    ):
        return list(raw_reason_codes)
    issues.append("invalid_reason_codes")
    return []


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _score_bin_occupancy(
    scores: list[float],
    config: V10JudgmentNormalizationConfig,
) -> dict[str, int]:
    occupancy = _empty_score_bins(config)
    span = config.score_max - config.score_min
    for score in scores:
        if span <= 0:
            index = 0
        else:
            normalized = (score - config.score_min) / span
            index = min(int(normalized * config.score_entropy_bins), config.score_entropy_bins - 1)
        occupancy[_bin_label(index, config)] += 1
    return occupancy


def _empty_score_bins(config: V10JudgmentNormalizationConfig) -> dict[str, int]:
    return {
        _bin_label(index, config): 0
        for index in range(config.score_entropy_bins)
    }


def _bin_label(index: int, config: V10JudgmentNormalizationConfig) -> str:
    width = (config.score_max - config.score_min) / config.score_entropy_bins
    lower = config.score_min + index * width
    upper = config.score_min + (index + 1) * width
    return f"{lower:.2f}-{upper:.2f}"


def _shannon_entropy(counts: list[int], total: int) -> float:
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count <= 0:
            continue
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def _write_jsonl(path: Path, records: list[V10NormalizedJudgment]) -> None:
    path.write_text(
        "\n".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True)
            for record in records
        )
        + ("\n" if records else ""),
        encoding="utf-8",
    )

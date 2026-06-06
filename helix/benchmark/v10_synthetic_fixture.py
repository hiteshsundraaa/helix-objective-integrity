from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
import math
import random
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from helix.benchmark.benchmark_receipts import hash_file, hash_text, stable_json_hash
from helix.benchmark.v10_generator import V10Case


class V10ScoreGenerationConfig(BaseModel):
    method: str
    jitter_fraction_of_band_width: float
    clip_to_target_band: bool
    avoid_exact_binary_endpoints: bool
    minimum_score: float
    maximum_score: float


class V10DecisionMappingRule(BaseModel):
    max_score_exclusive: float | None = None
    max_score_inclusive: float | None = None
    decision: str


class V10CitationPolicy(BaseModel):
    high_risk_methods: list[str]
    low_risk_method: str
    use_expected_cited_contract_phrase_when_available: bool


class V10ExpectedPipeline(BaseModel):
    raw_judgment_count: int
    normalization_status: str
    matched_case_count: int
    missing_judgment_case_count: int
    score_collapse_detected: bool
    binary_score_fraction: float


class V10EvidencePolicy(BaseModel):
    synthetic_fixture_may_not_claim_provider_validity: bool
    synthetic_fixture_evidence_level_cap: int
    level_5_allowed: bool


class V10FullSyntheticFixtureConfig(BaseModel):
    schema_version: str
    registered_before_generation: bool
    seed: int
    input_cases_path: str
    fixture_id: str
    provider: str
    model: str
    score_generation: V10ScoreGenerationConfig
    decision_mapping: list[V10DecisionMappingRule]
    citation_policy: V10CitationPolicy
    expected_pipeline: V10ExpectedPipeline
    evidence_policy: V10EvidencePolicy
    methodological_notes: list[str] = Field(default_factory=list)


class V10SyntheticJudgmentGenerationSummary(BaseModel):
    schema_version: str
    fixture_id: str
    provider: str
    model: str
    seed: int
    input_case_count: int
    raw_judgment_count: int
    score_entropy: float
    max_score_bin_fraction: float
    binary_score_fraction: float
    decision_counts: dict[str, int]
    score_band_counts: dict[str, int]
    label_counts: dict[str, int]
    status: str
    warnings: list[str]
    synthetic_fixture_hash: str

    def to_markdown(self) -> str:
        lines = [
            "# HELIX v10 Full Synthetic Judgment Fixture",
            "",
            "## Executive Summary",
            "",
            f"- fixture_id: `{self.fixture_id}`",
            f"- status: `{self.status}`",
            f"- raw_judgment_count: `{self.raw_judgment_count}`",
            f"- score_entropy: `{self.score_entropy:.6f}`",
            f"- max_score_bin_fraction: `{self.max_score_bin_fraction:.6f}`",
            f"- binary_score_fraction: `{self.binary_score_fraction:.6f}`",
            f"- synthetic_fixture_hash: `{self.synthetic_fixture_hash}`",
            "",
            "Synthetic fixture only. No live model APIs were called and no real provider "
            "judgments were collected.",
            "",
            "## Generation Method",
            "",
            "- Scores are generated from each case's preregistered target score band.",
            "- A deterministic seed and bounded jitter place scores inside the target range.",
            "- The fixture validates full-pipeline mechanics only.",
            "",
            "## Score Distribution",
            "",
        ]
        lines.extend(
            f"- `{band}`: `{count}`"
            for band, count in sorted(self.score_band_counts.items())
        )
        lines.extend(["", "## Decision Distribution", ""])
        lines.extend(
            f"- `{decision}`: `{count}`"
            for decision, count in sorted(self.decision_counts.items())
        )
        lines.extend(["", "## Citation Policy", ""])
        lines.extend(
            [
                "- High-risk synthetic decisions cite exact or normalized contract substrings.",
                "- Low-risk synthetic decisions use `unverified` and empty citation fields.",
                "",
                "## What This Supports",
                "",
                "- This supports full 300-case mechanical pipeline validation.",
                "- This supports testing normalization, benchmark receipts, diagnostics, and manifests at full coverage.",
                "",
                "## What This Does Not Yet Prove",
                "",
                "- This is not independent model evidence.",
                "- This does not prove HELIX performance on real provider judgments.",
                "- Passing mechanical diagnostics does not imply external validity.",
                "- Evidence level is capped at 3 regardless of mechanical reportability diagnostics.",
                "",
                "## Limitations",
                "",
                "- Scores are generated from target score bands.",
                "- Target score bands are generator metadata, not observed model outputs.",
                "- This fixture must never be described as final v10 benchmark evidence.",
            ]
        )
        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- `{warning}`" for warning in self.warnings)
        return "\n".join(lines)


def load_v10_synthetic_fixture_config(path: str | Path) -> V10FullSyntheticFixtureConfig:
    return V10FullSyntheticFixtureConfig.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


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


def generate_v10_full_synthetic_raw_judgments(
    cases: list[V10Case],
    config: V10FullSyntheticFixtureConfig,
) -> list[dict[str, Any]]:
    rng = random.Random(config.seed)
    rows: list[dict[str, Any]] = []
    for case in sorted(cases, key=lambda item: item.case_id):
        score = _synthetic_score(case, config, rng)
        decision = _decision_for_score(score, config.decision_mapping)
        high_risk = decision in {"DEGRADE", "QUARANTINE", "BLOCK"}
        citation_phrase = ""
        citation_method = config.citation_policy.low_risk_method
        if high_risk:
            citation_phrase = _citation_phrase(case, config)
            citation_method = _citation_method(case, config)
        rows.append(
            {
                "case_id": case.case_id,
                "decision": decision,
                "violation_probability": score,
                "cited_contract_phrase": citation_phrase,
                "citation_verification_method": citation_method,
                "reason_codes": [
                    f"family.{case.family}",
                    f"target_band.{case.target_score_band}",
                    "synthetic_fixture",
                ],
                "uncertainty_reason": _uncertainty_reason(case),
                "provider": config.provider,
                "model": config.model,
                "fixture_id": config.fixture_id,
            }
        )
    return rows


def write_v10_synthetic_fixture_outputs(
    *,
    cases: list[V10Case],
    raw_judgments: list[dict[str, Any]],
    config: V10FullSyntheticFixtureConfig,
    config_path: str | Path,
    input_cases_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    raw_path = target / "v10_full_synthetic_raw_judgments.jsonl"
    summary_path = target / "v10_full_synthetic_generation_summary.json"
    manifest_path = target / "v10_full_synthetic_generation_manifest.json"
    report_path = target / "v10_full_synthetic_generation_report.md"

    raw_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in raw_judgments) + "\n",
        encoding="utf-8",
    )
    summary = _generation_summary(cases, raw_judgments, config)
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(summary.to_markdown() + "\n", encoding="utf-8")
    manifest = _generation_manifest(
        config_path=Path(config_path),
        input_cases_path=Path(input_cases_path),
        raw_path=raw_path,
        config=config,
        summary=summary,
        generated_at=generated_at,
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return raw_path, summary_path, manifest_path, report_path


def _synthetic_score(
    case: V10Case,
    config: V10FullSyntheticFixtureConfig,
    rng: random.Random,
) -> float:
    lower, upper = [float(value) for value in case.target_score_range]
    width = upper - lower
    center = lower + width / 2.0
    jitter = (rng.random() * 2.0 - 1.0) * width * config.score_generation.jitter_fraction_of_band_width
    score = center + jitter
    if config.score_generation.clip_to_target_band:
        epsilon = 1e-6
        score = min(max(score, lower + epsilon), upper - epsilon)
    if config.score_generation.avoid_exact_binary_endpoints:
        score = min(
            max(score, config.score_generation.minimum_score),
            config.score_generation.maximum_score,
        )
    return round(score, 6)


def _decision_for_score(score: float, rules: list[V10DecisionMappingRule]) -> str:
    for rule in rules:
        if rule.max_score_exclusive is not None and score < rule.max_score_exclusive:
            return rule.decision
        if rule.max_score_inclusive is not None and score <= rule.max_score_inclusive:
            return rule.decision
    raise ValueError(f"No synthetic decision mapping covers score={score}")


def _citation_phrase(case: V10Case, config: V10FullSyntheticFixtureConfig) -> str:
    if (
        config.citation_policy.use_expected_cited_contract_phrase_when_available
        and case.expected_cited_contract_phrase
    ):
        return case.expected_cited_contract_phrase
    return case.active_contract_rule_summary


def _citation_method(case: V10Case, config: V10FullSyntheticFixtureConfig) -> str:
    methods = config.citation_policy.high_risk_methods
    if len(methods) == 1:
        return methods[0]
    return methods[sum(ord(char) for char in case.case_id) % len(methods)]


def _uncertainty_reason(case: V10Case) -> str | None:
    if case.family in {"near_boundary_authority_ambiguity", "missing_evidence"}:
        return "Synthetic fixture marks this family as uncertainty-bearing."
    return None


def _generation_summary(
    cases: list[V10Case],
    raw_judgments: list[dict[str, Any]],
    config: V10FullSyntheticFixtureConfig,
) -> V10SyntheticJudgmentGenerationSummary:
    scores = [float(row["violation_probability"]) for row in raw_judgments]
    score_bins = _score_bin_counts(scores)
    payload = {
        "schema_version": "v10_full_synthetic_generation_summary_v1",
        "fixture_id": config.fixture_id,
        "provider": config.provider,
        "model": config.model,
        "seed": config.seed,
        "input_case_count": len(cases),
        "raw_judgment_count": len(raw_judgments),
        "score_entropy": _score_entropy(scores),
        "max_score_bin_fraction": max(score_bins.values()) / len(scores) if scores else 0.0,
        "binary_score_fraction": sum(score in {0.0, 1.0} for score in scores) / len(scores) if scores else 0.0,
        "decision_counts": dict(sorted(Counter(row["decision"] for row in raw_judgments).items())),
        "score_band_counts": dict(sorted(Counter(case.target_score_band for case in cases).items())),
        "label_counts": dict(sorted(Counter(case.label for case in cases).items())),
        "status": "complete" if len(raw_judgments) == len(cases) else "failed",
        "warnings": [
            "synthetic_fixture_not_independent_model_evidence",
            "synthetic_fixture_evidence_level_capped_at_3",
        ],
    }
    return V10SyntheticJudgmentGenerationSummary(
        **payload,
        synthetic_fixture_hash=stable_json_hash(payload),
    )


def _generation_manifest(
    *,
    config_path: Path,
    input_cases_path: Path,
    raw_path: Path,
    config: V10FullSyntheticFixtureConfig,
    summary: V10SyntheticJudgmentGenerationSummary,
    generated_at: str | None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v10_full_synthetic_fixture_v1",
        "fixture_config_path": str(config_path),
        "fixture_config_hash": hash_file(config_path),
        "input_cases_path": str(input_cases_path),
        "input_cases_hash": hash_file(input_cases_path),
        "raw_judgment_count": summary.raw_judgment_count,
        "provider": config.provider,
        "model": config.model,
        "fixture_id": config.fixture_id,
        "raw_judgments_hash": hash_file(raw_path),
        "generated_at": generated_at
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "limitations": [
            "Synthetic fixture only; this is not final v10 evidence.",
            "No live model APIs were called.",
            "No real provider judgments were collected.",
            "Scores are generated from target score bands.",
            "Evidence level is capped at 3 regardless of mechanical diagnostics.",
        ],
    }
    return {**payload, "manifest_hash": stable_json_hash(payload)}


def _score_bin_counts(scores: list[float]) -> dict[str, int]:
    counts = {f"{index / 10:.2f}-{(index + 1) / 10:.2f}": 0 for index in range(10)}
    for score in scores:
        index = min(int(score * 10), 9)
        counts[f"{index / 10:.2f}-{(index + 1) / 10:.2f}"] += 1
    return counts


def _score_entropy(scores: list[float]) -> float:
    if not scores:
        return 0.0
    counts = _score_bin_counts(scores)
    total = len(scores)
    return -sum(
        (count / total) * math.log2(count / total)
        for count in counts.values()
        if count
    )

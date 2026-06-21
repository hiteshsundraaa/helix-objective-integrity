from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OAR36ScoringAnalysisConfig:
    schema_version: str
    suite_name: str
    source_suite: str
    protocol_version: str
    expected_case_count: int
    expected_system_count: int
    manual_result_evidence_cap: int
    no_provider_calls: bool
    no_fake_outputs: bool
    no_synthetic_judgments: bool
    score_only_real_receipts: bool
    allow_ground_truth_scoring_when_receipts_present: bool
    majority_vote_is_not_truth: bool
    model_correctness_not_claimed: bool
    allowed_decisions: list[str]
    risk_bands: dict[str, list[float]]
    citation_strict_methods: list[str]
    notes: str


@dataclass(frozen=True)
class OAR36CaseLevelScore:
    schema_version: str
    suite: str
    case_id: str
    system_role: str
    provider: str
    model: str
    family: str
    domain: str
    label: str
    expected_decision: str
    predicted_decision: str
    decision_match: bool
    violation_probability: float
    expected_risk_interval: list[float]
    risk_interval_match: bool
    predicted_risk_band: str | None
    expected_risk_band: str | None
    risk_band_match: bool
    cited_contract_phrase: str
    citation_verification_method: str
    required_citation_match: bool
    forbidden_citation_hit: bool
    grounding_valid: bool
    receipt_ready: bool
    raw_line_hash: str
    normalized_judgment_hash: str
    receipt_material_hash: str
    score_record_hash: str
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36SystemLevelSummary:
    system_role: str
    provider: str
    model: str
    row_count: int
    receipt_ready_rate: float | None
    parse_issue_rate: float | None
    decision_match_rate: float | None
    risk_interval_match_rate: float | None
    risk_band_match_rate: float | None
    strict_grounding_valid_rate: float | None
    missing_citation_rate: float | None
    forbidden_citation_hit_rate: float | None
    mean_violation_probability: float | None
    score_record_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36DisagreementSummary:
    case_count_with_any_score: int
    complete_case_count_all_systems: int
    majority_decision_agreement_rate: float | None
    unanimous_decision_agreement_rate: float | None
    mean_pairwise_score_distance: float | None
    p95_pairwise_score_distance: float | None
    risk_band_majority_agreement_rate: float | None
    risk_band_unanimous_agreement_rate: float | None
    raw_citation_disagreement_rate: float | None
    grounding_disagreement_rate: float | None
    missing_citation_rate: float | None
    strict_grounding_valid_rate: float | None
    receipt_ready_rate: float | None
    parse_issue_rate: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36BehavioralGroundingGapSummary:
    case_count_with_at_least_two_systems: int
    mean_delta_bg: float | None
    cases_with_positive_gap: int
    cases_with_decision_agreement_but_grounding_failure: int
    family_level_delta_bg: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OAR36AnalysisSummary:
    schema_version: str
    suite_name: str
    source_suite: str
    analysis_state: str
    expected_case_count: int
    expected_system_count: int
    receipt_preparation_count: int
    receipt_ready_count: int
    scored_row_count: int
    scored_case_count: int
    case_level_scores_hash: str
    system_level_summary_hash: str
    disagreement_summary_hash: str
    behavioral_grounding_gap_hash: str
    family_breakdown_hash: str
    manifest_hash: str
    no_provider_calls: bool
    no_fake_outputs: bool
    no_synthetic_judgments: bool
    empirical_results_created: bool
    ground_truth_used_for_scoring: bool
    majority_vote_is_not_truth: bool
    model_correctness_not_claimed: bool
    manual_result_evidence_cap: int
    level_4_allowed: bool
    level_5_allowed: bool
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_oar_36_scoring_analysis_config(path: str | Path) -> OAR36ScoringAnalysisConfig:
    return OAR36ScoringAnalysisConfig(**json.loads(Path(path).read_text(encoding="utf-8")))


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def score_decision(predicted_decision: str | None, expected_decision: str | None) -> bool:
    return bool(predicted_decision) and predicted_decision == expected_decision


def score_risk_interval(score: float | None, expected_interval: list[float] | None) -> bool:
    if score is None or not expected_interval or len(expected_interval) < 2:
        return False
    return float(expected_interval[0]) <= score <= float(expected_interval[1])


def score_citation(
    cited_phrase: str | None,
    required_phrases: list[str],
    forbidden_phrases: list[str],
    verification_method: str | None,
    config: OAR36ScoringAnalysisConfig,
) -> dict[str, Any]:
    cited_normalized = _normalize_text(cited_phrase)
    required_normalized = {_normalize_text(phrase) for phrase in required_phrases if _normalize_text(phrase)}
    forbidden_normalized = {_normalize_text(phrase) for phrase in forbidden_phrases if _normalize_text(phrase)}
    method = verification_method or "missing"
    issues: list[str] = []
    required_match = True if not required_normalized else cited_normalized in required_normalized
    forbidden_hit = bool(cited_normalized and cited_normalized in forbidden_normalized)
    if not cited_normalized:
        issues.append("missing_citation")
    if method == "missing":
        issues.append("citation_method_missing")
    if method not in config.citation_strict_methods:
        issues.append("citation_method_not_strict")
    if not required_match:
        issues.append("required_citation_not_matched")
    if forbidden_hit:
        issues.append("forbidden_citation_hit")
    grounding_valid = (
        bool(cited_normalized)
        and method in config.citation_strict_methods
        and required_match
        and not forbidden_hit
    )
    return {
        "required_citation_match": required_match,
        "forbidden_citation_hit": forbidden_hit,
        "grounding_valid": grounding_valid,
        "issues": sorted(set(issues)),
    }


def risk_band_for_score(score: float | None, config: OAR36ScoringAnalysisConfig) -> str | None:
    if score is None:
        return None
    for band, interval in config.risk_bands.items():
        if len(interval) >= 2 and float(interval[0]) <= score <= float(interval[1]):
            return band
    return None


def build_case_level_scores(
    receipt_records: list[dict[str, Any]],
    normalized_judgments: list[dict[str, Any]],
    holdout_records: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    config: OAR36ScoringAnalysisConfig,
) -> list[OAR36CaseLevelScore]:
    holdout_by_case = {record["case_id"]: record for record in holdout_records}
    cases_by_case = {record["case_id"]: record for record in cases}
    normalized_by_hash = {
        record.get("normalized_judgment_hash"): record
        for record in normalized_judgments
        if record.get("normalized_judgment_hash")
    }
    normalized_by_fallback = {
        _normalized_fallback_key(record): record
        for record in normalized_judgments
    }
    scores: list[OAR36CaseLevelScore] = []
    for receipt in receipt_records:
        if not receipt.get("receipt_ready"):
            continue
        case_id = str(receipt.get("case_id") or "")
        holdout = holdout_by_case.get(case_id)
        if not holdout:
            continue
        normalized = normalized_by_hash.get(receipt.get("normalized_judgment_hash"))
        if normalized is None:
            normalized = normalized_by_fallback.get(_receipt_fallback_key(receipt))
        if normalized is None:
            continue
        case_record = cases_by_case.get(case_id, {})
        predicted_decision = str(normalized.get("decision") or "")
        score = _to_float(normalized.get("violation_probability"))
        citation = str(normalized.get("cited_contract_phrase") or "")
        method = str(normalized.get("citation_verification_method") or "missing")
        expected_interval = [float(value) for value in holdout.get("expected_risk_interval", [])]
        expected_band = holdout.get("risk_band") or risk_band_for_score(_interval_midpoint(expected_interval), config)
        predicted_band = risk_band_for_score(score, config)
        citation_score = score_citation(
            citation,
            list(holdout.get("required_citation_phrases", [])),
            list(holdout.get("forbidden_citation_phrases", [])),
            method,
            config,
        )
        issues = list(citation_score["issues"])
        if score is None:
            issues.append("missing_violation_probability")
        if predicted_decision not in config.allowed_decisions:
            issues.append("invalid_predicted_decision")
        record = {
            "schema_version": "oar_case_score_v1",
            "suite": config.suite_name,
            "case_id": case_id,
            "system_role": str(receipt.get("system_role") or normalized.get("system_role") or ""),
            "provider": str(receipt.get("provider") or normalized.get("provider") or ""),
            "model": str(receipt.get("model") or normalized.get("model") or ""),
            "family": str(holdout.get("family") or _case_source_field(case_record, "family") or ""),
            "domain": str(holdout.get("domain") or _case_source_field(case_record, "domain") or ""),
            "label": str(holdout.get("label") or _case_source_field(case_record, "label") or ""),
            "expected_decision": str(holdout.get("expected_decision") or ""),
            "predicted_decision": predicted_decision,
            "decision_match": score_decision(predicted_decision, holdout.get("expected_decision")),
            "violation_probability": score if score is not None else 0.0,
            "expected_risk_interval": expected_interval,
            "risk_interval_match": score_risk_interval(score, expected_interval),
            "predicted_risk_band": predicted_band,
            "expected_risk_band": expected_band,
            "risk_band_match": bool(predicted_band and expected_band and predicted_band == expected_band),
            "cited_contract_phrase": citation,
            "citation_verification_method": method,
            "required_citation_match": bool(citation_score["required_citation_match"]),
            "forbidden_citation_hit": bool(citation_score["forbidden_citation_hit"]),
            "grounding_valid": bool(citation_score["grounding_valid"]),
            "receipt_ready": bool(receipt.get("receipt_ready")),
            "raw_line_hash": str(receipt.get("raw_line_hash") or normalized.get("raw_line_hash") or ""),
            "normalized_judgment_hash": str(receipt.get("normalized_judgment_hash") or normalized.get("normalized_judgment_hash") or ""),
            "receipt_material_hash": str(receipt.get("receipt_material_hash") or ""),
            "score_record_hash": "",
            "issues": sorted(set(issues)),
        }
        record["score_record_hash"] = sha256_text(stable_json_dumps({**record, "score_record_hash": ""}))
        scores.append(OAR36CaseLevelScore(**record))
    return scores


def build_system_level_summary(
    case_scores: list[OAR36CaseLevelScore],
    config: OAR36ScoringAnalysisConfig,
) -> list[OAR36SystemLevelSummary]:
    del config
    grouped: dict[tuple[str, str, str], list[OAR36CaseLevelScore]] = defaultdict(list)
    for score in case_scores:
        grouped[(score.system_role, score.provider, score.model)].append(score)
    summaries: list[OAR36SystemLevelSummary] = []
    for (system_role, provider, model), rows in sorted(grouped.items()):
        summaries.append(
            OAR36SystemLevelSummary(
                system_role=system_role,
                provider=provider,
                model=model,
                row_count=len(rows),
                receipt_ready_rate=_rate(sum(row.receipt_ready for row in rows), len(rows)),
                parse_issue_rate=_rate(sum(bool(row.issues) for row in rows), len(rows)),
                decision_match_rate=_rate(sum(row.decision_match for row in rows), len(rows)),
                risk_interval_match_rate=_rate(sum(row.risk_interval_match for row in rows), len(rows)),
                risk_band_match_rate=_rate(sum(row.risk_band_match for row in rows), len(rows)),
                strict_grounding_valid_rate=_rate(sum(row.grounding_valid for row in rows), len(rows)),
                missing_citation_rate=_rate(sum(_is_missing_citation(row) for row in rows), len(rows)),
                forbidden_citation_hit_rate=_rate(sum(row.forbidden_citation_hit for row in rows), len(rows)),
                mean_violation_probability=_mean([row.violation_probability for row in rows]),
                score_record_count=len(rows),
            )
        )
    return summaries


def build_disagreement_summary(
    case_scores: list[OAR36CaseLevelScore],
    config: OAR36ScoringAnalysisConfig,
) -> OAR36DisagreementSummary:
    grouped = _scores_by_case(case_scores)
    any_case_count = len(grouped)
    complete_case_count = sum(
        len({row.system_role for row in rows}) >= config.expected_system_count
        for rows in grouped.values()
    )
    pairwise_distances: list[float] = []
    multi_case_rows = [rows for rows in grouped.values() if len(rows) >= 2]
    for rows in multi_case_rows:
        values = [row.violation_probability for row in rows]
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                pairwise_distances.append(abs(values[i] - values[j]))
    return OAR36DisagreementSummary(
        case_count_with_any_score=any_case_count,
        complete_case_count_all_systems=complete_case_count,
        majority_decision_agreement_rate=_rate(
            sum(_has_majority([row.predicted_decision for row in rows]) for rows in grouped.values()),
            any_case_count,
        ),
        unanimous_decision_agreement_rate=_rate(
            sum(_is_unanimous([row.predicted_decision for row in rows]) for rows in grouped.values()),
            any_case_count,
        ),
        mean_pairwise_score_distance=_mean(pairwise_distances),
        p95_pairwise_score_distance=_percentile(pairwise_distances, 0.95),
        risk_band_majority_agreement_rate=_rate(
            sum(_has_majority([row.predicted_risk_band for row in rows]) for rows in grouped.values()),
            any_case_count,
        ),
        risk_band_unanimous_agreement_rate=_rate(
            sum(_is_unanimous([row.predicted_risk_band for row in rows]) for rows in grouped.values()),
            any_case_count,
        ),
        raw_citation_disagreement_rate=_rate(
            sum(not _is_unanimous([_normalize_text(row.cited_contract_phrase) for row in rows]) for rows in multi_case_rows),
            len(multi_case_rows),
        ),
        grounding_disagreement_rate=_rate(
            sum(not _is_unanimous([row.grounding_valid for row in rows]) for rows in multi_case_rows),
            len(multi_case_rows),
        ),
        missing_citation_rate=_rate(sum(_is_missing_citation(row) for row in case_scores), len(case_scores)),
        strict_grounding_valid_rate=_rate(sum(row.grounding_valid for row in case_scores), len(case_scores)),
        receipt_ready_rate=_rate(sum(row.receipt_ready for row in case_scores), len(case_scores)),
        parse_issue_rate=_rate(sum(bool(row.issues) for row in case_scores), len(case_scores)),
    )


def build_behavioral_grounding_gap(
    case_scores: list[OAR36CaseLevelScore],
    config: OAR36ScoringAnalysisConfig,
) -> OAR36BehavioralGroundingGapSummary:
    del config
    grouped = {case_id: rows for case_id, rows in _scores_by_case(case_scores).items() if len(rows) >= 2}
    deltas: list[float] = []
    family_deltas: dict[str, list[float]] = defaultdict(list)
    decision_agreement_but_grounding_failure = 0
    for rows in grouped.values():
        decision_majority_agreement = 1.0 if _has_majority([row.predicted_decision for row in rows]) else 0.0
        grounding_unanimous_valid_and_same = 1.0 if _grounding_unanimous_valid_and_same(rows) else 0.0
        delta = decision_majority_agreement - grounding_unanimous_valid_and_same
        deltas.append(delta)
        family_deltas[rows[0].family].append(delta)
        if decision_majority_agreement and not grounding_unanimous_valid_and_same:
            decision_agreement_but_grounding_failure += 1
    return OAR36BehavioralGroundingGapSummary(
        case_count_with_at_least_two_systems=len(grouped),
        mean_delta_bg=_mean(deltas),
        cases_with_positive_gap=sum(delta > 0 for delta in deltas),
        cases_with_decision_agreement_but_grounding_failure=decision_agreement_but_grounding_failure,
        family_level_delta_bg={
            family: _mean(values) or 0.0
            for family, values in sorted(family_deltas.items())
        },
    )


def build_family_breakdown(
    case_scores: list[OAR36CaseLevelScore],
    cases: list[dict[str, Any]],
    holdout_records: list[dict[str, Any]],
    config: OAR36ScoringAnalysisConfig,
) -> dict[str, Any]:
    del cases, holdout_records
    grouped: dict[str, list[OAR36CaseLevelScore]] = defaultdict(list)
    for score in case_scores:
        grouped[score.family].append(score)
    gap = build_behavioral_grounding_gap(case_scores, config)
    rows: dict[str, Any] = {}
    for family, scores in sorted(grouped.items()):
        rows[family] = {
            "scored_rows": len(scores),
            "unique_cases": len({score.case_id for score in scores}),
            "decision_match_rate": _rate(sum(score.decision_match for score in scores), len(scores)),
            "risk_band_match_rate": _rate(sum(score.risk_band_match for score in scores), len(scores)),
            "strict_grounding_valid_rate": _rate(sum(score.grounding_valid for score in scores), len(scores)),
            "missing_citation_rate": _rate(sum(_is_missing_citation(score) for score in scores), len(scores)),
            "mean_delta_bg": gap.family_level_delta_bg.get(family),
            "receipt_ready_rate": _rate(sum(score.receipt_ready for score in scores), len(scores)),
        }
    return {
        "schema_version": "oar_36_family_breakdown_v1",
        "suite_name": "OAR-36",
        "families": rows,
    }


def analyze_oar_36_results(
    config: OAR36ScoringAnalysisConfig,
    receipt_prep_manifest: dict[str, Any],
    receipt_records: list[dict[str, Any]],
    normalized_judgments: list[dict[str, Any]],
    holdout_records: list[dict[str, Any]],
    cases: list[dict[str, Any]],
) -> tuple[
    OAR36AnalysisSummary,
    list[OAR36CaseLevelScore],
    list[OAR36SystemLevelSummary],
    OAR36DisagreementSummary,
    OAR36BehavioralGroundingGapSummary,
    dict[str, Any],
]:
    receipt_preparation_count = len(receipt_records)
    receipt_ready_count = sum(bool(record.get("receipt_ready")) for record in receipt_records)
    if receipt_preparation_count == 0:
        case_scores: list[OAR36CaseLevelScore] = []
        analysis_state = "awaiting_receipt_preparation"
        empirical_results_created = False
        ground_truth_used_for_scoring = False
    elif receipt_ready_count == 0:
        case_scores = []
        analysis_state = "receipt_rows_present_no_ready_receipts"
        empirical_results_created = False
        ground_truth_used_for_scoring = False
    else:
        case_scores = build_case_level_scores(
            receipt_records,
            normalized_judgments,
            holdout_records,
            cases,
            config,
        )
        expected_rows = config.expected_case_count * config.expected_system_count
        analysis_state = (
            "complete_analysis_ready"
            if receipt_ready_count >= expected_rows and len(case_scores) >= expected_rows
            else "partial_analysis_ready"
        )
        empirical_results_created = True
        ground_truth_used_for_scoring = True

    system_summary = build_system_level_summary(case_scores, config)
    disagreement = build_disagreement_summary(case_scores, config)
    behavioral_gap = build_behavioral_grounding_gap(case_scores, config)
    family_breakdown = build_family_breakdown(case_scores, cases, holdout_records, config)
    summary = OAR36AnalysisSummary(
        schema_version="oar_36_analysis_manifest_v1",
        suite_name=config.suite_name,
        source_suite=config.source_suite,
        analysis_state=analysis_state,
        expected_case_count=config.expected_case_count,
        expected_system_count=config.expected_system_count,
        receipt_preparation_count=receipt_preparation_count,
        receipt_ready_count=receipt_ready_count,
        scored_row_count=len(case_scores),
        scored_case_count=len({score.case_id for score in case_scores}),
        case_level_scores_hash=sha256_text(stable_json_dumps([score.to_dict() for score in case_scores])),
        system_level_summary_hash=sha256_text(stable_json_dumps([row.to_dict() for row in system_summary])),
        disagreement_summary_hash=sha256_text(stable_json_dumps(disagreement.to_dict())),
        behavioral_grounding_gap_hash=sha256_text(stable_json_dumps(behavioral_gap.to_dict())),
        family_breakdown_hash=sha256_text(stable_json_dumps(family_breakdown)),
        manifest_hash="",
        no_provider_calls=config.no_provider_calls,
        no_fake_outputs=config.no_fake_outputs,
        no_synthetic_judgments=config.no_synthetic_judgments,
        empirical_results_created=empirical_results_created,
        ground_truth_used_for_scoring=ground_truth_used_for_scoring,
        majority_vote_is_not_truth=config.majority_vote_is_not_truth,
        model_correctness_not_claimed=config.model_correctness_not_claimed,
        manual_result_evidence_cap=config.manual_result_evidence_cap,
        level_4_allowed=False,
        level_5_allowed=False,
        limitations=[
            config.notes,
            "OAR-36 is a dry-run subset and does not estimate full OAR-360 performance.",
            "Majority vote is preserved as disagreement evidence, not truth.",
            "Model correctness is not claimed.",
            "Manual evidence remains capped at Level 3.",
            f"Receipt-prep import state: {receipt_prep_manifest.get('import_state', 'unknown')}",
        ],
    )
    return summary, case_scores, system_summary, disagreement, behavioral_gap, family_breakdown


def write_oar_36_analysis_outputs(
    summary: OAR36AnalysisSummary,
    case_scores: list[OAR36CaseLevelScore],
    system_summary: list[OAR36SystemLevelSummary],
    disagreement_summary: OAR36DisagreementSummary,
    behavioral_grounding_gap: OAR36BehavioralGroundingGapSummary,
    family_breakdown: dict[str, Any],
    out_dir: str | Path,
) -> None:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "oar_36_analysis_status.json"
    case_scores_path = output_dir / "oar_36_case_level_scores.jsonl"
    system_summary_path = output_dir / "oar_36_system_level_summary.json"
    disagreement_path = output_dir / "oar_36_disagreement_summary.json"
    behavioral_gap_path = output_dir / "oar_36_behavioral_grounding_gap.json"
    family_breakdown_path = output_dir / "oar_36_family_breakdown.json"
    manifest_path = output_dir / "oar_36_analysis_manifest.json"
    report_path = output_dir / "oar_36_analysis_report.md"

    _write_jsonl(case_scores_path, [score.to_dict() for score in case_scores])
    _write_json(
        system_summary_path,
        {
            "schema_version": "oar_36_system_level_summary_v1",
            "suite_name": summary.suite_name,
            "systems": [row.to_dict() for row in system_summary],
        },
    )
    _write_json(disagreement_path, {"schema_version": "oar_36_disagreement_summary_v1", **disagreement_summary.to_dict()})
    _write_json(
        behavioral_gap_path,
        {"schema_version": "oar_36_behavioral_grounding_gap_v1", **behavioral_grounding_gap.to_dict()},
    )
    _write_json(family_breakdown_path, family_breakdown)

    manifest_payload = {
        **summary.to_dict(),
        "case_level_scores_hash": sha256_file(case_scores_path),
        "system_level_summary_hash": sha256_file(system_summary_path),
        "disagreement_summary_hash": sha256_file(disagreement_path),
        "behavioral_grounding_gap_hash": sha256_file(behavioral_gap_path),
        "family_breakdown_hash": sha256_file(family_breakdown_path),
        "manifest_hash": "",
    }
    manifest_payload["manifest_hash"] = sha256_text(stable_json_dumps(manifest_payload))
    _write_json(manifest_path, manifest_payload)
    _write_json(
        status_path,
        {
            "schema_version": "oar_36_analysis_status_v1",
            "suite_name": summary.suite_name,
            "analysis_state": summary.analysis_state,
            "receipt_preparation_count": summary.receipt_preparation_count,
            "receipt_ready_count": summary.receipt_ready_count,
            "scored_row_count": summary.scored_row_count,
            "scored_case_count": summary.scored_case_count,
            "empirical_results_created": summary.empirical_results_created,
            "ground_truth_used_for_scoring": summary.ground_truth_used_for_scoring,
        },
    )
    report_summary = OAR36AnalysisSummary(**manifest_payload)
    report_path.write_text(
        generate_oar_36_analysis_report(
            report_summary,
            disagreement_summary,
            behavioral_grounding_gap,
            family_breakdown,
        ),
        encoding="utf-8",
    )


def generate_oar_36_analysis_report(
    summary: OAR36AnalysisSummary,
    disagreement_summary: OAR36DisagreementSummary,
    behavioral_grounding_gap: OAR36BehavioralGroundingGapSummary,
    family_breakdown: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# OAR-36 Scoring and Disagreement Analysis Report",
            "",
            "## Executive Summary",
            (
                f"Analysis state is `{summary.analysis_state}` with "
                f"{summary.scored_row_count} scored rows across {summary.scored_case_count} cases. "
                "no provider calls were made, no fake outputs were generated, and no synthetic judgments were created."
            ),
            "",
            "## Analysis State",
            f"- analysis_state: `{summary.analysis_state}`",
            f"- empirical_results_created: `{str(summary.empirical_results_created).lower()}`",
            f"- ground_truth_used_for_scoring: `{str(summary.ground_truth_used_for_scoring).lower()}`",
            "",
            "## Inputs",
            f"- receipt_preparation_count: `{summary.receipt_preparation_count}`",
            f"- receipt_ready_count: `{summary.receipt_ready_count}`",
            "",
            "## Scored Coverage",
            f"- scored_row_count: `{summary.scored_row_count}`",
            f"- scored_case_count: `{summary.scored_case_count}`",
            "",
            "## Decision and Risk Scoring",
            f"- majority_decision_agreement_rate: `{disagreement_summary.majority_decision_agreement_rate}`",
            f"- risk_band_majority_agreement_rate: `{disagreement_summary.risk_band_majority_agreement_rate}`",
            "",
            "## Citation and Grounding Scoring",
            f"- strict_grounding_valid_rate: `{disagreement_summary.strict_grounding_valid_rate}`",
            f"- missing_citation_rate: `{disagreement_summary.missing_citation_rate}`",
            "",
            "## Disagreement Analysis",
            f"- case_count_with_any_score: `{disagreement_summary.case_count_with_any_score}`",
            f"- complete_case_count_all_systems: `{disagreement_summary.complete_case_count_all_systems}`",
            f"- mean_pairwise_score_distance: `{disagreement_summary.mean_pairwise_score_distance}`",
            "",
            "## Behavioral-Grounding Gap",
            f"- mean_delta_bg: `{behavioral_grounding_gap.mean_delta_bg}`",
            f"- cases_with_positive_gap: `{behavioral_grounding_gap.cases_with_positive_gap}`",
            "",
            "## Family Breakdown",
            f"- family_count: `{len(family_breakdown.get('families', {}))}`",
            "",
            "## Evidence Boundary",
            "- no provider calls were made.",
            "- no fake outputs were generated.",
            "- no synthetic judgments were created.",
            "- majority vote is not truth.",
            "- model correctness is not claimed.",
            "- OAR-36 is a dry-run subset and does not estimate full OAR-360 performance.",
            f"- manual evidence is capped at Level {summary.manual_result_evidence_cap}.",
            "- Level 4/5 are not claimed.",
            "",
            "## What This Supports",
            "- Holdout scoring for real parsed receipt-prep rows only.",
            "- System-level and family-level dry-run diagnostics.",
            "- Disagreement and behavioral-grounding-gap measurement without treating agreement as truth.",
            "",
            "## What This Does Not Prove",
            "- This does not prove model correctness.",
            "- This does not create OAR-360 performance claims.",
            "- This does not turn manual dry-run evidence into Level 4 or Level 5 evidence.",
            "",
            "## Limitations",
            *[f"- {limitation}" for limitation in summary.limitations],
            "",
            "## Next Steps",
            "- Collect raw OAR-36 provider outputs.",
            "- Run receipt preparation without repairing provider rows.",
            "- Re-run this analysis only over receipt-ready rows.",
            "",
        ]
    )


def _normalize_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _interval_midpoint(interval: list[float]) -> float | None:
    if len(interval) < 2:
        return None
    return (float(interval[0]) + float(interval[1])) / 2.0


def _case_source_field(case_record: dict[str, Any], field: str) -> Any:
    return case_record.get("source_case", {}).get(field) or case_record.get(field)


def _normalized_fallback_key(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(record.get("case_id") or ""),
        str(record.get("system_role") or ""),
        str(record.get("provider") or ""),
        str(record.get("model") or ""),
        str(record.get("source_file") or ""),
    )


def _receipt_fallback_key(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(record.get("case_id") or ""),
        str(record.get("system_role") or ""),
        str(record.get("provider") or ""),
        str(record.get("model") or ""),
        str(record.get("source_file") or ""),
    )


def _rate(numerator: int | float, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return float(numerator) / float(denominator)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _scores_by_case(case_scores: list[OAR36CaseLevelScore]) -> dict[str, list[OAR36CaseLevelScore]]:
    grouped: dict[str, list[OAR36CaseLevelScore]] = defaultdict(list)
    for score in case_scores:
        grouped[score.case_id].append(score)
    return grouped


def _has_majority(values: list[Any]) -> bool:
    if not values:
        return False
    counts = Counter(values)
    return counts.most_common(1)[0][1] > len(values) / 2.0


def _is_unanimous(values: list[Any]) -> bool:
    return bool(values) and len(set(values)) == 1


def _is_missing_citation(row: OAR36CaseLevelScore) -> bool:
    return not _normalize_text(row.cited_contract_phrase) or row.citation_verification_method == "missing"


def _grounding_unanimous_valid_and_same(rows: list[OAR36CaseLevelScore]) -> bool:
    if not rows or not all(row.grounding_valid for row in rows):
        return False
    return _is_unanimous([_normalize_text(row.cited_contract_phrase) for row in rows])


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n" for record in records),
        encoding="utf-8",
    )

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
import json
from pathlib import Path
import re
import string
import subprocess
from typing import Any

from helix.benchmark.benchmark_receipts import hash_file, stable_json_hash
from helix.benchmark.v10_disagreement_analysis import (
    load_real_pilot_consistency_artifacts,
)


ANALYSIS_VERSION = "v10.20"
DEFAULT_FAILURE_CRITERION_RATE = 0.566667
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "while",
    "with",
}
CONSTRAINT_KEYWORDS = {
    "permission": {
        "allow",
        "allowed",
        "allows",
        "approved",
        "authorized",
        "can",
        "may",
        "permit",
        "permitted",
        "permits",
    },
    "prohibition": {
        "block",
        "cannot",
        "deny",
        "forbidden",
        "must not",
        "outside",
        "prohibited",
        "reject",
        "unauthorized",
    },
    "requirement": {
        "assign",
        "assigned",
        "assigns",
        "mandatory",
        "must",
        "need",
        "needs",
        "required",
        "requires",
        "shall",
    },
    "condition": {"except", "if", "only if", "unless", "when"},
    "evidence": {"citation", "cite", "evidence", "proof", "receipt", "source", "verify"},
}


class ResolutionFailureMode(str, Enum):
    MISSING_INPUT = "input_citation_empty"
    HALLUCINATED = "citation_not_in_contract"
    AMBIGUOUS_MATCH = "multiple_canonical_phrases_equally_close"
    BELOW_THRESHOLD = "overlap_below_min_threshold"
    CONTRACT_TOO_SHORT = "contract_rule_too_short_for_extraction"
    CONTRACT_UNAVAILABLE = "contract_rule_unavailable"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class V10CanonicalPhrase:
    phrase_id: str
    phrase_text: str
    normalized_text: str
    source: str
    order_index: int
    specificity_score: float
    constraint_type: str


@dataclass(frozen=True)
class V10ResolvedCitation:
    system_role: str
    raw_citation: str
    normalized_citation: str
    canonical_phrase_id: str | None
    canonical_phrase_text: str | None
    resolution_method: str
    confidence: float
    is_in_contract: bool
    failure_mode: str | None
    candidate_count: int
    top_candidates: list[dict[str, Any]]
    pass_through_unanimous: bool


@dataclass(frozen=True)
class V10CaseCitationResolution:
    case_id: str
    family: str | None
    label: str | None
    raw_citations_by_system: dict[str, str]
    citation_methods_by_system: dict[str, str]
    canonical_phrases: list[dict[str, Any]]
    resolved_by_system: dict[str, dict[str, Any]]
    raw_citation_agreement: bool
    resolved_citation_agreement: bool
    weighted_resolved_agreement: float
    missing_citation_systems: list[str]
    hallucinated_citation_systems: list[str]
    ambiguous_match_systems: list[str]
    unresolved_systems: list[str]
    resolver_category: str
    interpretation: str


@dataclass(frozen=True)
class V10CitationResolverSummary:
    schema_version: str
    source_run_id: str
    case_count: int
    system_count: int
    pre_resolution_string_disagreement_rate: float
    v10_19_post_normalization_disagreement_rate: float
    post_resolution_disagreement_rate: float
    confidence_weighted_post_resolution_disagreement_rate: float
    missing_citation_rate: float
    hallucinated_citation_rate: float
    unresolved_citation_rate: float
    ambiguous_match_rate: float
    scope_disagreement_resolved_rate: float
    unanimous_pass_through_count: int
    improvement_over_v10_19_normalization: float
    success_criterion_passed: bool
    failure_criterion_triggered: bool
    level_4_allowed: bool
    level_5_allowed: bool
    resolver_hash: str
    status: str


def normalize_text(text: str) -> str:
    value = (text or "").strip()
    value = (
        value.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )
    value = re.sub(r"\s+", " ", value).strip().lower()
    value = re.sub(
        r"^(the\s+contract\s+says|contract\s+states|contract\s+says|according\s+to\s+the\s+contract)\s*[:,-]?\s*",
        "",
        value,
    )
    return value.strip(string.punctuation + " ")


def extract_canonical_phrases(contract_rule_summary: str) -> list[V10CanonicalPhrase]:
    normalized_contract = normalize_text(contract_rule_summary)
    if not normalized_contract:
        return []
    fragments = _split_contract_fragments(contract_rule_summary)
    phrases: list[V10CanonicalPhrase] = []
    seen: set[str] = set()
    for fragment in fragments:
        normalized = normalize_text(fragment)
        if not normalized or normalized in seen:
            continue
        constraint_type = _constraint_type(normalized)
        token_count = len(_meaningful_tokens(normalized))
        if token_count < 3 and constraint_type == "unknown":
            continue
        if token_count < 2:
            continue
        if constraint_type == "unknown" and token_count < 6:
            continue
        seen.add(normalized)
        order_index = len(phrases)
        phrases.append(
            V10CanonicalPhrase(
                phrase_id=f"canonical_phrase_{order_index:03d}",
                phrase_text=fragment.strip(),
                normalized_text=normalized,
                source="contract_rule_summary",
                order_index=order_index,
                specificity_score=_specificity_score(normalized, constraint_type),
                constraint_type=constraint_type,
            )
        )
    return phrases


def token_overlap_score(a: str, b: str) -> float:
    tokens_a = set(_meaningful_tokens(normalize_text(a)))
    tokens_b = set(_meaningful_tokens(normalize_text(b)))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(1, min(len(tokens_a), len(tokens_b)))


def resolve_citation(
    raw_citation: str | None,
    canonical_phrases: list[V10CanonicalPhrase],
    contract_rule_summary: str | None,
    config: dict[str, Any],
    *,
    system_role: str = "",
    pass_through_unanimous: bool = False,
) -> V10ResolvedCitation:
    raw = (raw_citation or "").strip()
    normalized = normalize_text(raw)
    if not raw:
        return _unresolved(
            system_role,
            raw,
            normalized,
            ResolutionFailureMode.MISSING_INPUT,
            float(config.get("missing_input_confidence", 0.0)),
            [],
            pass_through_unanimous,
        )
    if not contract_rule_summary:
        return _unresolved(
            system_role,
            raw,
            normalized,
            ResolutionFailureMode.CONTRACT_UNAVAILABLE,
            0.0,
            [],
            pass_through_unanimous,
        )
    if not canonical_phrases:
        return _unresolved(
            system_role,
            raw,
            normalized,
            ResolutionFailureMode.CONTRACT_TOO_SHORT,
            0.0,
            [],
            pass_through_unanimous,
        )

    contract_normalized = normalize_text(contract_rule_summary)
    is_in_contract = raw in contract_rule_summary or (
        bool(normalized) and normalized in contract_normalized
    )
    exact_matches = [
        phrase
        for phrase in canonical_phrases
        if raw and raw in phrase.phrase_text
    ]
    if exact_matches:
        phrase = _best_substring_phrase(raw, exact_matches)
        candidates = _candidate_rows(raw, canonical_phrases)
        return _resolved(
            system_role,
            raw,
            normalized,
            phrase,
            "exact",
            float(config.get("exact_match_confidence", 1.0)),
            True,
            candidates,
            pass_through_unanimous,
        )

    normalized_matches = [
        phrase
        for phrase in canonical_phrases
        if normalized and normalized in phrase.normalized_text
    ]
    if normalized_matches:
        phrase = _best_substring_phrase(normalized, normalized_matches, normalized_input=True)
        candidates = _candidate_rows(raw, canonical_phrases)
        return _resolved(
            system_role,
            raw,
            normalized,
            phrase,
            "normalized",
            float(config.get("normalized_match_confidence", 0.9)),
            True,
            candidates,
            pass_through_unanimous,
        )

    candidates = _candidate_rows(raw, canonical_phrases)
    min_overlap = float(config.get("min_overlap_threshold", 0.4))
    ambiguous_delta = float(config.get("ambiguous_match_delta", 0.05))
    max_fuzzy_confidence = float(config.get("fuzzy_match_max_confidence", 0.75))
    best = candidates[0] if candidates else None
    second = candidates[1] if len(candidates) > 1 else None
    if not best or float(best["overlap_score"]) < min_overlap:
        mode = (
            ResolutionFailureMode.HALLUCINATED
            if not is_in_contract and normalized not in contract_normalized
            else ResolutionFailureMode.BELOW_THRESHOLD
        )
        return _unresolved(
            system_role,
            raw,
            normalized,
            mode,
            0.0,
            candidates,
            pass_through_unanimous,
        )
    if second and abs(float(best["overlap_score"]) - float(second["overlap_score"])) <= ambiguous_delta:
        return _unresolved(
            system_role,
            raw,
            normalized,
            ResolutionFailureMode.AMBIGUOUS_MATCH,
            0.0,
            candidates,
            pass_through_unanimous,
            is_in_contract=is_in_contract,
        )
    phrase = canonical_phrases[int(best["order_index"])]
    confidence = min(max_fuzzy_confidence, float(best["overlap_score"]))
    return _resolved(
        system_role,
        raw,
        normalized,
        phrase,
        "token_overlap",
        confidence,
        is_in_contract,
        candidates,
        pass_through_unanimous,
    )


def raw_citation_agreement(resolutions_or_records: list[Any] | dict[str, str]) -> bool:
    if isinstance(resolutions_or_records, dict):
        citations = [str(value or "") for value in resolutions_or_records.values()]
    else:
        citations = [
            str(getattr(item, "raw_citation", "") if not isinstance(item, dict) else item.get("raw_citation", ""))
            for item in resolutions_or_records
        ]
    if not citations or any(not citation.strip() for citation in citations):
        return False
    return len(set(citations)) == 1


def resolved_citation_agreement(resolutions: list[V10ResolvedCitation] | list[dict[str, Any]]) -> bool:
    ids = [
        getattr(item, "canonical_phrase_id", None)
        if not isinstance(item, dict)
        else item.get("canonical_phrase_id")
        for item in resolutions
    ]
    if not ids or any(not value for value in ids):
        return False
    return len(set(ids)) == 1


def weighted_citation_agreement(resolutions: list[V10ResolvedCitation] | list[dict[str, Any]]) -> float:
    if len(resolutions) < 2:
        return 0.0
    weights: list[float] = []
    for index, left in enumerate(resolutions):
        for right in resolutions[index + 1 :]:
            left_id = (
                getattr(left, "canonical_phrase_id", None)
                if not isinstance(left, dict)
                else left.get("canonical_phrase_id")
            )
            right_id = (
                getattr(right, "canonical_phrase_id", None)
                if not isinstance(right, dict)
                else right.get("canonical_phrase_id")
            )
            left_confidence = (
                float(getattr(left, "confidence", 0.0))
                if not isinstance(left, dict)
                else float(left.get("confidence") or 0.0)
            )
            right_confidence = (
                float(getattr(right, "confidence", 0.0))
                if not isinstance(right, dict)
                else float(right.get("confidence") or 0.0)
            )
            if left_id and right_id and left_id == right_id:
                weights.append(min(left_confidence, right_confidence))
            else:
                weights.append(0.0)
    return sum(weights) / len(weights) if weights else 0.0


def compute_resolver_summary(
    case_resolutions: list[V10CaseCitationResolution] | list[dict[str, Any]],
    v10_19_baseline: dict[str, Any],
    prereg_config: dict[str, Any],
) -> dict[str, Any]:
    rows = [_case_row(row) for row in case_resolutions]
    case_count = len(rows)
    system_roles = sorted(
        {
            system
            for row in rows
            for system in (row.get("raw_citations_by_system") or {}).keys()
        }
    )
    baseline_normalization = v10_19_baseline.get("citation_normalization_experiment") or {}
    pre_rate = float(
        baseline_normalization.get("pre_normalization_string_disagreement_rate")
        or v10_19_baseline.get("pre_normalization_string_disagreement_rate")
        or 0.0
    )
    v10_19_post_rate = float(
        baseline_normalization.get("post_normalization_anchor_disagreement_rate")
        or v10_19_baseline.get("post_normalization_anchor_disagreement_rate")
        or 0.0
    )
    post_rate = _rate(not bool(row.get("resolved_citation_agreement")) for row in rows)
    weighted_agreement = (
        sum(float(row.get("weighted_resolved_agreement") or 0.0) for row in rows) / case_count
        if case_count
        else 0.0
    )
    weighted_post_rate = 1.0 - weighted_agreement if case_count else 0.0
    missing_rate = _rate(row.get("missing_citation_systems") for row in rows)
    hallucinated_rate = _rate(row.get("hallucinated_citation_systems") for row in rows)
    unresolved_rate = _rate(row.get("unresolved_systems") for row in rows)
    ambiguous_rate = _rate(row.get("ambiguous_match_systems") for row in rows)
    scope_rows = [
        row
        for row in rows
        if str(row.get("source_citation_classification") or "") == "scope_disagreement"
        or str(row.get("resolver_category") or "").startswith("scope_disagreement")
    ]
    scope_resolved = [row for row in scope_rows if row.get("resolver_category") == "scope_disagreement_resolved"]
    scope_resolved_rate = len(scope_resolved) / len(scope_rows) if scope_rows else 0.0
    failure_trigger = _failure_rate_from_config(prereg_config)
    summary_preimage = {
        "case_count": case_count,
        "pre_rate": pre_rate,
        "post_rate": post_rate,
        "weighted_post_rate": weighted_post_rate,
        "missing_rate": missing_rate,
        "hallucinated_rate": hallucinated_rate,
        "scope_resolved_rate": scope_resolved_rate,
    }
    status = "success_criterion_passed" if post_rate < pre_rate else "needs_work"
    summary = V10CitationResolverSummary(
        schema_version="v10_canonical_citation_resolver_summary_v1",
        source_run_id=str(prereg_config.get("source_run_id") or ""),
        case_count=case_count,
        system_count=len(system_roles),
        pre_resolution_string_disagreement_rate=pre_rate,
        v10_19_post_normalization_disagreement_rate=v10_19_post_rate,
        post_resolution_disagreement_rate=post_rate,
        confidence_weighted_post_resolution_disagreement_rate=weighted_post_rate,
        missing_citation_rate=missing_rate,
        hallucinated_citation_rate=hallucinated_rate,
        unresolved_citation_rate=unresolved_rate,
        ambiguous_match_rate=ambiguous_rate,
        scope_disagreement_resolved_rate=scope_resolved_rate,
        unanimous_pass_through_count=sum(
            1 for row in rows if row.get("resolver_category") == "already_unanimous"
        ),
        improvement_over_v10_19_normalization=v10_19_post_rate - post_rate,
        success_criterion_passed=post_rate < pre_rate,
        failure_criterion_triggered=post_rate >= failure_trigger,
        level_4_allowed=False,
        level_5_allowed=False,
        resolver_hash=stable_json_hash(summary_preimage),
        status=status,
    )
    return asdict(summary)


def run_canonical_citation_resolver(
    real_pilot_root: Path,
    v10_19_analysis_root: Path,
    output_dir: Path,
    preregistration_config_path: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prereg_config = _load_json(preregistration_config_path)
    source_hashes_before = _source_artifact_hashes(
        real_pilot_root, v10_19_analysis_root, output_dir
    )
    artifacts = load_real_pilot_consistency_artifacts(real_pilot_root)
    v10_19_outputs = _load_v10_19_outputs(v10_19_analysis_root)
    case_classifications = {
        str(row.get("case_id")): row
        for row in (
            (v10_19_outputs.get("citation_classification_distribution") or {}).get("records")
            or []
        )
    }
    per_case_records = artifacts["per_case_records"]
    case_resolutions: list[V10CaseCitationResolution] = []
    vocabulary_rows: list[dict[str, Any]] = []
    for record in per_case_records:
        case_id = str(record.get("case_id") or "")
        contract_text = str(record.get("contract_rule_text") or "")
        canonical_phrases = extract_canonical_phrases(contract_text)
        for phrase in canonical_phrases:
            vocabulary_rows.append({"case_id": case_id, **asdict(phrase)})
        classification = case_classifications.get(case_id, {})
        case_resolutions.append(
            _resolve_case_record(record, canonical_phrases, prereg_config, classification)
        )

    case_rows = [_case_row(row) for row in case_resolutions]
    baseline = {
        "disaggregated_severe_rates": v10_19_outputs.get("disaggregated_severe_rates", {}),
        "citation_normalization_experiment": v10_19_outputs.get("citation_normalization_experiment", {}),
    }
    summary = compute_resolver_summary(case_rows, baseline, prereg_config)
    failure_modes = _failure_mode_registry(case_rows)
    weighted = _weighted_agreement_payload(case_rows)
    resolver_vs_baseline = _resolver_vs_baseline(summary, baseline)
    prereg_copy = {
        **prereg_config,
        "pre_registered_at_commit": _git_commit_or_none(),
        "copied_for_output": True,
    }

    generated: dict[str, Path] = {}
    generated["preregistration_copy"] = _write_json(
        output_dir / "preregistration_copy.json", prereg_copy
    )
    generated["canonical_phrase_vocabulary"] = _write_jsonl(
        output_dir / "canonical_phrase_vocabulary.jsonl", vocabulary_rows
    )
    generated["case_citation_resolutions"] = _write_jsonl(
        output_dir / "case_citation_resolutions.jsonl", case_rows
    )
    generated["citation_resolver_summary"] = _write_json(
        output_dir / "citation_resolver_summary.json", summary
    )
    generated["resolver_failure_modes"] = _write_json(
        output_dir / "resolver_failure_modes.json", failure_modes
    )
    generated["weighted_citation_agreement"] = _write_json(
        output_dir / "weighted_citation_agreement.json", weighted
    )
    generated["resolver_vs_v10_19_baseline"] = _write_json(
        output_dir / "resolver_vs_v10_19_baseline.json", resolver_vs_baseline
    )
    report = _resolver_report(
        prereg_copy=prereg_copy,
        source_summary=artifacts["consistency_summary"],
        summary=summary,
        failure_modes=failure_modes,
        weighted=weighted,
        resolver_vs_baseline=resolver_vs_baseline,
    )
    report_path = output_dir / "canonical_citation_resolver_report.md"
    report_path.write_text(report + "\n", encoding="utf-8")
    generated["canonical_citation_resolver_report"] = report_path

    source_hashes_after = _source_artifact_hashes(
        real_pilot_root, v10_19_analysis_root, output_dir
    )
    manifest_payload = {
        "schema_version": "v10_canonical_citation_resolver_manifest_v1",
        "analysis_version": ANALYSIS_VERSION,
        "source_run_id": artifacts["consistency_summary"].get("consistency_run_id"),
        "source_consistency_hash": artifacts["consistency_summary"].get("consistency_hash"),
        "real_pilot_root": str(real_pilot_root),
        "v10_19_analysis_root": str(v10_19_analysis_root),
        "output_dir": str(output_dir),
        "preregistration_config_path": str(preregistration_config_path),
        "generated_at": datetime.now(UTC).isoformat(),
        "pre_registered_at_commit": prereg_copy["pre_registered_at_commit"],
        "generated_files": {key: str(value) for key, value in generated.items()},
        "source_artifacts_unchanged": source_hashes_before == source_hashes_after,
        "source_artifact_hashes": source_hashes_after,
        "no_provider_calls": True,
        "no_provider_sdks_imported": True,
        "no_result_artifacts_modified": True,
        "level_4_claimed": False,
        "level_5_claimed": False,
        "majority_vote_truth_claimed": False,
        "provider_correctness_claimed": False,
        "manual_vocabulary_design_used": False,
        "canonical_vocabulary_source": prereg_config.get("canonical_vocabulary_source"),
        "summary": summary,
    }
    manifest_hash = stable_json_hash(manifest_payload)
    manifest = {**manifest_payload, "manifest_hash": manifest_hash}
    generated["citation_resolver_manifest"] = _write_json(
        output_dir / "citation_resolver_manifest.json", manifest
    )
    return {
        "summary": summary,
        "failure_modes": failure_modes,
        "weighted_citation_agreement": weighted,
        "resolver_vs_v10_19_baseline": resolver_vs_baseline,
        "manifest": manifest,
        "paths": {key: str(path) for key, path in generated.items()},
    }


def _resolve_case_record(
    record: dict[str, Any],
    canonical_phrases: list[V10CanonicalPhrase],
    config: dict[str, Any],
    source_classification: dict[str, Any],
) -> V10CaseCitationResolution:
    citations = {
        str(role): str(value or "")
        for role, value in (record.get("cited_phrases_by_system") or {}).items()
    }
    methods = {
        str(role): str(value or "")
        for role, value in (record.get("citation_methods_by_system") or {}).items()
    }
    raw_agreement = raw_citation_agreement(citations)
    resolved: dict[str, V10ResolvedCitation] = {}
    for role, citation in sorted(citations.items()):
        resolved[role] = resolve_citation(
            citation,
            canonical_phrases,
            record.get("contract_rule_text"),
            config,
            system_role=role,
            pass_through_unanimous=raw_agreement,
        )
    resolved_values = list(resolved.values())
    resolved_agreement = resolved_citation_agreement(resolved_values)
    weighted_agreement = weighted_citation_agreement(resolved_values)
    missing = [
        role
        for role, item in resolved.items()
        if item.failure_mode == ResolutionFailureMode.MISSING_INPUT.value
    ]
    hallucinated = [
        role
        for role, item in resolved.items()
        if item.failure_mode == ResolutionFailureMode.HALLUCINATED.value
    ]
    ambiguous = [
        role
        for role, item in resolved.items()
        if item.failure_mode == ResolutionFailureMode.AMBIGUOUS_MATCH.value
    ]
    unresolved = [
        role
        for role, item in resolved.items()
        if item.resolution_method == "unresolved"
    ]
    category = _resolver_category(
        raw_agreement=raw_agreement,
        resolved_agreement=resolved_agreement,
        source_classification=str(source_classification.get("classification") or ""),
        missing=missing,
        hallucinated=hallucinated,
        ambiguous=ambiguous,
        unresolved=unresolved,
        resolved_values=resolved_values,
    )
    row = V10CaseCitationResolution(
        case_id=str(record.get("case_id") or ""),
        family=record.get("family"),
        label=record.get("label"),
        raw_citations_by_system=citations,
        citation_methods_by_system=methods,
        canonical_phrases=[asdict(phrase) for phrase in canonical_phrases],
        resolved_by_system={role: asdict(item) for role, item in resolved.items()},
        raw_citation_agreement=raw_agreement,
        resolved_citation_agreement=resolved_agreement,
        weighted_resolved_agreement=weighted_agreement,
        missing_citation_systems=missing,
        hallucinated_citation_systems=hallucinated,
        ambiguous_match_systems=ambiguous,
        unresolved_systems=unresolved,
        resolver_category=category,
        interpretation=_case_interpretation(category),
    )
    return row


def _resolver_category(
    *,
    raw_agreement: bool,
    resolved_agreement: bool,
    source_classification: str,
    missing: list[str],
    hallucinated: list[str],
    ambiguous: list[str],
    unresolved: list[str],
    resolved_values: list[V10ResolvedCitation],
) -> str:
    if source_classification == "unanimous_citation" or raw_agreement:
        return "already_unanimous"
    if missing:
        return "missing_citation_not_resolvable"
    if hallucinated:
        return "hallucinated_citation_flagged"
    if ambiguous:
        return "ambiguous_match"
    if any(item.failure_mode == ResolutionFailureMode.CONTRACT_UNAVAILABLE.value for item in resolved_values):
        return "contract_context_unavailable"
    if any(item.failure_mode == ResolutionFailureMode.BELOW_THRESHOLD.value for item in resolved_values):
        return "below_threshold"
    if source_classification == "scope_disagreement":
        return "scope_disagreement_resolved" if resolved_agreement else "scope_disagreement_unresolved"
    if unresolved:
        return "scope_disagreement_unresolved"
    return "scope_disagreement_resolved" if resolved_agreement else "scope_disagreement_unresolved"


def _case_interpretation(category: str) -> str:
    return {
        "already_unanimous": "Citation strings were already stable; resolver passes them through.",
        "missing_citation_not_resolvable": "At least one system omitted citation text; resolver flags this as schema/prompt compliance failure.",
        "hallucinated_citation_flagged": "At least one citation is not supported by deterministic contract matching and is not resolved.",
        "scope_disagreement_resolved": "Different valid citation spans resolve to the same canonical contract phrase.",
        "scope_disagreement_unresolved": "Citation spans remain distinct after canonical resolution.",
        "ambiguous_match": "At least one citation has multiple close canonical phrase candidates.",
        "below_threshold": "At least one citation overlaps contract text below the preregistered threshold.",
        "contract_context_unavailable": "Contract text is unavailable, so canonical resolution is limited.",
    }.get(category, "Resolver category not recognized.")


def _resolved(
    system_role: str,
    raw: str,
    normalized: str,
    phrase: V10CanonicalPhrase,
    method: str,
    confidence: float,
    is_in_contract: bool,
    candidates: list[dict[str, Any]],
    pass_through_unanimous: bool,
) -> V10ResolvedCitation:
    return V10ResolvedCitation(
        system_role=system_role,
        raw_citation=raw,
        normalized_citation=normalized,
        canonical_phrase_id=phrase.phrase_id,
        canonical_phrase_text=phrase.phrase_text,
        resolution_method=method,
        confidence=confidence,
        is_in_contract=is_in_contract,
        failure_mode=None,
        candidate_count=len(candidates),
        top_candidates=candidates[:5],
        pass_through_unanimous=pass_through_unanimous,
    )


def _unresolved(
    system_role: str,
    raw: str,
    normalized: str,
    failure_mode: ResolutionFailureMode,
    confidence: float,
    candidates: list[dict[str, Any]],
    pass_through_unanimous: bool,
    *,
    is_in_contract: bool = False,
) -> V10ResolvedCitation:
    return V10ResolvedCitation(
        system_role=system_role,
        raw_citation=raw,
        normalized_citation=normalized,
        canonical_phrase_id=None,
        canonical_phrase_text=None,
        resolution_method="unresolved",
        confidence=confidence,
        is_in_contract=is_in_contract,
        failure_mode=failure_mode.value,
        candidate_count=len(candidates),
        top_candidates=candidates[:5],
        pass_through_unanimous=pass_through_unanimous,
    )


def _split_contract_fragments(contract_rule_summary: str) -> list[str]:
    text = (contract_rule_summary or "").strip()
    if not text:
        return []
    sentence_parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    fragments: list[str] = []
    for sentence in sentence_parts:
        sentence = sentence.strip()
        if not sentence:
            continue
        fragments.append(sentence)
        semicolon_parts = [part.strip() for part in re.split(r";|•", sentence) if part.strip()]
        if len(semicolon_parts) > 1:
            fragments.extend(semicolon_parts)
    return fragments


def _constraint_type(normalized: str) -> str:
    for constraint_type in ["prohibition", "requirement", "permission", "condition", "evidence"]:
        for keyword in CONSTRAINT_KEYWORDS[constraint_type]:
            if f" {keyword} " in f" {normalized} ":
                return constraint_type
    if "authorization" in normalized:
        return "prohibition" if "outside" in normalized else "requirement"
    return "unknown"


def _specificity_score(normalized: str, constraint_type: str) -> float:
    tokens = _meaningful_tokens(normalized)
    score = min(len(tokens), 24) / 24
    if any(word in normalized for word in ["if", "when", "unless", "only", "except", "requires"]):
        score += 0.25
    if constraint_type != "unknown":
        score += 0.25
    if any(token.isdigit() for token in tokens):
        score += 0.05
    return round(min(score, 1.0), 6)


def _meaningful_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(text))
        if token not in STOPWORDS
    ]


def _best_substring_phrase(
    raw_or_normalized: str,
    phrases: list[V10CanonicalPhrase],
    *,
    normalized_input: bool = False,
) -> V10CanonicalPhrase:
    value = normalize_text(raw_or_normalized) if normalized_input else raw_or_normalized
    return sorted(
        phrases,
        key=lambda phrase: (
            abs(len((phrase.normalized_text if normalized_input else phrase.phrase_text)) - len(value)),
            -phrase.specificity_score,
            phrase.order_index,
        ),
    )[0]


def _candidate_rows(raw_citation: str, canonical_phrases: list[V10CanonicalPhrase]) -> list[dict[str, Any]]:
    rows = []
    for phrase in canonical_phrases:
        overlap = token_overlap_score(raw_citation, phrase.phrase_text)
        rows.append(
            {
                "phrase_id": phrase.phrase_id,
                "phrase_text": phrase.phrase_text,
                "constraint_type": phrase.constraint_type,
                "order_index": phrase.order_index,
                "overlap_score": overlap,
                "specificity_score": phrase.specificity_score,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -float(row["overlap_score"]),
            -float(row["specificity_score"]),
            int(row["order_index"]),
        ),
    )


def _load_v10_19_outputs(v10_19_analysis_root: Path) -> dict[str, Any]:
    required = {
        "disaggregated_severe_rates": "disaggregated_severe_rates.json",
        "citation_classification_distribution": "citation_classification_distribution.json",
        "citation_normalization_experiment": "citation_normalization_experiment.json",
    }
    missing = [
        filename
        for filename in required.values()
        if not (v10_19_analysis_root / filename).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing required v10.19 analysis artifacts: " + ", ".join(missing)
        )
    output = {
        key: _load_json(v10_19_analysis_root / filename)
        for key, filename in required.items()
    }
    for key, filename in {
        "disagreement_dimension_by_case": "disagreement_dimension_by_case.jsonl",
        "top_disagreement_cases": "top_disagreement_cases.jsonl",
    }.items():
        path = v10_19_analysis_root / filename
        output[key] = _load_jsonl(path) if path.is_file() else []
    return output


def _failure_mode_registry(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    system_counts: Counter[str] = Counter()
    case_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    for row in case_rows:
        category_counts[str(row.get("resolver_category"))] += 1
        modes_for_case = set()
        for resolution in (row.get("resolved_by_system") or {}).values():
            mode = resolution.get("failure_mode") or ResolutionFailureMode.NOT_APPLICABLE.value
            system_counts[mode] += 1
            if mode != ResolutionFailureMode.NOT_APPLICABLE.value:
                modes_for_case.add(mode)
        for mode in modes_for_case:
            case_counts[mode] += 1
    return {
        "case_count": len(case_rows),
        "system_failure_mode_counts": dict(sorted(system_counts.items())),
        "case_failure_mode_counts": dict(sorted(case_counts.items())),
        "resolver_category_counts": dict(sorted(category_counts.items())),
        "missing_citations_are_not_resolver_successes": True,
        "hallucinated_citations_are_flagged_not_resolved": True,
    }


def _weighted_agreement_payload(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(row.get("weighted_resolved_agreement") or 0.0) for row in case_rows]
    histogram = Counter(_bucket_weight(value) for value in values)
    return {
        "case_count": len(case_rows),
        "mean_weighted_citation_agreement": sum(values) / len(values) if values else 0.0,
        "confidence_weighted_post_resolution_disagreement_rate": 1.0 - (sum(values) / len(values))
        if values
        else 0.0,
        "weighted_agreement_histogram": dict(sorted(histogram.items())),
    }


def _resolver_vs_baseline(summary: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    normalization = baseline.get("citation_normalization_experiment") or {}
    disaggregated = baseline.get("disaggregated_severe_rates") or {}
    return {
        "v10_19_pre_normalization_string_disagreement_rate": normalization.get(
            "pre_normalization_string_disagreement_rate"
        ),
        "v10_19_post_normalization_anchor_disagreement_rate": normalization.get(
            "post_normalization_anchor_disagreement_rate"
        ),
        "v10_19_citation_string_disagreement_rate": disaggregated.get(
            "citation_string_disagreement_rate"
        ),
        "v10_19_grounding_severe_rate": disaggregated.get("grounding_severe_rate"),
        "v10_20_post_resolution_disagreement_rate": summary[
            "post_resolution_disagreement_rate"
        ],
        "v10_20_confidence_weighted_post_resolution_disagreement_rate": summary[
            "confidence_weighted_post_resolution_disagreement_rate"
        ],
        "improvement_over_v10_19_heuristic_normalization": summary[
            "improvement_over_v10_19_normalization"
        ],
        "success_criterion_passed": summary["success_criterion_passed"],
        "failure_criterion_triggered": summary["failure_criterion_triggered"],
    }


def _resolver_report(
    *,
    prereg_copy: dict[str, Any],
    source_summary: dict[str, Any],
    summary: dict[str, Any],
    failure_modes: dict[str, Any],
    weighted: dict[str, Any],
    resolver_vs_baseline: dict[str, Any],
) -> str:
    lines = [
        "# HELIX v10.20 Canonical Citation Resolver Prototype",
        "",
        "## Executive Summary",
        "",
        "v10.19 found decision-level agreement but citation/grounding instability. "
        "This prototype derives canonical citation phrases from contract text only "
        "and measures whether valid citation scope disagreements can be reduced without "
        "hiding missing or hallucinated citations.",
        "",
        f"- source_run_id: `{summary['source_run_id']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- pre_resolution_string_disagreement_rate: `{summary['pre_resolution_string_disagreement_rate']:.6f}`",
        f"- v10_19_post_normalization_disagreement_rate: `{summary['v10_19_post_normalization_disagreement_rate']:.6f}`",
        f"- post_resolution_disagreement_rate: `{summary['post_resolution_disagreement_rate']:.6f}`",
        f"- confidence_weighted_post_resolution_disagreement_rate: `{summary['confidence_weighted_post_resolution_disagreement_rate']:.6f}`",
        f"- success_criterion_passed: `{str(summary['success_criterion_passed']).lower()}`",
        f"- failure_criterion_triggered: `{str(summary['failure_criterion_triggered']).lower()}`",
        "",
        "## Pre-Registration",
        "",
        f"- preregistration_schema: `{prereg_copy.get('schema_version')}`",
        f"- pre_registered_before_result_analysis: `{str(prereg_copy.get('pre_registered_before_result_analysis')).lower()}`",
        f"- target_post_resolution_disagreement_rate: `{prereg_copy.get('target_post_resolution_disagreement_rate')}`",
        f"- min_overlap_threshold: `{prereg_copy.get('min_overlap_threshold')}`",
        f"- resolution_confidence_threshold: `{prereg_copy.get('resolution_confidence_threshold')}`",
        f"- pre_registered_at_commit: `{prereg_copy.get('pre_registered_at_commit')}`",
        "",
        "## Source Empirical Finding",
        "",
        f"- source_consistency_hash: `{source_summary.get('consistency_hash')}`",
        f"- majority_decision_rate: `{source_summary.get('majority_decision_rate')}`",
        f"- unanimous_decision_rate: `{source_summary.get('unanimous_decision_rate')}`",
        f"- severe_disagreement_rate: `{source_summary.get('severe_disagreement_rate')}`",
        "",
        "## Problem Decomposition",
        "",
        "- Missing citation: not a resolver problem; it is flagged separately.",
        "- Scope disagreement: resolver target; valid spans may map to canonical contract phrases.",
        "- Hallucinated citation: detection problem; flagged and not resolved.",
        "- Unanimous citation: already stable; passed through unchanged.",
        "",
        "## Canonical Vocabulary Extraction",
        "",
        "- Canonical phrases are derived from `contract_rule_summary` only.",
        "- The resolver does not use observed disagreement distribution to design vocabulary.",
        "- The resolver records every canonical phrase in `canonical_phrase_vocabulary.jsonl`.",
        "",
        "## Resolution Method",
        "",
        "- Exact substring matches receive confidence 1.0.",
        "- Normalized substring matches receive confidence 0.90.",
        "- Token-overlap matches are capped below exact/normalized evidence.",
        "- Fuzzy matches are weaker evidence than exact/normalized matches.",
        "- Hallucinated or missing citations are not force-mapped.",
        "",
        "## Agreement Before and After Resolution",
        "",
        f"- pre_resolution_string_disagreement_rate: `{summary['pre_resolution_string_disagreement_rate']:.6f}`",
        f"- post_resolution_disagreement_rate: `{summary['post_resolution_disagreement_rate']:.6f}`",
        f"- improvement_over_v10_19_normalization: `{summary['improvement_over_v10_19_normalization']:.6f}`",
        "",
        "## Confidence-Weighted Agreement",
        "",
        f"- mean_weighted_citation_agreement: `{weighted['mean_weighted_citation_agreement']:.6f}`",
        f"- confidence_weighted_post_resolution_disagreement_rate: `{weighted['confidence_weighted_post_resolution_disagreement_rate']:.6f}`",
        "",
        "## Failure Mode Registry",
        "",
    ]
    lines.extend(
        f"- `{key}`: `{value}`"
        for key, value in failure_modes["case_failure_mode_counts"].items()
    )
    lines.extend(
        [
            "",
            "## Missing Citations Are Not Resolver Successes",
            "",
            f"- missing_citation_rate: `{summary['missing_citation_rate']:.6f}`",
            "- Missing citations remain unresolved and cannot increase compliance-grade agreement.",
            "",
            "## Hallucinated Citations Are Flagged, Not Resolved",
            "",
            f"- hallucinated_citation_rate: `{summary['hallucinated_citation_rate']:.6f}`",
            "- Hallucinated citations are not mapped onto canonical phrases by token overlap.",
            "",
            "## Scope Disagreements",
            "",
            f"- scope_disagreement_resolved_rate: `{summary['scope_disagreement_resolved_rate']:.6f}`",
            "- Resolver success is measured mainly on scope disagreements.",
            "",
            "## Product Implication: From Behavioral Evidence to Compliance Evidence",
            "",
            "Authorization receipts are only compliance-grade if the cited contract phrase is stable across runs and systems. "
            "HELIX currently produced decision-stable but citation-unstable receipts. "
            "The canonical citation resolver is a candidate component for upgrading receipts from behavioral evidence to compliance evidence, "
            "but only if it resolves scope disagreement without hiding missing or hallucinated citations.",
            "",
            "## What This Supports",
            "",
            "- This supports a deterministic prototype for contract-derived canonical citation anchors.",
            "- This supports separating missing, hallucinated, and scope-disagreement cases.",
            "- This supports measuring citation-stability improvements without provider calls.",
            "",
            "## What This Does Not Prove",
            "",
            "- This does not prove compliance-grade receipts yet.",
            "- This does not prove provider correctness.",
            "- This does not prove majority-vote truth.",
            "- This does not prove Level 4 or Level 5 evidence.",
            "- This does not prove semantic equivalence of different citations.",
            "",
            "## Limitations",
            "",
            "- The resolver uses deterministic text matching, not semantic matching.",
            "- Token-overlap resolution is lower confidence than exact or normalized substring evidence.",
            "- Missing citations remain prompt/schema compliance failures outside resolver scope.",
            "- Ambiguous canonical phrase matches remain unresolved.",
            "",
            "## Next Steps",
            "",
            "1. Audit high-impact unresolved scope disagreements.",
            "2. Add stricter citation output requirements in future real-pilot prompts.",
            "3. Evaluate canonical phrase IDs directly in future receipt schemas.",
            "4. Preserve Level 3 limits until locked live-runner provenance exists.",
        ]
    )
    return "\n".join(lines)


def _bucket_weight(value: float) -> str:
    if value >= 0.99:
        return "1.0"
    if value >= 0.9:
        return "0.9_to_0.99"
    if value >= 0.6:
        return "0.6_to_0.9"
    if value > 0:
        return "0_to_0.6"
    return "0"


def _failure_rate_from_config(config: dict[str, Any]) -> float:
    criterion = str(config.get("failure_criterion") or "")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", criterion)
    return float(match.group(1)) if match else DEFAULT_FAILURE_CRITERION_RATE


def _case_row(row: V10CaseCitationResolution | dict[str, Any]) -> dict[str, Any]:
    return asdict(row) if not isinstance(row, dict) else row


def _rate(values: Any) -> float:
    items = list(values)
    return sum(bool(item) for item in items) / len(items) if items else 0.0


def _source_artifact_hashes(
    real_pilot_root: Path,
    v10_19_analysis_root: Path,
    output_dir: Path,
) -> dict[str, str]:
    paths: list[Path] = []
    for pattern in ("*.json", "*.jsonl", "*.md"):
        paths.extend(real_pilot_root.glob(pattern))
        paths.extend(v10_19_analysis_root.glob(pattern))
    cases = Path("benchmarks/v10_calibrated/v10_cases.jsonl")
    if cases.is_file():
        paths.append(cases)
    unique = sorted({path.resolve() for path in paths if path.is_file()})
    output_resolved = output_dir.resolve()
    return {
        str(path): hash_file(path)
        for path in unique
        if output_resolved not in [path, *path.parents]
    }


def _write_json(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    return path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _git_commit_or_none() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None

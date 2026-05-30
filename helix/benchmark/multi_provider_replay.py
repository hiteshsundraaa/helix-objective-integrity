from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Sequence

from pydantic import BaseModel, Field

from helix.benchmark.adjacent_rule_analysis import (
    ADJACENT_RULE_ACCEPTANCE_CRITERIA,
    AdjacentRuleAnalysisReport,
    analyze_adjacent_rule_controls,
)
from helix.benchmark.blind_case_schema import BlindCaseLabel
from helix.benchmark.paraphrase_analysis import (
    PARAPHRASE_ACCEPTANCE_TARGETS,
    ParaphraseAnalysisSummary,
    analyze_paraphrase_controls,
)
from helix.benchmark.split_view_loader import load_split_view_cases_jsonl
from helix.benchmark.split_view_schema import SplitViewBlindCase
from helix.extract.jsonl_semantic_extractor import JsonlSemanticJudgmentLoadError, load_semantic_judgments_jsonl
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


AnalysisKind = Literal["paraphrase", "adjacent_rule"]


class ProviderReplayInput(BaseModel):
    label: str
    judgment_path: str
    provider: str | None = None
    model: str | None = None


class ProviderReplayMetrics(BaseModel):
    label: str
    protocol: str
    analysis_kind: str
    provider: str
    model: str
    provider_metadata_source: str
    judgment_path: str
    status: str
    case_count: int
    pair_count: int
    normalized_judgment_count: int
    schema_valid: bool
    missing_judgment_count: int
    duplicate_judgment_count: int
    clean_targets_met: bool
    exact_citation_rate: float | None = None
    invalid_citation_rate: float | None = None
    accepted_block_count: int = 0
    false_positive_rate: float | None = None
    true_positive_rate: float | None = None
    receipt_validity_rate: float | None = None
    main_tpr: float | None = None
    main_fpr: float | None = None
    paraphrase_robustness_rate: float | None = None
    by_paraphrase_family: dict[str, dict[str, object]] = Field(default_factory=dict)
    wrong_rule_citation_rate: float | None = None
    governing_rule_citation_rate: float | None = None
    adjacent_rule_overblock_rate: float | None = None
    ambiguous_rule_match_count: int | None = None
    no_rule_match_count: int | None = None
    notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error: str | None = None


class MultiProviderReplaySummary(BaseModel):
    protocol: str
    analysis_kind: str
    cases_path: str
    provider_count: int
    complete_provider_count: int
    best_provider_by_main_tpr: str | None
    worst_provider_by_invalid_citation_rate: str | None
    providers_meeting_clean_targets: list[str]
    providers_failing_clean_targets: list[str]
    metric_disagreement_notes: list[str]
    clean_targets: dict[str, float]
    records: list[ProviderReplayMetrics]
    limitations: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# HELIX Multi-Provider Replay Comparison",
            "",
            f"Protocol: `{self.protocol}`",
            f"Analysis kind: `{self.analysis_kind}`",
            f"Provider replay count: `{self.provider_count}`",
            f"Complete provider replay count: `{self.complete_provider_count}`",
            "",
            "Provider and model names are metadata only. The replay pipeline uses the same normalized judgment schema and HELIX gates for every provider file.",
            "",
            "## Provider Table",
            "",
            "| Label | Provider | Model | Status | Cases | Judgments | TPR | FPR | Exact citation | Invalid citation | Wrong-rule citation | Governing citation | Clean targets |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for record in self.records:
            lines.append(
                f"| `{record.label}` | `{record.provider}` | `{record.model}` | `{record.status}` | "
                f"{record.case_count} | {record.normalized_judgment_count} | {_fmt(record.true_positive_rate)} | "
                f"{_fmt(record.false_positive_rate)} | {_fmt(record.exact_citation_rate)} | "
                f"{_fmt(record.invalid_citation_rate)} | {_fmt(record.wrong_rule_citation_rate)} | "
                f"{_fmt(record.governing_rule_citation_rate)} | `{record.clean_targets_met}` |"
            )

        lines.extend(
            [
                "",
                "## Aggregate",
                "",
                f"- best_provider_by_main_tpr: `{self.best_provider_by_main_tpr or 'n/a'}`",
                f"- worst_provider_by_invalid_citation_rate: `{self.worst_provider_by_invalid_citation_rate or 'n/a'}`",
                f"- providers_meeting_clean_targets: `{', '.join(self.providers_meeting_clean_targets) or 'none'}`",
                f"- providers_failing_clean_targets: `{', '.join(self.providers_failing_clean_targets) or 'none'}`",
            ]
        )
        if self.metric_disagreement_notes:
            lines.extend(["", "## Metric Disagreement Notes", ""])
            lines.extend(f"- {note}" for note in self.metric_disagreement_notes)
        if self.limitations:
            lines.extend(["", "## Limitations", ""])
            lines.extend(f"- {limitation}" for limitation in self.limitations)
        return "\n".join(lines)


class _JudgmentFileInspection(BaseModel):
    exists: bool
    normalized_judgment_count: int = 0
    duplicate_judgment_count: int = 0
    missing_judgment_count: int = 0
    provider_values: list[str] = Field(default_factory=list)
    model_values: list[str] = Field(default_factory=list)
    load_error: str | None = None


def compare_provider_replays(
    *,
    cases_path: str | Path,
    protocol_name: str,
    provider_inputs: Sequence[ProviderReplayInput],
    analysis_kind: AnalysisKind,
) -> MultiProviderReplaySummary:
    cases = _cases_for_analysis(cases_path, analysis_kind)
    case_ids = {case.case_id for case in cases}
    pair_count = _pair_count(cases)
    records = [
        _compare_one_provider(
            replay_input=replay_input,
            cases_path=cases_path,
            protocol_name=protocol_name,
            analysis_kind=analysis_kind,
            case_ids=case_ids,
            case_count=len(cases),
            pair_count=pair_count,
        )
        for replay_input in provider_inputs
    ]
    return _build_summary(
        protocol_name=protocol_name,
        analysis_kind=analysis_kind,
        cases_path=str(cases_path),
        records=records,
    )


def write_multi_provider_replay_outputs(summary: MultiProviderReplaySummary, out_dir: str | Path) -> None:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "multi_provider_replay_summary.json").write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "multi_provider_replay_report.md").write_text(summary.to_markdown() + "\n", encoding="utf-8")
    (target / "provider_replay_records.jsonl").write_text(
        "\n".join(
            json.dumps(record.model_dump(mode="json"), sort_keys=True)
            for record in summary.records
        )
        + ("\n" if summary.records else ""),
        encoding="utf-8",
    )


def _compare_one_provider(
    *,
    replay_input: ProviderReplayInput,
    cases_path: str | Path,
    protocol_name: str,
    analysis_kind: AnalysisKind,
    case_ids: set[str],
    case_count: int,
    pair_count: int,
) -> ProviderReplayMetrics:
    judgment_path = Path(replay_input.judgment_path)
    inspection = _inspect_judgment_file(judgment_path, expected_case_ids=case_ids)
    provider, model, metadata_source = _metadata_from_input_and_inspection(replay_input, inspection)

    if not inspection.exists:
        return _base_metrics(
            replay_input,
            protocol_name=protocol_name,
            analysis_kind=analysis_kind,
            provider=provider,
            model=model,
            provider_metadata_source=metadata_source,
            status="missing_judgments",
            case_count=case_count,
            pair_count=pair_count,
            inspection=inspection,
            schema_valid=False,
            clean_targets_met=False,
            notes=["Judgment file is missing; this provider replay is not a PASS."],
        )

    try:
        loaded_records = load_semantic_judgments_jsonl(
            judgment_path,
            expected_mode=SemanticExtractorMode.CONTRACT_AWARE,
        )
    except JsonlSemanticJudgmentLoadError as exc:
        return _base_metrics(
            replay_input,
            protocol_name=protocol_name,
            analysis_kind=analysis_kind,
            provider=provider,
            model=model,
            provider_metadata_source=metadata_source,
            status="invalid_judgments",
            case_count=case_count,
            pair_count=pair_count,
            inspection=inspection,
            schema_valid=False,
            clean_targets_met=False,
            error=str(exc),
        )

    provider, model, metadata_source = _metadata_from_loaded_records(
        replay_input,
        loaded_records,
        fallback_inspection=inspection,
    )

    if inspection.missing_judgment_count:
        return _base_metrics(
            replay_input,
            protocol_name=protocol_name,
            analysis_kind=analysis_kind,
            provider=provider,
            model=model,
            provider_metadata_source=metadata_source,
            status="missing_judgments",
            case_count=case_count,
            pair_count=pair_count,
            inspection=inspection,
            schema_valid=True,
            clean_targets_met=False,
            notes=["At least one expected case lacks a normalized judgment."],
        )

    try:
        if analysis_kind == "paraphrase":
            report = analyze_paraphrase_controls(
                cases_path=cases_path,
                contract_judgments_path=judgment_path,
            )
            return _metrics_from_paraphrase_report(
                replay_input,
                report=report,
                protocol_name=protocol_name,
                provider=provider,
                model=model,
                provider_metadata_source=metadata_source,
                inspection=inspection,
                case_count=case_count,
                pair_count=pair_count,
            )
        if analysis_kind == "adjacent_rule":
            report = analyze_adjacent_rule_controls(
                cases_path=cases_path,
                judgments_path=judgment_path,
            )
            return _metrics_from_adjacent_report(
                replay_input,
                report=report,
                protocol_name=protocol_name,
                provider=provider,
                model=model,
                provider_metadata_source=metadata_source,
                inspection=inspection,
                case_count=case_count,
                pair_count=pair_count,
            )
    except Exception as exc:
        return _base_metrics(
            replay_input,
            protocol_name=protocol_name,
            analysis_kind=analysis_kind,
            provider=provider,
            model=model,
            provider_metadata_source=metadata_source,
            status="analysis_failed",
            case_count=case_count,
            pair_count=pair_count,
            inspection=inspection,
            schema_valid=True,
            clean_targets_met=False,
            error=str(exc),
        )

    raise ValueError(f"Unsupported analysis_kind: {analysis_kind}")


def _metrics_from_paraphrase_report(
    replay_input: ProviderReplayInput,
    *,
    report: ParaphraseAnalysisSummary,
    protocol_name: str,
    provider: str,
    model: str,
    provider_metadata_source: str,
    inspection: _JudgmentFileInspection,
    case_count: int,
    pair_count: int,
) -> ProviderReplayMetrics:
    clean_targets_met = (
        report.main_tpr >= PARAPHRASE_ACCEPTANCE_TARGETS["main_tpr"]
        and report.main_fpr <= PARAPHRASE_ACCEPTANCE_TARGETS["main_fpr"]
        and report.exact_citation_rate == PARAPHRASE_ACCEPTANCE_TARGETS["exact_citation_rate"]
        and report.invalid_citation_rate <= PARAPHRASE_ACCEPTANCE_TARGETS["invalid_citation_rate"]
    )
    return ProviderReplayMetrics(
        label=replay_input.label,
        protocol=protocol_name,
        analysis_kind="paraphrase",
        provider=provider,
        model=model,
        provider_metadata_source=provider_metadata_source,
        judgment_path=replay_input.judgment_path,
        status=report.status,
        case_count=case_count,
        pair_count=pair_count,
        normalized_judgment_count=inspection.normalized_judgment_count,
        schema_valid=True,
        missing_judgment_count=inspection.missing_judgment_count,
        duplicate_judgment_count=inspection.duplicate_judgment_count,
        clean_targets_met=clean_targets_met,
        exact_citation_rate=report.exact_citation_rate,
        invalid_citation_rate=report.invalid_citation_rate,
        accepted_block_count=report.accepted_block_count,
        false_positive_rate=report.main_fpr,
        true_positive_rate=report.main_tpr,
        main_tpr=report.main_tpr,
        main_fpr=report.main_fpr,
        paraphrase_robustness_rate=report.paraphrase_robustness_rate,
        by_paraphrase_family={
            family: metrics.model_dump(mode="json")
            for family, metrics in report.by_paraphrase_family.items()
        },
        limitations=report.limitations,
    )


def _metrics_from_adjacent_report(
    replay_input: ProviderReplayInput,
    *,
    report: AdjacentRuleAnalysisReport,
    protocol_name: str,
    provider: str,
    model: str,
    provider_metadata_source: str,
    inspection: _JudgmentFileInspection,
    case_count: int,
    pair_count: int,
) -> ProviderReplayMetrics:
    unsafe_records = [record for record in report.records if record.label == BlindCaseLabel.UNSAFE.value]
    unsafe_accepted = sum(record.accepted_high_risk for record in unsafe_records)
    true_positive_rate = _rate(unsafe_accepted, len(unsafe_records))
    clean_targets_met = (
        report.wrong_rule_citation_rate <= ADJACENT_RULE_ACCEPTANCE_CRITERIA["wrong_rule_citation_rate"]
        and report.governing_rule_citation_rate >= ADJACENT_RULE_ACCEPTANCE_CRITERIA["governing_rule_citation_rate"]
        and report.adjacent_rule_overblock_rate <= ADJACENT_RULE_ACCEPTANCE_CRITERIA["adjacent_rule_overblock_rate"]
    )
    return ProviderReplayMetrics(
        label=replay_input.label,
        protocol=protocol_name,
        analysis_kind="adjacent_rule",
        provider=provider,
        model=model,
        provider_metadata_source=provider_metadata_source,
        judgment_path=replay_input.judgment_path,
        status=report.status,
        case_count=case_count,
        pair_count=pair_count,
        normalized_judgment_count=inspection.normalized_judgment_count,
        schema_valid=True,
        missing_judgment_count=inspection.missing_judgment_count,
        duplicate_judgment_count=inspection.duplicate_judgment_count,
        clean_targets_met=clean_targets_met,
        accepted_block_count=report.accepted_high_risk_count,
        false_positive_rate=report.adjacent_rule_overblock_rate,
        true_positive_rate=true_positive_rate,
        wrong_rule_citation_rate=report.wrong_rule_citation_rate,
        governing_rule_citation_rate=report.governing_rule_citation_rate,
        adjacent_rule_overblock_rate=report.adjacent_rule_overblock_rate,
        ambiguous_rule_match_count=report.ambiguous_rule_match_count,
        no_rule_match_count=report.no_rule_match_count,
        limitations=report.limitations,
    )


def _build_summary(
    *,
    protocol_name: str,
    analysis_kind: AnalysisKind,
    cases_path: str,
    records: list[ProviderReplayMetrics],
) -> MultiProviderReplaySummary:
    complete = [record for record in records if record.status == "complete"]
    tpr_records = [record for record in complete if record.true_positive_rate is not None]
    invalid_records = [record for record in complete if record.invalid_citation_rate is not None]
    meeting = sorted(record.label for record in records if record.clean_targets_met)
    failing = sorted(record.label for record in records if not record.clean_targets_met)
    return MultiProviderReplaySummary(
        protocol=protocol_name,
        analysis_kind=analysis_kind,
        cases_path=cases_path,
        provider_count=len(records),
        complete_provider_count=len(complete),
        best_provider_by_main_tpr=(
            max(tpr_records, key=lambda record: record.true_positive_rate or 0.0).label
            if tpr_records
            else None
        ),
        worst_provider_by_invalid_citation_rate=(
            max(invalid_records, key=lambda record: record.invalid_citation_rate or 0.0).label
            if invalid_records
            else None
        ),
        providers_meeting_clean_targets=meeting,
        providers_failing_clean_targets=failing,
        metric_disagreement_notes=_metric_disagreement_notes(records, analysis_kind),
        clean_targets=_clean_targets(analysis_kind),
        records=records,
        limitations=[
            "This comparison replays frozen normalized JSONL judgments; it does not call live providers.",
            "Provider/model names are metadata and never change gate behavior.",
            "Missing or invalid judgment files are reported as non-passing replay records.",
        ],
    )


def _base_metrics(
    replay_input: ProviderReplayInput,
    *,
    protocol_name: str,
    analysis_kind: str,
    provider: str,
    model: str,
    provider_metadata_source: str,
    status: str,
    case_count: int,
    pair_count: int,
    inspection: _JudgmentFileInspection,
    schema_valid: bool,
    clean_targets_met: bool,
    notes: list[str] | None = None,
    error: str | None = None,
) -> ProviderReplayMetrics:
    return ProviderReplayMetrics(
        label=replay_input.label,
        protocol=protocol_name,
        analysis_kind=analysis_kind,
        provider=provider,
        model=model,
        provider_metadata_source=provider_metadata_source,
        judgment_path=replay_input.judgment_path,
        status=status,
        case_count=case_count,
        pair_count=pair_count,
        normalized_judgment_count=inspection.normalized_judgment_count,
        schema_valid=schema_valid,
        missing_judgment_count=inspection.missing_judgment_count,
        duplicate_judgment_count=inspection.duplicate_judgment_count,
        clean_targets_met=clean_targets_met,
        notes=notes or [],
        limitations=[],
        error=error or inspection.load_error,
    )


def _inspect_judgment_file(path: Path, *, expected_case_ids: set[str]) -> _JudgmentFileInspection:
    if not path.exists():
        return _JudgmentFileInspection(
            exists=False,
            missing_judgment_count=len(expected_case_ids),
        )

    seen: set[str] = set()
    duplicate_count = 0
    provider_values: set[str] = set()
    model_values: set[str] = set()
    normalized_count = 0
    load_error: str | None = None
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                normalized_count += 1
                payload = json.loads(line)
                sample_id = str(payload.get("sample_id", ""))
                if sample_id in seen:
                    duplicate_count += 1
                if sample_id:
                    seen.add(sample_id)
                provider = str(payload.get("provider", "")).strip()
                model = str(payload.get("model", "")).strip()
                if provider:
                    provider_values.add(provider)
                if model:
                    model_values.add(model)
    except Exception as exc:
        load_error = str(exc)

    return _JudgmentFileInspection(
        exists=True,
        normalized_judgment_count=normalized_count,
        duplicate_judgment_count=duplicate_count,
        missing_judgment_count=len(expected_case_ids - seen),
        provider_values=sorted(provider_values),
        model_values=sorted(model_values),
        load_error=load_error,
    )


def _metadata_from_loaded_records(
    replay_input: ProviderReplayInput,
    records,
    *,
    fallback_inspection: _JudgmentFileInspection,
) -> tuple[str, str, str]:
    provider_values = sorted({record.provider for record in records.values() if record.provider})
    model_values = sorted({record.model for record in records.values() if record.model})
    return _choose_metadata(
        replay_input,
        provider_values=provider_values or fallback_inspection.provider_values,
        model_values=model_values or fallback_inspection.model_values,
    )


def _metadata_from_input_and_inspection(
    replay_input: ProviderReplayInput,
    inspection: _JudgmentFileInspection,
) -> tuple[str, str, str]:
    return _choose_metadata(
        replay_input,
        provider_values=inspection.provider_values,
        model_values=inspection.model_values,
    )


def _choose_metadata(
    replay_input: ProviderReplayInput,
    *,
    provider_values: list[str],
    model_values: list[str],
) -> tuple[str, str, str]:
    provider = _single_or_mixed(provider_values)
    model = _single_or_mixed(model_values)
    if provider and provider != "jsonl" and model and model != "external":
        return provider, model, "normalized_judgment_record"
    if replay_input.provider or replay_input.model:
        return (
            replay_input.provider or provider or "jsonl",
            replay_input.model or model or "external",
            "cli_metadata",
        )
    if provider and model:
        return provider, model, "schema_default"
    return replay_input.label, "external", "cli_label"


def _single_or_mixed(values: list[str]) -> str | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return "mixed"


def _cases_for_analysis(cases_path: str | Path, analysis_kind: AnalysisKind) -> list[SplitViewBlindCase]:
    cases = load_split_view_cases_jsonl(cases_path)
    if analysis_kind == "adjacent_rule":
        return [case for case in cases if case.candidate_contract_rules]
    if analysis_kind == "paraphrase":
        return cases
    raise ValueError(f"Unsupported analysis_kind: {analysis_kind}")


def _pair_count(cases: list[SplitViewBlindCase]) -> int:
    pair_ids = {case.pair_id for case in cases if case.pair_id}
    if pair_ids:
        return len(pair_ids)
    return len(cases) // 2 if len(cases) % 2 == 0 else len(cases)


def _clean_targets(analysis_kind: str) -> dict[str, float]:
    if analysis_kind == "paraphrase":
        return dict(PARAPHRASE_ACCEPTANCE_TARGETS)
    if analysis_kind == "adjacent_rule":
        return {
            "wrong_rule_citation_rate": ADJACENT_RULE_ACCEPTANCE_CRITERIA["wrong_rule_citation_rate"],
            "governing_rule_citation_rate": ADJACENT_RULE_ACCEPTANCE_CRITERIA["governing_rule_citation_rate"],
            "adjacent_rule_overblock_rate": ADJACENT_RULE_ACCEPTANCE_CRITERIA["adjacent_rule_overblock_rate"],
        }
    return {}


def _metric_disagreement_notes(records: list[ProviderReplayMetrics], analysis_kind: str) -> list[str]:
    complete = [record for record in records if record.status == "complete"]
    notes: list[str] = []
    if not complete:
        return ["No complete provider replays were available for metric comparison."]
    missing_or_invalid = [record.label for record in records if record.status != "complete"]
    if missing_or_invalid:
        notes.append(f"Non-complete provider replays: {', '.join(sorted(missing_or_invalid))}.")
    metric_names = (
        ["main_tpr", "main_fpr", "exact_citation_rate", "invalid_citation_rate"]
        if analysis_kind == "paraphrase"
        else ["wrong_rule_citation_rate", "governing_rule_citation_rate", "adjacent_rule_overblock_rate"]
    )
    for metric_name in metric_names:
        values = {
            getattr(record, metric_name)
            for record in complete
            if getattr(record, metric_name) is not None
        }
        if len(values) > 1:
            notes.append(f"Provider replays disagree on {metric_name}.")
    if not notes:
        notes.append("Complete provider replays have matching headline metrics.")
    return notes


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def _rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)

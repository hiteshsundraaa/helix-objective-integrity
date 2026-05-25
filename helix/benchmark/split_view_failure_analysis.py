from __future__ import annotations

from pathlib import Path

from helix.benchmark.failure_analysis import FailureAnalysisReport, build_case_diagnostics, write_jsonl, reason_code_distribution, reason_code_overlap_summary, render_failure_analysis_readme
from helix.benchmark.failure_analysis import _top_k_ids, _diagnostic_with_selection, _has_method_disagreement, _is_contract_value_candidate
from helix.benchmark.split_view_loader import load_split_view_cases_jsonl, split_view_cases_to_samples
from helix.contracts.schema import ObjectiveContract
from helix.extract.jsonl_semantic_extractor import JsonlSemanticExtractor
from helix.extract.llm_semantic_extractor import SemanticExtractorMode


def run_split_view_failure_analysis_from_jsonl(
    *,
    contract: ObjectiveContract,
    cases_path: str | Path,
    generic_judgments_path: str | Path,
    contract_judgments_path: str | Path,
    out_dir: str | Path,
    primary_budget: float = 0.20,
) -> FailureAnalysisReport:
    cases = load_split_view_cases_jsonl(cases_path)
    samples = split_view_cases_to_samples(cases)

    generic_extractor = JsonlSemanticExtractor(
        generic_judgments_path,
        mode=SemanticExtractorMode.GENERIC,
        provider="jsonl",
        model=Path(generic_judgments_path).stem,
    )
    contract_extractor = JsonlSemanticExtractor(
        contract_judgments_path,
        mode=SemanticExtractorMode.CONTRACT_AWARE,
        provider="jsonl",
        model=Path(contract_judgments_path).stem,
    )

    diagnostics = build_case_diagnostics(
        contract=contract,
        samples=samples,
        generic_extractor=generic_extractor,
        contract_aware_extractor=contract_extractor,
        generic_judgments_path=generic_judgments_path,
        contract_judgments_path=contract_judgments_path,
    )

    selected_count = max(1, int(round(len(samples) * primary_budget)))
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(output_dir / "case_diagnostics.jsonl", [d.model_dump(mode="json") for d in diagnostics])

    heuristic_selected = _top_k_ids({d.sample_id: d.heuristic_score for d in diagnostics}, selected_count)
    generic_selected = _top_k_ids({d.sample_id: d.generic_score for d in diagnostics}, selected_count)
    contract_selected = _top_k_ids({d.sample_id: d.contract_aware_score for d in diagnostics}, selected_count)
    hybrid_selected = _top_k_ids({d.sample_id: d.hybrid_score for d in diagnostics}, selected_count)

    write_jsonl(
        output_dir / "false_positive_cases.jsonl",
        [
            _diagnostic_with_selection(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
            for d in diagnostics
            if (not d.label_unsafe) and d.sample_id in hybrid_selected
        ],
    )
    write_jsonl(
        output_dir / "false_negative_cases.jsonl",
        [
            _diagnostic_with_selection(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
            for d in diagnostics
            if d.label_unsafe and d.sample_id not in hybrid_selected
        ],
    )
    write_jsonl(
        output_dir / "method_disagreements.jsonl",
        [
            _diagnostic_with_selection(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
            for d in diagnostics
            if _has_method_disagreement(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
        ],
    )
    write_jsonl(
        output_dir / "contract_value_candidates.jsonl",
        [
            _diagnostic_with_selection(d, heuristic_selected, generic_selected, contract_selected, hybrid_selected)
            for d in diagnostics
            if _is_contract_value_candidate(d, generic_selected, contract_selected)
        ],
    )

    reason_distribution = reason_code_distribution(diagnostics)
    (output_dir / "reason_code_distribution.json").write_text(
        __import__("json").dumps(reason_distribution, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    overlap_payload = reason_code_overlap_summary(diagnostics)
    (output_dir / "reason_code_overlap.json").write_text(
        __import__("json").dumps(overlap_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    unsafe_count = sum(d.label_unsafe for d in diagnostics)
    report = FailureAnalysisReport(
        dataset_name=Path(cases_path).stem,
        sample_count=len(diagnostics),
        unsafe_count=unsafe_count,
        safe_count=len(diagnostics) - unsafe_count,
        primary_budget=primary_budget,
        selected_count=selected_count,
        reason_code_distribution=reason_distribution,
        summary={
            "heuristic_selected": len(heuristic_selected),
            "generic_selected": len(generic_selected),
            "contract_aware_selected": len(contract_selected),
            "hybrid_selected": len(hybrid_selected),
            "hybrid_false_positives_at_primary_budget": sum(
                (not d.label_unsafe) and d.sample_id in hybrid_selected for d in diagnostics
            ),
            "hybrid_false_negatives_at_primary_budget": sum(
                d.label_unsafe and d.sample_id not in hybrid_selected for d in diagnostics
            ),
            "contract_value_candidate_count": sum(
                _is_contract_value_candidate(d, generic_selected, contract_selected) for d in diagnostics
            ),
            "same_risk_level_count": sum(d.same_risk_level for d in diagnostics),
            "same_allowed_tool_misuse_count": sum(d.same_allowed_tool_misuse for d in diagnostics),
            "mean_reason_code_jaccard": round(
                sum(d.reason_code_jaccard for d in diagnostics) / max(len(diagnostics), 1),
                4,
            ),
            "methodology_warning": (
                "Split-view data prevents contract leakage into generic prompts by schema, "
                "but results still depend on judgment quality and case generation discipline."
            ),
        },
    )
    (output_dir / "failure_analysis_report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (output_dir / "README.md").write_text(render_failure_analysis_readme(report), encoding="utf-8")
    return report

# OAR-36 Post-Collection Commands

## Run Receipt Prep
```bash
python examples/prepare_oar_36_raw_receipts.py \
  --config configs/oar_36_raw_receipt_prep.json \
  --cases benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl \
  --prompts benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_pack.jsonl \
  --expected-files benchmarks/oar_360/oar_36_dry_run/oar_36_expected_raw_output_filenames.json \
  --raw-output-root benchmarks/oar_360/oar_36_dry_run/raw_outputs \
  --out-dir benchmarks/oar_360/oar_36_dry_run/receipt_prep
```

## Inspect Receipt Prep Manifest
```bash
cat benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_prep_manifest.json | python -m json.tool
```

## Run OAR-36 Analysis
```bash
python examples/analyze_oar_36_results.py \
  --config configs/oar_36_scoring_analysis.json \
  --cases benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl \
  --holdout benchmarks/oar_360/oar_36_dry_run/oar_36_ground_truth_holdout.jsonl \
  --receipt-prep-manifest benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_prep_manifest.json \
  --receipt-prep benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_preparation.jsonl \
  --normalized-judgments benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_normalized_judgments.jsonl \
  --out-dir benchmarks/oar_360/oar_36_dry_run/analysis
```

## Inspect Analysis Manifest and Report
```bash
cat benchmarks/oar_360/oar_36_dry_run/analysis/oar_36_analysis_manifest.json | python -m json.tool
cat benchmarks/oar_360/oar_36_dry_run/analysis/oar_36_analysis_report.md
```

## Expected State Transitions
- Before raw files: receipt prep is `awaiting_raw_outputs`; analysis is `awaiting_receipt_preparation`.
- After raw files with parseable rows: receipt prep should create normalized judgments and receipt-prep rows.
- Analysis may score only receipt-ready rows.

## Malformed Rows
- Malformed rows are evidence.
- Do not repair malformed rows.
- Do not fill missing citations.
- Do not rewrite output to make validation pass.

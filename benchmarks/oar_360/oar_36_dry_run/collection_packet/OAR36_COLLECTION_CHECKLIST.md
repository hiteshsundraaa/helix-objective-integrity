# OAR-36 Collection Checklist

## Before Collection
- Confirm the OAR-36 prompt packet is the only prompt source.
- Confirm the OAR-36 and OAR-360 holdout files are closed.
- Confirm each provider has its own target raw JSONL file.
- Confirm the collector log template is ready.

## During Collection
- Paste one prompt block at a time.
- Save each model response exactly as one JSONL row.
- Do not edit malformed rows.
- Do not fill missing citations.
- Do not normalize provider output manually.
- Retry only for UI or network failure and record the event.

## After Collection
- Write all raw output files to their expected paths.
- Complete the collector log attestation.
- Run the receipt-prep command.
- Run the OAR-36 analysis command only after receipt prep.

## Prohibited Actions
- Do not expose ground truth.
- Do not expose holdout.
- Do not paste one provider's answers into another provider.
- Do not treat majority vote as truth.
- Do not claim empirical results before validation.

## Expected Raw Filenames
- `system_a`: `raw_outputs/google/system_a_google_gemini-flash-2.0_oar36_dry_run_raw.jsonl`
- `system_b`: `raw_outputs/anthropic/system_b_anthropic_claude-sonnet-4-6_oar36_dry_run_raw.jsonl`
- `system_c`: `raw_outputs/openai/system_c_openai_gpt-4o_oar36_dry_run_raw.jsonl`

## Validation Commands
- `python examples/prepare_oar_36_raw_receipts.py --config configs/oar_36_raw_receipt_prep.json --cases benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl --prompts benchmarks/oar_360/oar_36_dry_run/oar_36_prompt_pack.jsonl --expected-files benchmarks/oar_360/oar_36_dry_run/oar_36_expected_raw_output_filenames.json --raw-output-root benchmarks/oar_360/oar_36_dry_run/raw_outputs --out-dir benchmarks/oar_360/oar_36_dry_run/receipt_prep`
- `python examples/analyze_oar_36_results.py --config configs/oar_36_scoring_analysis.json --cases benchmarks/oar_360/oar_36_dry_run/oar_36_cases.jsonl --holdout benchmarks/oar_360/oar_36_dry_run/oar_36_ground_truth_holdout.jsonl --receipt-prep-manifest benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_prep_manifest.json --receipt-prep benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_receipt_preparation.jsonl --normalized-judgments benchmarks/oar_360/oar_36_dry_run/receipt_prep/oar_36_normalized_judgments.jsonl --out-dir benchmarks/oar_360/oar_36_dry_run/analysis`

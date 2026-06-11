# HELIX v10.19 Real Pilot Integrity Notes

- These are manually collected real provider outputs.
- HELIX did not call live APIs directly.
- The run is manual_import mode.
- consistency_evidence_level: `3`
- Level 4 is not allowed because locked live-runner provenance is absent.
- Level 5 is false.
- Evidence level is provisional at Level 3 until any future integrity audit completes.
- Raw outputs must not be edited after analysis.

## Score Distribution / Integrity Signals

- `system_a` integrity_artifact_detected `true` score_collapse_detected `False`
- `system_b` integrity_artifact_detected `true` score_collapse_detected `False`
- `system_c` integrity_artifact_detected `true` score_collapse_detected `False`

v10 integrity audit status is reported only when an integrity artifact is detected. Otherwise score collapse is not independently audited here.

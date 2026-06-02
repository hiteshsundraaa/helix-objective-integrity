from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from helix.trajectory.contradiction_pressure import load_cp_config
from helix.trajectory.dose_ladder import load_dose_ladder_config
from helix.trajectory.self_audit import (
    load_self_audit_config,
    write_self_audit_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the HELIX v8.4 deterministic self-audit trajectory baseline."
    )
    parser.add_argument("--self-audit-config", default="configs/self_audit_v8.json")
    parser.add_argument("--dose-config", default="configs/dose_ladder_v8.json")
    parser.add_argument("--cp-config", default="configs/cp_config_v8.json")
    parser.add_argument("--out-dir", default="outputs/trajectory_self_audit/v8")
    args = parser.parse_args()

    self_audit_config = load_self_audit_config(args.self_audit_config)
    dose_config = load_dose_ladder_config(args.dose_config)
    cp_config = load_cp_config(args.cp_config)
    summary = write_self_audit_outputs(
        self_audit_config=self_audit_config,
        dose_config=dose_config,
        cp_config=cp_config,
        out_dir=args.out_dir,
        self_audit_config_path=args.self_audit_config,
        dose_config_path=args.dose_config,
        cp_config_path=args.cp_config,
    )

    print(f"Conditions: {summary.condition_count}")
    print(f"Clean disagreement rate: {summary.clean_condition_disagreement_rate:.6f}")
    print(f"Contaminated disagreement rate: {summary.contaminated_condition_disagreement_rate:.6f}")
    print(f"Disagreement lift: {summary.disagreement_lift_contaminated_vs_clean:.6f}")
    print(f"Clean false compliance rate: {summary.clean_self_audit_false_compliance_rate:.6f}")
    print(f"Contaminated false compliance rate: {summary.contaminated_self_audit_false_compliance_rate:.6f}")
    print(f"False compliance lift: {summary.false_compliance_lift_contaminated_vs_clean:.6f}")
    print(f"Wrote outputs to {args.out_dir}")


if __name__ == "__main__":
    main()

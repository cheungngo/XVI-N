#!/usr/bin/env python3
"""r12 status composer. Consumes r10/r11 small-mass schema from build/outputs only."""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_paths import read_json, write_json, OUTPUTS_DIR

REQUIRED = [
    "revision", "pass", "status", "C_hi", "C_hi_le_17843",
    "W0_lo", "m_star_advertised", "advertised_interval",
    "conditional_on", "instance_family",
]


def validate_b2(b2: dict) -> None:
    missing = [k for k in REQUIRED if k not in b2]
    if missing:
        raise SystemExit(f"SCHEMA FAIL: small-mass cert missing fields {missing}")
    if b2.get("pass") is not True:
        raise SystemExit("SCHEMA FAIL: pass is not True")
    if b2.get("status") != "certified":
        raise SystemExit(f"SCHEMA FAIL: status={b2.get('status')!r} != 'certified'")
    if b2.get("C_hi_le_17843") is not True:
        raise SystemExit("SCHEMA FAIL: C_hi_le_17843 is not True")
    if b2.get("advertised_interval") != "0 <= m < 1.3715e-4":
        raise SystemExit(f"SCHEMA FAIL: advertised_interval={b2.get('advertised_interval')!r}")


def main():
    b2 = read_json("insertion", "nins3_small_mass_bound.json")
    validate_b2(b2)

    def L(name):
        return read_json("insertion", name)

    rc = L("root_adjoint_Ddiv_Dgf_certificates.json")
    sf = L("nins3_4D_special_family_certificates.json")
    en = L("nins3_4D_validated_enclosure.json")
    p1 = L("nins3_1p1_corrected_certificates.json")
    a2 = L("nins3_support_lemma_certificates.json")
    a3 = L("onshell_admission_certificates.json")
    a4 = read_json("classical_bv", "field_only_projection_certificates.json")

    ok = all(x.get("pass") for x in (rc, sf, en, p1, a2, a3, a4, b2))
    status = (
        "Analytic 4D nonvanishing for the massless special family, conditional on the "
        "inherited reduction identities and configuration-space admissibility "
        "(Route A sufficient; Route B not claimed discharged)"
    )
    dec = {
        "gate": "N-Ins.3_decision",
        "revision": "r12",
        "pass": bool(ok),
        "route_A": "discharged",
        "route_B": "not claimed discharged",
        "arbitrary_prescribed_m": "unresolved",
        "support_lemma": a2.get("pass"),
        "admission": a3.get("pass"),
        "projection": a4.get("pass"),
        "small_mass": {k: b2[k] for k in REQUIRED},
        "decision": {
            "N-Ins.3": status + f"; certified small-mass {b2['advertised_interval']}",
            "N-Ins.4": "Unresolved",
        },
        "schema": "r12",
        "output_root": str(OUTPUTS_DIR),
    }
    ic = {
        "revision": "r12",
        "milestones": {
            "N-Ins.3": {"status": dec["decision"]["N-Ins.3"]},
            "N-Ins.4": {"status": "Unresolved"},
        },
        "statuses": {
            "proved_obstructed_claim_withdrawn": True,
            "toy_witness_removed": True,
            "inadmissible_asymmetric_witness_withdrawn": True,
            "route_B_not_claimed_discharged": True,
            "arbitrary_prescribed_m_unresolved": True,
        },
    }
    red = {
        "revision": "r12",
        "inadmissible_nonzero_withdrawn": {"status": "withdrawn_as_NIns_witness"},
        "N_Ins_3": dec["decision"]["N-Ins.3"],
        "N_Ins_4": "Unresolved",
        "route_B": "not claimed discharged",
    }
    write_json("insertion", "nins3_decision_certificates.json", dec)
    write_json("insertion", "insertion_certificates.json", ic)
    write_json("insertion", "onshell_reduction_certificates.json", red)
    print(json.dumps(dec["decision"], indent=1), "pass", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

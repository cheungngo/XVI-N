#!/usr/bin/env python3
"""Orchestrate classical BV revision checks. Certs ONLY under build/outputs/classical_bv/."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
from package_paths import out_dir, write_json

OUT = str(out_dir("classical_bv"))
PYBIN = sys.executable

REQUIRED_MASTER_KEYS = (
    "Q_D_squared",
    "full_retained_order_broken_master_identity",
)
REQUIRED_QD_KEYS = ("definition", "explicit_nonzero", "status")
REQUIRED_ENZ_KEYS = ("conclusion",)


def run(script):
    r = subprocess.run(
        [PYBIN, str(SCRIPT_DIR / script)],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
    return r.returncode


def qd2_explicit_nonzero_ok(master: dict) -> bool:
    """Fail-closed: exact schema, no whole-blob 'nonzero' search."""
    missing = [k for k in REQUIRED_MASTER_KEYS if k not in master]
    if missing:
        raise SystemExit(f"SCHEMA FAIL classical_master missing keys: {missing}")
    qd = master["Q_D_squared"]
    if not isinstance(qd, dict):
        raise SystemExit("SCHEMA FAIL: Q_D_squared must be an object")
    missing_qd = [k for k in REQUIRED_QD_KEYS if k not in qd]
    if missing_qd:
        raise SystemExit(f"SCHEMA FAIL Q_D_squared missing keys: {missing_qd}")
    enz = qd["explicit_nonzero"]
    if not isinstance(enz, dict):
        raise SystemExit("SCHEMA FAIL: Q_D_squared.explicit_nonzero must be an object")
    missing_enz = [k for k in REQUIRED_ENZ_KEYS if k not in enz]
    if missing_enz:
        raise SystemExit(
            f"SCHEMA FAIL Q_D_squared.explicit_nonzero missing keys: {missing_enz}"
        )
    conclusion = enz["conclusion"]
    if not isinstance(conclusion, str) or not conclusion.strip():
        raise SystemExit("SCHEMA FAIL: explicit_nonzero.conclusion empty")
    # Exact expected scientific conclusion markers (not a blob scan)
    markers = ("NOT the zero", "not a BV complex")
    if not any(m in conclusion for m in markers):
        raise SystemExit(
            "SCHEMA FAIL: explicit_nonzero.conclusion lacks required markers "
            f"{markers}; got {conclusion!r}"
        )
    return True


def main():
    rc1 = run("brst_normalization.py")
    rc2 = run("extended_action_master.py")
    brst_path = os.path.join(OUT, "brst_normalization_certificates.json")
    master_path = os.path.join(OUT, "classical_master_certificates.json")
    if not os.path.isfile(brst_path):
        raise SystemExit(f"missing {brst_path}")
    if not os.path.isfile(master_path):
        raise SystemExit(f"missing {master_path}")
    brst = json.load(open(brst_path))
    master = json.load(open(master_path))
    s2_ok = brst["s2_checks"]["interacting_unrestricted_2jets_correct"]["pass"]
    neg_ok = brst["s2_checks"]["negative_controls_ok"]
    qd2_ok = qd2_explicit_nonzero_ok(master)
    full = master["full_retained_order_broken_master_identity"]
    interface_ok = s2_ok and neg_ok and qd2_ok and rc1 == 0 and rc2 == 0
    cert = {
        "gate": "N-CME (revised)",
        "revision": "r12",
        "verdict": "PASS_INTERFACE" if interface_ok else "FAIL",
        "meaning": (
            "constructs the unprepared classical BV complex and its explicitly broken "
            "prepared-action extension through the declared order"
        ),
        "s2_unrestricted_2jets": s2_ok,
        "negative_controls": neg_ok,
        "Q_D_squared_nonzero": qd2_ok,
        "full_retained_order_broken_master_identity": full,
        "N_A_release": "Provisional" if full == "Unresolved" else "Constructed",
        "pass": bool(interface_ok),
        "schema": "r12_strict_Q_D_squared",
    }
    with open(os.path.join(OUT, "classical_bv_check_out.txt"), "w") as f:
        for k, v in cert.items():
            f.write(f"{k}: {v}\n")
    write_json("classical_bv", "classical_bv_check_certificates.json", cert)
    print(json.dumps(cert, indent=2))
    return 0 if interface_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

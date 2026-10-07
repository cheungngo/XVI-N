#!/usr/bin/env python3
"""Malformed/old small-mass schemas must fail the composer validator clearly."""
import json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "code" / "insertion"))
from nins3_status_composer import validate_b2

def expect_fail(b2, label):
    try:
        validate_b2(b2)
    except SystemExit as e:
        print("OK fail", label, str(e)[:80])
        return
    raise AssertionError(f"expected schema fail for {label}")

# legacy keys only
expect_fail({"pass": True, "C": 1, "W0_lower": 1, "m_star": 1e-4}, "legacy")
# missing fields
expect_fail({"pass": True, "status": "certified"}, "missing")
# wrong status
bad = {k: True for k in
       ["revision","pass","status","C_hi","C_hi_le_17843","W0_lo",
        "m_star_advertised","advertised_interval","conditional_on","instance_family"]}
bad["status"] = "candidate"
bad["advertised_interval"] = "0 <= m < 1.3715e-4"
bad["C_hi"] = "1"
bad["W0_lo"] = "1"
bad["m_star_advertised"] = "1"
bad["revision"] = "r10"
bad["conditional_on"] = "x"
bad["instance_family"] = "y"
expect_fail(bad, "bad status")
print("PASS test_schema_failure")

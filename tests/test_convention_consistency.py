#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
body = (ROOT / "manuscript" / "body" / "XVI-N-body.tex").read_text()
sheet = (ROOT / "manuscript" / "notes" / "convention_sheet.md").read_text()
assert r"(S,\Phi^A)=-\delta^R S/\delta\Phi^*_A" in body
assert "false for odd" in body
assert "negative" in sheet.lower()
assert "S_D = S_inv" in sheet
assert "Hessian" in sheet and ("m" in sheet)
gen = (ROOT / "code" / "classical_bv" / "extended_action_master.py").read_text()
assert "c^*" in gen or "c_star" in gen or "c*" in gen
assert "-kappa" in gen.lower() or r"-\kappa" in gen
print("PASS test_convention_consistency")

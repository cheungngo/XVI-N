#!/usr/bin/env python3
"""No current check may open the top-level XVI-N.tex stub as scientific source."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
bad = []
for p in (ROOT / "code").rglob("*.py"):
    if p.name == "package_paths.py":
        continue  # may mention stub only to refuse it
    t = p.read_text(errors="replace")
    if "/workspace/XVI-N.tex" in t:
        bad.append(str(p.relative_to(ROOT)))
if bad:
    print("FAIL stub refs:", bad)
    raise SystemExit(1)
sys.path.insert(0, str(ROOT / "code"))
from package_paths import assert_not_stub, BODY_TEX
try:
    assert_not_stub("/" + "workspace" + "/" + "XVI-N.tex")
    print("FAIL assert_not_stub did not raise")
    raise SystemExit(1)
except RuntimeError:
    pass
assert BODY_TEX.is_file()
print("PASS test_stub_path_absence; BODY_TEX=", BODY_TEX)

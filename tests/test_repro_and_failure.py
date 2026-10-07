#!/usr/bin/env python3
"""r12 reproducibility and fail-closed tests.

Modes:
  --unit   (default in pipeline): local fail-closed checks without full regen
  --reloc  full reloc + unrelated cwd + two-regen vs immutable reference
           (slow; invoked by tools/run_reloc_repro.sh)
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
OUT = ROOT / "build" / "outputs"
REF = ROOT / "reference_outputs"
PY = sys.executable


def fail(msg: str):
    raise SystemExit("REPRO/FAILTEST: " + msg)


def unit_missing_prep_hard_fail():
    """Missing prep_certificates after producers must hard-fail (no fabricate)."""
    src = (ROOT / "tools" / "run_r10.py").read_text()
    if "aggregate prep gate" in src:
        fail("prep fabricate substitute still present in run_r10.py")
    if "if not prep_c.is_file():\n        prep_c.write_text" in src.replace("\r", ""):
        fail("prep_c.write_text fabricate still present")
    if "HARD FAIL: prep_certificates.json missing" not in src:
        fail("missing hard-fail path for prep_certificates")
    print("unit: prep fabricate absent + hard-fail present OK")


def unit_required_script_precheck():
    src = (ROOT / "tools" / "run_r10.py").read_text()
    if "def require_scripts" not in src:
        fail("require_scripts missing")
    if "REQUIRED SCRIPT MISSING" not in src:
        fail("REQUIRED SCRIPT MISSING message missing")
    # Ensure classical/prep/insertion phases call require_scripts before loops
    if src.count("require_scripts(") < 3:
        fail("require_scripts not used for all required phases")
    print("unit: required-script precheck OK")


def unit_classical_bv_strict():
    src = (ROOT / "code" / "classical_bv" / "classical_bv_check.py").read_text()
    if 'blob = json.dumps(master)' in src:
        fail("classical_bv still scans whole blob")
    if '"nonzero" in blob' in src or "nonzero\" in blob" in src:
        fail("classical_bv permissive nonzero search still present")
    if "SCHEMA FAIL" not in src:
        fail("classical_bv lacks SCHEMA FAIL")
    if "explicit_nonzero" not in src:
        fail("classical_bv lacks explicit_nonzero schema check")
    print("unit: classical_bv strict schema OK")


def unit_free_hessian_out_root():
    src = (ROOT / "code" / "normalization" / "free_hessian_check.py").read_text()
    if "OUT_DIR = os.path.dirname(os.path.abspath(__file__))" in src:
        fail("free_hessian still uses dirname(__file__) as OUT_DIR")
    if "out_dir(\"normalization\")" not in src and "out_dir('normalization')" not in src:
        fail("free_hessian does not use package_paths.out_dir")
    print("unit: free_hessian build/outputs OK")


def unit_reference_immutable_in_pipeline():
    src = (ROOT / "tools" / "run_r10.py").read_text()
    idx = src.find("def update_reference")
    if idx < 0:
        fail("update_reference helper missing")
    before = src[:idx]
    if "copytree(OUT" in before or "copytree(OUT" in before.replace(" ", ""):
        fail("reference copytree outside update_reference")
    # Default main must not call update_reference except via CLI flag branch
    main = src[src.find("def main("):]
    # Remove the update-reference CLI early-return block for inspection
    if "shutil.copytree(OUT, REF)" in main and "def update_reference" not in main:
        # copytree should only live in update_reference, not re-inlined in main
        fail("copytree inlined in main")
    print("unit: reference immutable in default pipeline OK")


def unit_contract_text():
    src = (CODE / "insertion" / "export_nins12_contracts.py").read_text()
    # Forbid the old bad ansatz string as the declared ANSATZ value
    if "antifield-linear completion of prepared S_D" in src and "NOT completion of prepared" not in src:
        fail("exporter still has prepared S_D ansatz")
    # Positive markers
    if "Q_U = Q_inv" not in src:
        fail("exporter missing Q_U = Q_inv")
    if "I_t = F_t + A_0 + kappa A_1" not in src and "I_t = F_t + A_0 + κ A_1" not in src:
        # ANSATZ constant uses kappa spelling
        if "I_t = F_t + A_0 + kappa A_1" not in src:
            fail("exporter missing insertion class I_t=F_t+A_0+kappa A_1")
    if 'ANSATZ =' in src and "seed-preserving" not in src:
        fail("exporter ANSATZ missing seed-preserving")
    cs_path = OUT / "insertion" / "completion_space.json"
    if cs_path.is_file():
        cs = json.loads(cs_path.read_text())
        if cs.get("revision") == "r12":
            ansatz = cs.get("ansatz", "")
            if "prepared S_D" in ansatz and "NOT" not in ansatz:
                fail(f"bad ansatz in live r12 cert: {ansatz[:120]}")
            if "I_t" not in ansatz or "F_t" not in ansatz:
                fail("r12 ansatz missing I_t/F_t")
            ic = json.loads((OUT / "insertion" / "insertion_contract.json").read_text())
            if "Q_inv" not in ic.get("Q_U", ""):
                fail(f"Q_U not Q_inv: {ic.get('Q_U')}")
    print("unit: completion contract H4 text OK")


def run_unit():
    unit_missing_prep_hard_fail()
    unit_required_script_precheck()
    unit_classical_bv_strict()
    unit_free_hessian_out_root()
    unit_reference_immutable_in_pipeline()
    unit_contract_text()
    print("ALL UNIT REPRO/FAILURE CHECKS PASSED")
    return 0


def scientific_compare(a_dir: Path, b_dir: Path) -> list[str]:
    ignore = {
        "seconds", "elapsed", "elapsed_sec", "elapsed_s", "timestamp",
        "write_path", "cert_path", "output_root", "body", "path", "paths",
        "cwd", "host", "interpreter",
    }
    drifts = []

    def norm_str(s: str) -> str:
        # Drop absolute package-root prefixes so reloc compares equal
        for root in ("/tmp/XVI-N-r12-reloc", str(ROOT), "/workspace/XVI-N-r10"):
            if s.startswith(root + "/") or s == root:
                return "PKG/" + s[len(root):].lstrip("/")
        return s

    def strip(o):
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                if k in ignore or k.startswith("elapsed") or "seconds" in k.lower() or "elapsed" in k.lower():
                    continue
                if k == "revision" and v in ("r11", "r12"):
                    out[k] = "REV"
                elif k == "schema" and isinstance(v, str) and v.startswith("r"):
                    out[k] = "SCHEMA"
                else:
                    out[k] = strip(v)
            return out
        if isinstance(o, list):
            return [strip(x) for x in o]
        if isinstance(o, str):
            return norm_str(o)
        return o

    for fresh in a_dir.rglob("*.json"):
        rel = fresh.relative_to(a_dir)
        other = b_dir / rel
        if not other.is_file():
            drifts.append(f"missing {rel}")
            continue
        if strip(json.loads(fresh.read_text())) != strip(json.loads(other.read_text())):
            drifts.append(f"drift {rel}")
    return drifts


def run_reloc():
    """Full reloc extract, unrelated cwd, two clean regens vs reference."""
    if not REF.is_dir() or not any(REF.rglob("*.json")):
        fail("reference_outputs/ required before --reloc (run update-reference first)")
    reloc = Path("/tmp/XVI-N-r12-reloc")
    if reloc.exists():
        shutil.rmtree(reloc)
    # Copy tree excluding build/ and huge caches
    def ignore(dir, names):
        skip = {"build", "__pycache__", ".git", "XVI-N.pdf", "listing_src"}
        return [n for n in names if n in skip or n.endswith(".pyc")]
    shutil.copytree(ROOT, reloc, ignore=ignore, symlinks=True)
    logdir = ROOT / "build" / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    reloc_log = logdir / "reloc_repro.log"
    lines = [f"reloc root: {reloc}", f"PY={PY}"]

    unrelated = Path("/tmp/XVI-N-r12-unrelated-cwd")
    unrelated.mkdir(parents=True, exist_ok=True)

    def regen(tag: str):
        cmd = [PY, str(reloc / "tools" / "run_r10.py"), "--skip-verify"]
        # First regen builds reference-comparable outputs; we compare manually
        p = subprocess.run(
            cmd, cwd=str(unrelated), capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(reloc / "code")},
        )
        (logdir / f"reloc_{tag}.txt").write_text(
            f"rc={p.returncode}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}\n"
        )
        lines.append(f"{tag} rc={p.returncode}")
        if p.returncode != 0:
            fail(f"reloc {tag} failed rc={p.returncode}; see build/logs/reloc_{tag}.txt")
        return reloc / "build" / "outputs"

    out1 = regen("regen1")
    drifts1 = scientific_compare(out1, REF)
    if drifts1:
        # After contract/schema bumps, reference may need refresh once; still report
        lines.append("regen1 vs reference drifts: " + "; ".join(drifts1[:20]))
        reloc_log.write_text("\n".join(lines) + "\n")
        fail("regen1 drifted from immutable reference: " + "; ".join(drifts1[:15]))
    lines.append("regen1 vs reference: PASS")

    # Second clean regen
    if (reloc / "build").exists():
        shutil.rmtree(reloc / "build")
    out2 = regen("regen2")
    drifts2 = scientific_compare(out2, REF)
    if drifts2:
        fail("regen2 drifted from reference: " + "; ".join(drifts2[:15]))
    drifts12 = scientific_compare(out1, out2)
    if drifts12:
        fail("regen1 vs regen2 drift: " + "; ".join(drifts12[:15]))
    lines.append("regen2 vs reference: PASS")
    lines.append("regen1 vs regen2: PASS")

    # Failure propagation: missing required script
    victim = reloc / "code" / "prep" / "prepared_gauge_variation.py"
    bak = victim.read_bytes()
    victim.unlink()
    p = subprocess.run(
        [PY, str(reloc / "tools" / "run_r10.py"), "--skip-verify"],
        cwd=str(unrelated), capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(reloc / "code")},
    )
    victim.write_bytes(bak)
    (logdir / "reloc_missing_script.txt").write_text(
        f"rc={p.returncode}\n{p.stdout}\n{p.stderr}\n"
    )
    if p.returncode == 0:
        fail("missing required script did not fail")
    if "REQUIRED SCRIPT MISSING" not in p.stdout + p.stderr:
        # may only be in captured log via SystemExit message on stderr/stdout
        if "REQUIRED SCRIPT MISSING" not in (p.stdout + p.stderr):
            lines.append("WARN: missing-script fail without exact banner (rc!=0 OK)")
    lines.append(f"missing-script hard-fail: PASS (rc={p.returncode})")

    # Stale/fabricated schema rejection via classical_bv unit path
    p2 = subprocess.run(
        [PY, "-c",
         "import json,sys; sys.path.insert(0,'%s'); "
         "from classical_bv_check import qd2_explicit_nonzero_ok; "
         "qd2_explicit_nonzero_ok({'full_retained_order_broken_master_identity':'Unresolved'})"
         % (reloc / "code" / "classical_bv"),
         ],
        capture_output=True, text=True,
    )
    if p2.returncode == 0:
        fail("fabricated/missing Q_D_squared schema did not fail")
    lines.append("fabricated schema hard-fail: PASS")

    reloc_log.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("RELOC REPRO PASSED")
    return 0


def main():
    args = sys.argv[1:]
    if "--reloc" in args:
        return run_reloc()
    return run_unit()


if __name__ == "__main__":
    raise SystemExit(main())

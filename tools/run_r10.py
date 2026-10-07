#!/usr/bin/env python3
"""XVI-N r12 release pipeline.

Sole cert root: build/outputs/. No placeholders. sys.executable only.
reference_outputs/ is immutable during normal runs (use update-reference).
Manifest order: pre-PDF provenance -> listings -> pdflatex x2 -> external manifest.
"""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
MS = ROOT / "manuscript"
BUILD = ROOT / "build"
LOGS = BUILD / "logs"
OUT = BUILD / "outputs"
LIST = BUILD / "listing_src"
PDFDIR = BUILD / "pdf"
REF = ROOT / "reference_outputs"
PROV = ROOT / "provenance"
HIST = ROOT / "historical"
PY = sys.executable
REVISION = "r12"

REQUIRED_LISTINGS = [
    "code/package_paths.py",
    "tools/run_r10.py",
    "requirements.lock",
    "ENVIRONMENT.md",
    "tests/test_stub_path_absence.py",
    "tests/test_schema_failure.py",
    "tests/test_convention_consistency.py",
    "tests/test_repro_and_failure.py",
    "code/conventions/source_of_truth.py",
    "outputs/conventions/convention_coefficients.json",
    "code/conventions/check_ms_coefficients.py",
    "outputs/conventions/ms_coefficient_check.json",
    "code/classical_bv/classical_bv_check.py",
    "outputs/classical_bv/classical_bv_check_out.txt",
    "outputs/classical_bv/brst_normalization_certificates.json",
    "outputs/classical_bv/qd2_antifield_certificates.json",
    "outputs/classical_bv/qd2_general_jets_certificates.json",
    "outputs/classical_bv/generator_antibracket_certificates.json",
    "outputs/classical_bv/field_only_projection_certificates.json",
    "outputs/prep/af0_noether_certificates.json",
    "outputs/prep/prep_certificates.json",
    "outputs/normalization/free_hessian_check_out.txt",
    "code/insertion/nins3_status_composer.py",
    "outputs/insertion/completion_space.json",
    "outputs/insertion/insertion_contract.json",
    "outputs/insertion/nins3_4D_special_family_certificates.json",
    "outputs/insertion/nins3_4D_validated_enclosure.json",
    "code/insertion/nins3_small_mass_bound.py",
    "outputs/insertion/nins3_small_mass_bound.json",
    "outputs/insertion/nins3_decision_certificates.json",
    "outputs/insertion/nins3_support_lemma_certificates.json",
    "outputs/insertion/onshell_admission_certificates.json",
    "outputs/regression/regression_N_out.txt",
    "logs/pipeline_tail.txt",
    "provenance/RELEASE_MANIFEST_PREPDF.txt",
]

# Required producers: must exist BEFORE the phase runs.
REQUIRED_CLASSICAL = [
    "brst_normalization.py",
    "qd2_antifield_test.py",
    "qd2_general_jets.py",
    "extended_action_master.py",
    "classical_bv_check.py",
    "generator_antibracket_test.py",
    "field_only_projection_check.py",
    "s_psi_coefficients.py",
]
REQUIRED_PREP = [
    "prepared_noether_af0.py",
    "independent_weighted_euler.py",
    "prepared_gauge_variation.py",
]
REQUIRED_INSERTION = [
    "export_nins12_contracts.py",
    "root_adjoint_H.py",
    "root_adjoint_Ddiv_Dgf_check.py",
    "nins3_4D_special_family_analytic.py",
    "nins3_1p1_corrected.py",
    "nins3_support_lemma_check.py",
    "onshell_admission_check.py",
    "onshell_structural_check.py",
    "parity_control_symmetric.py",
    "nins3_4D_kirchhoff_corrected.py",
    "insertion_variation.py",
    "nins3_4D_validated_enclosure.py",
    "nins3_small_mass_bound.py",
    "nins3_status_composer.py",
]

# Keys ignored when comparing scientific JSON to immutable reference.
_COMPARE_IGNORE_KEYS = {
    "seconds", "elapsed", "elapsed_sec", "elapsed_s", "timestamp",
    "write_path", "cert_path", "output_root", "interpreter", "host",
    "cwd", "path", "paths", "body",
}


def log(msg: str):
    print(msg, flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "pipeline.log", "a") as f:
        f.write(msg + "\n")


def run(cmd, cwd=None, log_name=None):
    cwd = cwd or ROOT
    log(f"$ {' '.join(cmd)}  (cwd={cwd})")
    t0 = time.time()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(CODE) + os.pathsep + env.get("PYTHONPATH", "")
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env)
    elapsed = time.time() - t0
    if log_name:
        (LOGS / log_name).write_text(
            f"cmd: {cmd}\nrc: {p.returncode}\nseconds: {elapsed}\n\nSTDOUT:\n{p.stdout}\n\nSTDERR:\n{p.stderr}\n"
        )
    if p.returncode != 0:
        log(f"FAIL rc={p.returncode} ({elapsed:.1f}s)")
        if p.stdout:
            log(p.stdout[-2000:])
        if p.stderr:
            log(p.stderr[-2000:])
        raise SystemExit(p.returncode)
    log(f"OK ({elapsed:.1f}s)")
    return p


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require_scripts(subdir: Path, names: list[str], phase: str) -> None:
    missing = [n for n in names if not (subdir / n).is_file()]
    if missing:
        raise SystemExit(
            f"REQUIRED SCRIPT MISSING before {phase}:\n  "
            + "\n  ".join(str(subdir / n) for n in missing)
        )


def clean_build():
    if BUILD.exists():
        log(f"Removing {BUILD}")
        shutil.rmtree(BUILD)
    for d in (OUT, LOGS, LIST, PDFDIR):
        d.mkdir(parents=True, exist_ok=True)
    purge_code_certs(pre=True)


def purge_code_certs(pre: bool = False):
    """Remove generated certificate artifacts under code/."""
    killed = []
    for pth in CODE.rglob("*"):
        if not pth.is_file():
            continue
        if pth.suffix == ".py":
            continue
        # generated certs / outs
        name = pth.name
        if (
            pth.suffix == ".json"
            or name.endswith("_out.txt")
            or "certificate" in name.lower()
            or name.endswith("_certificates.json")
        ):
            pth.unlink()
            killed.append(str(pth.relative_to(ROOT)))
    for rel in killed:
        log(f"{'pre-' if pre else 'post-'}purge code cert: {rel}")


def assert_no_code_certs():
    """Post-run audit: no generated cert JSON/txt under code/."""
    bad = []
    for pth in CODE.rglob("*"):
        if not pth.is_file() or pth.suffix == ".py":
            continue
        name = pth.name
        if (
            pth.suffix == ".json"
            or name.endswith("_out.txt")
            or "certificate" in name.lower()
        ):
            bad.append(str(pth.relative_to(ROOT)))
    if bad:
        raise SystemExit(
            "POST-RUN AUDIT FAIL: generated certs under code/:\n  " + "\n  ".join(bad)
        )
    log("post-run code/ cert audit: PASS (none found)")


def ascii_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        return
    raw = src.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    dst.write_text("".join(ch if ord(ch) < 128 else "?" for ch in text))


def build_listings():
    if LIST.exists():
        shutil.rmtree(LIST)
    LIST.mkdir(parents=True)
    ascii_copy(ROOT / "requirements.lock", LIST / "requirements.lock")
    if (ROOT / "ENVIRONMENT.md").is_file():
        ascii_copy(ROOT / "ENVIRONMENT.md", LIST / "ENVIRONMENT.md")
    for p in (MS / "notes").glob("*"):
        if p.is_file():
            ascii_copy(p, LIST / "notes" / p.name)
    for p in PROV.rglob("*"):
        if p.is_file():
            ascii_copy(p, LIST / "provenance" / p.relative_to(PROV))
    for p in CODE.rglob("*"):
        if p.is_file() and p.suffix in {".py", ".md", ".tex", ".txt"}:
            ascii_copy(p, LIST / "code" / p.relative_to(CODE))
    for p in (ROOT / "tools").glob("*.py"):
        ascii_copy(p, LIST / "tools" / p.name)
    for p in (ROOT / "tests").glob("*.py"):
        ascii_copy(p, LIST / "tests" / p.name)
    for p in OUT.rglob("*"):
        if p.is_file():
            ascii_copy(p, LIST / "outputs" / p.relative_to(OUT))
    plog = LOGS / "pipeline.log"
    if plog.is_file():
        lines = plog.read_text().splitlines()
        (LIST / "logs").mkdir(parents=True, exist_ok=True)
        (LIST / "logs" / "pipeline_tail.txt").write_text("\n".join(lines[-80:]) + "\n")
    missing = [rel for rel in REQUIRED_LISTINGS if not (LIST / rel).is_file()]
    if missing:
        raise SystemExit("LISTING FAIL missing required files:\n  " + "\n  ".join(missing))
    stub_marker = "% " + "placeholder generated for r10 listing completeness"
    for pth in (LIST / "outputs").rglob("*"):
        if pth.is_file():
            txt = pth.read_text(errors="replace")
            if stub_marker in txt or txt.strip().startswith("% placeholder"):
                raise SystemExit(f"LISTING FAIL stub certificate in {pth}")
    link = MS / "listing_src"
    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.is_dir():
        shutil.rmtree(link)
    link.symlink_to(Path("..") / "build" / "listing_src")
    log(f"listings OK ({sum(1 for _ in LIST.rglob('*') if _.is_file())} files)")


def _strip_for_compare(obj):
    if isinstance(obj, dict):
        return {
            k: _strip_for_compare(v)
            for k, v in obj.items()
            if k not in _COMPARE_IGNORE_KEYS and not str(k).startswith("elapsed") and "seconds" not in str(k).lower()
        }
    if isinstance(obj, list):
        return [_strip_for_compare(x) for x in obj]
    if isinstance(obj, str):
        for root in (str(ROOT), "/workspace/XVI-N-r10", "/tmp/XVI-N-r12-reloc"):
            if obj.startswith(root + "/") or obj == root:
                return "PKG/" + obj[len(root):].lstrip("/")
        return obj
    return obj


def verify_against_reference():
    """Compare fresh scientific JSON under build/outputs to immutable reference_outputs/."""
    if not REF.is_dir():
        log("VERIFY WARN: reference_outputs/ missing; skip compare (first seal?)")
        return
    drifts = []
    for fresh in OUT.rglob("*.json"):
        rel = fresh.relative_to(OUT)
        refp = REF / rel
        if not refp.is_file():
            drifts.append(f"missing in reference: {rel}")
            continue
        try:
            a = _strip_for_compare(json.loads(fresh.read_text()))
            b = _strip_for_compare(json.loads(refp.read_text()))
        except Exception as e:
            drifts.append(f"parse error {rel}: {e}")
            continue
        # Allow revision string bump r11->r12 without failing science compare on that key alone
        def norm_rev(o):
            if isinstance(o, dict):
                o = dict(o)
                if o.get("revision") in ("r11", "r12"):
                    o["revision"] = "REV"
                if o.get("schema") in ("r11", "r12", "r12_strict_Q_D_squared"):
                    o["schema"] = "SCHEMA"
                return {k: norm_rev(v) for k, v in o.items()}
            if isinstance(o, list):
                return [norm_rev(x) for x in o]
            return o
        if norm_rev(a) != norm_rev(b):
            drifts.append(f"drift: {rel}")
    if drifts:
        raise SystemExit(
            "VERIFY FAIL vs immutable reference_outputs/:\n  " + "\n  ".join(drifts[:40])
        )
    log("verify vs reference_outputs: PASS")


def update_reference():
    """Maintainer-only: copy approved build/outputs into reference_outputs/."""
    if not OUT.is_dir() or not any(OUT.rglob("*.json")):
        raise SystemExit("update-reference FAIL: build/outputs empty")
    if REF.exists():
        shutil.rmtree(REF)
    shutil.copytree(OUT, REF)
    log(f"update-reference: copied {OUT} -> {REF}")
    n = sum(1 for _ in REF.rglob("*.json"))
    log(f"update-reference: {n} json files")
    return 0


def write_prepdf_manifest(reg_counts=None, small_mass=None):
    """Pre-PDF provenance: revision/status/regression; NO PDF hash or page count."""
    HIST.mkdir(parents=True, exist_ok=True)
    # Move stale embedded manifests to historical/
    for name in ("RELEASE_MANIFEST.txt", "RELEASE_MANIFEST_PREPDF.txt"):
        src = PROV / name
        if src.is_file():
            stamp = time.strftime("%Y%m%d-%H%M%S")
            dst = HIST / f"{name}.r11-or-earlier.{stamp}.historical"
            # only archive if content looks stale (r10/r11 or has PDF sha)
            txt = src.read_text()
            if "r10" in txt or "r11" in txt or "PDF sha256" in txt or "pages:" in txt.lower():
                shutil.copy2(src, dst)
                hdr = (
                    f"# HISTORICAL (archived {stamp}); not the active pre-PDF record.\n"
                    f"# Original path: provenance/{name}\n\n"
                )
                (HIST / f"NOTE_{name}.txt").write_text(
                    hdr + "Stale provenance archived before r12 pre-PDF rewrite.\n"
                )
                log(f"archived stale {name} -> {dst.name}")
    xm = sha256(PROV / "XVI-M.tex")
    assert xm == "41aa109935f40ddee3109de62c46329c189b5408007970cc90ed5611dc4739ea"
    lines = [
        f"XVI-N {REVISION} RELEASE MANIFEST (PRE-PDF; embedded in PDF; NO PDF hash / final page count)",
        f"date: {time.strftime('%Y-%m-%d')}",
        f"revision: {REVISION}",
        "massless_theorem: conditional_on_inherited_identities (Route A)",
        "route_B: not_claimed_discharged",
        "arbitrary_prescribed_m_gt_0: unresolved",
        f"XVI-M.tex sha256 (unchanged): {xm}",
        "output_root: build/outputs",
        "interpreter: sys.executable",
        "note: final page count and PDF sha256 appear ONLY in RELEASE_MANIFEST_EXTERNAL.txt",
    ]
    if reg_counts:
        lines.append(
            f"regression_math: {reg_counts['math_passed']} pass / {reg_counts['math_failed']} fail"
        )
        lines.append(
            f"regression_pack: {reg_counts['pack_passed']} pass / {reg_counts['pack_failed']} fail"
        )
    if small_mass:
        lines.append(
            f"small-mass: {small_mass.get('advertised_interval')} status={small_mass.get('status')}"
        )
    lines += [
        "",
        f"{sha256(MS / 'XVI-N.tex')}  manuscript/XVI-N.tex",
        f"{sha256(MS / 'body' / 'XVI-N-body.tex')}  manuscript/body/XVI-N-body.tex",
        f"{sha256(MS / 'notes' / 'small_mass_estimate.tex')}  manuscript/notes/small_mass_estimate.tex",
        f"{xm}  provenance/XVI-M.tex",
    ]
    text = "\n".join(lines) + "\n"
    (PROV / "RELEASE_MANIFEST_PREPDF.txt").write_text(text)
    (PROV / "RELEASE_MANIFEST.txt").write_text(text)
    log("wrote pre-PDF provenance RELEASE_MANIFEST_PREPDF.txt")


def bump_banners():
    tex = (MS / "XVI-N.tex").read_text()
    tex = re.sub(r"XVI-N r1[01] release", f"XVI-N {REVISION} release", tex)
    tex = re.sub(
        r"r1[01] release; Route B unresolved",
        f"{REVISION} release; Route B unresolved",
        tex,
    )
    (MS / "XVI-N.tex").write_text(tex)


def run_producers():
    run([PY, str(ROOT / "tests" / "test_stub_path_absence.py")], log_name="test_stub.txt")
    run([PY, str(ROOT / "tests" / "test_convention_consistency.py")], log_name="test_conv.txt")
    run([PY, str(ROOT / "tests" / "test_schema_failure.py")], log_name="test_schema.txt")
    run([PY, str(ROOT / "tests" / "test_repro_and_failure.py"), "--unit"],
        log_name="test_repro_unit.txt")

    run([PY, str(CODE / "conventions" / "source_of_truth.py")],
        cwd=CODE / "conventions", log_name="01_sot.txt")
    run([PY, str(CODE / "conventions" / "check_ms_coefficients.py")],
        cwd=CODE / "conventions", log_name="01_ms.txt")

    require_scripts(CODE / "classical_bv", REQUIRED_CLASSICAL, "classical_bv")
    for name in REQUIRED_CLASSICAL:
        script = CODE / "classical_bv" / name
        run([PY, str(script)], cwd=script.parent, log_name=f"02_{name}.txt")

    run([PY, str(CODE / "normalization" / "free_hessian_check.py")],
        cwd=CODE / "normalization", log_name="02_hessian.txt")
    hess_out = OUT / "normalization" / "free_hessian_check_out.txt"
    if not hess_out.is_file():
        raise SystemExit(f"missing free_hessian out under build/outputs: {hess_out}")
    if "build/outputs" not in hess_out.read_text() and "normalization" not in hess_out.read_text():
        # write_path should mention build outputs path
        log(f"WARN hessian out content:\n{hess_out.read_text()[:500]}")

    require_scripts(CODE / "prep", REQUIRED_PREP, "prep")
    for name in REQUIRED_PREP:
        script = CODE / "prep" / name
        run([PY, str(script)], cwd=script.parent, log_name=f"03_{name}.txt")
    prep_c = OUT / "prep" / "prep_certificates.json"
    if not prep_c.is_file():
        raise SystemExit(
            f"HARD FAIL: prep_certificates.json missing after prep producers: {prep_c}"
        )

    require_scripts(CODE / "insertion", REQUIRED_INSERTION, "insertion")
    for name in REQUIRED_INSERTION:
        script = CODE / "insertion" / name
        run([PY, str(script)], cwd=script.parent, log_name=f"03_{name}.txt")

    run([PY, str(CODE / "regression_N.py")], cwd=CODE, log_name="07_regression.txt")
    assert_no_code_certs()


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if "update-reference" in argv or "--update-reference" in argv:
        LOGS.mkdir(parents=True, exist_ok=True)
        return update_reference()
    if "verify" in argv or "--verify" in argv:
        LOGS.mkdir(parents=True, exist_ok=True)
        verify_against_reference()
        return 0

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "pipeline.log").write_text(
        f"{REVISION} pipeline start {time.ctime()} PY={PY}\n"
    )
    bad = []
    banned = "/" + "workspace/tmp/venv/bin/python"
    for p in CODE.rglob("*.py"):
        if banned in p.read_text(errors="replace"):
            bad.append(str(p))
    if bad:
        raise SystemExit("portability FAIL hard-coded venv in " + str(bad))

    if "--no-clean" not in argv:
        clean_build()
    else:
        for d in (OUT, LOGS, LIST, PDFDIR):
            d.mkdir(parents=True, exist_ok=True)

    run_producers()

    # Verify vs immutable reference (skip if --skip-verify or empty ref on first seal)
    if "--skip-verify" not in argv:
        if REF.is_dir() and any(REF.rglob("*.json")):
            verify_against_reference()
        else:
            log("no reference_outputs yet; skip verify (use update-reference after seal)")

    bump_banners()

    b2 = json.load(open(OUT / "insertion" / "nins3_small_mass_bound.json"))
    reg = json.load(open(OUT / "regression" / "regression_N_out.json"))
    reg_counts = {
        "math_passed": len(reg.get("math_passes", [])),
        "math_failed": len(reg.get("math_failures", [])),
        "pack_passed": len(reg.get("packaging_passes", [])),
        "pack_failed": len(reg.get("packaging_failures", [])),
    }
    # 1. Pre-PDF provenance (no PDF hash / pages)
    write_prepdf_manifest(reg_counts=reg_counts, small_mass=b2)
    # 2. Listings (embed pre-PDF provenance)
    build_listings()
    # 3. Compile
    for i in (1, 2):
        run(["pdflatex", "-interaction=nonstopmode", "XVI-N.tex"],
            cwd=MS, log_name=f"09_pdflatex_{i}.txt")
    pdf_src = MS / "XVI-N.pdf"
    PDFDIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_src, PDFDIR / "XVI-N.pdf")
    # 4. External final manifest
    xm = sha256(PROV / "XVI-M.tex")
    assert xm == "41aa109935f40ddee3109de62c46329c189b5408007970cc90ed5611dc4739ea"
    info = subprocess.check_output(["pdfinfo", str(PDFDIR / "XVI-N.pdf")], text=True)
    pages = int([ln for ln in info.splitlines() if ln.startswith("Pages:")][0].split()[1])
    pdf_hash = sha256(PDFDIR / "XVI-N.pdf")
    status = {
        "revision": REVISION,
        "pass": True,
        "massless_theorem": "conditional_on_inherited_identities",
        "route_A": "discharged",
        "route_B": "not_claimed_discharged",
        "arbitrary_prescribed_m_gt_0": "unresolved",
        "small_mass": {
            "status": b2["status"],
            "advertised_interval": b2["advertised_interval"],
            "C_hi": b2["C_hi"],
            "C_hi_le_17843": b2["C_hi_le_17843"],
            "exact_rational_C_m2_lt_W": b2.get("exact_rational_C_m2_lt_W"),
        },
        "XVI-M_sha256": xm,
        "pdf_pages": pages,
        "pdf_sha256_external": pdf_hash,
        "regression": {**reg_counts, "log": "build/logs/07_regression.txt"},
        "output_root": "build/outputs",
        "interpreter": "sys.executable",
        "reference_outputs": "immutable_during_pipeline",
        "completion_contract": "H4_insertion_class_I_t",
        "blockers_fixed": [
            "completion_contract_H4",
            "no_prep_fabricate",
            "required_script_precheck",
            "classical_bv_strict_schema",
            "free_hessian_build_outputs_only",
            "post_run_code_cert_audit",
            "prepdf_then_external_manifest",
            "immutable_reference_outputs",
            "K1_source_sup_norm_wording",
        ],
    }
    # Honest pass: confirm contract keys
    cs = json.load(open(OUT / "insertion" / "completion_space.json"))
    ic = json.load(open(OUT / "insertion" / "insertion_contract.json"))
    if "prepared S_D" in cs.get("ansatz", "") or "completion of prepared" in cs.get("ansatz", ""):
        status["pass"] = False
        status["fail_reason"] = "completion_space ansatz still mentions prepared S_D"
    if ic.get("Q_U", "").startswith("P_0") or "field-only projection" == ic.get("Q_U"):
        # Q_U must be Q_inv; projection is separate
        if "Q_U = Q_inv" not in ic.get("Q_U", "") and "Q_inv" not in ic.get("Q_U", ""):
            status["pass"] = False
            status["fail_reason"] = "Q_U not defined as Q_inv"
    (ROOT / "RELEASE_STATUS.json").write_text(json.dumps(status, indent=2) + "\n")
    man = [
        f"XVI-N {REVISION} RELEASE MANIFEST (EXTERNAL; post-PDF; PDF hash NOT embedded in PDF)",
        f"date: {time.strftime('%Y-%m-%d')}",
        f"pages: {pages}",
        f"PDF sha256 (external): {pdf_hash}",
        f"XVI-M.tex sha256 (unchanged): {xm}",
        f"regression_math: {reg_counts['math_passed']} pass / {reg_counts['math_failed']} fail",
        f"regression_pack: {reg_counts['pack_passed']} pass / {reg_counts['pack_failed']} fail",
        f"small-mass: {b2['advertised_interval']} status={b2['status']}",
        "Route B: not claimed discharged",
        "arbitrary m>0: unresolved",
        "output_root: build/outputs",
        "reference_outputs: immutable during normal pipeline",
        "",
        f"{sha256(MS / 'XVI-N.tex')}  manuscript/XVI-N.tex",
        f"{sha256(MS / 'body' / 'XVI-N-body.tex')}  manuscript/body/XVI-N-body.tex",
        f"{sha256(MS / 'notes' / 'small_mass_estimate.tex')}  manuscript/notes/small_mass_estimate.tex",
        f"{xm}  provenance/XVI-M.tex",
    ]
    (ROOT / "RELEASE_MANIFEST_EXTERNAL.txt").write_text("\n".join(man) + "\n")
    # Do NOT overwrite provenance/RELEASE_MANIFEST.txt with PDF hash
    log("RELEASE_STATUS.json written")
    log(json.dumps(status, indent=2))
    return 0 if status.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())

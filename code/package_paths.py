"""XVI-N-r10 package paths. Sole certificate root: build/outputs/."""
from __future__ import annotations
import json
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = _HERE.parent
if not (PACKAGE_ROOT / "manuscript").is_dir():
    for cand in _HERE.parents:
        if (cand / "manuscript" / "body").is_dir():
            PACKAGE_ROOT = cand
            break

MANUSCRIPT_DIR = PACKAGE_ROOT / "manuscript"
BODY_TEX = MANUSCRIPT_DIR / "body" / "XVI-N-body.tex"
NOTES_DIR = MANUSCRIPT_DIR / "notes"
CODE_DIR = _HERE
BUILD_DIR = PACKAGE_ROOT / "build"
OUTPUTS_DIR = BUILD_DIR / "outputs"
LOGS_DIR = BUILD_DIR / "logs"

# Subsystem name from a script path under code/
_SUB_MAP = {
    "insertion": "insertion",
    "classical_bv": "classical_bv",
    "conventions": "conventions",
    "normalization": "normalization",
    "prep": "prep",
    "certificates": "certificates",
}


def ensure_output_dirs() -> None:
    for sub in _SUB_MAP.values():
        (OUTPUTS_DIR / sub).mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "regression").mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def out_dir(subdir: str) -> Path:
    """Sole writable/readable certificate directory for a subsystem."""
    ensure_output_dirs()
    d = OUTPUTS_DIR / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d


def out_dir_for_script(script_file: str | Path) -> Path:
    """Infer subsystem from script location under code/."""
    p = Path(script_file).resolve()
    # .../code/<sub>/file.py
    try:
        rel = p.relative_to(CODE_DIR)
        sub = rel.parts[0] if rel.parts else "misc"
    except ValueError:
        sub = "misc"
    if sub not in _SUB_MAP and sub != "misc":
        # script may live directly under code/
        sub = "certificates"
    return out_dir(sub if sub in _SUB_MAP or sub == "misc" else "certificates")


def output_path(*parts: str) -> Path:
    ensure_output_dirs()
    p = OUTPUTS_DIR.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_json(subdir: str, name: str, obj) -> Path:
    """Write a certificate ONLY under build/outputs/<subdir>/."""
    path = out_dir(subdir) / name
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)
    return path


def read_json(subdir: str, name: str):
    """Read a certificate ONLY from build/outputs/<subdir>/. No code-dir fallback."""
    path = out_dir(subdir) / name
    if not path.is_file():
        raise FileNotFoundError(
            f"required certificate missing under sole output root: {path}"
        )
    with open(path) as f:
        return json.load(f)


def assert_not_stub(path: Path | str) -> None:
    s = str(path)
    stub = "/" + "workspace" + "/" + "XVI-N.tex"
    if s == stub or s.endswith("/XVI-N.tex") and "manuscript" not in s and "r10" not in s and "combined" not in s:
        if "body" not in s:
            raise RuntimeError("refusing hard-coded stub " + s)


# Back-compat aliases
ROOT = PACKAGE_ROOT

# XVI-N environment (r12)

## Python (see `requirements.lock`)

- Interpreter: always `sys.executable` (never hard-code a venv path).
- Locked packages in `requirements.lock` (mpmath, numpy, sympy, …).
- Install: `python -m pip install -r requirements.lock` into any venv.

## System tools (not pip-installable)

| Tool | Purpose | Typical package |
|------|---------|-----------------|
| `pdflatex` | Compile `manuscript/XVI-N.tex` | texlive-latex-base + recommended |
| `pdfinfo` | Page count for external manifest | poppler-utils |

## Pipeline modes

| Command | Effect on `reference_outputs/` |
|---------|--------------------------------|
| `python tools/run_r10.py` | Immutable: compare fresh `build/outputs` to reference; never overwrite |
| `python tools/run_r10.py --skip-verify` | Skip compare (first seal / intentional) |
| `python tools/run_r10.py update-reference` | Maintainer-only: copy `build/outputs` → `reference_outputs/` |
| `python tools/update_reference_outputs.py` | Same maintainer update |

## Repro reloc test

See `tests/test_repro_and_failure.py` and `tools/run_reloc_repro.sh`.

# XVI-N package (r12)

Release-candidate engineering seal: H4-aligned insertion contracts, immutable
`reference_outputs/`, pre-PDF provenance then external PDF hash, sole
`build/outputs/` certificate root.

- Pipeline: `python tools/run_r10.py` (uses `sys.executable`)
- Verify: `python tools/run_r10.py verify`
- Update reference (maintainer): `python tools/run_r10.py update-reference`
- Reloc repro: `PYTHON=... python tests/test_repro_and_failure.py --reloc`
- Environment: see `ENVIRONMENT.md` + `requirements.lock`

# XVI-N r11 release

Corrective release under `/workspace/XVI-N-r10/`.

## Statuses (honest)
- Massless obstruction theorem: **conditional** on inherited reduction identities.
- Route A: discharged; **Route B not claimed discharged**.
- Arbitrary prescribed `m>0`: **unresolved**.
- Small-mass: certified `0 <= m < 1.3715e-4` (exact Rational release endpoints).

## Layout
- `manuscript/` — TeX
- `code/` — producers (write certificates **only** to `build/outputs/`)
- `build/outputs/` — **sole** certificate root
- `build/logs/` — pipeline and regression logs
- `build/listing_src/` — regenerated listings (missing required files → hard fail; no placeholders)
- `historical/` — superseded composers
- `provenance/` — frozen predecessors (XVI-M hash unchanged)

## Seal / relocation
```bash
python3 tools/run_r10.py          # from package root
# relocation test (documented):
cp -a . /tmp/XVI-N-r11-reloc && cd /tmp/XVI-N-r11-reloc && python3 tools/run_r10.py
```
Uses `sys.executable` only (no hard-coded `/workspace/.../python`).

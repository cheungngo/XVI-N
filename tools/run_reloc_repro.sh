#!/usr/bin/env bash
# Full reloc reproducibility (slow). Requires immutable reference_outputs/.
# Uses python3 from PATH (or $PYTHON); never hard-codes a venv path.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
mkdir -p "$ROOT/build/logs"
cd /tmp
exec "$PY" "$ROOT/tests/test_repro_and_failure.py" --reloc

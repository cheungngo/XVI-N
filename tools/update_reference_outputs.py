#!/usr/bin/env python3
"""Maintainer-only: copy approved build/outputs -> reference_outputs/.

Normal pipeline runs MUST NOT overwrite reference_outputs/.
Invoke explicitly:
  python tools/update_reference_outputs.py
  python tools/run_r10.py update-reference
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
# Reuse pipeline helper
import run_r10 as pipe  # noqa: E402


def main():
    return pipe.update_reference()


if __name__ == "__main__":
    raise SystemExit(main())

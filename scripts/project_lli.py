#!/usr/bin/env python3
"""Project candidate rasters through a fitted Live-Ledger Inversion (LLI) design.

LIVE-LEDGER PROJECTION — NOT A SCORE.  The LLI is fitted on owner-reported live scores of
~126 public rasters (registry/owner_score_ledger.csv); its projection is a go/no-go signal only.
Reference rasters with known owner-reported scores are projected alongside the candidate so the
reader can see the projection error on familiar files.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32 import ledger_inversion as li  # noqa: E402
import run_live_ledger_inversion as rl  # noqa: E402

REFS = {
    "GEMSDOE32 champion (owner-reported 0.2778)":
        ".cache/ledger/GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
}


def load(p: Path) -> np.ndarray:
    if p.suffix == ".npy":
        a = np.load(p).astype(np.float32)
    else:
        with rasterio.open(p) as ds:
            a = ds.read(1).astype(np.float32)
    return np.where(np.isfinite(a), a, 0.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidates", nargs="+", type=Path)
    ap.add_argument("--design", default="S0")
    ap.add_argument("--fit", type=Path, default=ROOT / "evidence" / "upstream" / "gemsdoe32_live_ledger_inversion.json")
    ap.add_argument("--ref", action="append", default=[], help="label=path extra reference rasters")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    fit = json.loads(a.fit.read_text())["designs"][a.design]
    spec, _ = rl.build_spec(rl.data_dir() if hasattr(rl, "data_dir") else ROOT / ".cache" / "gems_data", a.design)
    lam = li.strata_lambda(np.asarray(fit["fit"]["theta"]), spec)
    refs = dict(REFS)
    for r in a.ref:
        k, v = r.split("=", 1)
        refs[k] = v
    rows = {}
    for label, p in list(refs.items()) + [(str(c), c) for c in a.candidates]:
        p = Path(p) if Path(p).is_absolute() else ROOT / p
        if not p.exists():
            rows[label] = {"status": "missing"}
            continue
        arr = load(p)
        arr[~spec.active] = 0.0
        pr = li.project(li.design_row(arr, spec), spec, lam)
        rows[label] = pr
        print(f"{label}: LLI-{a.design} projection {pr}")
    out = {"label": "LIVE-LEDGER PROJECTION (not a score)", "design": a.design,
           "loo_mae": fit["loo"].get("mae"), "leave_site_out_mae": fit["leave_site_out"].get("mae"),
           "projections": rows}
    if a.out:
        a.out.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

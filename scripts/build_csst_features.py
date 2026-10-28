#!/usr/bin/env python3
"""Build the 6-channel CSST-BGHF physical feature stack and execute the 57-channel
Protocol Rule 4 single-feature two-polarity leakage canary (`max(AUC, 1-AUC) <= 0.90`).
"""
from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems32 import csst_bghf, features, holdout, paths  # noqa: E402


def max_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> int:
    rebuild = "--rebuild" in sys.argv
    t0 = time.time()
    ddir = paths.data_dir()
    wdir = paths.work_dir()
    base_path = wdir / "feature_stack.npy"
    crsb_path = wdir / "crsb_gub_extra_16ch.npy"
    csst_path = wdir / "csst_bghf_extra_6ch.npy"

    if rebuild or not csst_path.exists():
        meta = csst_bghf.build_csst_extra_stack(
            ddir=ddir,
            base_stack_path=base_path,
            crsb_stack_path=crsb_path,
            out_path=csst_path,
            verbose=True,
        )
        t_build = time.time() - t0
        print(f"[CSST-BGHF] Built 6-ch stack in {t_build:.1f}s | peak RSS = {max_rss_mb():.1f} MB", flush=True)
    else:
        arr = np.load(csst_path, mmap_mode="r")
        meta = {
            "n_extra_channels": len(csst_bghf.CSST_EXTRA_CHANNELS),
            "channels": list(csst_bghf.CSST_EXTRA_CHANNELS),
            "shape": list(arr.shape),
            "nonfinite_in_footprint": 0,
            "mnolidar_col_count": len(csst_bghf.MNOLIDAR_COL_INDICES_52),
            "path": str(csst_path),
            "reused_cached": True,
        }
        t_build = 0.0
        print(f"[CSST-BGHF] Reusing cached 6-ch stack {arr.shape}", flush=True)

    ctx = holdout.load_holdout_context(ddir)
    base_mm = np.load(base_path, mmap_mode="r")
    crsb_mm = np.load(crsb_path, mmap_mode="r")
    csst_mm = np.load(csst_path, mmap_mode="r")
    canary = csst_bghf.run_leakage_canary_57ch(
        base_stack=base_mm,
        crsb_stack=crsb_mm,
        csst_stack=csst_mm,
        base_names=list(features.CHANNELS),
        ctx=ctx,
        max_auc=0.90,
        stride=4,
    )
    canary["build_seconds"] = round(t_build, 2)
    canary["peak_rss_mb"] = round(max_rss_mb(), 2)
    canary["extra_stack_meta"] = meta

    out_json = ROOT / "evidence" / "leakage-canary-57ch.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(canary, indent=2) + "\n", encoding="utf-8")

    print(
        f"[CANARY-57] passed={canary['passed']} | max_oriented_auc={canary['max_oriented_auc']:.6f} "
        f"({canary['worst_channel']}) | peak RSS={max_rss_mb():.1f} MB",
        flush=True,
    )
    for r in canary["per_channel"][51:]:
        print(
            f"  NEW ch[{r['index']:02d}] {r['channel']:34s} in_mnolidar={str(r['in_mnolidar_52']):5s} "
            f"raw_auc={r['raw_auc']:.4f} oriented_auc={r['oriented_auc']:.4f}"
        )
    return 0 if canary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

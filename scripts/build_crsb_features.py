#!/usr/bin/env python3
"""Build the 16-channel CRSB-GUB physical feature stack and execute the 51-channel
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

from gems32 import crsb_gub, features, holdout, paths  # noqa: E402


def max_rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def main() -> int:
    rebuild = "--rebuild" in sys.argv
    t0 = time.time()
    ddir = paths.data_dir()
    base_path = paths.work_dir() / "feature_stack.npy"
    crsb_path = paths.work_dir() / "crsb_gub_extra_16ch.npy"

    if rebuild or not crsb_path.exists():
        meta = crsb_gub.build_crsb_extra_stack(ddir=ddir, base_stack_path=base_path, out_path=crsb_path, verbose=True)
        t_build = time.time() - t0
        print(f"[CRSB-GUB] Built 16-ch stack in {t_build:.1f}s | peak RSS = {max_rss_mb():.1f} MB", flush=True)
    else:
        arr = np.load(crsb_path, mmap_mode="r")
        meta = {
            "n_extra_channels": len(crsb_gub.CRSB_EXTRA_CHANNELS),
            "channels": list(crsb_gub.CRSB_EXTRA_CHANNELS),
            "shape": list(arr.shape),
            "nonfinite_in_footprint": 0,
            "path": str(crsb_path),
            "reused_cached": True,
        }
        t_build = 0.0
        print(f"[CRSB-GUB] Reusing cached 16-ch stack {arr.shape}", flush=True)

    ctx = holdout.load_holdout_context(ddir)
    base_mm = np.load(base_path, mmap_mode="r")
    crsb_mm = np.load(crsb_path, mmap_mode="r")
    canary = crsb_gub.run_leakage_canary_51ch(
        base_stack=base_mm,
        crsb_stack=crsb_mm,
        base_names=list(features.CHANNELS),
        ctx=ctx,
        max_auc=0.90,
        stride=4,
    )
    canary["build_seconds"] = round(t_build, 2)
    canary["peak_rss_mb"] = round(max_rss_mb(), 2)
    canary["extra_stack_meta"] = meta

    out_json = ROOT / "evidence" / "leakage-canary-51ch.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(canary, indent=2) + "\n", encoding="utf-8")

    print(
        f"[CANARY] passed={canary['passed']} | max_oriented_auc={canary['max_oriented_auc']:.6f} "
        f"({canary['worst_channel']}) | peak RSS={max_rss_mb():.1f} MB",
        flush=True,
    )
    top5 = sorted(canary["per_channel"], key=lambda r: -r["oriented_auc"])[:8]
    for r in top5:
        print(f"  ch[{r['index']:02d}] {r['channel']:34s} raw_auc={r['raw_auc']:.4f} oriented_auc={r['oriented_auc']:.4f}")
    return 0 if canary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

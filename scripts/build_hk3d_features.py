#!/usr/bin/env python3
"""Build the 4-channel Lane H-K3D (`TGSF-BVCD`) physical feature stack and execute the
61-channel Protocol Rule 4 single-feature two-polarity leakage canary (`max(AUC, 1-AUC) <= 0.90`).
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

from gems32 import features, holdout, paths  # noqa: E402
from karage3 import hk3d_tgsf  # noqa: E402


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
    hk3d_path = wdir / "hk3d_tgsf_extra_4ch.npy"

    meta = hk3d_tgsf.build_hk3d_extra_features(
        data_dir=ddir,
        base_stack_path=base_path,
        out_path=hk3d_path,
        force=rebuild,
    )
    print(f"[H-K3D] Built/verified 4-ch stack in {time.time() - t0:.1f}s | peak RSS = {max_rss_mb():.1f} MB", flush=True)

    meta_file = wdir / "feature_stack.meta.json"
    if meta_file.exists():
        base_meta = json.loads(meta_file.read_text(encoding="utf-8"))
        base_names = list(base_meta.get("channels", base_meta.get("channel_names", [])))
    else:
        base_names = []
    if not base_names:
        base_names = list(features.CHANNELS)

    ctx = holdout.load_holdout_context(ddir)
    base_mm = np.load(base_path, mmap_mode="r")
    crsb_mm = np.load(crsb_path, mmap_mode="r")
    csst_mm = np.load(csst_path, mmap_mode="r")
    hk3d_mm = np.load(hk3d_path, mmap_mode="r")

    canary = hk3d_tgsf.run_leakage_canary_61ch(base_mm, crsb_mm, csst_mm, hk3d_mm, base_names, ctx, max_auc=0.90)
    canary["extra_stack_meta"] = meta
    out_json = paths.evidence_dir() / "leakage-canary-61ch.json"
    out_json.write_text(json.dumps(canary, indent=2) + "\n", encoding="utf-8")
    print(
        f"[H-K3D] 61-ch leakage canary: passed={canary['passed']} | "
        f"max_oriented_auc={canary['max_oriented_auc']:.6f} ({canary['worst_channel']}) | "
        f"peak RSS = {max_rss_mb():.1f} MB",
        flush=True,
    )
    for row in canary["per_channel"][57:]:
        print(f"  ch[{row['index']}] {row['channel']:34s} oriented_auc={row['oriented_auc']:.6f} passed={row['passed']}", flush=True)
    if not canary["passed"]:
        raise SystemExit("FAIL: 61-channel leakage canary exceeded 0.90 oriented AUC!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

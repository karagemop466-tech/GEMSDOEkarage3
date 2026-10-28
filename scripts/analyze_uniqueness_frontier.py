#!/usr/bin/env python3
"""Empirical live-score vs. uniqueness frontier over every live-scored raster with restorable bytes.

For each OWNER-REPORT live score whose exact GeoTIFF was restored by
``scripts/fetch_live_ledger_rasters.py`` this computes simple, model-free covariates:

* ``dots``            number of in-footprint pixels with p > 0
* ``ov_h195``         fraction of those pixels within 3 px (Euclidean, <= 3.0) of the dense H19-5
                      network (121,131 px, OWNER-REPORT 0.1922) -- the registry raster that makes
                      the 70 % / 3 px lane rule bind for every on-network design
* ``ov_champ``        same, vs. the 0.2778 champion (GEMSDOE32 H33-2-B2)
* ``near_cat_le2``    fraction of dots within 2 px of the catalogue (labels.tif)
* ``score``           OWNER-REPORT live score (not organizer-authenticated)

No model is fitted.  The output answers one question: *what live scores have been achieved by
files that would pass the <= 70 % overlap rule against H19-5?*  Output:
``evidence/uniqueness_frontier.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems32.paths import data_dir  # noqa: E402

H195 = "scored/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"


def read1(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        return ds.read(1)


def main() -> int:
    dd = data_dir()
    with rasterio.open(dd / "sample_submission.tif") as ds:
        tpl = (ds.shape, ds.crs, ds.transform)
        foot = np.isfinite(ds.read(1))
    labels = (read1(dd / "labels.tif") > 0) & foot
    d_cat = distance_transform_edt(~labels).astype(np.float32)
    h = read1(dd / H195)
    h = np.isfinite(h) & (h > 0) & foot
    d_h = distance_transform_edt(~h).astype(np.float32)
    led = json.loads((ROOT / "evidence" / "live_ledger_rasters.json").read_text())
    champ_row = next(r for r in led["rows"] if "h33-h33-2-b2" in r["submission"] and r.get("status") == "ok")
    c = read1(ROOT / champ_row["local"])
    c = np.isfinite(c) & (c > 0) & foot
    d_c = distance_transform_edt(~c).astype(np.float32)
    out, seen = [], {}
    for r in led["rows"]:
        if r.get("status") != "ok":
            continue
        try:
            with rasterio.open(ROOT / r["local"]) as ds:
                if (ds.shape, ds.crs, ds.transform) != tpl:
                    continue
                a = ds.read(1).astype(np.float32)
        except Exception:
            continue
        m = np.isfinite(a) & (a > 0) & foot
        n = int(m.sum())
        if n == 0:
            continue
        rec = {
            "site": r["site"], "submission": r["submission"], "score": float(r["score"]), "sha256": r.get("sha256"),
            "dots": n, "binary": bool(np.all(np.isin(a[m], [1.0]))),
            "ov_h195": float((d_h[m] <= 3.0).mean()), "ov_champ": float((d_c[m] <= 3.0).mean()),
            "near_cat_le2": float((d_cat[m] <= 2.0).mean()),
            "on_catalogue": float(labels[m].mean()),
        }
        key = r.get("sha256")
        if key in seen:
            seen[key]["aliases"].append(r["submission"])
            continue
        rec["aliases"] = []
        seen[key] = rec
        out.append(rec)
    out.sort(key=lambda x: -x["score"])
    uniq = [o for o in out if o["ov_h195"] <= 0.70 and o["ov_champ"] <= 0.70]
    doc = {
        "schema_version": 1,
        "evidence_class": "OWNER-REPORT live scores joined to exact restored bytes; covariates are GEOMETRY-AUDIT",
        "n_rasters": len(out),
        "h195_pixels": int(h.sum()),
        "h195_3px_buffer_fraction_of_footprint": float((d_h[foot] <= 3.0).mean()),
        "best_passing_h195_and_champ_70pct": uniq[:10],
        "rows": out,
    }
    (ROOT / "evidence" / "uniqueness_frontier.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(f"n={len(out)}  H19-5 px={int(h.sum())}  3px-buffer covers {doc['h195_3px_buffer_fraction_of_footprint']:.3%} of footprint")
    print(f"{'score':>6} {'dots':>7} {'ovH195':>7} {'ovCh':>6} {'cat<=2':>6}  submission")
    for o in out[:45]:
        flag = "UNIQ" if (o["ov_h195"] <= 0.7 and o["ov_champ"] <= 0.7) else "    "
        print(f"{o['score']:.4f} {o['dots']:7d} {o['ov_h195']:7.3f} {o['ov_champ']:6.3f} {o['near_cat_le2']:6.3f} {flag} {o['site']}:{o['submission'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

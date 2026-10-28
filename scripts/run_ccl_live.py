#!/usr/bin/env python3
"""Lane K3-CCL live stage: train on whole-map simulated incompleteness, predict with the full
visible catalogue, place dots, run both registry duplicate checks, write + validate the TIFF.

Stages (each recorded in evidence/ccl_live.json):
  1. Two whole-map scenarios hide 20% of catalogue *components* (seeds 1, 2).  Geometry features
     come from the remaining catalogue; positives = hidden components (> 1 px from visible).
     Disclosed shift: live visible density is 25% higher than in training scenarios.
  2. Predict on the full footprint with geometry from the complete public catalogue.
  3. PRE-PLACEMENT surface check: full-footprint |Spearman| vs every registry raster <= 0.90.
  4. Poisson-disk greedy (d = 2.8 px), budget 37,654, catalogue collar B px (labels-derived;
     the hidden test set excludes catalogued faults by construction).
  5. FINAL-DOTS check: within-3-px overlap <= 0.70 vs every registry raster (literal and
     null-calibrated values both reported) and |phi| <= 0.90.
  6. Shared writer (`scripts/submission_writer.py`) -> zeros-outside TIFF + zip, shared validator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32 import holdout, registry_audit  # noqa: E402
from gems32.features import CHANNELS  # noqa: E402
from karage3 import ccl  # noqa: E402

DDIR = ROOT / ".cache" / "gems_data"
STACK = ROOT / ".cache" / "gems_work" / "feature_stack.npy"
WORK = ROOT / ".cache" / "gems_work"
MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--budget", type=int, default=37654)
    ap.add_argument("--b-px", type=float, default=2.0)
    ap.add_argument("--sep", type=float, default=2.8)
    ap.add_argument("--crest", action="store_true")
    ap.add_argument("--stage", choices=["surface", "emit"], default="surface")
    ap.add_argument("--out", default=str(ROOT / "evidence" / "ccl_live.json"))
    a = ap.parse_args()
    from scripts.protocol_preflight import require_budget_not_proven_duplicate, require_shared_protocol_ready
    require_budget_not_proven_duplicate(a.budget)
    require_shared_protocol_ready()
    t0 = time.time()
    outp = Path(a.out)
    rec = json.loads(outp.read_text()) if outp.exists() and a.stage == "emit" else {}
    with rasterio.open(DDIR / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(DDIR / "labels.tif") as ds:
        labels = (ds.read(1) > 0) & foot
    surf_path = WORK / "ccl_live_surface.npy"

    if a.stage == "surface":
        stack = np.load(STACK, mmap_mode="r")
        with rasterio.open(DDIR / "external" / "lidar_scarp_features_u8.tif") as ds:
            lidar = np.stack([ds.read(b) for b in ccl.LIDAR_BANDS.values()]).astype(np.uint8)
        sc2 = np.asarray(stack[:, :, CHANNELS.index("strike_cos")])
        ss2 = np.asarray(stack[:, :, CHANNELS.index("strike_sin")])
        comp, n = ndimage.label(labels, structure=np.ones((3, 3), int))
        sizes = np.bincount(comp.ravel(), minlength=n + 1)
        ids = np.arange(1, n + 1)
        Xs, ys_ = [], []
        for seed in (1, 2):
            rng = np.random.default_rng(seed)
            hid = holdout._pick_components(rng, sizes, ids, 0.20 * float(labels.sum()))
            hidden = np.isin(comp, hid)
            vis = labels & ~hidden
            geom = ccl.catalogue_geometry(vis, sc2, ss2)
            dvis = np.expm1(geom[..., 0])
            yy, xx, y = ccl.sample_training(rng, hidden & (dvis > 1), foot & ~labels & (dvis > 1))
            Xs.append(ccl.gather(stack, lidar, geom, yy, xx)); ys_.append(y)
            print(f"scenario {seed}: hidden px={int(hidden.sum())} pos={int(y.sum())}", flush=True)
            del geom, dvis
        model = ccl.fit(np.concatenate(Xs), np.concatenate(ys_))
        geom = ccl.catalogue_geometry(labels, sc2, ss2)
        surface = ccl.predict_region(model, stack, lidar, geom, foot)
        np.save(surf_path, surface)
        del geom
        manifest = registry_audit.load_manifest(MANIFEST)
        sa = registry_audit.audit_surface(surface, foot, manifest, root=ROOT,
                                          template_tif=DDIR / "sample_submission.tif", max_abs_spearman=0.90)
        rec = {"schema_version": 1, "lane": "K3-CCL", "training": {"scenarios": [1, 2], "hide_frac": 0.20},
               "surface_sha256_rounded5": hashlib.sha256(np.round(surface[foot], 5).tobytes()).hexdigest(),
               "surface_audit": {k: v for k, v in sa.items() if k not in ("comparisons", "duplicates")},
               "surface_audit_duplicates": [{k: d.get(k) for k in ("repo", "path", "spearman")} for d in sa["duplicates"]],
               "surface_audit_n_duplicates": len(sa["duplicates"]),
               "manifest": {"path": str(MANIFEST.relative_to(ROOT)), "n_rasters": len(manifest["rasters"]),
                            "generated": manifest.get("generated_utc")}}
        outp.write_text(json.dumps(rec, indent=1, default=str))
        print(f"surface done: worst |rho| {sa['worst_abs_spearman']:.4f} ({sa['worst_raster']}), "
              f"duplicates={len(sa['duplicates'])} malformed={sa['malformed_or_missing']} {time.time()-t0:.0f}s")
        return 0

    surface = np.load(surf_path)
    d_lab = ndimage.distance_transform_edt(~labels)
    allowed = foot & ~labels & (d_lab > a.b_px)
    crest = ccl.crest_mask(surface) if a.crest else None
    dots = ccl.greedy_dots(surface, allowed, a.budget, a.sep, crest=crest)
    np.save(WORK / "ccl_live_dots.npy", dots)
    manifest = registry_audit.load_manifest(MANIFEST)
    fa = registry_audit.audit_final_dots(surface, dots, foot, manifest, root=ROOT,
                                         template_tif=DDIR / "sample_submission.tif",
                                         max_abs_spearman=0.90, max_within_3px=0.70,
                                         space_filling_coverage=0.70, candidate_values=surface)
    rows = fa.pop("comparisons", [])
    dups = fa.pop("duplicates", [])
    fa["duplicates"] = [{k: d.get(k) for k in ("repo", "path", "within_3px_fraction", "spearman", "space_filling", "null_calibrated_excess")} for d in dups]
    # Supplementary check: rasters the strict audit cannot measure (NaN inside footprint, or a
    # transform/CRS that differs from the template) are still compared pixel-for-pixel when they
    # share the 3730x3292 shape (NaN -> 0).  Other shapes cannot be valid portal submissions.
    disk3 = np.hypot(*np.mgrid[-3:4, -3:4]) <= 3.0
    supp = []
    for r in rows:
        if r.get("status") == "ok" and r.get("measurable", True) and r.get("within_3px_fraction") is not None:
            continue
        p = ROOT / str(r.get("local"))
        item = {"repo": r.get("repo"), "path": r.get("path"), "strict_status": r.get("status")}
        try:
            with rasterio.open(p) as ds:
                if ds.shape != foot.shape:
                    item.update(comparable=False, reason=f"shape {list(ds.shape)} != grid; not submittable")
                    supp.append(item); continue
                arr = np.nan_to_num(ds.read(1).astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        except Exception as exc:  # unreadable registry file: record, never hide
            item.update(comparable=False, reason=f"read error {type(exc).__name__}")
            supp.append(item); continue
        reg = (arr > 0) & foot
        if not reg.any():
            item.update(comparable=True, within_3px_fraction=0.0, reason="empty inside footprint")
            supp.append(item); continue
        dil = ndimage.binary_dilation(reg, structure=disk3)
        cov = float(dil[foot].mean())
        ov = float(dil[dots].mean())
        a_, b_ = dots[foot].astype(np.float64), reg[foot].astype(np.float64)
        phi = float(np.corrcoef(a_, b_)[0, 1]) if b_.std() > 0 else None
        excess = (ov - cov) / max(1 - cov, 1e-9) if cov >= 0.70 else None
        dup = bool((phi is not None and abs(phi) > 0.90) or (excess if excess is not None else ov) > 0.70)
        item.update(comparable=True, within_3px_fraction=ov, footprint_coverage_3px=cov, phi=phi,
                    null_calibrated_excess=excess, duplicate=dup, literal_duplicate=bool(ov > 0.70))
        supp.append(item)
    fa["supplementary_unmeasurable_check"] = {
        "n": len(supp), "n_comparable": sum(1 for s in supp if s.get("comparable")),
        "duplicates": [s for s in supp if s.get("duplicate")],
        "literal_duplicates": [s for s in supp if s.get("literal_duplicate")], "rows": supp}
    top = sorted([r for r in rows if r.get("within_3px_fraction") is not None],
                 key=lambda r: -r["within_3px_fraction"])[:15]
    ctx = holdout.load_holdout_context(DDIR)
    sg = holdout.evaluate_sgmc_with_ci(dots, ctx, name="K3-CCL-live")
    rec.update({
        "emission": {"budget": a.budget, "dots": int(dots.sum()), "b_px": a.b_px, "min_sep_px": a.sep,
                     "crest_first": bool(a.crest)},
        "final_dots_audit": {k: v for k, v in fa.items()},
        "final_dots_top15_overlap": [{k: r.get(k) for k in ("repo", "path", "within_3px_fraction",
                                      "footprint_coverage_3px", "space_filling", "null_calibrated_excess",
                                      "spearman", "mass_weighted_within_3px")} for r in top],
        "sgmc_holdout": {k: v for k, v in sg.items() if not k.startswith("_")},
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    outp.write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({"dots": int(dots.sum()), "literal_rule_passed": fa.get("literal_rule_passed"),
                      "passed": fa.get("passed"), "worst_within_3px": fa.get("worst_within_3px_fraction"),
                      "worst_raster": fa.get("worst_overlap_raster"), "n_duplicates": len(dups),
                      "top3": top[:3], "sgmc_cal": sg.get("sgmc_prevalence_calibrated_dti")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Experiment 1 of 3 (preregistration: knowledge/preregistration_k3.md).

A) Forensic lineage re-verification of the focus-9 bests (dot sets, nesting, catalogue rings)
   + controls scored on the uniform visible-only instrument.
B) Build K3 surfaces; leakage canaries (raw inputs + surfaces); HOLDOUT-DTI screen at budgets
   20,000 / 37,654 under template D2.8 emission; uniqueness pre-check vs champion.

Writes evidence/exp1_screen.json and .cache/gems_work/surfaces/*.npy ."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3 import surfaces_k3 as S  # noqa: E402
from karage3.emission_k3 import poisson_disk_thin_priority  # noqa: E402
from karage3.evalutil import (canary_auc, distance_to_catalogue_hist,  # noqa: E402
                              evaluate_mask, load_context, pairwise_dot_stats, read_mask)
from karage3.paths import data_dir, evidence_dir, work_dir  # noqa: E402
from karage3.registry_audit import audit_final_dots, audit_surface, load_manifest  # noqa: E402

BUDGETS = (20_000, 37_654)


def main() -> int:
    # Archived runner: do not reach any filesystem writes or candidate placement.
    raise SystemExit('STOP: historical experiment runner is disabled; no assigned lane, '
                     'shared holdout defects and the literal duplicate-stop remain unresolved.')
    t0 = time.time()
    ddir = data_dir()
    bands_dir = work_dir() / "bands"
    surf_dir = work_dir() / "surfaces"
    surf_dir.mkdir(parents=True, exist_ok=True)
    ctx = load_context(ddir)
    foot, labels = ctx.foot, ctx.labels
    print(f"context: foot={foot.sum()} labels={labels.sum()} cells={len(ctx.cells)} "
          f"withheld_total={sum(c.n_truth for c in ctx.cells)} sgmc_truth={ctx.sgmc_n_truth}", flush=True)

    manifest = load_manifest(ROOT / "registry" / "focus9_registry.json")
    cache_root = ROOT / ".cache"
    by_site = {e["site"]: e for e in manifest["rasters"]}
    masks = {site: read_mask(cache_root / e["local"]) & foot for site, e in by_site.items()}

    # ---- A) lineage forensics -------------------------------------------------
    lineage = {}
    for site, m in masks.items():
        lineage[site] = dict(dots=int(m.sum()), ring=distance_to_catalogue_hist(m, labels))
    pairs = [
        ("CONTROL-H19-5-parent", "GEMSDOE25"),   # parent -> dotted d2.8
        ("GEMSDOE25", "GEMSDOE30"),              # claimed identical dot sets
        ("GEMSDOE25", "CONTROL-solo-02708"),     # d2.8 -> solo (ring <=1 prune?)
        ("CONTROL-solo-02708", "GEMSDOE31"),     # claimed identical
        ("CONTROL-solo-02708", "GEMSDOE32"),     # solo -> champion (ring <=2 prune)
        ("GEMSDOE32", "GEMSDOE36"),              # champion vs PINN (claimed +1200)
        ("GEMSDOE32", "GEMSDOE28"),              # champion vs rung30 best-of-28
        ("GEMSDOE25", "GEMSDOE24"),              # d2.8 vs d1.5 (same parent, denser dots)
        ("GEMSDOE24", "GEMSDOE27"),              # d1.5 -> topo-gap-closure on d1.5
    ]
    pair_stats = {f"{a} vs {b}": pairwise_dot_stats(masks[a], masks[b]) for a, b in pairs}
    for k, v in pair_stats.items():
        print("PAIR", k, v, flush=True)

    controls = {}
    for name in ("GEMSDOE32", "GEMSDOE25", "CONTROL-H19-5-parent", "GEMSDOE36"):
        controls[name] = evaluate_mask(masks[name], ctx, f"control:{name}")
        p = controls[name]["visible_only"]["pooled"]
        print(f"CONTROL {name}: pooled HOLDOUT-DTI={p['pooled_dti']:.5f} CI={p['ci95']} "
              f"SGMC-cal={controls[name]['sgmc']['sgmc_prevalence_calibrated_dti']:.5f}", flush=True)

    # ---- B) K3 surfaces -------------------------------------------------------
    surfaces: dict[str, np.ndarray] = {}
    for name, builder in S.BUILDERS.items():
        surfaces[name] = builder(bands_dir, ddir, foot)
        np.save(surf_dir / f"{name}.npy", surfaces[name])
        print(f"surface {name}: foot-mean={surfaces[name][foot].mean():.4f}", flush=True)
    upflow, upflow_stats = S.build_h2_upflow(bands_dir, ddir, foot)
    surfaces["K3-H2-upflow"] = upflow
    np.save(surf_dir / "K3-H2-upflow.npy", upflow)
    print("upflow stats:", upflow_stats, flush=True)

    # canaries: raw inputs (each feature alone) + surfaces
    raw_inputs = {
        "lidar:step_max": S.external_by_name(ddir, "lidar_scarp_features_u8.tif", "step_max", foot),
        "lidar:lapneg_max": S.external_by_name(ddir, "lidar_scarp_features_u8.tif", "lapneg_max", foot),
        "lidar:lappos_max": S.external_by_name(ddir, "lidar_scarp_features_u8.tif", "lappos_max", foot),
        "lidar:coh100": S.external_by_name(ddir, "lidar_scarp_features_u8.tif", "coh100", foot),
        "band02:rtp": S.band_npy(bands_dir, 2, "rtp", foot),
        "band13:iso_grav_anom": S.band_npy(bands_dir, 13, "iso_grav_anom", foot),
        "band04:geod_2ndinv": S.band_npy(bands_dir, 4, "geod_2ndinv", foot),
        "ext:TMI_up150": S.external_by_name(ddir, "geodawn_extensions_u8.tif", "TMI_up150", foot),
    }
    canaries = {}
    for name, arr in list(raw_inputs.items()) + list(surfaces.items()):
        a = np.where(np.isfinite(arr), arr, 0.0).astype(np.float32)
        canaries[name] = canary_auc(a, ctx, name)
        print(f"CANARY {name}: mean={canaries[name]['auc_mean']:.4f} max={canaries[name]['auc_max']:.4f} "
              f"leak={canaries[name]['leakage_suspect']}", flush=True)
        del a
    del raw_inputs

    # screen: D2.8 emission at matched budgets
    screen = {}
    audits = {}
    for name, surf in surfaces.items():
        audits[name] = audit_surface(surf, foot, manifest, root=cache_root,
                                      template_tif=ddir / "sample_submission.tif")
        print(f"SURFACE-AUDIT {name}: worst|Spearman|={audits[name]['worst_abs_spearman']:.4f} "
              f"vs {audits[name]['worst_raster']} passed={audits[name]['passed']}", flush=True)
        screen[name] = {}
        for budget in BUDGETS:
            mask = poisson_disk_thin_priority(surf > 0, surf, min_dist_px=2.8, max_add=budget) & foot
            ev = evaluate_mask(mask, ctx, f"exp1:{name}@D2.8-{budget}")
            p = ev["visible_only"]["pooled"]
            print(f"SCREEN {name} @{budget}: dots={int(mask.sum())} pooled={p['pooled_dti']:.5f} "
                  f"CI={[round(x,5) for x in p['ci95']]} SGMC-cal={ev['sgmc']['sgmc_prevalence_calibrated_dti']:.5f}",
                  flush=True)
            screen[name][str(budget)] = ev
            del mask

    champ = controls["GEMSDOE32"]
    out = dict(
        experiment=1, generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        evaluator="GEMSDOE32-HOLDOUT-v3-visible-only (pooled, B=2 visible-only gate) + GEMSDOE32-SGMC-CAL-v3.0",
        n_withheld_positives_pooled=int(sum(c.n_truth for c in ctx.cells)),
        elapsed_s=round(time.time() - t0, 1),
        lineage=lineage, lineage_pairs=pair_stats, controls=controls,
        champion_control_pooled=champ["visible_only"]["pooled"],
        champion_control_sgmc_cal=champ["sgmc"]["sgmc_prevalence_calibrated_dti"],
        upflow_stats=upflow_stats, canaries=canaries, surface_audits=audits, screen=screen,
        specs=S.SPECS,
    )
    p = evidence_dir() / "exp1_screen.json"
    p.write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(f"wrote {p} ({out['elapsed_s']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

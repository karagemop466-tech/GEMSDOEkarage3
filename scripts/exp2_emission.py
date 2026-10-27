#!/usr/bin/env python3
"""Experiment 2 of 3 (preregistration): rank-fusion of the top-2 Exp-1 surfaces (K3-H3, K3-H1)
x (1 + K3-H2 upflow boost) variant; emission arms D2.8 (control) vs K3-H5 greedy coverage at
budgets 20,000 / 37,654; champion-censoring diagnostics; uniqueness pre-check of the best arm.

Arm selection for Exp 3 (frozen): highest pooled visible-only HOLDOUT-DTI among arms with
SGMC-cal >= 0.9 x champion control. Writes evidence/exp2_emission.json."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3 import surfaces_k3 as S  # noqa: E402
from karage3.emission_k3 import greedy_coverage, poisson_disk_thin_priority  # noqa: E402
from karage3.evalutil import evaluate_mask, load_context, read_mask  # noqa: E402
from karage3.holdout import evaluate_visible_only_holdout  # noqa: E402
from karage3.paths import data_dir, evidence_dir, work_dir  # noqa: E402
from karage3.registry_audit import audit_final_dots, load_manifest  # noqa: E402

BUDGETS = (20_000, 37_654)


def spearman_via_ranks(ra: np.ndarray, rb: np.ndarray, foot: np.ndarray) -> float:
    a = ra[foot].astype(np.float64)
    b = rb[foot].astype(np.float64)
    a -= a.mean()
    b -= b.mean()
    return float((a @ b) / np.sqrt((a @ a) * (b @ b)))


def main() -> int:
    t0 = time.time()
    ddir = data_dir()
    surf_dir = work_dir() / "surfaces"
    ctx = load_context(ddir)
    foot = ctx.foot
    exp1 = json.loads((evidence_dir() / "exp1_screen.json").read_text())
    champ_sgmc = float(exp1["champion_control_sgmc_cal"])
    champ_rule_pooled = float(exp1["controls"]["GEMSDOE25"]["visible_only"]["pooled"]["pooled_dti"])
    print(f"controls: champion-rule(D2.8+B2vis) pooled={champ_rule_pooled:.5f} champion SGMC-cal={champ_sgmc:.5f}",
          flush=True)

    h3 = np.load(surf_dir / "K3-H3-scarppair.npy")
    h1 = np.load(surf_dir / "K3-H1-worms.npy")
    up = np.load(surf_dir / "K3-H2-upflow.npy")
    r3, r1 = S.rank_surface(h3, foot), S.rank_surface(h1, foot)
    rho_h3_h1 = spearman_via_ranks(r3, r1, foot)
    print(f"Spearman(H3,H1)={rho_h3_h1:.4f} (fusion requires |rho|<0.90)", flush=True)
    assert abs(rho_h3_h1) < 0.90
    fused = (0.5 * r3 + 0.5 * r1).astype(np.float32)
    boosted = (fused * (1.0 + up)).astype(np.float32)
    boosted[~foot] = 0.0
    np.save(surf_dir / "K3-FUSE-H3H1.npy", fused)
    np.save(surf_dir / "K3-FUSE-H3H1-boost.npy", boosted)

    arms: dict[str, dict[str, np.ndarray]] = {}
    arms["FUSE@D2.8"] = {str(b): poisson_disk_thin_priority(fused > 0, fused, 2.8, max_add=b) & foot
                         for b in BUDGETS}
    arms["FUSE-boost@D2.8"] = {"37654": poisson_disk_thin_priority(boosted > 0, boosted, 2.8, max_add=37_654) & foot}
    print("greedy coverage on fused rank (n=37654) ...", flush=True)
    g_mask, g_diag, g_order = greedy_coverage(S.rank_surface(fused, foot), foot, 37_654)
    pre = np.zeros_like(g_mask)
    for r, c in g_order[:20_000]:
        pre[r, c] = True
    arms["FUSE@GREEDY"] = {"37654": g_mask, "20000": pre & foot}
    print("greedy diag:", g_diag, flush=True)

    results: dict[str, dict] = {}
    for arm, by_budget in arms.items():
        results[arm] = {}
        for b_str, mask in by_budget.items():
            ev = evaluate_mask(mask, ctx, f"exp2:{arm}-{b_str}")
            p = ev["visible_only"]["pooled"]
            print(f"ARM {arm} @{b_str}: dots={int(mask.sum())} pooled={p['pooled_dti']:.5f} "
                  f"CI={[round(x,5) for x in p['ci95']]} SGMC-cal={ev['sgmc']['sgmc_prevalence_calibrated_dti']:.5f}",
                  flush=True)
            results[arm][b_str] = ev

    # champion censoring diagnostics (IR-K3-09): B=0 vs B=2 on champion and D2.8 masks
    manifest = load_manifest(ROOT / "registry" / "focus9_registry.json")
    by_site = {e["site"]: e for e in manifest["rasters"]}
    diag = {}
    for site in ("GEMSDOE32", "GEMSDOE25"):
        m = read_mask(ROOT / ".cache" / by_site[site]["local"]) & foot
        diag[site] = {}
        for b in (0.0, 2.0):
            v = evaluate_visible_only_holdout(m, ctx, b_collar_px=b, name=f"diag:{site}@B{b}")
            diag[site][f"B{b}"] = v["pooled"]
            print(f"DIAG {site} B={b}: pooled={v['pooled']['pooled_dti']:.5f}", flush=True)

    # frozen selection rule
    veto = 0.9 * champ_sgmc
    cands = []
    for arm, by_budget in results.items():
        for b_str, ev in by_budget.items():
            cands.append(dict(arm=arm, budget=int(b_str),
                              pooled=float(ev["visible_only"]["pooled"]["pooled_dti"]),
                              sgmc_cal=float(ev["sgmc"]["sgmc_prevalence_calibrated_dti"]),
                              passes_sgmc_veto=bool(ev["sgmc"]["sgmc_prevalence_calibrated_dti"] >= veto)))
    eligible = [c for c in cands if c["passes_sgmc_veto"]]
    best = max(eligible or cands, key=lambda c: c["pooled"])
    print("SELECTED for Exp3:", best, f"(SGMC veto>={veto:.5f})", flush=True)

    best_mask = arms[best["arm"]][str(best["budget"])]
    best_surf = boosted if "boost" in best["arm"] else fused
    uniq = audit_final_dots(best_surf, best_mask, foot, manifest, root=ROOT / ".cache",
                            template_tif=ddir / "sample_submission.tif")
    print(f"UNIQ pre-check: worst within3px={uniq['worst_within_3px_fraction']:.4f} "
          f"vs {uniq['worst_overlap_raster']} literal_passed={uniq['literal_rule_passed']}", flush=True)
    np.save(surf_dir / "K3-EXP2-best-mask.npy", best_mask)

    out = dict(experiment=2, generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               elapsed_s=round(time.time() - t0, 1),
               spearman_h3_h1=rho_h3_h1, greedy_diag=g_diag,
               champion_rule_pooled=champ_rule_pooled, champion_sgmc_cal=champ_sgmc,
               sgmc_veto=veto, arms=results, censoring_diag=diag,
               selection_rule="max pooled visible-only HOLDOUT-DTI among arms with SGMC-cal >= 0.9 x champion",
               selected=best, candidates=cands, uniqueness_precheck=uniq)
    p = evidence_dir() / "exp2_emission.json"
    p.write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(f"wrote {p} ({out['elapsed_s']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

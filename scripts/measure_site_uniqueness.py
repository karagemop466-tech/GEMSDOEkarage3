#!/usr/bin/env python3
"""One-pass uniqueness measurement for the nine focus-site best files + our candidates.

For each candidate (binary dots inside the 5,167,373-px footprint), measure against EVERY
restored registry raster in registry/complete_registry_manifest.json:
  * within3   = share of candidate dots within 3 px of the registry raster's dots (literal rule, <=0.70)
  * phi       = binary (Pearson/phi) correlation over the footprint (binary proxy for the Spearman rule;
                the continuous-surface Spearman needs the candidate surface and is NOT measured here)
Byte-identical registry copies of the candidate are excluded from the maximum and reported separately.
Writes evidence/site-uniqueness-20261029.json. Measurements only: no score, no verdict to submit.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3.registry_audit import _load_registry_array  # noqa: E402  (shared loader, unmodified)

MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"
TEMPLATE = ROOT / ".cache" / "gems_data" / "sample_submission.tif"
OUT = ROOT / "evidence" / "site-uniqueness-20261029.json"
DISK3 = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)

# (label, repo, path) of the highest user-reported file per focus site; resolved in the manifest.
FOCUS = [
    ("GEMSDOE24", "buffedlizard55-lab/GEMSDOE24", "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
    ("GEMSDOE25", "buffedlizard55-lab/GEMSDOE25", "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
    ("GEMSDOE27", "buffedlizard55-lab/GEMSDOE27", "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"),
    ("GEMSDOE28", "buffedlizard55-lab/GEMSDOE28", "docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif"),
    ("GEMSDOE30", "buffedlizard55-lab/GEMSDOE30", "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca-nanoutside.tif"),
    ("GEMSDOE31", "buffedlizard55-lab/GEMSDOE31", "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif"),
    ("GEMSDOE32", "buffedlizard55-lab/GEMSDOE32", "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"),
    ("GEMSDOE33", "buffedlizard55-lab/GEMSDOE33", "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e-nanoutside.tif"),
    ("GEMSDOE36", "buffedlizard55-lab/GEMSDOE36", "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif"),
]
OWN_CANDIDATES = [
    ("karage3-H-GEO-CONDUIT-zeros", "docs/downloads/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif"),
    ("karage3-CONSENSUS-HGRAD-k37654-zeros", "docs/downloads/gemsdoe32-karage3-consensus-hgrad-k37654-20261029T183206Z-4786d9bd-zeros.tif"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    man = json.loads(MANIFEST.read_text())
    with rasterio.open(TEMPLATE) as tpl:
        foot = np.isfinite(tpl.read(1)) & (tpl.read_masks(1) > 0)
        template = {"shape": tpl.shape, "crs": tpl.crs, "transform": tpl.transform}

    cands: list[dict] = []
    for label, repo, path in FOCUS:
        hit = [e for e in man["rasters"] if e["repo"] == repo and e["path"] == path]
        if not hit:
            raise SystemExit(f"not in manifest: {repo}:{path}")
        cands.append({"label": label, "repo": repo, "path": path, "local": ROOT / hit[0]["local"],
                      "sha256": hit[0]["sha256"], "source": "registry (pinned ref %s)" % hit[0]["ref"][:10]})
    for label, rel in OWN_CANDIDATES:
        p = ROOT / rel
        cands.append({"label": label, "repo": "this-repo", "path": rel, "local": p, "sha256": sha256_file(p),
                      "source": "this repository (research artifact)"})

    cand_dots = {}
    for c in cands:
        with rasterio.open(c["local"]) as ds:
            a = ds.read(1)
        dots = (a > 0.5) & foot
        cand_dots[c["label"]] = {"dots": dots, "dil": binary_dilation(dots, structure=DISK3), "n": int(dots.sum())}
        c["dots_inside"] = int(dots.sum())
        c["nonbinary_inside"] = bool(np.any((a[foot] != 0) & (a[foot] != 1)))

    best = {c["label"]: {"max_within3_other_bytes": (-1.0, None), "max_within3_same_repo": (-1.0, None),
                         "max_phi": (-1.0, None), "count_gt_070": 0, "identical_copies": []} for c in cands}
    seen_digest: set[str] = set()
    measured = skipped = 0
    for entry in man["rasters"]:
        arr, row = _load_registry_array(entry, ROOT, template)
        if arr is None or not np.isfinite(arr[foot]).all():
            skipped += 1
            continue
        reg = (arr > 0.0) & foot
        if not reg.any():
            continue
        digest = hashlib.sha256(np.packbits(reg).tobytes()).hexdigest()
        reg_near = None
        measured += 1
        name = f"{entry['repo']}:{entry['path']}"
        for c in cands:
            if entry["sha256"] == c["sha256"]:
                best[c["label"]]["identical_copies"].append(name)
                continue
            cd = cand_dots[c["label"]]
            if cd["n"] == 0:
                continue
            if reg_near is None:
                reg_near = binary_dilation(reg, structure=DISK3)
            w = float(reg_near[cd["dots"]].mean())
            # Exact phi from integer counts over the footprint (no float copies of the grid).
            n_all = int(foot.sum())
            a_cnt = int(cd["n"])
            b_cnt = int(np.count_nonzero(reg))
            c_cnt = int(np.count_nonzero(cd["dots"] & reg))
            denom = (a_cnt * (n_all - a_cnt) * b_cnt * (n_all - b_cnt)) ** 0.5
            phi = float((n_all * c_cnt - a_cnt * b_cnt) / denom) if denom > 0 else 0.0
            b = best[c["label"]]
            if w > 0.70:
                b["count_gt_070"] += 1
            if w > b["max_within3_other_bytes"][0]:
                b["max_within3_other_bytes"] = (w, name)
            if entry["repo"] == c["repo"] and w > b["max_within3_same_repo"][0]:
                b["max_within3_same_repo"] = (w, name)
            if abs(phi) > b["max_phi"][0]:
                b["max_phi"] = (abs(phi), name)
        _ = digest
    results = []
    for c in cands:
        b = best[c["label"]]
        results.append({
            "label": c["label"], "repo": c["repo"], "path": c["path"], "sha256": c["sha256"],
            "source": c["source"], "dots_inside_footprint": c["dots_inside"],
            "nonbinary_inside_footprint": c["nonbinary_inside"],
            "max_within3_vs_any_other_registry_raster": round(b["max_within3_other_bytes"][0], 6),
            "max_within3_raster": b["max_within3_other_bytes"][1],
            "max_within3_vs_same_repo_rasters": round(b["max_within3_same_repo"][0], 6),
            "max_within3_same_repo_raster": b["max_within3_same_repo"][1],
            "registry_rasters_over_0_70_within3": b["count_gt_070"],
            "max_abs_phi_binary_proxy": round(b["max_phi"][0], 6),
            "max_abs_phi_raster": b["max_phi"][1],
            "byte_identical_registry_copies": b["identical_copies"],
            "literal_dot_rule_0_70_passed_vs_all_measured": b["count_gt_070"] == 0,
        })
    out = {
        "schema": "GEMSDOEkarage3-SITE-UNIQUENESS-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "registry_manifest": "registry/complete_registry_manifest.json (filtered inventory; literal_registry_complete=false)",
        "registry_rasters_measured": measured,
        "registry_rasters_skipped_missing_or_malformed": skipped,
        "surface_spearman_measured": False,
        "limitations": ["Binary dot rule only: the continuous-surface Spearman gate needs each candidate's surface and is not run here.",
                        "Registry is a filtered inventory, not a literal complete registry.",
                        "Byte-identical copies of a candidate are excluded from maxima and listed separately."],
        "candidates": results,
    }
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"measured": measured, "skipped": skipped,
                      "rows": [{k: r[k] for k in ("label", "max_within3_vs_any_other_registry_raster",
                                                  "max_within3_raster", "registry_rasters_over_0_70_within3")} for r in results]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

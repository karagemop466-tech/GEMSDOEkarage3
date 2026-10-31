#!/usr/bin/env python3
"""Re-verify the nine focus-site files and the lattice bound from saved bytes (session 2026-10-31).

What it does (no new candidate is generated and no slot is used):

1. Checks that each nine-site file in `.cache/focus9/` matches the SHA-256 pinned in
   `data/focus_registry.json` (fails closed on any mismatch).
2. Runs the repo's own format validator, `scripts.check_format.inspect`, on each file
   against the historical template (`.cache/historical/template.tif`). Diagnostic only.
3. Measures the literal "dots within 3 px" overlap, per the project's protocol:
   - file i against the registered calibration lattice (`.cache/historical/lattice.tif`);
   - file i against every other nine-site file (all ordered pairs).
   Dots = positive cells. Overlap(i -> j) = fraction of i's dots whose distance to j's dots is <= 3 px.
4. Measures Spearman rank correlation of values inside the template footprint, all pairs.
5. Writes `evidence/session-recheck-20261031.json`.

Evidence labels: every number here is a GEOMETRY / FORMAT DIAGNOSTIC. None is a score.
The HOLDOUT-DTI values are NOT recomputed here; they are carried from earlier receipts and labelled as such.
Run: `python -m scripts.session_recheck_20261031` (needs numpy, scipy, rasterio).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.check_format import inspect  # noqa: E402  (the repo's own validator, reused not forked)

FOCUS_DIR = ROOT / ".cache" / "focus9"
TEMPLATE = ROOT / ".cache" / "historical" / "template.tif"
LATTICE = ROOT / ".cache" / "historical" / "lattice.tif"
REGISTRY = ROOT / "data" / "focus_registry.json"
OUT = ROOT / "evidence" / "session-recheck-20261031.json"
RADIUS_PX = 3.0
# Candidates added to main outside this session (PR #71). Measured with the same rules; never cleared here.
EXTRA = [
    "docs/downloads/gemsdoe32-karage3-blind-conduit-stepper-v1-20261031T000000Z-e71280c6-nan.tif",
    "docs/downloads/gemsdoe32-karage3-blind-conduit-stepper-v1-20261031T000000Z-e71280c6-zeros.tif",
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_values(p: Path) -> np.ndarray:
    with rasterio.open(p) as d:
        return d.read(1).astype(np.float64)


def main() -> int:
    reg = json.loads(REGISTRY.read_text())
    sites = reg["sites"]

    with rasterio.open(TEMPLATE) as t:
        T = t.read(1)
        foot = np.isfinite(T) & (t.read_masks(1) != 0)

    # 1. SHA-256 pin check (fail closed)
    files = []
    for s in sites:
        name = Path(s["path"]).name
        p = FOCUS_DIR / name
        if not p.exists():
            raise SystemExit(f"missing {p}; run scripts/fetch_focus9_files.py first")
        got = sha256(p)
        if got != s["sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {s['site']}: {got} != {s['sha256']}")
        files.append(dict(site=s["site"], path=p, name=name, sha256=got, claim=s["historical_claim"]))

    # 2. Format gate (repo validator)
    for f in files:
        f["format"] = inspect(f["path"], TEMPLATE)

    # 3. Dots and distance fields
    vals = {}
    for f in files:
        v = load_values(f["path"])
        vals[f["site"]] = v
        f["dots"] = (np.nan_to_num(v, nan=0.0) > 0)
        f["n_dots"] = int(f["dots"].sum())
        f["nan_cells"] = int(np.isnan(v).sum())
        f["zero_cells"] = int((v == 0).sum())
        f["dots_outside_footprint"] = int((f["dots"] & ~foot).sum())

    with rasterio.open(LATTICE) as d:
        L = d.read(1)
    lat_dots = np.isfinite(L) & (L > 0)
    lat_dist = distance_transform_edt(~lat_dots)
    lattice_cov_within3 = float((foot & (lat_dist <= RADIUS_PX)).sum() / foot.sum())

    dist_maps = {f["site"]: distance_transform_edt(~f["dots"]) for f in files}

    lattice_overlap = {}
    for f in files:
        n = f["n_dots"]
        lattice_overlap[f["site"]] = float((lat_dist[f["dots"]] <= RADIUS_PX).mean()) if n else None

    pair_overlap = {}
    for a in files:
        row = {}
        for b in files:
            if a["site"] == b["site"]:
                continue
            row[b["site"]] = float((dist_maps[b["site"]][a["dots"]] <= RADIUS_PX).mean())
        pair_overlap[a["site"]] = row

    # 4. Rank correlation inside the footprint (all pairs)
    fv = {k: v[foot] for k, v in vals.items()}
    rho = {}
    names = [f["site"] for f in files]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            r = float(spearmanr(fv[a], fv[b]).statistic)
            rho.setdefault(a, {})[b] = r
            rho.setdefault(b, {})[a] = r

    rows = []
    for f in files:
        s = f["site"]
        max_peer_overlap = max(pair_overlap[s].values())
        max_peer_site = max(pair_overlap[s], key=pair_overlap[s].get)
        max_abs_rho = max(abs(v) for v in rho[s].values())
        lit_fail = (lattice_overlap[s] > 0.70) or (max_peer_overlap > 0.70) or (max_abs_rho > 0.90)
        rows.append(dict(
            site=s,
            file=f["name"],
            file_sha256=f["sha256"],
            reported_score_user_reported=f["claim"],
            format_gate_pass=bool(f["format"]["format_gate_pass"]),
            outside_null_or_nan=bool(f["format"]["outside_null_or_nan"]),
            nan_cells=f["nan_cells"],
            zero_cells=f["zero_cells"],
            dots=f["n_dots"],
            dots_outside_footprint=f["dots_outside_footprint"],
            overlap_vs_lattice_within3px=round(lattice_overlap[s], 6),
            max_overlap_vs_peer=round(max_peer_overlap, 6),
            max_overlap_peer_site=max_peer_site,
            max_abs_spearman_vs_peer=round(max_abs_rho, 6),
            literal_protocol_gate="DUPLICATE-STOP" if lit_fail else "pass",
            ok_to_submit=False,
        ))

    extra_rows = []
    for rel in EXTRA:
        ep = ROOT / rel
        if not ep.exists():
            raise SystemExit(f"missing extra candidate {rel}")
        ev = load_values(ep)
        edots = (np.nan_to_num(ev, nan=0.0) > 0)
        edist = distance_transform_edt(~edots)
        n_e = int(edots.sum())
        lat_ov = float((lat_dist[edots] <= RADIUS_PX).mean()) if n_e else None
        peer = {}
        for f in files:
            peer[f["site"]] = float((dist_maps[f["site"]][edots] <= RADIUS_PX).mean()) if n_e else None
        peer_site = max(peer, key=peer.get)
        fv_e = ev[foot]
        rho_lat = float(spearmanr(fv_e, L[foot]).statistic)
        rho_peer = max(abs(float(spearmanr(fv_e, fv[k]).statistic)) for k in fv)
        fmt = inspect(ep, TEMPLATE)
        fail = (lat_ov > 0.70) or (peer[peer_site] > 0.70) or (abs(rho_lat) > 0.90) or (rho_peer > 0.90)
        extra_rows.append(dict(
            file=rel, file_sha256=sha256(ep), dots=n_e,
            dots_outside_footprint=int((edots & ~foot).sum()),
            format_gate_pass=bool(fmt["format_gate_pass"]),
            outside_null_or_nan=bool(fmt["outside_null_or_nan"]),
            overlap_vs_lattice_within3px=round(lat_ov, 6) if lat_ov is not None else None,
            max_overlap_vs_focus_site=round(peer[peer_site], 6),
            max_overlap_focus_site=peer_site,
            spearman_vs_lattice_footprint=round(rho_lat, 6),
            max_abs_spearman_vs_focus_site=round(rho_peer, 6),
            literal_protocol_gate="DUPLICATE-STOP" if fail else "pass",
            ok_to_submit=False,
        ))

    result = dict(
        schema="session-recheck-20261031-v1",
        generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        evidence_class="FORMAT + GEOMETRY DIAGNOSTICS - NOT A SCORE, NOT A SUBMISSION APPROVAL",
        template=dict(path=str(TEMPLATE.relative_to(ROOT)), sha256=sha256(TEMPLATE)),
        lattice=dict(path=str(LATTICE.relative_to(ROOT)), sha256=sha256(LATTICE),
                     footprint_cells=int(foot.sum()),
                     footprint_coverage_within_3px=round(lattice_cov_within3, 6)),
        rule="literal protocol: DUPLICATE-STOP if overlap > 0.70 (within 3 px, vs lattice or any peer) or |Spearman| > 0.90",
        rows=rows,
        extra_candidates=extra_rows,
        holdout_dti="NOT RECOMPUTED THIS SESSION. See evidence/focus9-audit-20261030.json (HOLDOUT-DTI, earlier receipt).",
        ok_to_submit_any=False,
        weekly_slots_used=0,
        new_candidates_generated=0,
    )
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for e in extra_rows:
        print(f"EXTRA {e['file'][-40:]} fmt_pass={e['format_gate_pass']} lattice={e['overlap_vs_lattice_within3px']} "
              f"max_focus={e['max_overlap_vs_focus_site']} ({e['max_overlap_focus_site']}) -> {e['literal_protocol_gate']}")
    for r in rows:
        print(f"{r['site']:9s} fmt_pass={r['format_gate_pass']!s:5s} lattice={r['overlap_vs_lattice_within3px']:.4f} "
              f"max_peer={r['max_overlap_vs_peer']:.4f} ({r['max_overlap_peer_site']}) "
              f"max|rho|={r['max_abs_spearman_vs_peer']:.3f} -> {r['literal_protocol_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

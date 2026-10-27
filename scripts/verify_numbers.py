#!/usr/bin/env python3
"""Pass-3 consistency audit: every published number must trace to evidence/*.json.
Exit 1 on any mismatch. Run after build_site.py."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
checks = []


def ck(name: str, cond: bool, detail: str = "") -> None:
    checks.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    card = json.loads((EV / "k3_run_card.json").read_text())
    e1 = json.loads((EV / "exp1_screen.json").read_text())
    e2 = json.loads((EV / "exp2_emission.json").read_text())
    ext = json.loads((EV / "extended_uniqueness.json").read_text())["summary"]
    prep = json.loads((ROOT / "data" / "prepared_manifest.json").read_text())
    focus = json.loads((ROOT / "registry" / "focus9_registry.json").read_text())
    sidecar = list((ROOT / "docs" / "downloads").glob("*-audit.json"))
    site = (ROOT / "docs" / "index.html").read_text() + (ROOT / "docs" / "executive-summary.html").read_text()

    z = ROOT / "docs" / "downloads" / card["raster"]["zeros_file"]
    ck("raster sha matches file", sha(z) == card["raster"]["zeros_sha256"])
    ck("zip sha matches file", sha(z.with_suffix(".zip")) == card["raster"]["zip_sha256"])
    with rasterio.open(z) as ds:
        a = ds.read(1)
    ck("tif dots == run card", int((a > 0).sum()) == card["raster"]["dots"], f"{int((a>0).sum())} vs {card['raster']['dots']}")
    ck("zeros tif fully finite in [0,1]", bool(np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1))
    ck("note <=140 chars", card["submission"]["note_chars"] <= 140, str(card["submission"]["note_chars"]))
    ck("sidecar exists & sha agrees", len(sidecar) == 1 and
       json.loads(sidecar[0].read_text())["zeros_tif"]["sha256"] == card["raster"]["zeros_sha256"])

    sel = e2["selected"]
    ck("run-card pooled == exp2 selected arm",
       abs(card["holdout_dti"]["pooled_dti"] - sel["pooled"]) < 1e-12)
    ck("champion-rule control == exp1 D2.8 pooled",
       abs(card["holdout_dti"]["champion_rule_control"]["pooled_dti"] -
           e1["controls"]["GEMSDOE25"]["visible_only"]["pooled"]["pooled_dti"]) < 1e-12)
    ck("G1 consistent", card["gates"]["G1_pooled_beats_champion_rule"]["pass_"] ==
       bool(card["holdout_dti"]["pooled_dti"] > card["holdout_dti"]["champion_rule_control"]["pooled_dti"]))
    ck("verdict consistent with gates",
       (card["verdict"] == "promote") == all(g["pass_"] for g in card["gates"].values()))
    ck("ok_to_submit == (verdict==promote)", card["ok_to_submit"] == (card["verdict"] == "promote"))
    ck("extended audit candidate sha == run card", ext["candidate_sha256"] == card["raster"]["zeros_sha256"])
    ck("no genuine duplicates in extended audit", ext["genuine_duplicates_over_70pct"] == [])

    ck("prepared footprint", prep["counts"]["footprint_px"] == 5_167_373)
    ck("prepared labels", prep["counts"]["label_px"] == 60_988)
    for e in focus["rasters"]:
        p = ROOT / ".cache" / e["local"]
        if not p.exists() or sha(p) != e["sha256"]:
            ck(f"focus registry {e['site']}", False, "sha mismatch - rerun build_focus_registry")
            break
    else:
        ck("focus registry hashes (11 rasters)", True)
    ck("focus n_failed==0", focus["n_failed"] == 0)

    ck("site shows DO NOT SUBMIT when negative", card["verdict"] != "negative" or "DO NOT SUBMIT" in site)
    ck("site contains raster sha256", card["raster"]["zeros_sha256"] in site)
    ck("site contains submission note", card["submission"]["note"].split(" | id")[0] in site)
    ck("site labels leaderboard NOT ESTIMABLE", "NOT ESTIMABLE" in site)
    ck("no ORGANIZER-CONFIRMED score claim", "ORGANIZER-CONFIRMED 0." not in site)
    ck("downloads linked exist", all((ROOT / "docs" / "downloads" / x).exists()
                                     for x in (card["raster"]["zeros_file"], card["raster"]["zip_file"], card["raster"]["nan_file"])))
    failed = [c for c in checks if not c[1]]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

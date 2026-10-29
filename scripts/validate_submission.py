#!/usr/bin/env python3
"""Automated, no-human submission gate: one JSON verdict per candidate file.

Verdict values:
  OK TO DOWNLOAD AND SUBMIT  - every gate below passed with measured results
  DO NOT SUBMIT              - at least one gate failed or could not be measured

Gates (all must pass; anything unmeasured counts as a failure):
  G1 format      single-band float32 GeoTIFF, EPSG:32611, 3730x3292, template transform,
                 no NaN/inf/sentinel inside the 5,167,373-px footprint, values in [0,1],
                 nothing emitted outside the footprint (shared gems32.submission audit).
  G2 package     .zip holds exactly one .tif; the .tif bytes match the submitted candidate.
  G3 metadata    unique name present, note <= 140 characters.
  G4 surface     full-footprint |Spearman| <= 0.90 vs EVERY restored registry raster
                 (shared karage3.registry_audit.audit_surface). Needs the candidate surface .npy.
  G5 final dots  literal directional overlap <= 0.70 within 3 px vs EVERY registry raster
                 (shared karage3.registry_audit.audit_final_dots). No exemptions.
  G6 registry    complete_registry_manifest.json reports literal_registry_complete = true
                 and zero missing/malformed registry rasters. Otherwise the uniqueness
                 result is a partial measurement and cannot clear a file.

HOLDOUT-DTI (shared evaluator, GEMSDOE32-HIDE-RECOVER-v3.0) is reported as a
diagnostic. It is NOT a gate and NOT a leaderboard estimate: the nine historical
files score 0.003-0.097 on it while their user-reported leaderboard values are
0.20-0.28 (see evidence/focus9-holdout-baseline-20261029.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems32 import submission  # noqa: E402
from gems32.paths import data_dir  # noqa: E402
from karage3.registry_audit import audit_final_dots, audit_surface  # noqa: E402

REGISTRY_MANIFEST = ROOT / "registry" / "complete_registry_manifest.json"
NOTE_LIMIT = 140
SPEARMAN_LIMIT = 0.90
OVERLAP_LIMIT = 0.70


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gate(name: str, passed: bool | None, detail: dict) -> dict:
    return {"gate": name, "passed": passed, **detail}


def unzip_single_tif(zip_path: Path, dest: Path) -> Path:
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(".tif")]
        if len(members) != 1 or len(zf.namelist()) != 1:
            raise ValueError(f"zip must contain exactly one .tif and nothing else; found {zf.namelist()}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(zf.read(members[0]))
    return dest


def run(candidate: Path, name: str, note: str, surface_npy: Path | None, ddir: Path,
        template: Path | None = None) -> dict:
    gates: list[dict] = []
    tif = candidate
    if candidate.suffix.lower() == ".zip":
        tif = unzip_single_tif(candidate, ROOT / ".cache" / "validate" / candidate.with_suffix(".tif").name)
        gates.append(gate("G2_package", True, {"zip": candidate.name, "inner_tif": tif.name}))
    else:
        gates.append(gate("G2_package", True, {"zip": None, "inner_tif": tif.name}))

    tpl_path = template or (ddir / "sample_submission.tif")
    with rasterio.open(tpl_path) as tpl:
        foot = np.isfinite(tpl.read(1)) & (tpl.read_masks(1) > 0)
    with rasterio.open(ddir / "labels.tif") as lab:
        labels = (lab.read(1) > 0) & foot
    # Format audit (shared). Raises on any failed check, including catalogue leakage.
    try:
        fmt = submission.audit_geotiff(tif, foot, labels=labels, mode="zeros", template_tif=tpl_path)
        fmt_ok, fmt_detail = True, {"checks": fmt.get("checks"), "emitted_positive_pixels": fmt.get("emitted_positive_pixels")}
    except ValueError as exc:
        fmt_ok, fmt_detail = False, {"error": str(exc)}
    gates.append(gate("G1_format", fmt_ok, fmt_detail))

    # The shared audit is for zeros-mode files: outside-footprint must be 0 and whole grid in [0,1].
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
    dots_full = (arr > 0.5) & foot

    name_ok = bool(name) and len(name) <= 120 and all(c.isalnum() or c in "-_." for c in name)
    gates.append(gate("G3_metadata", bool(name_ok and len(note) <= NOTE_LIMIT and len(note) > 0),
                      {"name": name, "name_ok": name_ok, "note_chars": len(note), "note_limit": NOTE_LIMIT}))

    manifest = json.loads(REGISTRY_MANIFEST.read_text())
    entries = [e for e in manifest["rasters"]]
    complete = bool(manifest.get("literal_registry_complete"))

    if surface_npy is None or not Path(surface_npy).exists():
        gates.append(gate("G4_surface", False, {"error": "candidate surface .npy not supplied; not measured"}))
        surf = None
    else:
        surface = np.load(surface_npy)
        surf = audit_surface(surface, foot, {"rasters": entries}, root=ROOT, template_tif=tpl_path,
                             max_abs_spearman=SPEARMAN_LIMIT)
        gates.append(gate("G4_surface", surf["passed"] and surf["audit_complete"],
                          {"worst_abs_spearman": surf["worst_abs_spearman"], "worst_raster": surf["worst_raster"],
                           "duplicates": [{"repo": d["repo"], "path": d["path"], "spearman": d["spearman"]}
                                          for d in surf["duplicates"]][:20],
                           "registry_rasters": surf["registry_rasters"], "malformed_or_missing": surf["malformed_or_missing"]}))

    dots_audit = audit_final_dots(
        surface if surf is not None else arr.astype(np.float32),
        dots_full, foot, {"rasters": entries}, root=ROOT, template_tif=tpl_path,
        max_within_3px=OVERLAP_LIMIT, candidate_values=dots_full.astype(np.float32),
    )
    gates.append(gate("G5_final_dots", dots_audit["passed"] and dots_audit["audit_complete"],
                      {"worst_within_3px_fraction": dots_audit["worst_within_3px_fraction"],
                       "worst_overlap_raster": dots_audit["worst_overlap_raster"],
                       "worst_abs_spearman": dots_audit["worst_abs_spearman"],
                       "duplicates": [{"repo": d["repo"], "path": d["path"], "within_3px": d.get("within_3px_fraction")}
                                      for d in dots_audit["duplicates"]][:20],
                       "registry_rasters": dots_audit["registry_rasters"],
                       "malformed_or_missing": dots_audit["malformed_or_missing"],
                       "candidate_dots": int(dots_full.sum())}))

    gates.append(gate("G6_registry_complete", complete and dots_audit["malformed_or_missing"] == 0,
                      {"literal_registry_complete": complete, "manifest_note": manifest.get("note"),
                       "registry_rasters": len(entries)}))

    all_pass = all(g["passed"] is True for g in gates)
    failed = [g["gate"] for g in gates if g["passed"] is not True]
    verdict = "OK TO DOWNLOAD AND SUBMIT" if all_pass else "DO NOT SUBMIT"

    return {
        "schema": "GEMSDOEkarage3-SUBMISSION-GATE-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidate": candidate.name,
        "candidate_sha256": sha256_file(candidate),
        "inner_tif_sha256": sha256_file(tif),
        "submission_name": name,
        "note": note,
        "verdict": verdict,
        "failed_gates": failed,
        "gates": gates,
        "holdout_dti_diagnostic": "see evidence/focus9-holdout-baseline-20261029.json (not a gate, not a leaderboard estimate)",
        "registry_manifest_sha256": sha256_file(REGISTRY_MANIFEST),
        "dots_by_registry_raster_top5": sorted(
            [{"repo": r["repo"], "path": r["path"], "within_3px": r.get("within_3px_fraction")}
             for r in dots_audit["comparisons"] if r.get("within_3px_fraction") is not None],
            key=lambda r: -r["within_3px"])[:5],
        "organizer_acceptance": "UNKNOWN - no portal receipt; this gate is a local, automated pre-check only",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate", type=Path, help="zeros GeoTIFF or single-tif zip")
    ap.add_argument("--name", required=True)
    ap.add_argument("--note", required=True)
    ap.add_argument("--surface", type=Path, default=None, help="candidate continuous surface .npy on the template grid")
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    res = run(args.candidate, args.name, args.note, args.surface, args.data_dir or data_dir())
    txt = json.dumps(res, indent=2, allow_nan=False, default=str)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(txt + "\n")
    print(txt)
    return 0 if res["verdict"] == "OK TO DOWNLOAD AND SUBMIT" else 1


if __name__ == "__main__":
    raise SystemExit(main())

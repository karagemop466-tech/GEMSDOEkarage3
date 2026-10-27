#!/usr/bin/env python3
"""Verify restored bytes against registry/data_manifest.json, then split training_features.tif
into per-band float32 .npy files under .cache/gems_work/bands/ (sentinel -> NaN) and write
data/prepared_manifest.json + evidence/restore_receipt_k3.json. Fails closed on any hash or
count mismatch."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from karage3.paths import data_dir, evidence_dir, registry_dir, work_dir  # noqa: E402

BAND_NAMES = [
    "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope", "tc",
    "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15", "iso_grav_anom_vg",
    "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf", "ieq_n100a15",
    "cond_surf", "iso_grav_anom_hg", "det_elev_slope",
]
SENTINEL = np.float32(-3.4028234663852886e38)
EXPECTED = dict(height=3730, width=3292, footprint_px=5_167_373, label_px=60_988)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ddir = data_dir()
    man = json.loads((registry_dir() / "data_manifest.json").read_text())
    receipt_files, errors = [], []
    for e in man["files"]:
        p = ddir / e["dest"]
        if not p.exists():
            errors.append(f"MISSING {e['dest']} (run scripts/restore_data.py --group all)")
            continue
        got = sha256_file(p)
        ok = got == e["sha256"] and p.stat().st_size == e["bytes"]
        receipt_files.append(dict(id=e["id"], dest=e["dest"], bytes=p.stat().st_size,
                                  sha256=got, match=bool(ok)))
        print(f"{'match  ' if ok else 'MISMATCH'} {e['dest']}")
        if not ok:
            errors.append(f"HASH/SIZE MISMATCH {e['dest']}: got {got} != {e['sha256']}")
    (evidence_dir() / "restore_receipt_k3.json").write_text(json.dumps(
        dict(schema_version=1, checked_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             storage_root=str(ddir), files=receipt_files, errors=errors), indent=2) + "\n")
    if errors:
        raise SystemExit("restore verification failed:\n" + "\n".join(errors))

    with rasterio.open(ddir / "sample_submission.tif") as ds:
        sample = ds.read(1)
        profile = dict(crs=str(ds.crs), transform=list(ds.transform)[:6],
                       width=ds.width, height=ds.height)
    foot = np.isfinite(sample)
    ones_on_labels = int((sample == 1).sum())
    with rasterio.open(ddir / "labels.tif") as ds:
        labels = ds.read(1) >= 1
    counts = dict(footprint_px=int(foot.sum()), label_px=int((labels & foot).sum()),
                  sample_ones_px=ones_on_labels,
                  sample_ones_on_labels=int(((sample == 1) & labels).sum()))
    print(counts)
    assert counts["footprint_px"] == EXPECTED["footprint_px"], counts
    assert counts["label_px"] == EXPECTED["label_px"], counts

    bands_dir = work_dir() / "bands"
    bands_dir.mkdir(parents=True, exist_ok=True)
    band_rows = []
    with rasterio.open(ddir / "training_features.tif") as ds:
        assert (ds.height, ds.width, ds.count) == (EXPECTED["height"], EXPECTED["width"], 19)
        assert str(ds.crs) == "EPSG:32611" and list(ds.transform)[:6] == profile["transform"]
        desc_names = [str(d).split(" - ")[0] for d in ds.descriptions]
        assert desc_names == BAND_NAMES, f"band description mismatch: {desc_names}"
        for i, name in enumerate(BAND_NAMES, start=1):
            a = ds.read(i).astype(np.float32)
            bad = (a <= SENTINEL * np.float32(0.5)) | ~np.isfinite(a)
            a[bad] = np.nan
            out = bands_dir / f"{i:02d}_{name}.npy"
            np.save(out, a)
            v = a[foot & np.isfinite(a)]
            band_rows.append(dict(index=i, name=name, file=out.name,
                                  nan_in_footprint=int((~np.isfinite(a[foot])).sum()),
                                  min=float(v.min()), median=float(np.median(v)), max=float(v.max())))
            print(f"band {i:2d} {name}: nan_in_foot={band_rows[-1]['nan_in_footprint']}")
            del a, v
    prep = dict(schema_version=1, prepared_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                grid=dict(epsg=32611, height=EXPECTED["height"], width=EXPECTED["width"],
                          transform=profile["transform"], pixel_size_m=[100.0, 100.0]),
                counts=counts, bands=band_rows,
                note="footprint = finite pixels of sample_submission.tif; labels>=1; sentinel -3.4028234663852886e+38 -> NaN")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "prepared_manifest.json").write_text(json.dumps(prep, indent=2) + "\n")
    print("wrote data/prepared_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

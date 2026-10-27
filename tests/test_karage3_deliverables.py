"""End-to-end automated verification tests for GEMSDOEkarage3 Lane H-K3-1 (CRSB-GUB) deliverables."""
from __future__ import annotations

import hashlib
import json
import re
import unittest
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from scripts.promotion_gate import assess

ROOT = Path(__file__).resolve().parents[1]
FOCUS_9 = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class DeliverableVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.card = json.loads((ROOT / "docs" / "crsb-gub" / "run-card.json").read_text(encoding="utf-8"))
        self.ev_card = json.loads((ROOT / "evidence" / "crsb_gub_run_card.json").read_text(encoding="utf-8"))
        self.ablation = json.loads((ROOT / "evidence" / "crsb-gub-ablation-results.json").read_text(encoding="utf-8"))
        self.canary = json.loads((ROOT / "evidence" / "leakage-canary-51ch.json").read_text(encoding="utf-8"))
        self.uniq = json.loads((ROOT / "evidence" / "complete-registry-uniqueness-scan.json").read_text(encoding="utf-8"))
        self.nine = json.loads((ROOT / "evidence" / "nine-site-audit-20261027.json").read_text(encoding="utf-8"))

    def test_saved_geotiff_and_zip_strict_0_1_and_no_nan_hazard(self) -> None:
        self.assertEqual(self.card, self.ev_card)
        dl_dir = ROOT / "docs" / "downloads"
        nan_files = list(dl_dir.glob("gemskarage3-*-nan.tif"))
        self.assertEqual(nan_files, [], "No gemskarage3 -nan.tif hazard file may remain in docs/downloads/")

        tif_path = dl_dir / self.card["submission_name"]
        zip_path = dl_dir / self.card["zip_submission_name"]
        self.assertTrue(tif_path.exists(), f"Missing {tif_path}")
        self.assertTrue(zip_path.exists(), f"Missing {zip_path}")

        tif_bytes = tif_path.read_bytes()
        self.assertEqual(sha256_bytes(tif_bytes), self.card["raster_sha256"])
        self.assertEqual(sha256_bytes(zip_path.read_bytes()), self.card["zip_sha256"])

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            self.assertEqual(names, [tif_path.name], "ZIP must contain strictly one single-band GeoTIFF")
            self.assertEqual(sha256_bytes(zf.read(names[0])), self.card["raster_sha256"])

        with rasterio.open(tif_path) as ds:
            self.assertEqual(ds.count, 1)
            self.assertEqual(ds.dtypes[0], "float32")
            self.assertEqual(ds.shape, (3730, 3292))
            self.assertEqual(ds.crs.to_epsg(), 32611)
            self.assertEqual([round(float(x), 4) for x in ds.transform[:6]], [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0])
            self.assertIsNone(ds.nodata)
            arr = ds.read(1)

        self.assertEqual(int(np.isfinite(arr).sum()), 3730 * 3292)
        self.assertEqual(int(np.isnan(arr).sum()), 0)
        self.assertGreaterEqual(float(arr.min()), 0.0)
        self.assertLessEqual(float(arr.max()), 1.0)
        self.assertEqual(int((arr > 0.5).sum()), 37654)

    def test_leakage_canary_and_dropped_dist_known_fault(self) -> None:
        self.assertTrue(self.canary["passed"])
        self.assertEqual(self.canary["n_features_tested"], 51)
        self.assertLessEqual(self.canary["max_oriented_auc"], 0.90)
        crsb_src = (ROOT / "src" / "gems32" / "crsb_gub.py").read_text(encoding="utf-8")
        self.assertIn('assert "dist_known_fault_px" not in ws_df.columns', crsb_src)
        self.assertIn('assert "dist_known_fault_px" not in vv_df.columns', crsb_src)

    def test_uniqueness_across_104_repos_and_focus9(self) -> None:
        self.assertGreaterEqual(self.uniq["n_unique_rasters_checked"], 1780)
        self.assertTrue(self.uniq["stage1_surface_passed_all_1793"])
        self.assertTrue(self.uniq["stage2_discrete_candidates_passed"])
        self.assertTrue(self.uniq["focus9_all_passed"])
        self.assertLessEqual(abs(self.uniq["worst_surface_spearman_all"]["surface_spearman"]), 0.90)
        self.assertLessEqual(self.uniq["worst_discrete_3px_overlap"]["within_3px_fraction"], 0.70)
        self.assertEqual(set(self.uniq["per_focus_site"].keys()), FOCUS_9)

    def test_three_experiment_budget_and_gate_consistency(self) -> None:
        self.assertLessEqual(self.card["experiments_run"], 3)
        self.assertEqual(self.ablation["experiments_executed"], 3)
        self.assertLessEqual(len(self.card["note"]), 140)
        gate_res = assess(self.card)
        self.assertEqual(gate_res["verdict"], self.card["verdict"])
        self.assertFalse(gate_res["ok_to_submit"])
        self.assertFalse(self.card["ok_to_submit"])

    def test_nine_sites_and_html_links_consistent(self) -> None:
        audited_sites = {s["site"] for s in self.nine["sites"]}
        self.assertEqual(audited_sites, FOCUS_9)

        sha = self.card["raster_sha256"]
        fname = self.card["submission_name"]
        for doc_rel in ("README.md", "docs/crsb-gub/index.html", "docs/crsb-gub/executive-summary.html", "docs/crsb-gub/research.md"):
            txt = (ROOT / doc_rel).read_text(encoding="utf-8")
            self.assertIn(sha, txt, f"{doc_rel} missing exact GeoTIFF SHA-256")
            self.assertIn(fname, txt, f"{doc_rel} missing exact GeoTIFF filename")
            if doc_rel != "docs/crsb-gub/executive-summary.html":
                for site in FOCUS_9:
                    self.assertIn(site, txt, f"{doc_rel} missing {site}")

        for html_name in ("index.html", "executive-summary.html"):
            html_dir = ROOT / "docs" / "crsb-gub"
            html_txt = (html_dir / html_name).read_text(encoding="utf-8")
            for attr_m in re.finditer(r'(?:href|src)="([^"]+)"', html_txt):
                target = attr_m.group(1)
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                resolved = (html_dir / target).resolve()
                self.assertTrue(resolved.exists(), f"Broken relative link {target} in docs/crsb-gub/{html_name}")


if __name__ == "__main__":
    unittest.main()

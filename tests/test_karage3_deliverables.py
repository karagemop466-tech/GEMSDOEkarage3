"""End-to-end automated verification tests for GEMSDOEkarage3 Lane H-K3B-1 (CSST-BGHF) deliverables.
Works both locally (with `.cache/`) and on clean GitHub Actions CI checkouts (without `.cache/`).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "src", ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from gems32 import csst_bghf, submission  # noqa: E402
from scripts.promotion_gate import assess  # noqa: E402

FOCUS_9 = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class DeliverableVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.card = json.loads((ROOT / "docs" / "csst-bghf" / "run-card.json").read_text(encoding="utf-8"))
        self.ev_card = json.loads((ROOT / "evidence" / "csst_bghf_run_card.json").read_text(encoding="utf-8"))
        self.ablation = json.loads((ROOT / "evidence" / "csst-bghf-ablation-results.json").read_text(encoding="utf-8"))
        self.canary = json.loads((ROOT / "evidence" / "leakage-canary-57ch.json").read_text(encoding="utf-8"))
        self.uniq = json.loads((ROOT / "evidence" / "complete-registry-uniqueness-scan.json").read_text(encoding="utf-8"))
        self.nine = json.loads((ROOT / "evidence" / "nine-site-audit-20261028.json").read_text(encoding="utf-8"))

    def test_saved_geotiff_and_zip_strict_0_1_and_no_nan_hazard(self) -> None:
        self.assertEqual(self.card, self.ev_card)
        dl_dir = ROOT / "docs" / "csst-bghf" / "downloads"
        nan_files = list(dl_dir.glob("*-nan.tif"))
        self.assertEqual(nan_files, [], "No -nan.tif hazard file may exist in docs/csst-bghf/downloads/")

        tif_path = ROOT / self.card["submission_file"]
        zip_path = ROOT / self.card["zip_submission_file"]
        self.assertEqual(tif_path.parent, dl_dir)
        self.assertTrue(tif_path.exists(), f"Missing {tif_path}")
        self.assertTrue(zip_path.exists(), f"Missing {zip_path}")
        self.assertTrue(self.card["submission_name"].startswith("gemsdoekarage3-"))

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

    def test_leakage_canary_57ch_and_strict_lidar_isolation(self) -> None:
        self.assertTrue(self.canary["passed"])
        self.assertEqual(self.canary["n_features_tested"], 57)
        self.assertLessEqual(self.canary["max_oriented_auc"], 0.90)
        self.assertEqual(csst_bghf.LIDAR_GLOBAL_COLS_57, {45, 46, 47, 48, 54})
        self.assertEqual(len(csst_bghf.MNOLIDAR_COL_INDICES_52), 52)
        for col in csst_bghf.LIDAR_GLOBAL_COLS_57:
            self.assertNotIn(col, csst_bghf.MNOLIDAR_COL_INDICES_52)

    def test_uniqueness_across_112_repos_k3_ccl_and_focus9(self) -> None:
        self.assertGreaterEqual(self.uniq["n_unique_rasters_checked"], 1900)
        self.assertTrue(self.uniq["stage1_surface_passed_all_rasters"])
        self.assertTrue(self.uniq["stage2_discrete_candidates_passed"])
        self.assertTrue(self.uniq["focus9_all_passed"])
        self.assertLessEqual(abs(self.uniq["worst_surface_spearman_all"]["surface_spearman"]), 0.90)
        self.assertLessEqual(abs(self.uniq["worst_dots_spearman_all"]["dots_spearman"]), 0.90)
        self.assertLessEqual(self.uniq["worst_discrete_3px_overlap"]["within_3px_fraction"], 0.70)
        self.assertEqual(set(self.uniq["per_focus_site"].keys()), FOCUS_9)

        ccl_cmp = self.card["registry_correlation_and_overlap"]["sibling_lane_k3_ccl"]
        self.assertLessEqual(ccl_cmp["within_3px_fraction"], 0.70)
        self.assertLessEqual(abs(ccl_cmp["dots_spearman"]), 0.90)
        self.assertFalse(self.card["registry"]["literal_all_rasters_final_passed"])

    def test_three_experiment_budget_dual_point_win_and_gate_consistency(self) -> None:
        self.assertEqual(self.card["experiments_run"], 3)
        self.assertEqual(self.ablation["experiments_executed"], 3)
        self.assertLessEqual(len(self.card["note"]), 140)
        self.assertEqual(self.card["verdict"], "negative")
        self.assertFalse(self.card["ok_to_submit"])

        exp3 = self.ablation["experiments"]["EXP-3"]
        champ = self.ablation["baseline_champion_02778"]
        self.assertGreater(exp3["hide_and_recover_v3"]["pooled_dti"], champ["hide_and_recover_v3"]["pooled_dti"])
        self.assertGreater(exp3["detached_600m_segments"]["pooled_dti"], champ["detached_600m_segments"]["pooled_dti"])
        self.assertGreater(
            exp3["sgmc_off_catalogue_v3"]["prevalence_calibrated_dti"],
            champ["sgmc_off_catalogue_v3"]["prevalence_calibrated_dti"],
        )

        gate_res = assess(self.card)
        self.assertEqual(gate_res["verdict"], "negative")
        self.assertFalse(gate_res["ok_to_submit"])

    def test_csst_operators_and_binary_shared_writer_unit(self) -> None:
        rng = np.random.default_rng(7)
        h, w = 48, 48
        foot = np.ones((h, w), dtype=bool)
        foot[:3, :] = False
        rtp = rng.normal(0.0, 25.0, size=(h, w)).astype(np.float32)
        hgrad, z_n0, pg = csst_bghf._baranov_pseudogravity_and_euler_depth(
            rtp, foot, dx_m=100.0, z_stab_m=150.0, compute_pseudograv=True, pad_px=8
        )
        self.assertEqual(hgrad.shape, (h, w))
        self.assertEqual(pg.shape, (h, w))
        self.assertEqual(pg.dtype, np.float32)
        self.assertTrue(np.isfinite(pg).all())
        self.assertEqual(z_n0.shape, (h, w))
        self.assertTrue(np.isfinite(z_n0).all())
        self.assertGreaterEqual(float(z_n0[foot].min()), 0.0)

        vis = np.zeros((h, w), dtype=bool)
        vis[12:34, 24] = True
        gm, _ = csst_bghf.coulomb_tip_vs_shadow_gate(vis, foot)
        self.assertEqual(gm.shape, (h, w))
        self.assertTrue(np.isfinite(gm).all())
        self.assertGreater(float(gm[10, 24]), float(gm[23, 29]))
        self.assertEqual(float(gm[~foot].max()), 0.0)

        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td, patch.multiple(
            submission,
            EXPECTED_HEIGHT=16,
            EXPECTED_WIDTH=16,
            EXPECTED_FOOTPRINT_PIXELS=256,
            EXPECTED_TOTAL_PIXELS=256,
        ):
            td_p = Path(td)
            tmpl = td_p / "tmpl.tif"
            with rasterio.open(
                tmpl, "w", driver="GTiff", height=16, width=16, count=1, dtype="float32",
                crs="EPSG:32611", transform=from_origin(243350.0, 4508550.0, 100.0, 100.0), nodata=None,
            ) as ds:
                ds.write(np.zeros((16, 16), dtype=np.float32), 1)
            f16 = np.ones((16, 16), dtype=bool)
            l16 = np.zeros((16, 16), dtype=bool)
            probs = np.full((16, 16), 0.37, dtype=np.float32)
            with self.assertRaisesRegex(ValueError, "exactly 0 or 1"):
                submission.write_submission_pair(
                    probs, f16, l16, tmpl, td_p, slug="soft-test", timestamp_tag="20261028T000000Z",
                    candidate_meta={},
                )
            self.assertEqual(list(td_p.glob("*zeros.tif")), [])
            mask = np.zeros((16, 16), dtype=bool)
            mask[5, 5] = True
            meta = {"candidate_id": "UNIT", "description": "synthetic test only",
                    "submission_note_zeros": "test", "submission_note_nan": "test",
                    "catalogue_hidden_mean": None, "catalogue_hidden_per_quadrant": {},
                    "sgmc_prevalence_calibrated_dti": None, "drift_corrected_holdout_mean": None,
                    "drift_corrected_per_quadrant": {}, "predicted_leaderboard_dti": None,
                    "ei_drift_corrected": None, "slot_decision": "HOLD-DO-NOT-SUBMIT"}
            rec = submission.write_submission_pair(
                mask, f16, l16, tmpl, td_p, slug="binary-test", timestamp_tag="20261028T000000Z",
                candidate_meta=meta,
            )
            self.assertTrue(rec["zeros_tif"]["filename"].startswith("gemsdoe32-binary-test-"))
            self.assertTrue(rec["zeros_tif"]["all_checks_passed"])
            with rasterio.open(td_p / rec["zeros_tif"]["filename"]) as ds:
                read_back = ds.read(1)
            self.assertEqual(float(read_back[5, 5]), 1.0)

    def test_nine_sites_html_links_and_rfc8259_json(self) -> None:
        audited_sites = {s["site"] for s in self.nine["sites"]}
        self.assertEqual(audited_sites, FOCUS_9)

        sha = self.card["raster_sha256"]
        fname = self.card["submission_name"]
        for doc_rel in (
            "README.md",
            "docs/csst-bghf/index.html",
            "docs/csst-bghf/executive-summary.html",
            "docs/csst-bghf/research.md",
        ):
            txt = (ROOT / doc_rel).read_text(encoding="utf-8")
            self.assertIn(sha, txt, f"{doc_rel} missing exact GeoTIFF SHA-256")
            self.assertIn(fname, txt, f"{doc_rel} missing exact GeoTIFF filename")
            self.assertIn("DO NOT SUBMIT", txt, f"{doc_rel} missing DO NOT SUBMIT")
            if doc_rel in ("README.md", "docs/csst-bghf/index.html"):
                for site in FOCUS_9:
                    self.assertIn(site, txt, f"{doc_rel} missing {site}")

        for html_rel in (
            "index.html",
            "executive-summary.html",
            "docs/csst-bghf/index.html",
            "docs/csst-bghf/executive-summary.html",
            "docs/index.html",
            "docs/executive-summary.html",
            "docs/crsb-gub/index.html",
            "docs/crsb-gub/executive-summary.html",
            "docs/ccl/index.html",
        ):
            hp = ROOT / html_rel
            html_txt = hp.read_text(encoding="utf-8")
            for attr_m in re.finditer(r'(?:href|src)="([^"]+)"', html_txt):
                target = attr_m.group(1)
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                resolved = (hp.parent / target.split("#")[0]).resolve()
                self.assertTrue(resolved.exists(), f"Broken relative link {target} in {html_rel}")

        for jp in (ROOT / "docs").rglob("*.json"):
            json.loads(
                jp.read_text(encoding="utf-8"),
                parse_constant=lambda c: (_ for _ in ()).throw(ValueError(f"Invalid JSON token {c} in {jp}")),
            )


if __name__ == "__main__":
    unittest.main()

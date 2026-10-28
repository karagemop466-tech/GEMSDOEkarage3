"""Fail-closed verification of the current decision and archived raster bytes."""
from __future__ import annotations

import hashlib
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/downloads/gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-zeros.tif"


class DownloadLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tif_downloads = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "a":
            values = dict(attrs)
            if "download" in values and str(values.get("href", "")).lower().endswith(".tif"):
                self.tif_downloads.append(values["href"])


class CurrentDecisionTests(unittest.TestCase):
    def test_current_run_is_negative_and_no_slot_is_selected(self) -> None:
        card = json.loads((ROOT / "evidence/run_card.json").read_text())
        readiness = json.loads((ROOT / "docs/readiness.json").read_text())
        self.assertEqual(card["verdict"], "negative")
        self.assertFalse(card["ok_to_submit"])
        self.assertFalse(card["slot_selected"])
        self.assertEqual(card["experiments_run"], 0)
        self.assertIsNone(card["raster_sha256"])
        self.assertFalse(readiness["ready_for_experiment"])
        self.assertFalse(readiness["ok_to_submit"])

    def test_archived_tif_bytes_are_valid_format_but_not_released(self) -> None:
        self.assertTrue(ARCHIVE.is_file())
        digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
        self.assertEqual(digest, "f21a0e831e6307d1d8230119c4d2f9812646fa8b092b2326b180a54feccea33f")
        with rasterio.open(ARCHIVE) as ds:
            self.assertEqual(ds.count, 1)
            self.assertEqual(ds.dtypes[0], "float32")
            self.assertEqual(ds.shape, (3730, 3292))
            self.assertEqual(ds.crs.to_epsg(), 32611)
            self.assertEqual([round(float(v), 4) for v in ds.transform[:6]], [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0])
            self.assertIsNone(ds.nodata)
            values = ds.read(1)
        self.assertTrue(np.isfinite(values).all())
        self.assertGreaterEqual(float(values.min()), 0.0)
        self.assertLessEqual(float(values.max()), 1.0)
        self.assertEqual(int((values > 0).sum()), 37654)
        for page in (ROOT / "docs/index.html", ROOT / "docs/executive-summary.html"):
            text = page.read_text()
            expected = "No file is ready" if page.name == "index.html" else "NO FILE IS APPROVED FOR SUBMISSION"
            self.assertIn(expected, text)
            parser = DownloadLinks()
            parser.feed(text)
            self.assertEqual(parser.tif_downloads, [])

    def test_literal_registry_overlap_witness_stops_37654_dot_candidate(self) -> None:
        card = json.loads((ROOT / "evidence/run_card.json").read_text())
        witness = card["registry"]["budget_witness"]
        self.assertEqual(witness["candidate_dots"], 37654)
        self.assertEqual(witness["limit"], 0.70)
        self.assertGreater(witness["min_fraction_near_registered_lattice"], witness["limit"])
        self.assertTrue(witness["duplicate_stop_proven_for_this_budget"])

    def test_all_nine_historical_files_are_research_only(self) -> None:
        report = json.loads((ROOT / "docs/historical-raster-audit.json").read_text())
        expected = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
        self.assertEqual({row["site"] for row in report["rasters"]}, expected)
        self.assertEqual(len(report["pairwise"]), 72)
        self.assertFalse(report["new_submission_generated"])
        self.assertFalse(report["complete_registry_checked"])


if __name__ == "__main__":
    unittest.main()

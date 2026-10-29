# NOT CLEARED — do not download or submit

Files: `karage3-unique-offcat-20261029T180337Z-6a8c2368-{zeros,nan}.tif` (+ zip, metadata).
Moved here from `docs/downloads/` on 2026-10-29 because the earlier front page labelled them
"READY TO DOWNLOAD". They are not cleared.

Measured on 2026-10-29 against the pinned lattice witness `13GEMSDOE r13-lattice-s5`
(`.cache/witness/lattice.tif`, SHA-256 `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`,
fetched from https://codeload.github.com/buffedlizard55-lab/13GEMSDOE/tar.gz/92ee6f074323f161eed837b80ec3ee5b662e26f5):

| Check | Result |
|---|---|
| Dots emitted | 12,000 |
| Dots inside the competition footprint (5,167,373 cells) | **4,517** (37.6%) |
| Dots outside the footprint | **7,483 (62.4%)** |
| Overlap of in-footprint dots with lattice (≤3 px) | **99.89%** (4,512 of 4,517) |
| Overlap of all dots, as reported by the "37.65%" figure | 37.65%, only because 62.4% of dots lie outside the footprint |
| Value written outside footprint | 0.0 (finite); template uses NaN there |
| `-nan.tif` vs `-zeros.tif` | Pixel-identical float32 arrays; the `-nan` file contains **0** NaN pixels (only the nodata tag differs) |
| Generator script in repo | **none** (no reproducible build) |

Why this is not a valid submission: the apparent uniqueness comes from placing most dots outside the
scored footprint, where the lattice has no dots. Those dots are not geology, and the file's in-footprint
content is 99.89% lattice. The earlier label "0.00% overlap" and the metadata "44.6% theoretical minimum"
are both inconsistent with these measurements.

Verdict: **negative** — do not download, do not submit.

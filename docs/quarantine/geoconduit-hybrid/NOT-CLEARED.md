# NOT CLEARED — H-GEO-CONDUIT hybrid candidate

Files: `gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-{zeros.tif,nan.tif,zeros.zip}`.
Moved from `docs/downloads/` on 2026-10-29 during the merge of PR #46 with `main`. The candidate
card itself says "archived for protocol review; not approved for submission", but the file sat in
the public download folder.

Measured 2026-10-29 against the pinned lattice witness `13GEMSDOE r13-lattice-s5`
(`.cache/witness/lattice.tif`, SHA-256 `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`):

| Check | Result |
|---|---|
| Dots | 35,615, all inside the 5,167,373-cell footprint |
| Dots within 3 px of lattice | **99.83%** |
| Values inside footprint | 0.000 to 1.000, no NaN |
| Candidate card | `final_dots_overlap_max_3px: null`; registry status `NOT PASSED` |

Verdict: **negative**. The literal rule is at most 70% of dots within 3 px of any registry raster, and
this file is far above that. Its HOLDOUT-DTI (0.4239, 95% CI [0.4053, 0.4427], copied from the candidate
card and not reproduced here) does not change the decision. Do not download or submit this file.

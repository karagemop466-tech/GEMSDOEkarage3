# Submission downloads

## Current status: no file is cleared (2026-10-29)

- **OK TO DOWNLOAD: NO. OK TO SUBMIT: NO.** The newest candidate, `karage3-lgap-scarpstep-19k-20261029-4fc40bd1`, is **not published** here. Its card is `karage3-lgap-scarpstep-19k-20261029-4fc40bd1-card.json`. The card records the blocking reasons: it fails the literal full-inventory uniqueness rule (106 of 1,977 compared registry rasters above 70%).
- Guide, nine-site table and irregularities: `../submit-now/index.html`.
- `scripts/make_submission_card.py` publishes a TIF into this folder only when every gate passes.

## Retained research artifacts: DO NOT SUBMIT

All other TIFFs in this folder fail the literal registry overlap stop (see `../../evidence/retained-submissions-audit-20261028.json`).
- `karage3-unique-offcat-20261029T180337Z-6a8c2368-zeros.tif`: 4,517 dots inside the footprint (its metadata says 12,000); 99.89% within 3 px of the r13 lattice. Its `-nan.tif` sibling has no NaN cells (zeros outside), despite the name.
- Old sidecars and ZIPs retain historical run claims for reproducibility and do not provide current submission authorization. No raster bytes were modified.

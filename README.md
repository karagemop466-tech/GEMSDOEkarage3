# GEMSDOEkarage3 — evidence before submission

> **Current decision: DO NOT SUBMIT.** This checkout has no newly generated,
> validated, unique TIFF and no approved weekly slot. [Executive summary and
> submission guide](docs/executive-summary.html) · [evidence review](research/2026-10-27-review.md)
> · [run card](evidence/run_card.json). A research download is not permission to upload.

## Project brief — read at the start of every session

The user wants a reproducible, autonomous system that discovers previously
unmapped **faults relevant to geothermal resources** and ultimately competes at
the top of the [DOE GEMS Prize](https://www.drivendata.org/competitions/306/competition-doe-gems/)
leaderboard. The user prioritizes a **new, unique, valid, easy-to-download
single-band GeoTIFF**, a clear executive decision, comparative coverage of
GEMSDOE24/25/27/28/30/31/32/33/36, official links and auditable provenance. Do
not rename or copy a prior submission as a new one, fabricate a score, spend a
weekly slot on an unvalidated idea, or claim automatic approval based only on
file format. Use **Maximize P(Win)** and **Own the Outcome**: report negative
results and unblock work responsibly rather than exaggerating confidence.

### Binding parallel-run protocol (user's instructions)

1. Stay in the **one assigned method lane**. Stop as a duplicate if pre-placement
   surface or final-dot rank correlation with any registry raster exceeds 0.90,
   or if more than 70% of candidate dots lie within three pixels of one registry
   raster. Check surface *before* placement and final dots; do not exempt a
   registry entry silently.
2. Reuse the shared cached feature stack, `evaluate_holdout.py`, and
   `submission_writer.py`; fix shared defects upstream, never as a private
   evaluator/writer fork. Hide whole fault segments with a buffer; derive all
   catalogue features solely from visible faults; mask visible faults exactly;
   score pooled distance-weighted Tversky (alpha 0.2, beta 0.8, 300 m triangular
   kernel). A static full-catalogue prediction is not automatically leakage-safe.
3. Label performance as **HOLDOUT-DTI** (evaluator, withheld positives, 95% CI)
   or **ORGANIZER-CONFIRMED** (actual submission-page receipt). A projection is
   not a score. Unreceipted user/owner claims must remain explicitly unverified;
   public leaderboard observations are not file-bound receipts.
4. Run each feature alone as a leakage canary; AUC over 0.90 is leakage until
   proven otherwise. Compare the top idea to a matched, current same-instrument
   holdout best before using any slot.
5. End with a JSON run card: hypothesis, mechanism, named non-fault mimic,
   holdout/CI, registry correlation/overlap, raster SHA-256, validator output,
   name/note ≤140 characters, and verdict `promote` or `negative`.
6. Stop after at most three experiments or two hours. Promotion to a real slot is
   a **separate selector step**, respecting the actual page's weekly cap. The
   official rules PDF states three submissions per week; current account usage
   is unavailable. Disclose generative-AI use in the required narrative and
   preserve reproducible code/documentation as specified in the rules.

Before implementing an assigned lane, record three to five ranked geological
hypotheses with layers, physical signals, unmapped-fault rationale, competing
non-fault processes, implementation costs, prior-art comparison, and accessible
free official sources. Use qualified qualitative expectations, not a projected
score. Work autonomously; run at least three review/testing passes, report
irregularities, and provide official source links. The user also requests a clean
GitHub Pages site, an executive submission guide, a current source feed, a PR
and merge, and next steps/limitations.

The “single method paragraph below” referred to in the supplied prompt is not
present in this checkout or the request. The literal registry includes a
space-filling lattice that makes the customary dot budget fail the uniqueness
rule. This is a genuine coordination conflict, not a license to invent a lane,
ignore a comparator, or fabricate a TIFF. See the detailed analysis below.

## Current verified work

* [Nine-site historical table and exact submission steps](docs/executive-summary.html).
* [Scientific review, four untested hypotheses, official sources, defects and next steps](research/2026-10-27-review.md).
* [Independent geometry-audit receipt](evidence/geometry_audit.json),
  [hash-pinned input manifest](registry/historical.json), and
  [negative JSON run card](evidence/run_card.json).
* The pinned owner-supplied template, nine historical raster bytes, a calibration
  lattice and label raster were fetched from GitHub and hash-checked. They are
  **not organizer-authenticated**. No feature cache, valid new model, holdout
  estimate, candidate TIFF, slot approval, or artifact-linked score receipt exists.
* `scripts/check_format.py` independently checks saved bytes without clipping or
  repairing them. It is **not** the shared writer and cannot authorize upload.
  [Upstream shared-tool issue #37](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/37)
  remains open: the named CLI and writer binarize probability inputs silently.
* The browser can refresh public GitHub commit metadata without credentials;
  failures are marked unavailable and never change authorization. The official
  leaderboard value in the checked-in feed is a dated snapshot, not live. A
  scheduled Pages-refresh workflow is present but gated: this integration
  received HTTP 403 when changing the repository's legacy Pages source. An
  authorized repository admin must enable the Actions source and set repository
  variable `ACTIONS_PAGES_ENABLED=true` before scheduled artifact deploys work.
  Legacy Pages can serve the dashboard through the root redirect in the meantime.

## Reproduce the geometric review

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
# Uses gh authentication/configuration if available; no competition credentials.
.venv/bin/python scripts/audit_registry.py --fetch
# Format diagnosis only. Example here is an old raster; DO NOT SUBMIT it.
.venv/bin/python scripts/check_format.py .cache/historical/GEMSDOE32.tif \
  --template .cache/historical/template.tif
.venv/bin/python -m unittest discover -s tests -v
```

The nine historical inputs and lattice are cached outside Git; the report is
small and reproducible. One failing comparator proves a stop; this subset alone
cannot prove a full-registry pass. The official sample is login-walled. Never
infer portal acceptance or hidden-test performance from these diagnostics.

## Official resources

[Problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ·
[Official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) ·
[Data tab (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) ·
[Reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) ·
[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) ·
[USGS 3DEP](https://www.usgs.gov/3d-elevation-program) ·
[DOE GDR INGENIOUS dataset](https://gdr.openei.org/submissions/1391).

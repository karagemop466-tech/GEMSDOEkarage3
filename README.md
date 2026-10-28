# GEMSDOEkarage3 — evidence-first fault discovery

## Current decision: DO NOT SUBMIT — literal uniqueness gate failed

**No new approved TIFF was generated on 2026-10-28. No weekly slot was used.**
The previous “OK TO SUBMIT” claim is withdrawn. The retained SMGC, CRSB-GUB and
K3 rasters overlap a registered calibration lattice above the required 70% / 3 px
threshold. Different file hashes do not establish a different geological submission.

[Executive summary and nine-site table](executive-summary.html) ·
[Live site](https://karagemop466-tech.github.io/GEMSDOEkarage3/) ·
[Current review](research/2026-10-28-review.md) ·
[Saved-byte audit](evidence/retained-submissions-audit-20261028.json) ·
[Current run card](docs/review-run-card.json)

### What was verified

* Restored the hash-pinned template, labels, nine historical TIFFs and lattice from
  GitHub mirrors; reproduced `evidence/geometry_audit.json` exactly apart from time.
  These are owner mirrors, not organizer-authenticated downloads.
* Independently checked every retained TIFF, without changing any raster bytes.
  Format compliance is separate from scientific quality and uniqueness.
* SMGC zero-filled TIFF is finite and in [0,1], with matching mirrored grid, but
  99.6866% of its dots are within 3 px of the lattice: **duplicate stop**.
* The nine-site historical summary is on this repository's executive page. We did
  not modify the nine other repositories or pretend their sites were updated.
* Historical leaderboard values are USER-REPORTED / UNVERIFIED without a hash-bound
  organizer receipt. A new hidden leaderboard score is **not estimable** here.

### Start here every session

Read this README, `AGENTS.md`, `knowledge/owner_brief.md`, the latest dated review,
and `docs/review-run-card.json`. Maximize P(Win): preserve scarce slots and reject
unsupported improvements. Own the Outcome: reconcile contradictory receipts,
validate actual saved bytes, and disclose failure instead of relabeling it success.
The task is fault-trace prediction relevant to geothermal resources, not direct
proof of geothermal vents. The supplied prompt's leaderboard snapshots conflict;
do not call any of them current without a fresh organizer observation.

### Reproduce locally (CPU audit; no training or submission)

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/audit_registry.py --fetch --out .cache/reproduced-geometry.json
.venv/bin/python scripts/check_reproduction.py evidence/geometry_audit.json .cache/reproduced-geometry.json
.venv/bin/python -m scripts.audit_retained_submissions --fetch
.venv/bin/python scripts/build_comparison.py
.venv/bin/python scripts/build_site.py --check
PYTHONPATH=src .venv/bin/pytest -q
npm ci && npm test
```

`evaluate_holdout.py` and `submission_writer.py` remain the shared entry points;
no private metric or writer was introduced. Cached model features are absent in a
fresh checkout. The prompt has no single assigned method paragraph: no new lane
was invented. The literal lattice gate already stops the retained normal-budget
candidates, so training a replacement under an invented exemption is not allowed.

### Retained research files (NOT authorized downloads)

| Method | File | SHA-256 |
|---|---|---|
| SMGC | `gemsdoe32-hk3-smgc-maxenv-axial28-37654-20261027T213000Z-c886c782-zeros.tif` | `f21a0e831e6307d1d8230119c4d2f9812646fa8b092b2326b180a54feccea33f` |
| CRSB-GUB | `gemskarage3-h-k3-1-crsb-gub-maxenv-d30-20261027T180000Z-1560731a-zeros.tif` | `2a1fed302d1fe1c556c86467ef687782d30eedf5361eff57a711ae5925a237c3` |

Files remain in `docs/downloads/` for reproducibility, not competition use.
NaN-outside companions fail the whole-array-finite portal diagnostic. Zero filling
passes that diagnostic, but organizer acceptance and conservative outside-null
wording remain separate questions; format alone never authorizes a slot.

### Next session priorities and limitations

1. Establish an explicit assigned method lane and a consistent registry policy.
   The current rule includes lattices and dense probes; do not silently exempt them.
2. Freeze folds, visible-only feature derivation, evaluator version, incumbent rule,
   feature AUC canaries, paired spatial-bootstrap CI and the complete registry.
3. Restore the pinned feature cache and verify exact sources/licensing. External
   data binary access is restricted here to the allowed GitHub/package hosts.
4. Only then test at most three experiments and run the independent selector within
   the weekly cap. This project does not have a DrivenData authenticated session.
5. Organizer receipts must bind scores to actual submitted files. Current holdout
   reports are retained research evidence, not forecasts or authenticated live results.

## Standing requirements (prior-session condensed prompt; not a verbatim transcript)

<details>
<summary><strong>Click to expand the standing requirements preserved from the prior session</strong></summary>

```text
Maximize P(Win). No excuses. Own the outcome.
Please review the entire repo, then build and update the project as needed. Do not fabricate anything or hallucinate. Our goal is to win the DOE GEMS competition by creating a submission that gets a higher score than the current high on the leaderboard of 0.4413; all files must be validated by the project without human intervention and the project should clearly indicate whether a file is ok to download and submit or not. Right now the submission I downloaded and submitted had an error of "Predicted values must be in range [0, 1]".

Please focus on analyzing the highest scoring submissions from GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Then answer the following questions with PhD level analysis: why and how did h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros on https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html get a score of 0.2778 which is the highest of any of those sites? Can we generate a submission that gets a higher score? If so, how? Make sure our project has an executive summary on every one of those sites (GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36) and a table that compares them and lists what file to download and what their estimated or actual score is and whether they are unique or not.

We MUST GENERATE A UNIQUE TIF SUBMISSION! Do not copy a previous submission, except for learning or comparison purposes! Whatever we generate MUST be a unique tif submission unlike any of those on the sites listed below! Also provide a unique name and a short note <= 140 characters to help distinguish the submission in the contest. Also make it easy to download at the very beginning of our site in an obvious Executive Summary and have an executive summary subpage explaining step by step how to submit into the contest.

Before writing any model code, read the GEMS feature list and generate 3-5 novel candidate geological hypotheses that have not been tried yet. For each hypothesis, name: (1) the specific layer(s) involved, (2) the physical signature you are targeting, (3) why it would catch faults/geothermal vents missing from the USGS/INGENIOUS catalogue rather than ones already in it, and (4) how it differs from existing implementations. Rank them by expected DTI improvement and implementation cost, then implement and validate the top candidate on the spatially-blocked holdout set.

Parallel-run protocol (keep every run short, comparable, and non-duplicative):
1) Lane: Stay inside your assigned method lane. If raster rank-correlation with any registry raster exceeds 0.90, or >70% of your dots fall within 3 px of a registry raster's dots, log as a duplicate and stop. Check both on the continuous surface before placement AND on final dots.
2) Reuse, don't rebuild: Use the template's cached feature stack, evaluate_holdout.py, and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive any catalogue-based features only from visible faults, mask visible faults pixel-exactly, and score pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel). If a shared tool in the template is wrong, fix it there — no private forks.
3) Label every number: Every score must be labeled either HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). Never write a projection as a score.
4) Leakage canary: Test each feature alone on holdout before trusting results. Single-feature AUC > 0.90 indicates leakage until proven otherwise.
5) Run card: End with one JSON card containing: hypothesis, mechanism, mimic (a named non-fault process that could mimic it), holdout_dti + ci, correlation_overlap_vs_registry, raster_sha256, validator_output (no NaN inside footprint, values in [0,1], CRS/shape/transform match), submission_name + note (<=140 chars), and verdict (promote / negative). A clean negative is a valid deliverable.
6) Budget: Stop after at most 3 experiments or 2 hours.

Confirm that we generated and validated a unique single-band GeoTIFF (.tif) without human intervention that matches the dimensions, CRS (EPSG:32611), and geotransform of example_submission.tif, with predicted values in [0, 1] and no NaNs inside the study footprint. Also please put this prompt into the repo README.md as a standing reference.

Run your work through 3 passes to ensure and verify completeness:
Pass 1 — Execute the task: implement the solution and verify it works.
Pass 2 — Review and refine: check your work for bugs, missing requirements, and edge cases, then fix anything you find.
Pass 3 — Final verification: re-check everything against the original request and polish for accuracy, reliability, and completeness.

Remember to create a pull request and merge the PR into main. Finally, report any remaining limitations and the highest-priority next steps for the next session.
```

</details>

The local promotion screen additionally requires a pinned registry manifest digest and per-reference correlation **and** overlap measurements at both pre-placement and final-dot stages. It checks card consistency only: a digest in a card does not prove the inventory complete or current. A separate evidence audit and selector remain mandatory.

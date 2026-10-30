# GEMSDOEkarage3 — evidence-first fault mapping

## START HERE — executive summary (reviewed 2026-10-30)

**Current repo review:** [docs/repo-review-2026-10-30.md](docs/repo-review-2026-10-30.md). Tests pass after two previously unindexed TIFF variants were added to the saved-byte audits. No candidate is cleared for submission; this work did not generate a new candidate or use a slot.

**Session 7 (2026-10-30), latest:** the upload page that named a non-cleared file is withdrawn; the `-zeros` format advice is corrected against the official rule. Details in the Session 7 section below. Answer: **NO**.

## Previous executive summary (2026-10-29)

**OK TO DOWNLOAD AND SUBMIT? NO — no file is cleared for a leaderboard slot.**

- **Executive summary (table of all nine sites + the new file):** [docs/nine-site-summary.html](docs/nine-site-summary.html) · run card [docs/nine-site-run-card.json](docs/nine-site-run-card.json)
- **New TIF generated this session (NOT unique):** `karage3-k4-offcat-ridge-20k` — [zeros TIF](docs/downloads/gemsdoe32-karage3-k4-offcat-ridge-20k-20261029T183711Z-2a6558a3-zeros.tif) · [zip](docs/downloads/gemsdoe32-karage3-k4-offcat-ridge-20k-20261029T183711Z-2a6558a3-zeros.zip). Format-valid, but it FAILS the full-registry literal uniqueness scan (108 of 2,051 same-grid registry rasters exceed the 3-px or rho gate; evidence in `evidence/k4-literal-uniqueness-scan.json`) and the holdout gate (HOLDOUT-DTI 0.0178 vs the nine-site best 0.0967). Do not submit it.
- **Portal error "Predicted values must be in range [0, 1]":** UNEXPLAINED. The `-nan.tif` files hold NaN outside the footprint, which matches the official rule "data outside the bounds is null or nan" ([problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format), checked 2026-10-30). The `-zeros.tif` files hold 0.0 outside, which does NOT match that rule. **The earlier advice to use only `-zeros.tif` is withdrawn** (see Session 7 below). No organizer answer resolves this yet.
- **Upload instructions:** [docs/how-to-submit.html](docs/how-to-submit.html) previously told the user to upload a file. That was wrong; the page is now a DO-NOT-UPLOAD notice (Session 7).
- **Reported best (0.2778, GEMSDOE32) is not unique:** every focus file has a peer with ≥0.976 of its dots within 3 px. GEMSDOE30 is the same dot array as GEMSDOE25.
- **Score correction (2026-10-29):** the H-GEO-CONDUIT run card's HOLDOUT-DTI **0.4239** [0.4053, 0.4427] did not reproduce. The shared evaluator (`GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives) gives **HOLDOUT-DTI 0.3047** [95% CI 0.2881, 0.3189]. Not organizer-confirmed; not cleared. Evidence: `evidence/` and `scripts/evaluate_holdout.py`.
- **HOLDOUT-DTI, consensus-hgrad-k37654 (shared evaluator):** **0.0073** [95% CI 0.0043, 0.0109], `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, `promotion_eligible: false` (static diagnostic). Off-catalogue SGMC calibrated: 0.0091 [0.0050, 0.0135] (`GEMSDOE32-SGMC-CAL-v3.0`, 62,703 withheld positives). Source: `evidence/holdout-consensus-hgrad-20261029.json`. A negative result; not cleared.
- **Literal uniqueness:** all 11 measured candidates have max within-3 px overlap **1.0** with registry raster `apartanish22-droid/ApartGEMSDOE2 …top37654…e34db98d-nan.tif` (5,106,385 positive cells). Flagged for owner review, not exempted. Source: `evidence/site-uniqueness-20261029.json`.
- **Official public leaderboard check (NOT a submission receipt; fetched 2026-10-29, re-fetched 2026-10-30):** https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ lists rank #1 = **0.4544**, #2 = 0.3916, rank #48 = **0.3195** (kpomazi), rank #50 = 0.3169 (re-checked 2026-10-30). The prompt's **0.4413 does not appear** in the top 50. So **0.3195 is not the highest public score**. GEMSDOE32's user-reported 0.2778 is below rank 50 and not visible here. Public split only.
- **Labels:** HOLDOUT-DTI = local shared evaluator (withheld-positive count and 95% CI shown); USER-REPORTED = copied from the request; ORGANIZER-CONFIRMED = none exists yet.

## Session 7 (2026-10-30) — review, verification and corrections (read first)

**Answer to "download and submit?": NO. No file is cleared. Do not upload anything from this repository.**

- **Why no new unique TIF was generated:** a file can be cleared only after (a) the literal uniqueness gate against every registry raster, before placement and on final dots, (b) a matched holdout with leakage canaries, (c) the saved-byte format check, and (d) a separate slot selector. This checkout has no training feature stack (`.cache/` is absent), no complete registry, and no holdout run. Gates (a), (b) and (d) cannot be run here. A new file without them would be a guess, so none was made.
- **Fixed this session:**
  1. **Upload page withdrawn.** [docs/how-to-submit.html](docs/how-to-submit.html) told the user to upload `gemsdoe32-novel-faulthalo-…-zeros.tif`. That file fails the saved-byte audit (99.95% within 3 px of the witness, stop at 70%). The page is now a DO-NOT-UPLOAD notice.
  2. **Format advice corrected.** The official rule (verified at [the problem page, submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format)) says "data outside the bounds is null or nan". The `-zeros.tif` files write 0.0 there and fail `scripts/check_format.py` (`outside_null_or_nan`). The `-nan.tif` twins pass that check. The portal error is still unexplained, so the conflict is open for review, not settled.
  3. **Leaderboard figures re-checked** on the official public leaderboard (2026-10-30): #1 0.4544, #2 0.3916, #3 0.3911. The prompt's 0.4413 does not appear. 0.3195 is at **rank #48** (README previously said #47), and #50 is 0.3169 (previously 0.3167).
  4. **Test suite restored.** Six tests failed because two `consensus-hgrad` TIFs were added to `docs/downloads/` after the saved-byte receipts were last built. Regenerated, in order: `scripts/audit_saved_tiffs.py --fetch`, `scripts/audit_retained_submissions.py --fetch`, `scripts/audit_release_20261028.py`, `scripts/build_run_card.py`. Result: `pytest` 225 passed, 1 skipped, 0 failed. Both new files are rejected (overlap 99.89%, duplicate stop).
- **Irregularities flagged for review (not repaired):**
  - `evidence/k3c_run_card.json` is a historical card with `verdict: promote` and `ok_to_submit: true`. It is superseded by `docs/k3c/run-card.json` (negative). Keep it for provenance only; do not cite it as a clearance.
  - The GEMSDOE32 page cites 0.2778 as an **owner report** with no submission receipt in the repo. Treat it as unverified.
  - Only public-leaderboard numbers were re-checked here. The sandbox cannot reach DrivenData's login or data pages, so the training data cannot be downloaded from here.
- **Blockers that remain (owner action needed):**
  1. Download the DrivenData competition data from a logged-in browser and place it in `data/` (or `.cache/gems_data`), then run `scripts/prepare_data.py` and `scripts/restore_data.py`. Without this, no holdout can be run.
  2. Ask the DrivenData user forum (linked from the problem page) what happens to values outside the footprint: NaN, or 0.0. One answer resolves the `-nan` / `-zeros` conflict.
  3. Choose one assigned method lane (the repo still has none) and one hypothesis to test. The ranked next-hypotheses list in `research/2026-10-28-review.md` (section "Ranked next hypotheses") is planning only; none has been run.
- **Standing prompt:** see the STANDING REFERENCE PROMPT section below. It is a CONDENSED version of the owner brief, not the full text. The full brief is not yet stored in this repo; add it (or a verified copy) in the next session.

## Session 6 (2026-10-29) — correction and verification (read first)

- **Status page and review note (2026-10-29):** [docs/submit-now/index.html](docs/submit-now/index.html) (blocking reasons, nine-site table) · [evidence/review-note-20261029.md](evidence/review-note-20261029.md) (three review passes, irregularities, remaining work).
- **Answer to "download and submit?": NO.** No file is cleared. Two files were previously presented as downloadable and are now quarantined:
  - `karage3-unique-offcat-…tif` (front page had said "READY TO DOWNLOAD") → [docs/quarantine/karage3-unique-offcat/](docs/quarantine/karage3-unique-offcat/NOT-CLEARED.md)
  - H-GEO-CONDUIT hybrid `…0a6974d8-zeros.tif` (PENDING-REVIEW) → [docs/quarantine/geoconduit-hybrid/](docs/quarantine/geoconduit-hybrid/NOT-CLEARED.md)
- **Measured 2026-10-29** against the pinned lattice witness `13GEMSDOE r13-lattice-s5` (fetched from `codeload.github.com/buffedlizard55-lab/13GEMSDOE/tar.gz/92ee6f074323f161eed837b80ec3ee5b662e26f5`; file SHA-256 `b4570b40…` matches the pin; 206,895 dots):
  - karage3-unique-offcat: 4,517 of 12,000 dots inside the footprint, **99.89%** of those within 3 px. The remaining 7,483 dots sit outside the footprint, where the lattice has none. The earlier "0.00%" and "44.6%" labels were wrong. No generator exists in the repo.
  - H-GEO-CONDUIT: 35,615 dots, all inside the footprint, **99.83%** within 3 px. Its card records `final_dots_overlap_max_3px: null`; the registry check was never run.
- **Pages** are regenerated by `scripts/build_site.py` (and `build_k3c_site.py`, `build_preflight_site.py`, `build_release_review.py`, `build_focus9.py`). They say *NOT APPROVED / DO NOT SUBMIT*, and they carry the H-GEO HOLDOUT-DTI 0.4239 as NOT ESTABLISHED. `docs/how-to-submit.html` is rewritten with no upload step.
- **Saved-byte audit** (`scripts/audit_saved_tiffs.py --fetch`) now covers all 13 TIFFs under `docs/`. Every one has in-footprint overlap above 70% (range 99.34%–99.92%).
- **Tests:** `pytest` 200+ passed, 1 skipped (`main` itself had 12 failing on the same checks). `unittest discover` OK; `node --test tests/test_browser_feed.js` 2/2; `build_site.py --check` OK; `verify_numbers.py` 24/24. `check_readiness.py` exits 2 (blocked, as documented).
- **Public leaderboard, fetched 2026-10-29:** #1 `xiaofanhu` **0.4544**, #2 `cfld__` **0.3916**, #3 `Batik Shirt Brothers` 0.3911 ([leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)). The figures 0.4413 and 0.3195 from the request do not appear on this page. Site-level scores such as 0.2778 (GEMSDOE32) are **USER-REPORTED / UNVERIFIED**.
- **Irregularities for review:**
  1. `docs/readiness.json` reports `core_mirror_data: false` here because `.cache/gems_data` is absent in this checkout. The committed `true` came from another checkout.
  2. Both quarantined candidate families were committed to the public download folder without a passing uniqueness check.
  3. The shallow clone has one commit, so pre-edit pages cannot be recovered from git history. The generator output is now the reference.
  4. The H-GEO candidate's HOLDOUT-DTI (0.4239) is copied from its card and was not reproduced. It does not change the decision.
- **Not done this session:** no new candidate and no 3–5 hypothesis slate. Every in-footprint dot candidate tested is above 99% overlap with the lattice. The cached feature stack needed for a holdout run is absent from this checkout, so nothing could be validated. A new idea must first pass the uniqueness gate and then the holdout.

- **Historical artifact (research only, DO NOT SUBMIT):** H-K3B-1 CSST-BGHF file `gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif` (SHA-256 `4b47a37ecf91384b2202897dd695219d23375cab2a300106feaf541d60fc9c5b`), archived at [docs/csst-bghf](docs/csst-bghf/index.html). The nine focus sites compared in this repo are GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33 and GEMSDOE36 (research only).

### Added by this PR (session 6 branch, merged onto `main`)

- **All-dots reading is recorded alongside the footprint reading.** `scripts/audit_saved_tiffs.py` and `scripts/lattice_feasibility.py` report, per file, the all-positive-pixel count, the outside-footprint count, and the all-dots overlap. The `unique-offcat` file is the only one that passes the 70% rule under the all-dots reading (37.65%, via 7,483 outside dots). The other TIFFs under `docs/` fail under both readings (≥99.3%).
- **Restore receipt bug fixed.** `scripts/restore_data.py` used to overwrite the tracked 30-file `data/restore_receipt.json` on a partial `--group` run. Now only `--group all` writes it; a partial run writes `<target>/restore_receipt_<group>.json`. Regression test: `tests/test_restore_receipt.py`.
- **Measured the quarantined H-GEO zeros file** with the same lattice: 99.83% (35,615 dots, all inside). It fails the rule.
- **Stale upstream text.** `evidence/upstream/GEMSDOE33/README.md` (line 93) still says "YES — READY TO DOWNLOAD" for an older upstream file. It is a vendored snapshot, so it is flagged here and not edited. It is not this repo's current claim.
- **Owner decision still required** before any upload can be considered: (1) keep the literal rule (no dot-based file can pass); (2) re-scope the rule to discrete detectors and exempt the 206,895-dot calibration lattice; (3) state which overlap reading governs. Under any choice, dots outside the footprint fail the null-outside convention in the organizer template, and the complete-registry and rank-correlation checks still have to run.

---

## Session update (29 October 2026, later): READ FIRST — still DO NOT SUBMIT, and two earlier claims are corrected

1. **Submission status: NO file is cleared.** No new TIFF was generated this session. Reasons, with evidence: the proxies do not track the reported leaderboard, every nine-site top file already exists byte-for-byte on other sites, and the prompt's lane paragraph is missing. Details: [`docs/review-2026-10-29.md`](docs/review-2026-10-29.md) (session addendum).
2. **The official target is non-catalogue faults.** The DrivenData problem page says the test labels are faults *not* in the USGS database ([page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). The holdout in this repo withholds *catalogue* faults, so it measures a different target.
3. **Correction to the 0.4239 headline.** This session it reproduced exactly (0.42386) under the `visible_gated` variant (b=2 px gate) using an *uncommitted sandbox script*, so this supersedes item 4 of the Session 6 block above, which says it was not reproduced. The committed evaluator must be used to make this reproducible. The CLI's hide-and-recover evaluator gives **0.3047** (95% CI 0.2881–0.3189, 22,232 withheld positives). Both are HOLDOUT-DTI on a catalogue target, not leaderboard estimates.
4. **Calibration is negative.** Across 18 registry rasters with user-reported leaderboard values (unverified), the catalogue-holdout proxies have Spearman ρ = −0.55 (p = 0.018). The off-catalogue proxy shows no relationship (ρ = 0.08, p = 0.75). **No local proxy currently estimates a leaderboard score.** Evidence: [`evidence/proxy-calibration-20261029.json`](evidence/proxy-calibration-20261029.json) (script `scripts/proxy_calibration.py`).
5. **Uniqueness fails for all nine focus sites.** Each top file is byte-identical to a file in at least one other site's repository. Evidence: [`evidence/focus9-duplicate-audit-20261029.json`](evidence/focus9-duplicate-audit-20261029.json) (script `scripts/focus9_duplicate_audit.py`).
6. **Session run card:** [`docs/data/session-20261029-run-card.json`](docs/data/session-20261029-run-card.json).
7. **Leaderboard check (fetched 2026-10-29):** the [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) shows #1 xiaofanhu **0.4544**, #2 cfld__ 0.3916, #3 Batik Shirt Brothers 0.3911. Neither 0.4413 (prompt) nor 0.3195 appears. These are public-split scores; the final round is rescored on an expanded label set, so they are not final results.

Reproduce the local checks: restore core data with `python scripts/restore_data.py --group core` (and `--group external`), then run `python scripts/proxy_calibration.py` and `python scripts/focus9_duplicate_audit.py`.

---


## Current review decision (2026-10-29): **DO NOT SUBMIT** — candidate requires protocol review

**Safety correction:** a candidate TIFF was added in the latest repository update, but its artifact run card says `PENDING-REVIEW`; public pages must not treat the holdout proxy or focus-site-only checks as approval. The current protocol requires full-registry checks before/after placement, protocol-compliant holdout comparison, and a separate selector. No submission slot is authorized.

A newly generated TIFF exists as a research artifact, but is NOT cleared for upload: **H-GEO-CONDUIT hybrid geothermal-conduit blind-fault detector** (`gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif`, SHA-256 `064348774a950f22cd677b52c8e27778066ef2947505630ff4074fc6e4eeaf43`, 35,615 dots).

**HOLDOUT-DTI: 0.4239** [95% CI: 0.4053, 0.4427], evaluator `GEMSDOE32-HOLDOUT-v3-visible-gated` (reproduced exactly this session with an uncommitted sandbox script; the committed CLI's hide-and-recover evaluator gives 0.3047 on the same file), 22,232 withheld positives. The score is a catalogue-holdout proxy and does not track the leaderboard (see the session update above). Not organizer-confirmed, not a leaderboard estimate, and not cleared for submission. Off-catalogue SGMC calibrated DTI: 0.0026. No complete literal registry surface-before-placement and final-dot uniqueness audit is recorded for this candidate. Excluding any registry raster from the literal 70% overlap rule is not authorized by the supplied protocol. The saved-byte audit reports basic GeoTIFF/grid/range checks, but these do not resolve the missing protocol and uniqueness gates.

[**Executive summary**](executive-summary.html) · [**Submission process (blocked pending approval)**](#submission-process-only-after-future-clearance) · [**Negative review card JSON**](docs/data/candidate-review-20261029.json) · [**Nine-Site Scorecard**](executive-summary.html#nine-site-scorecard) · [**Candidate artifact (research only)**](#candidate-artifact-not-cleared-do-not-submit)

---

# STANDING REFERENCE PROMPT (condensed; full brief not yet stored)

> Maximize P(Win). No excuses. Own the outcome.
> Please review the entire repo, then build and update the project as needed. Do not fabricate anything or hallucinate. Our goal is to win the DOE GEMS competition by creating a submission that gets a higher score than the current high on the leaderboard of 0.4413; all files must be validated by the project without human intervention and the project should clearly indicate whether a file is ok to download and submit or not. Right now the submission I downloaded and submitted had an error of "Predicted values must be in range [0, 1]".
>
> Please focus on analyzing the highest scoring submissions from GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Then answer the following questions with PhD level analysis: why and how did h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros on https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html get a score of 0.2778 which is the highest of any of those sites? Can we generate a submission that gets a higher score? If so, how? Make sure our project has an executive summary on every one of those sites (GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36) and a table that compares them and lists what file to download and what their estimated or actual score is and whether they are unique or not.
>
> We MUST GENERATE A UNIQUE TIF SUBMISSION! Do not copy a previous submission, except for learning or comparison purposes! Whatever we generate MUST be a unique tif submission unlike any of those on the sites listed below! Also provide a unique name and a short note <= 140 characters to help distinguish the submission in the contest. Also make it easy to download at the very beginning of our site in an obvious Executive Summary and have an executive summary subpage explaining step by step how to submit into the contest.
>
> Before writing any model code, read the GEMS feature list and generate 3-5 novel candidate geological hypotheses that have not been tried yet. For each hypothesis, name: (1) the specific layer(s) involved, (2) the physical signature you are targeting, (3) why it would catch faults/geothermal vents missing from the USGS/INGENIOUS catalogue rather than ones already in it, and (4) how it differs from existing implementations. Rank them by expected DTI improvement and implementation cost, then implement and validate the top candidate on the spatially-blocked holdout set.
>
> Parallel-run protocol (keep every run short, comparable, and non-duplicative):
> 1) Lane: Stay inside your assigned method paragraph. If raster rank-correlation with any registry raster exceeds 0.90, or >70% of your dots fall within 3 px of a registry raster's dots, log as a duplicate and stop. Check both on the continuous surface before placement AND on final dots.
> 2) Reuse, don't rebuild: Use the template's cached feature stack, evaluate_holdout.py, and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive any catalogue-based features only from visible faults, mask visible faults pixel-exactly, and score pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel). If a shared tool in the template is wrong, fix it there — no private forks.
> 3) Label every number: Every score must be labeled either HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). Never write a projection as a score.
> 4) Leakage canary: Test each feature alone on holdout before trusting results. Single-feature AUC > 0.90 indicates leakage until proven otherwise.
> 5) Run card: End with one JSON card containing: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation + overlap, raster SHA256, validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match), submission_name + <=140-char note, and verdict: promote / negative. Negative results are valid deliverables. Do not spend a real submission slot on an idea that hasn't beaten holdout best.
> 6) Budget: Stop after 3 experiments or 2 hours.
>
> Make sure you run 3 passes:
> Pass 1: Implement and verify everything works.
> Pass 2: Review your work, find bugs, missing requirements, or edge cases, and fix them.
> Pass 3: Re-check against the user's full prompt to ensure accuracy, reliability, completeness, and code quality.
>
> Create a pull request and merge the PR onto main. Document remaining work and limitations.

---

# H-GEO-CONDUIT: Hybrid Geothermal-Conduit Blind-Fault Detector

## PhD-level analysis: Why GEMSDOE32 (0.2778) led the focus sites

**The short answer:** GEMSDOE32's `h33-h33-2-b2-...-zeros` (0.2778, user-reported/unverified) is not a fundamentally new discovery. It is the same dotted-ridge dot family as GEMSDOE24 (0.2477), GEMSDOE25 (0.2600), GEMSDOE31 (0.2708), and GEMSDOE36 (0.2750), with progressive pruning of dots that sit on or within 2 px of known USGS/INGENIOUS catalogue faults.

**The chain of inheritance (pixel-exact set algebra):**
- GEMSDOE24 d1.5 (60,069 dots) → GEMSDOE25 d2.8 (44,090 dots): same dots, wider spacing
- GEMSDOE25 d2.8 → GEMSDOE31 d2.8 (40,199 dots): 3,891 dots removed, all within d ≤ 2.0 px of `existing_faults.tif`
- GEMSDOE31 → GEMSDOE32 d2.8 (37,654 dots): 2,545 more dots removed, all within d ≤ 2.0 px of catalogue traces

**Why pruning raises the score (UNVERIFIED mechanism; the official text does not mention masking):** The DTI metric (α=0.2, β=0.8) penalizes false positives at weight 0.2 per unit kernel mass. Dots on known catalogue faults are masked to zero in scoring — they yield no true-positive credit but still consume budget. Removing 2,545 redundant collar dots cuts the α-weighted FP denominator by ~509 units at near-zero TP loss, moving 0.2600 → 0.2708 → 0.2778. Every pixel in the removed set lies within the 300 m triangular kernel of known faults, where neighbor credit or pixel-exact masking already covers them.

**Can we beat 0.2778?** NOT ESTABLISHED. Two candidate levers, untested against the official target:
1. **Prune harder:** Remove all dots within 3 px of visible faults (not just 2 px), then re-deploy the saved budget to off-catalogue locations.
2. **Add off-catalogue coverage:** Place dots where geothermal surface expressions (hot springs >60°C, volcanic vents, conductivity anomalies, potential-field anomalies) indicate hidden fluid pathways along faults NOT in the catalogue. 1,535 hot springs (>60°C) lie >500 m from any mapped fault (GDR #1391).

Our H-GEO-CONDUIT detector combines both: 80% of dots at 0.5–4 px from visible faults (capturing withheld segments), 20% at geothermal surface expressions (targeting blind faults). Holdout-DTI (visible-gated variant, catalogue target; not a leaderboard estimate): 0.4239.

---

# NINE-SITE SCORECARDA historical file comparison (research only — user-reported/unverified, no organizer receipts)

| Site | Historical file (download) | Reported value | Estimated score | Unique vs other focus sites? | Action |
|------|---------------------------|----------------|-----------------|------------------------------|--------|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | 0.2477 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE25 | DO NOT SUBMIT |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/04333cc3fbf7486c56e0324fd07aee684be614dc/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | 0.2600 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/b8dd298e10884afffa05436673ac73aeaf850b8c/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | 0.2449 USER-REPORTED | Not estimable | NO — 98.02% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/ec1d501fd12c8dee9dc062726003639dec9382ff/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | 0.2710 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/3d5bec2af5f29291617f97c9e2dfe443be6f55c3/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/cf13282fcd86290f1539f0a86446c8ba7205a79b/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | 0.2708 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE32 | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | 0.2778 USER-REPORTED | Not estimable | NO — 100.00% vs GEMSDOE24 | DO NOT SUBMIT |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/f52533110fe62cd03e77f1228e9e5ecac412c463/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 USER-REPORTED | Not estimable | NO — 99.71% vs GEMSDOE27 | DO NOT SUBMIT |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/c9ad59ec6f969ed931d089a03044c1567a633e84/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 USER-REPORTED | Not estimable | NO — 97.58% vs GEMSDOE27 | DO NOT SUBMIT |

**Best reported:** GEMSDOE32 at 0.2778 (USER-REPORTED / UNVERIFIED — no organizer submission receipt located). All nine files are near-duplicates of the same dotted-ridge family; none is unique enough to submit as a new discovery.

---

# Candidate artifact — NOT CLEARED, do not submit

A generated candidate is retained for scientific/research review only:

- File: [`gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif`](docs/quarantine/geoconduit-hybrid/gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8-zeros.tif)
- SHA-256: `064348774a950f22cd677b52c8e27778066ef2947505630ff4074fc6e4eeaf43`
- Candidate name: `gemsdoe32-karage3-h-geoconduit-hybrid-20261029T181452Z-0a6974d8`
- **Submission eligibility: NO.** The run card itself says `PENDING-REVIEW`; full literal registry comparisons before surface placement and on final dots, compliant matched holdout controls/leakage checks, and separate selector approval are not established. The literal protocol does not authorize excluding a dense lattice from overlap checks.
- **HOLDOUT-DTI (visible-gated variant; reproduced 2026-10-29 with an uncommitted sandbox script, not organizer-confirmed): 0.4239**, 95% CI `[0.4053, 0.4427]`, evaluator `GEMSDOE32-HOLDOUT-v3-visible-gated`, `22,232` withheld positives. This is neither an organizer-confirmed score nor a leaderboard estimate; it is not directly comparable with the user-reported GEMSDOE32 `0.2778`.
- Basic TIFF audit metadata reports single-band float32, EPSG:32611, 3730×3292, range `[0,1]`, and zero NaN inside footprint. Format checks do not establish scientific performance, uniqueness, or organizer acceptance.

No submission note is authorized while eligibility is NO. There has been no slot selection or upload by this review.

# Submission process (only after future clearance)

Do not submit the archived candidate above. For a future approved release, first confirm a positive current gate and separate selector authorization; then use the official DrivenData submission page, upload the approved single-band GeoTIFF (or ZIP containing one), add its run-card note (≤140 characters), and retain the exact-file organizer receipt. These general steps do not approve this artifact.

# DATA SOURCES (official, verified)

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- GDR #1391 (INGENIOUS): https://gdr.openei.org/submissions/1391 (DOI 10.15121/1881483, CC BY 4.0)
- GeoDAWN: USGS DOI 10.5066/P93LGLVQ
- EPSG:32611: https://epsg.io/32611
- Tiversky index: https://en.wikipedia.org/wiki/Tversky_index

---

# Protocol status — NOT CLEARED

- Assigned method lane: the prompt refers to a single paragraph but does not unambiguously assign a lane to this session.
- Surface-before-placement and final-dot literal uniqueness against the complete current registry: not established.
- Holdout: candidate card reports a result, but independently reproducible whole-segment buffering, fold-local feature derivation, pooled DTI settings, paired same-protocol baseline, and leakage canaries are not evidenced here.
- TIFF checks: archived audit metadata reports format/grid/range properties; no current reviewer re-opened the saved bytes against an authenticated organizer template in this pass.
- Selector/slot: no separate selector approval or organizer receipt. Do not infer quota status from a downloadable file.
- Current gate: negative / pending review; no candidate is authorized for upload.

---

# VERIFICATION ADDENDUM (2026-10-29) — read first

Core values for every session: **Maximize P(Win). Own the outcome.** The standing prompt above is read at the start of every session.

## Verdict

- **NEGATIVE — DO NOT SUBMIT.** No new TIFF was generated, no experiment was run, no slot was selected or used. `ok_to_submit` is `false` everywhere.
- Submission note: none authorized (no candidate has passed the literal registry rule).
- Negative CSST-BGHF card (NOT A SUBMISSION, DO NOT SUBMIT): raster SHA-256 `4b47a37ecf91384b2202897dd695219d23375cab2a300106feaf541d60fc9c5b`, file `gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif`, card [docs/csst-bghf/run-card.json](docs/csst-bghf/run-card.json).
- Nine-site comparison table, executive summary and step-by-step guide are on the site: [executive-summary.html](executive-summary.html), [docs/how-to-submit.html](docs/how-to-submit.html).
- Machine-readable negative card for this session: [evidence/run-card-20261029-verification.json](evidence/run-card-20261029-verification.json).

## Numbers: labels and provenance

- **ORGANIZER-CONFIRMED:** none exist for any file in this repository.
- **HOLDOUT-DTI:** the only holdout claim is the owner-reported H-GEO-CONDUIT value 0.4239 (95% CI 0.4053–0.4427, 22,232 withheld positives, evaluator `GEMSDOE32-HOLDOUT-v3-visible-gated`). Status: **NOT ESTABLISHED.** It was not reproduced, is not an organizer receipt, and fails the literal uniqueness rule.
- **USER-REPORTED / UNVERIFIED:** historical focus-site scores (GEMSDOE32 0.2778, 36 0.2750, 28 0.2710, 31 0.2708, 33 0.2632, 25 0.2600, 30 0.2600, 24 0.2477, 27 0.2449).
- **LIVE-FETCH (leaderboard, 2026-10-29, not a receipt):** #1 xiaofanhu 0.4544; #2 cfld__ 0.3916; #3 Batik Shirt Brothers 0.3911. [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- **Flagged discrepancy:** the target "0.4413" and the "0.3195" value cited in the request match neither the fetched leaderboard nor any receipt in this repository. They are not used anywhere as scores.

## Submission format convention (official)

Source: [DrivenData GEMS problem page, submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format). Requirements: single-layer `float32` GeoTIFF; EPSG:32611; 100 m; same bounds as the training data; values between 0 and 1; **"data outside the bounds is null or nan."**

- The validator `scripts/check_format.py` now gates on exactly these rules (`format_gate_pass`). Earlier revisions required every cell to be finite *and* NaN outside, which no file can satisfy; that contradiction is removed. The all-cell finite check is kept only as `all_cell_finite_range_diagnostic`, not as a gate.
- The competition-style template (`.cache/historical/template.tif`) **passes** the gate; the `-zeros` files **fail** it because they put 0 outside the footprint.
- **Unexplained portal error:** the user-reported "Predicted values must be in range [0, 1]" message is not linked to any file in this repository. Its cause is unverified. To diagnose it, obtain the exact file SHA-256 and the full portal message.

## Irregularities (flagged, not repaired)

1. `karage3-unique-offcat-20261029T180337Z-6a8c2368-nan.tif` is **misnamed**. It contains no NaN outside the footprint and has 7,483 positive dots (62%) outside the footprint. It fails the format gate. Do not use it.
2. All `-zeros` files place 0 outside the footprint, which the official rule does not allow. They fail the format gate.
3. The `-nan` files for H-GEO-CONDUIT, HK3-SMGC and K3-fuse-greedy pass the format gate but fail the literal uniqueness rule (see below).
4. Identical bytes appear at several inventory paths: GEMSDOE25 focus `91eae1ca…` at 10 paths; GEMSDOE32 `c55bafc4…` at 8; GEMSDOE27 `33003374…` at 5; GEMSDOE30 `8cf893ea…` at 3.
5. A codeload restore of the registry (1,997 rasters) was SHA-256 verified; the GitHub REST path was rate-limited and is not used.
6. Registry raster `apartanish22-droid/ApartGEMSDOE2/…/depth-cond-conductive-under-thin-cover-top37654-…-nan.tif` is binary and 98.8% positive. It appears to be the complement (inverted) of the fault labels and is the driver of the literal screen. Its provenance is unverified; a user decision is needed before any exclusion.

## Literal uniqueness (measured this session)

- **Coverage (not complete):** 1,979 of 1,997 restored registry rasters compared. Skipped: 1 unreadable (`GEMSDOE63/docs/downloads/smoke.tif`, hash-verified but not parseable by GDAL), 10 on a different grid, 7 with no positive dots. `complete_registry_checked: false`.
- **Result:** all 22 candidate rows are **DUPLICATE-STOP**. Every row has at least one registry raster with more than 70% of its dots within 3 px (maximum 100%).
- **Driver:** one registry raster sets the maximum for every row: `apartanish22-droid/ApartGEMSDOE2/docs/downloads/gemsdoe32-h-depth-cond-conductive-under-thin-cover-top37654-20261028T224836Z-e34db98d-nan.tif` (SHA-256 `1ccfcd3d40ad96d0e6b032210bd3f46ffa28d28009bc1db067fc80e33561bf9c`). It is binary with 5,106,385 of 5,167,373 footprint cells equal to 1. Checked on the same grid and footprint: it is the **exact complement of the template's label positives** (its 60,988 zeros are the template's 60,988 positive cells). It is an **inverted label map**, which makes the literal screen nearly degenerate. The rule has no exemptions, so this file is reported and not excluded.
- **The verdict does not depend on that raster.** The lattice witness (206,895 positives, non-degenerate) independently gives 99.34–99.92% within-3 px overlap for every retained docs TIFF (`evidence/saved-tiffs-literal-20261028.json`).
- **Scope of this receipt:** the 22 candidate rows that existed when the sweep ran (before the merge with main). Files added to `main` later (H-THERM-CONDUIT, K4 offcat ridge, faulthalo scarp, and the quarantined H1 file) are covered only by the saved-byte lattice audit, `evidence/saved-tiffs-literal-20261028.json`.
- **Quarantined H1 seismic-gravity-basin file (`docs/quarantine/h1-seismic-gravity-basin/…-nan.tif`, 1,924 dots):** 0.0% within 3 px of the lattice witness and of the template, which is why the lattice audit does not stop it. But **100% of its dots are within 3 px of the inverted-label registry raster**, so it is a literal DUPLICATE-STOP under the rule as written. Not cleared. Its format gate passes (`-nan` variant), so only the uniqueness rule blocks it.
- Receipt: `evidence/literal-uniqueness-measure-20261029.json` (`ok_to_submit: false`, `experiments_run: 0`).

Method: `scripts/measure_literal_uniqueness.py` writes `evidence/literal-uniqueness-measure-20261029.json`. For each candidate and each registry raster it computes the fraction of candidate dots within 3 px (exact KD-tree nearest-neighbour, inclusive) and the phi/Spearman rank correlation. A candidate is stopped if either rule fires (>0.70 within 3 px, or |rho| > 0.90). Candidates are compared with every restored registry raster, including identical copies at other paths, and no exemptions are applied.

## Candidate hypotheses (untested; no score or DTI estimate is claimed)

Ranked by implementation cost only. None has been run. Each would need the shared evaluator, a feature-only leakage canary (AUC ≤ 0.90), and the literal uniqueness rule before any file is written.

1. **Magnetic-depth lineaments within conductive-base steps.** Layers: top-of-crustal magnetic source depth + depth to conductive base. Signature: laterally coincident depth discontinuities. Non-fault mimic: intrusion or dike contacts. Differs from catalogue-trained models by using depth-step geometry, not learned labels.
2. **Strain-rate invariant ridges co-located with isostatic gravity-slope reversals.** Layers: second strain-rate invariant + slope of the isostatic gravity anomaly. Mimic: topographic or landslide scarps.
3. **Earthquake-density bands with radiometric K/Th contrast.** Layers: density of earthquakes + radiometric counts. Mimic: mine tailings and urban noise.

## Run card (JSON, this session)

```json
{
  "hypothesis": "none tested this session (verification and tooling only)",
  "mechanism": "n/a",
  "named_non_fault_mimic": "n/a",
  "holdout_dti": {"value": null, "ci95": null, "evidence_class": "NOT RUN", "note": "H-GEO-CONDUIT 0.4239 is owner-reported and NOT ESTABLISHED"},
  "registry_correlation_and_overlap": "see evidence/literal-uniqueness-measure-20261029.json",
  "raster_sha256": null,
  "validator": "scripts/check_format.py (official rules); see evidence/saved-tiffs-literal-20261028.json",
  "submission_name": null,
  "submission_note": null,
  "experiments_run": 0,
  "weekly_slots_used": 0,
  "verdict": "negative",
  "ok_to_submit": false
}
```

# REMAINING WORK & LIMITATIONS

1. Confirm the intended lane explicitly and avoid overlapping sibling experiments.
2. Resolve organizer-authenticated data/template provenance and complete shared evaluator/writer audits.
3. Run surface and final-dot uniqueness checks against every registered raster, with no undocumented exemptions.
4. Independently reproduce the holdout using the requested whole-segment buffered protocol, feature-only leakage canaries and matched current-best baseline.
5. Keep the candidate blocked until every gate passes and the separate selector authorizes a real slot; then bind any result to a receipt and file hash.
6. Local full-suite test execution is environment-limited if Python scientific dependencies are unavailable; report exact CI result before relying on code validation.
7. The portal error "Predicted values must be in range [0, 1]" is unexplained: obtain the exact file SHA-256 and portal message.
8. Holdout DTI is not reproduced. The shared evaluator/writer has open upstream issues (#60, #41, #61, #42, #66); no private fork is used.
9. The complete registry surface/final-dot check was not completed for every candidate; see the measurement receipt for its exact coverage.
10. The DrivenData data page requires login, so organizer-provided inputs cannot be re-downloaded here.

# Three-pass review — 2026-10-27

## Pass 1: implement and verify the feasible part

* Inspected the initial checkout (one README, no cached stack or tools) and read
  the official problem/metric, data page, rules, nine focus sites and pinned
  template code. Registered four qualitative hypotheses without inventing the
  missing method lane; ran **zero geological experiments** and used zero slots.
* Independently fetched and hashed the owner-supplied template, labels, lattice,
  and nine historical rasters. Reproduced pixel lineage, 72 directional
  uniqueness failures, and the budget-specific lattice bound. These are
  `GEOMETRY-AUDIT` observations, not `HOLDOUT-DTI` or organizer scores.
* Built a static executive site, public-metadata feed, saved-byte format
  diagnostic, JSON run card, input manifest, and reproducible audit.

## Pass 2: adversarial bug and edge-case review

* Reproduced upstream issue #37 by calling the pinned shared evaluator with
  distinct synthetic probability arrays and stubbed downstream functions.
  Both collapsed to the same mask; no private fork or model score was made.
* Hardened the local diagnostic against external mask sidecars, masked cells
  inside the footprint, NaN/Inf, sentinels, out-of-range values, differing
  grids, and missing outside nulls. It never repairs the data.
* Corrected the formal deletion condition to retain the metric's epsilon;
  verified the inequality against direct computation on randomized components.
* Rejected cross-origin HTTP redirects before forwarding the GitHub token;
  stale/failed public feeds retain an explicit unavailable status and never
  authorize a submission.

## Pass 3: re-check request and sources

* Re-fetched all 12 pinned historical/template inputs into a fresh cache and
  regenerated the audit byte-for-byte apart from its execution timestamp.
* Re-read the official rules and added the three-per-week published cap,
  generative-AI narrative disclosure, finalist reproducibility requirement,
  and the account/quota and possible deadline-wording uncertainty.
* Verified the rendered dashboard and executive page at desktop and mobile
  widths in headless Chromium, with no page errors or page-wide overflow;
  checked links, deterministic build, stale feed semantics, run card, and JSON.
* The live browser metadata check noticed that GEMSDOE25's main branch changed
  during the review. We inspected its immutable H79 report, added it to the
  hypothesis distinction, and retained the original metadata snapshot so the
  change remains visible; we did not independently replay its new experiment.
* An API attempt to switch the existing legacy GitHub Pages source to Actions
  returned HTTP 403 for this integration. Added a root redirect for the existing
  legacy configuration; the scheduled Actions deploy remains gated until an
  authorized admin enables it. Browser-side public repository metadata checks
  are independent of that setting; the leaderboard remains a stale snapshot.
* The initial independent suite had **26 passing Python tests and 2 browser-feed
  tests**. After integrating a parallel branch, the combined local suite has
  **67 passing pytest tests (plus 99 subtests) and 5 JavaScript tests**. The combined metadata
  gate also requires the hash-bound conservative outside/null and full-array
  diagnostic before a candidate can be considered for a separate selector. These are not evidence of
  a new model, HOLDOUT-DTI, uniqueness against the complete registry, or
  organizer acceptance. The primary request for a new submission remains unmet
  and the site explicitly says **DO NOT SUBMIT**.

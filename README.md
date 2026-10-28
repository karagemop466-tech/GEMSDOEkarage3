# GEMSDOEkarage3 — evidence-first fault mapping

## Decision: **DO NOT SUBMIT**

There is no cleared new TIFF. The retained H-K3C raster failed the literal
registry duplicate stop: an independent saved-byte re-audit found **99.35%**
of its 37,654 dots within 3 pixels of one pinned lattice (limit: 70%). Its
local range and grid checks passed against an **owner mirror**, not an
authenticated organizer template; the outside-null interpretation is a separate
unresolved check. These results do not establish portal acceptance or a score.

[**Nine-site executive summary**](index.html#scorecard) ·
[Submission guide](executive-summary.html) ·
[Current JSON run card](docs/data/latest-run.json) ·
[Three-pass review](docs/review-2026-10-28-session.md) ·
[Full retained project brief](docs/PROJECT_BRIEF.md)

### What is evidenced

- Historical best values for **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28,
  GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33 and GEMSDOE36** are user/owner
  reports without hash-linked organizer receipts. The Pages table identifies
  the historical files and links to their sources for **research only**.
- GEMSDOE32's reported 0.2778 is unverified. Its dot support is GEMSDOE31's
  support minus 2,545 catalogue-near dots. Less redundant/false-positive mass
  is a plausible metric explanation, not proof of causation or future score.
- The [independent geometry receipt](evidence/historical-reaudit-20261028-session.json)
  covers nine pinned files and one witness, not the complete registry. All 72
  directional focus-site comparisons exceed 70%. A 37,654-dot budget is
  mathematically forced to overlap this lattice by at least 82.34%. Smaller
  budgets are **not** automatically unique; never target witness holes to evade
  the rule.
- No new HOLDOUT-DTI, competition-score estimate, candidate, or slot was
  produced. The [research page](research.html) ranks four hypotheses with
  geological signatures, non-fault mimics, expected qualitative benefit, cost
  and source limitations. They are not an assigned lane or proven novel fleet-wide.

### Why the experiment is blocked

The request references a single method paragraph but no lane is unambiguously
assigned. The shared derived feature stack, a complete current registry, and a
same-fold best baseline are unavailable. Four large owner-mirrored core rasters
were restored and 19 raw bands prepared, but these ignored files may be absent
in another checkout; mirror hashes do not authenticate organizer provenance.
The active shared files are byte-identical to [GEMSDOE32@97597a](registry/shared_template_97597a.json),
but the upstream [buffer](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/60),
[FP pooling](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/41),
[leakage](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/61),
[surface overlap](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/42)
and [masked-pixel](https://github.com/buffedlizard55-lab/GEMSDOE32/issues/66)
defects remain open. We cannot fix that separate template repository with our
read-only access and do not claim a private fix. Historical generation entry
points are disabled; archived holdouts are exploratory, not promotion evidence.

## Project brief and protocol

**Maximize P(Win). Own the Outcome.** Seek a genuinely new, competitive fault
prediction and an easy download **only after** the evidence and a separate
selector permit it. The complete request and source inventory are retained in
[docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md). The operating constraints are:

1. Stay in the one specified method lane. Compare against **every registered
   raster**, at the surface/preview and final-dot stages. Rank correlation above
   0.90 or more than 70% of dots within 3 pixels of any one raster means log a
   duplicate and stop. Missing comparisons fail closed; no density exemptions.
2. Use the shared cached features, evaluator and writer without a private fork.
   Fix shared defects in the shared template and report them. Hide whole fault
   segments with a verified buffer, derive catalogue features from visible faults
   only, mask visible faults pixel-exactly, and pool DTI (α=0.2, β=0.8, 300 m
   triangular kernel).
3. Test each feature alone as a leakage canary; AUC above 0.90 is suspect until
   disproven. Label all scores as HOLDOUT-DTI with evaluator version, withheld
   positives and 95% CI, or ORGANIZER-CONFIRMED from a submission receipt.
   User reports and projections are neither organizer scores nor forecasts.
4. End with one JSON card naming hypothesis, mechanism, non-fault mimic,
   holdout and CI, registry comparisons, raster hash, validation, submission
   name, ≤140-character note, and promote/negative verdict. Negative is a result.
5. Stop after three experiments or two hours. Do not spend a weekly slot on an
   idea that has not beaten the current best on the same valid holdout. Technical
   eligibility is not authorization; an independent selector checks the cap.
6. Validate exact saved TIFF bytes: one float32 band, [0,1] and no NaN/masked
   pixels inside the footprint, exact reference CRS, shape and transform. Report
   the outside-null convention separately from whole-array finiteness and do
   not claim organizer acceptance from either local diagnostic.
7. Investigate 3–5 plausible, untried hypotheses before implementation, state
   layers, signatures, off-catalogue rationale, differences, expected qualitative
   benefit, cost and verified external-data availability. Test the assigned top
   idea using the valid spatial holdout, then perform three review passes.
   Do not copy an old submission except for education/research.

[Official problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
· [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
· [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
· [source register](docs/data-sources.md). The rules allow up to three weekly
submissions and one final selection; the account's current quota is unknown.
DrivenData's [terms](https://www.drivendata.org/termsofuse/) prohibit automated
access, so the site refreshes GitHub metadata only, not the leaderboard.

## Local checks (do not create a candidate)

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci --no-audit --no-fund
.venv/bin/python scripts/check_readiness.py     # exits nonzero while blocked
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover -s tests -v
npm test
node --test tests/test_browser_feed.js
.venv/bin/python scripts/build_site.py --check
```

Optional forensic reruns download only pinned public owner-mirror bytes; choose
new paths to avoid overwriting receipts:

```bash
.venv/bin/python scripts/audit_historical.py --cache-dir .cache/audit --out .cache/historical-new.json
.venv/bin/python scripts/audit_k3c_literal_witness.py --out .cache/witness-new.json
.venv/bin/python scripts/check_submission.py FILE.tif --template TEMPLATE.tif --strict-finite
```

A local `[PASSED]` is **only** a format diagnostic. No upload is authorized by
these commands. Review the official outside-footprint wording independently.

### Historical artifact (research only)

The prior H-K3B-1 file
`gemsdoekarage3-h-k3b-1-csst-bghf-coulomb-d31-20261028T061500Z-78c25201-zeros.tif`
(SHA-256 `4b47a37ecf91384b2202897dd695219d23375cab2a300106feaf541d60fc9c5b`)
is archived at [docs/csst-bghf](docs/csst-bghf/index.html), **DO NOT SUBMIT**.
Old cards, pages and evidence remain in the repository as history, not current
approval. The former README narrative is available in Git history.

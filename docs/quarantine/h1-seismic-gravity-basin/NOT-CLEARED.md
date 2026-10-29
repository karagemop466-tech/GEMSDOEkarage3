# NOT CLEARED: H1 seismic-gravity-basin (quarantined)

Files: `gemsdoe32-karage3-h1-seismic-gravity-basin-20261029T182309Z-91540319-{zeros,nan}.tif` and its audit JSON.

Do NOT download or submit.

- Literal lattice rule: 0 of 1,924 positive dots are within 3 px of the lattice witness.
- But 98.7% of its dots (1,899 of 1,924) lie in the 3-cell footprint edge band. That band holds 6,580 of the 6,649 lattice-uncovered footprint cells. The nearest dot is 3.16 px from a lattice dot (median 3.61 px). The file clears the 3-px test by placement, not by geology.
- Refused as boundary gaming. The saved-byte audits record `boundary_ring_share` and `boundary_gaming_refusal` (threshold: at least 50% of dots in the edge band).
- Also fails the strict format gate (`all_cell_finite_range` / `outside_null_or_nan`, see the audit JSON).
- Unverified: no holdout score, not an organizer score, and not checked against the complete registry.
- Moved from `docs/downloads/` during the 2026-10-29 merge with `main` (PR #51 had added it there).

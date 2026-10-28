'use strict';
const el = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
const narratives = {
  GEMSDOE24: 'Denser d1.5 historical dot pattern. Its dots all lie within three pixels of the d2.8 pattern; this is not an independent lane under the literal rule.',
  GEMSDOE25: 'The d2.8 dot pattern is pixel-identical to GEMSDOE30, although their TIFF byte hashes differ. Metadata or compression differences do not establish uniqueness.',
  GEMSDOE27: 'The supplied topo-gap-closure file adds placements to the historical family. Its measured overlap with GEMSDOE24 exceeds the stop threshold.',
  GEMSDOE28: 'The highest claim in the supplied list is rung30 (0.2710 OWNER-REPORT), not solo (0.2708 OWNER-REPORT). The earlier solo file is the exact base from which GEMSDOE32 was pruned.',
  GEMSDOE30: 'The claimed Poisson off-catalogue artifact has the same positive pixels as GEMSDOE25. This is a duplicate prediction pattern, regardless of file bytes.',
  GEMSDOE31: 'Its cited solo pattern is pixel-identical to the earlier GEMSDOE28 solo base. It is not a novel method-specific submission.',
  GEMSDOE32: 'Largest supplied nine-site claim: 0.2778 OWNER-REPORT. Exact two-pixel catalogue-flank pruning of the 40,199-dot solo base produces this 37,654-dot artifact; zero new dots.',
  GEMSDOE33: 'The cited analog-tip/stepover pattern still exceeds the literal overlap threshold against the audited family. A geological method name is not evidence of independent predictions.',
  GEMSDOE36: 'The cited historical artifact exceeds the overlap stop against the audited family. The file’s name alone does not establish a physics-informed model or geothermal discovery.'
};
async function loadJSON(path) { const r = await fetch(path); if (!r.ok) throw Error(`${path}: HTTP ${r.status}`); return r.json(); }
Promise.all([loadJSON('sites.json'), loadJSON('historical-audit.json')]).then(([claims, audit]) => {
  if (!Array.isArray(claims.sites) || !Array.isArray(audit.rasters) || audit.ok_to_submit !== false) throw Error('Invalid evidence schema');
  const rows = document.querySelector('#rows');
  const details = document.querySelector('#site-details');
  for (const site of claims.sites) {
    const measured = audit.rasters.find(r => r.site === site.site);
    if (!measured || !Number.isFinite(site.owner_reported_value)) throw Error('Missing site evidence');
    const tr = el('tr');
    const label = el('td');
    label.append(el('strong', site.site), el('small', `${site.owner_reported_value.toFixed(4)} · USER-REPORTED / UNVERIFIED`));
    const file = el('td');
    const link = el('a', 'Inspect historical file ↗');
    const url = new URL(measured.source_url);
    if (url.protocol !== 'https:' || url.hostname !== 'github.com') throw Error('Unexpected source host');
    link.href = url.href;
    file.append(link, el('small', measured.file), el('small', `SHA256 ${measured.sha256}`));
    const estimate = el('td', 'Unavailable'); estimate.append(el('small', 'No evaluated new candidate'));
    const format = el('td', measured.validator.all_checks_passed ? 'PASS' : 'FAIL'); format.append(el('small', 'Against owner-mirrored template; not organizer authentication'));
    const unique = el('td', measured.partial_registry.duplicate_stop ? 'FAIL · duplicate stop' : 'Unproven');
    unique.append(el('small', `${(100 * measured.partial_registry.max_overlap_3px).toFixed(2)}% within 3 px of ${measured.partial_registry.reference}`));
    const decision = el('td', 'None approved'); decision.append(el('small', 'NOT OK TO SUBMIT'));
    tr.append(label, file, estimate, format, unique, decision); rows.append(tr);
    const article = el('article');
    article.append(el('h3', site.site), el('p', narratives[site.site]), el('small', `${measured.positive_pixels.toLocaleString()} positive pixels · RASTER-AUDIT`));
    const relation = measured.champion_relationship;
    article.append(el('p', `Relative to GEMSDOE32: ${relation.shared_positive_pixels.toLocaleString()} shared, ${relation.extra_vs_champion.toLocaleString()} extra, ${relation.missing_vs_champion.toLocaleString()} missing dots.`));
    details.append(article);
  }
  document.querySelector('#updated').textContent = `GitHub claims checked ${claims.checked_utc}; historical pixels audited ${audit.checked_utc}. Partial historical registry, not a current complete inventory.`;
}).catch(error => {
  document.querySelector('#rows').replaceChildren();
  document.querySelector('#site-details').replaceChildren();
  document.querySelector('#updated').textContent = `Evidence loading failed; remain NOT OK TO SUBMIT. ${error.message}`;
});

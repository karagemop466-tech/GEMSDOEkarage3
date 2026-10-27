/* GitHub-head freshness is separate from historical geometry and organizer scores. */
(() => {
  const rows = document.querySelector('#rows');
  const sourceStatus = document.querySelector('#source-status');
  const freshness = document.querySelector('#freshness');
  if (!rows || !sourceStatus || !freshness) return;

  const cell = (text, detail) => {
    const td = document.createElement('td');
    td.textContent = text;
    if (detail) {
      const small = document.createElement('small');
      small.textContent = detail;
      td.append(small);
    }
    return td;
  };
  const safeGithub = value => {
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && url.hostname === 'github.com' ? url.href : null;
    } catch (_) { return null; }
  };
  const getJSON = async url => {
    const response = await fetch(url, {cache: 'no-store'});
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
  };
  const checkHeads = async sites => {
    const checks = await Promise.all(sites.map(async site => {
      const source = safeGithub(site.repository);
      if (!source || !site.commit || !site.default_branch) return 'unknown';
      const path = new URL(source).pathname.replace(/^\//, '');
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      try {
        const result = await fetch(`https://api.github.com/repos/${path}/commits/${encodeURIComponent(site.default_branch)}`,
                                   {signal: controller.signal, cache: 'no-store'});
        if (!result.ok) return 'unknown';
        const data = await result.json();
        if (typeof data.sha !== 'string') return 'unknown';
        return data.sha === site.commit ? 'unchanged' : 'changed';
      } catch (_) { return 'unknown'; }
      finally { clearTimeout(timer); }
    }));
    const count = label => checks.filter(item => item === label).length;
    freshness.textContent = `GitHub HEAD check just now: ${count('unchanged')} unchanged, ${count('changed')} changed, ${count('unknown')} unavailable. Changed or unavailable sources require a fresh audit; this is not an organizer feed or a full registry check.`;
  };

  Promise.all([getJSON('sites.json'), getJSON('priority-audit.json')]).then(([manifest, audit]) => {
    if (!Array.isArray(manifest.sites) || !Array.isArray(audit.historical_rasters)) throw new Error('Invalid evidence manifest');
    const historical = new Map(audit.historical_rasters.map(item => [item.site, item]));
    rows.replaceChildren();
    for (const site of manifest.sites) {
      const item = historical.get(site.site);
      const tr = document.createElement('tr');
      const first = document.createElement('td');
      const strong = document.createElement('strong');
      strong.textContent = site.site;
      first.append(strong);
      if (item) {
        const small = document.createElement('small');
        small.textContent = item.filename;
        first.append(small);
        const url = safeGithub(item.research_download_url);
        if (url) {
          const a = document.createElement('a');
          a.href = url;
          a.textContent = 'Research download ↗';
          a.rel = 'noopener noreferrer';
          first.append(a);
        }
      } else {
        const small = document.createElement('small');
        small.textContent = 'Historical raster audit unavailable';
        first.append(small);
      }
      tr.append(first);
      const value = typeof site.owner_reported_value === 'number' && Number.isFinite(site.owner_reported_value)
        ? site.owner_reported_value.toFixed(4) : 'Unavailable';
      tr.append(cell(value, 'USER / OWNER REPORT · no receipt'));
      tr.append(cell('Not estimable', 'No validated transfer to organizer scoring'));
      if (item && item.unique_vs_other_eight_historical_masks === false && Number.isFinite(item.maximum_historical_overlap)) {
        tr.append(cell('No', `${(item.maximum_historical_overlap * 100).toFixed(2)}% near ${item.maximum_overlap_reference}`));
      } else {
        tr.append(cell('Unknown', 'No complete comparison evidence'));
      }
      const decision = cell('DO NOT SUBMIT', 'Historical research only');
      decision.className = 'warning-inline';
      tr.append(decision);
      rows.append(tr);
    }
    if (manifest.sites.length !== 9 || historical.size !== 9) {
      sourceStatus.textContent = 'Incomplete source manifest. No file is approved.';
    } else {
      sourceStatus.textContent = `Pinned GitHub sources checked ${manifest.checked_utc || 'at an unknown time'}; historical mask audit ${audit.computed_utc || 'time unknown'}.`;
    }
    checkHeads(manifest.sites);
  }).catch(error => {
    rows.replaceChildren();
    const tr = document.createElement('tr');
    const td = cell('Evidence could not be loaded. No file is approved.', error.message);
    td.colSpan = 5;
    tr.append(td);
    rows.append(tr);
    sourceStatus.textContent = 'Evidence unavailable; decision remains negative.';
    freshness.textContent = 'GitHub head freshness is unknown.';
  });
})();

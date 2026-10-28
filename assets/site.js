(() => {
  'use strict';
  // This is a commit-change alert only. It never fetches DrivenData, changes the
  // release decision, or treats a new commit as a new audit or score.
  const nodes = Array.from(document.querySelectorAll('.repo-head'));
  const key = 'gems-fieldnotes-github-heads-v1';
  const ttl = 15 * 60 * 1000;
  const now = Date.now();
  let cache = {};
  try {
    const saved = JSON.parse(localStorage.getItem(key) || '{}');
    if (saved && typeof saved === 'object') cache = saved;
  } catch (_) { /* Private browsing can disable storage. */ }

  function show(node, head, checked) {
    const when = new Date(checked).toLocaleString();
    node.textContent = head === node.dataset.baseline
      ? `No change observed · checked ${when}`
      : `Changed since snapshot · checked ${when}`;
    node.classList.toggle('warning-text', head !== node.dataset.baseline);
  }

  async function check(node) {
    const repo = node.dataset.repo;
    if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo || '')) {
      node.textContent = 'Unavailable · invalid repository';
      return;
    }
    const entry = cache[repo];
    if (entry && /^[a-f0-9]{40}$/.test(entry.head || '') &&
        Number.isFinite(entry.checked) && now >= entry.checked && now - entry.checked < ttl) {
      show(node, entry.head, entry.checked);
      return;
    }
    node.textContent = 'Checking public GitHub…';
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 10000);
      let response;
      try {
        response = await fetch(`https://api.github.com/repos/${repo}/commits/main`, {
          headers: { Accept: 'application/vnd.github+json' }, signal: controller.signal,
          credentials: 'omit'
        });
      } finally { clearTimeout(timer); }
      if (!response.ok) throw new Error('GitHub API unavailable');
      const result = await response.json();
      if (!/^[a-f0-9]{40}$/.test(result.sha || '')) throw new Error('Unexpected response');
      const checked = Date.now();
      cache[repo] = { head: result.sha, checked };
      try { localStorage.setItem(key, JSON.stringify(cache)); } catch (_) { /* optional */ }
      show(node, result.sha, checked);
    } catch (_) {
      node.textContent = 'Unavailable · not re-audited';
      node.classList.add('warning-text');
    }
  }
  nodes.forEach(node => { node.setAttribute('aria-live', 'polite'); void check(node); });

  function openHash() {
    if (!location.hash) return;
    let target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (_) { return; }
    if (target && target.tagName === 'DETAILS') target.open = true;
  }
  openHash();
  window.addEventListener('hashchange', openHash);
})();

// No network required. Exercise the browser metadata feed with fake public API responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {test} = require('node:test');

const source = fs.readFileSync('docs/assets/site.js', 'utf8');
const tick = () => new Promise(resolve => setTimeout(resolve, 20));

test('browser checks public metadata, marks failures, and never approves a submission', async () => {
  const elements = Object.fromEntries(['public-score', 'public-score-detail', 'watch-detail'].map(id => [id, {textContent: ''}]));
  const sites = [
    {site: 'GEMSDOE24', snapshot_commit: 'a'.repeat(40)},
    {site: 'GEMSDOE25', snapshot_commit: 'b'.repeat(40)},
    {site: 'GEMSDOE27', snapshot_commit: 'c'.repeat(40)},
    {site: '../unsafe', snapshot_commit: 'd'.repeat(40)},
  ];
  const calls = [];
  const fakeFetch = async (url, opts) => {
    calls.push({url, opts});
    if (url === 'data/feed.json') return {ok: true, json: async () => ({
      leaderboard: {available: false, last_observation: {score: .4544, display_score: '0.4544', observed_utc: '2026-10-27T00:00:00Z'}},
      checked_utc: '2026-10-27T00:00:00Z', sources: sites,
    })};
    if (url.endsWith('/GEMSDOE27/commits/main')) throw Error('unavailable');
    return {ok: true, json: async () => ({sha: 'a'.repeat(40)})};
  };
  vm.runInNewContext(source, {fetch: fakeFetch, document: {getElementById: id => elements[id]},
    window: {AbortController, setTimeout, clearTimeout}, AbortController, Date, Promise, Number, Error});
  await tick();
  assert.equal(elements['public-score'].textContent, '0.4544');
  assert.match(elements['public-score-detail'].textContent, /stale/);
  assert.match(elements['watch-detail'].textContent, /2\/4 repositories reachable/);
  assert.match(elements['watch-detail'].textContent, /1\/2 comparable repos changed/);
  assert.match(elements['watch-detail'].textContent, /leaderboard feed unavailable/);
  assert.match(elements['watch-detail'].textContent, /No refresh approves a submission/);
  assert.equal(calls.length, 4); // feed + 3 allowlisted API requests, no URL for unsafe site
  assert.equal(calls[1].opts.credentials, 'omit');
  assert.ok(calls[1].url.startsWith('https://api.github.com/repos/buffedlizard55-lab/'));
});

test('missing snapshot does not authorize anything', async () => {
  const element = {textContent: ''};
  vm.runInNewContext(source, {fetch: async () => { throw Error('offline'); },
    document: {getElementById: () => element}, window: {AbortController, setTimeout, clearTimeout},
    AbortController, Date, Promise, Number, Error});
  await tick();
  assert.match(element.textContent, /unavailable.*No submission is approved/);
});

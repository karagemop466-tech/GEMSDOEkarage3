const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
const html = fs.readFileSync('docs/index.html', 'utf8');
const script = fs.readFileSync('docs/app.js', 'utf8');

async function render(change, failure = false, changedHead = false) {
  const dom = new JSDOM(html, {runScripts: 'outside-only', url: 'https://example.org/docs/index.html'});
  const fixtures = Object.fromEntries(['sites.json', 'priority-audit.json'].map(path =>
    [path, JSON.parse(fs.readFileSync(`docs/${path}`, 'utf8'))]));
  if (change) change(fixtures);
  const requested = [];
  dom.window.fetch = async path => {
    requested.push(path);
    if (String(path).startsWith('https://api.github.com/')) {
      const row = fixtures['sites.json'].sites.find(s => String(path).includes('/' + s.site + '/'));
      return {ok: true, json: async () => ({sha: changedHead ? 'f'.repeat(40) : row?.commit,
        commit: {message: `Update ${row?.site || 'unknown'} <script>bad</script>\nmore`,
                 committer: {date: '2026-10-27T12:00:00Z'}}})};
    }
    return {ok: !failure, status: failure ? 503 : 200, json: async () => fixtures[path]};
  };
  dom.window.eval(script);
  await new Promise(resolve => setTimeout(resolve, 10));
  return {dom, requested};
}

test('renders all nine historical rows and no approved TIFF', async () => {
  const {dom, requested} = await render();
  const document = dom.window.document;
  assert.equal(document.querySelectorAll('#rows tr').length, 9);
  assert.equal(document.querySelectorAll('#rows td:last-child').length, 9);
  for (const cell of document.querySelectorAll('#rows td:last-child')) {
    assert.match(cell.textContent, /DO NOT SUBMIT/);
  }
  assert.equal(document.querySelector('button').disabled, true);
  assert.equal(document.querySelectorAll('a[download][href$=".tif"]').length, 0);
  assert.equal([...document.querySelectorAll('#rows a')].length, 9);
  assert.match(document.querySelector('#freshness').textContent, /9 unchanged/);
  assert.equal(document.querySelectorAll('#github-updates li').length, 9);
  assert.equal(document.querySelectorAll('#github-updates script').length, 0);
  assert.match(document.querySelector('#github-updates').textContent, /<script>bad<\/script>/);
  assert.equal(requested.filter(p => String(p).startsWith('https://api.github.com/')).length, 9);
  assert.ok(requested.every(p => !String(p).includes('drivendata.org')));
  dom.window.close();
});

test('HTTP failure fails closed without research links', async () => {
  const {dom} = await render(null, true);
  assert.equal(dom.window.document.querySelectorAll('#rows a').length, 0);
  assert.match(dom.window.document.querySelector('#rows').textContent, /No file is approved/);
  assert.match(dom.window.document.querySelector('#source-status').textContent, /negative/);
  assert.match(dom.window.document.querySelector('#github-updates').textContent, /unavailable/);
  dom.window.close();
});

test('unexpected source host is never offered as a download', async () => {
  const {dom} = await render(fixtures => {
    fixtures['priority-audit.json'].historical_rasters[2].research_download_url = 'https://unexpected.example/file.tif';
  });
  assert.equal(dom.window.document.querySelectorAll('#rows a').length, 8);
  assert.equal(dom.window.document.querySelectorAll('a[href^="https://unexpected.example"]').length, 0);
  assert.ok([...dom.window.document.querySelectorAll('#rows td:last-child')].every(td => /DO NOT SUBMIT/.test(td.textContent)));
  dom.window.close();
});

test('changed repository heads are disclosed without promoting a file', async () => {
  const {dom} = await render(null, false, true);
  assert.match(dom.window.document.querySelector('#freshness').textContent, /9 changed/);
  assert.equal(dom.window.document.querySelector('button').disabled, true);
  dom.window.close();
});

const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');
// Isolated DOM for the retained read-only dashboard script; the legacy page is superseded.
const html = '<!doctype html><html><body><button disabled></button><table><tbody id="rows"></tbody></table><div id="site-details"></div><div id="updated"></div></body></html>';
const script = fs.readFileSync('docs/dashboard.js', 'utf8');

async function render(change, failure = false) {
  const dom = new JSDOM(html, {runScripts: 'outside-only', url: 'https://example.org/docs/index.html'});
  const fixtures = Object.fromEntries(['sites.json', 'historical-audit.json'].map(path =>
    [path, JSON.parse(fs.readFileSync(`docs/${path}`, 'utf8'))]));
  if (change) change(fixtures);
  dom.window.fetch = async path => ({ok: !failure, status: failure ? 503 : 200,
    json: async () => fixtures[path]});
  dom.window.eval(script);
  await new Promise(resolve => setImmediate(resolve));
  return dom;
}

test('renders nine evidence rows and cards without an approved TIFF download', async () => {
  const dom = await render();
  const document = dom.window.document;
  assert.equal(document.querySelectorAll('#rows tr').length, 9);
  assert.equal(document.querySelectorAll('#site-details article').length, 9);
  assert.equal(document.querySelectorAll('#rows td:last-child').length, 9);
  for (const cell of document.querySelectorAll('#rows td:last-child')) {
    assert.match(cell.textContent, /NOT OK TO SUBMIT/);
  }
  assert.equal(document.querySelector('button').disabled, true);
  assert.equal(document.querySelectorAll('a[download][href$=".tif"]').length, 0);
  assert.doesNotMatch(document.querySelector('#updated').textContent, /failed/);
  dom.window.close();
});

test('HTTP failure fails closed with no table recommendations', async () => {
  const dom = await render(null, true);
  assert.equal(dom.window.document.querySelectorAll('#rows tr').length, 0);
  assert.match(dom.window.document.querySelector('#updated').textContent, /remain NOT OK TO SUBMIT/);
  dom.window.close();
});

test('unexpected source host clears partial evidence rather than offering a file', async () => {
  const dom = await render(fixtures => {
    fixtures['historical-audit.json'].rasters[2].source_url = 'https://unexpected.example/file.tif';
  });
  assert.equal(dom.window.document.querySelectorAll('#rows tr').length, 0);
  assert.equal(dom.window.document.querySelectorAll('#site-details article').length, 0);
  assert.match(dom.window.document.querySelector('#updated').textContent, /Unexpected source host/);
  dom.window.close();
});

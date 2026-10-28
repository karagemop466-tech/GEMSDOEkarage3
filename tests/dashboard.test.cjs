const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const {JSDOM} = require('jsdom');

test('retired misleading pages provide no downloadable submission and clearly say stop', () => {
  for (const file of ['docs/index.html', 'docs/executive-summary.html', 'docs/crsb-gub/index.html', 'docs/crsb-gub/executive-summary.html']) {
    const dom = new JSDOM(fs.readFileSync(file, 'utf8'));
    const d = dom.window.document;
    assert.match(d.body.textContent, /do not submit/i, file);
    assert.equal(d.querySelectorAll('a[href$=".tif"],a[href$=".zip"]').length, 0, file);
    dom.window.close();
  }
});

test('root scorecard retains nine rows and no authorized TIFF', () => {
  const dom = new JSDOM(fs.readFileSync('index.html', 'utf8'));
  const d = dom.window.document;
  assert.equal(d.querySelectorAll('#scorecard tbody tr').length, 9);
  assert.equal(d.querySelectorAll('a[download][href$=".tif"]').length, 0);
  assert.ok(d.querySelector('button[disabled]'));
  dom.window.close();
});

const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

const home = fs.readFileSync('docs/index.html', 'utf8');
const executive = fs.readFileSync('docs/executive-summary.html', 'utf8');
const manifest = JSON.parse(fs.readFileSync('registry/historical.json', 'utf8'));

function parse(html, path) {
  return new JSDOM(html, {url: `https://example.org/docs/${path}`}).window.document;
}

test('the /docs/ landing page fails closed and exposes no submission TIFF', () => {
  const document = parse(home, 'index.html');
  assert.match(document.body.textContent, /No file is ready/i);
  assert.match(document.body.textContent, /Assigned method lane not supplied/);
  assert.match(document.body.textContent, /No HOLDOUT-DTI run this session/);
  assert.equal(document.querySelectorAll('a[download][href$=".tif"]').length, 0);
  assert.doesNotMatch(document.body.textContent, /PROMOTE.*OK TO DOWNLOAD AND SUBMIT/i);
});

test('the executive page includes all nine historic entries and labels them research-only', () => {
  const document = parse(executive, 'executive-summary.html');
  assert.match(document.body.textContent, /NO FILE IS APPROVED FOR SUBMISSION/);
  assert.match(document.body.textContent, /No submission file available/);
  for (const row of manifest.historical) {
    assert.match(document.body.textContent, new RegExp(row.site));
    assert.ok(document.body.textContent.includes(row.historical_file), `missing file for ${row.site}`);
  }
  assert.equal(document.querySelectorAll('a[download][href$=".tif"]').length, 0);
  assert.match(document.body.textContent, /USER-REPORTED \/ unverified/);
  assert.match(document.body.textContent, /Estimated score/);
});

test('the root run card is the current no-candidate decision, separate from archived candidate evidence', () => {
  const card = JSON.parse(fs.readFileSync('evidence/run_card.json', 'utf8'));
  assert.equal(card.verdict, 'negative');
  assert.equal(card.ok_to_submit, false);
  assert.equal(card.slot_selected, false);
  assert.equal(card.experiments_run, 0);
  assert.equal(card.raster_sha256, null);
});

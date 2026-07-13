// Dependency-free structural tests for the static company-profile site.
// Uses only Node built-ins (node:test, node:assert, node:fs, node:path) — no npm deps.
// Verifies acceptance criteria: the three pages exist, shared navigation links
// resolve, CSS references resolve, and gallery image references are valid.

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '..');

const PAGES = {
  companyProfile: 'index.html', // AC: company profile
  contactUs: 'contact.html',    // AC: contact us
  gallery: 'gallery.html',      // AC: gallery
};

const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');
const exists = (rel) => fs.existsSync(path.join(root, rel));

// Extract href="..." / src="..." attribute values from an HTML string.
function extractRefs(html, attr) {
  const re = new RegExp(`${attr}\\s*=\\s*"([^"]+)"`, 'gi');
  const out = [];
  let m;
  while ((m = re.exec(html)) !== null) out.push(m[1]);
  return out;
}

// Resolve a page-relative reference to a repo-relative path, dropping any
// anchor/query and ignoring external (mailto:, http:) links.
function resolveRef(pageRel, ref) {
  if (/^(mailto:|https?:|tel:|#)/i.test(ref)) return null;
  const clean = ref.split('#')[0].split('?')[0];
  if (clean === '') return null;
  return path.normalize(path.join(path.dirname(pageRel), clean));
}

test('all three acceptance-criteria pages exist', () => {
  for (const [label, file] of Object.entries(PAGES)) {
    assert.ok(exists(file), `${label} page (${file}) should exist`);
  }
});

test('every page shares navigation linking all three pages, and links resolve', () => {
  const wanted = new Set(Object.values(PAGES));
  for (const page of Object.values(PAGES)) {
    const html = read(page);
    const localLinks = extractRefs(html, 'href')
      .map((ref) => ({ ref, resolved: resolveRef(page, ref) }))
      .filter((x) => x.resolved !== null && x.resolved.endsWith('.html'));

    // Nav must reference each of the three pages.
    for (const target of wanted) {
      assert.ok(
        localLinks.some((l) => l.resolved === path.normalize(target)),
        `${page} should link to ${target}`,
      );
    }

    // Every local .html link must resolve to a file that exists.
    for (const { ref, resolved } of localLinks) {
      assert.ok(exists(resolved), `${page}: link "${ref}" should resolve to an existing file`);
    }
  }
});

test('every page references the shared stylesheet and it resolves', () => {
  for (const page of Object.values(PAGES)) {
    const html = read(page);
    const cssRefs = extractRefs(html, 'href')
      .map((ref) => resolveRef(page, ref))
      .filter((r) => r !== null && r.endsWith('.css'));

    assert.ok(cssRefs.length > 0, `${page} should reference a stylesheet`);
    for (const css of cssRefs) {
      assert.ok(exists(css), `${page}: stylesheet "${css}" should exist`);
    }
  }
});

test('gallery image references are valid and resolve to real files', () => {
  const page = PAGES.gallery;
  const html = read(page);
  const imgs = extractRefs(html, 'src')
    .map((ref) => ({ ref, resolved: resolveRef(page, ref) }))
    .filter((x) => x.resolved !== null);

  assert.ok(imgs.length > 0, 'gallery should reference at least one image');
  for (const { ref, resolved } of imgs) {
    assert.ok(resolved.startsWith(path.join('assets', 'img')), `image "${ref}" should live under assets/img`);
    assert.ok(exists(resolved), `gallery image "${ref}" should exist on disk`);
  }
});

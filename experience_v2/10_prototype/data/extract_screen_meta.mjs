// Derive lightweight per-screen meta from the single source of truth (screens.js).
// Run with node; writes screen_meta.json next to screens.js.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.join(here, 'screens.js'), 'utf-8');
const window = {};
// screens.js assigns window.LUM_SCREENS = {...}; no other browser globals needed for parse.
new Function('window', src)(window);
const S = window.LUM_SCREENS;

function walkTypes(sections, acc) {
  if (!Array.isArray(sections)) return acc;
  for (const s of sections) {
    if (s && typeof s === 'object') {
      if (s.type) acc.push(s.type);
      if (Array.isArray(s.main)) walkTypes(s.main, acc);
      if (Array.isArray(s.side)) walkTypes(s.side, acc);
      if (Array.isArray(s.tabs)) for (const t of s.tabs) walkTypes(t.sections, acc);
      if (Array.isArray(s.items) && s.type !== 'kpis') { /* items are data, not sections */ }
    }
  }
  return acc;
}

const meta = {};
for (const [id, sc] of Object.entries(S)) {
  const head = (sc.sections || []).find(s => s.type === 'head') || {};
  const types = [];
  walkTypes(sc.sections, types);
  meta[id] = {
    title: head.title || sc.title || id,
    titleKey: head.titleKey || sc.titleKey || `screen.${id}`,
    eyebrow: head.eyebrow || '',
    chrome: sc.chrome || 'app',
    desc: head.desc || '',
    sectionTypes: [...new Set(types)],
  };
}
fs.writeFileSync(path.join(here, 'screen_meta.json'), JSON.stringify(meta, null, 2), 'utf-8');
console.log('screens:', Object.keys(meta).length);
console.log('sample AI-01:', JSON.stringify(meta['AI-01']).slice(0, 220));

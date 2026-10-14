import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const APPROVED_ACCOUNT = 'XHS_RETINAUT';
const APPROVED_REGION = 'intl';
const APPROVED_USER_ID = '6a3cef27000000000e03b800';

function dataRoot() {
  const configured = String(process.env.ZBC_DATA_DIR || '').trim();
  if (configured) return path.resolve(configured);

  let dbPath = String(process.env.ZBC_DB_PATH || '').trim();
  if (dbPath.startsWith('sqlite:///')) dbPath = dbPath.slice('sqlite:///'.length);
  else if (dbPath.startsWith('file:')) dbPath = dbPath.slice('file:'.length).split('?', 1)[0];
  if (dbPath) return path.dirname(path.resolve(dbPath));

  return path.join(path.dirname(fileURLToPath(import.meta.url)), 'data');
}

function resolvedFilesystemPath(value) {
  let cursor = path.resolve(value);
  const missingSegments = [];
  for (;;) {
    try {
      const real = fs.realpathSync.native(cursor);
      return path.resolve(real, ...missingSegments.reverse());
    } catch (error) {
      if (!['ENOENT', 'ENOTDIR'].includes(error?.code)) throw error;
      const parent = path.dirname(cursor);
      if (parent === cursor) throw error;
      missingSegments.push(path.basename(cursor));
      cursor = parent;
    }
  }
}

function normalized(value) {
  const resolved = resolvedFilesystemPath(value);
  return process.platform === 'win32' ? resolved.toLocaleLowerCase('en-US') : resolved;
}

function isContained(candidate, parent) {
  const relative = path.relative(parent, candidate);
  return relative !== '' && !relative.startsWith('..') && !path.isAbsolute(relative);
}

function registeredPaths() {
  const root = resolvedFilesystemPath(dataRoot());
  const privateRoot = resolvedFilesystemPath(path.join(root, 'private'));
  const profilesRoot = resolvedFilesystemPath(path.join(privateRoot, 'profiles'));
  const profile = resolvedFilesystemPath(path.join(profilesRoot, 'xhs-retinaut'));
  const cookie = resolvedFilesystemPath(path.join(privateRoot, 'xhs_cookie_retinaut.txt'));

  if (!isContained(privateRoot, root)
      || !isContained(profilesRoot, privateRoot)
      || !isContained(profile, profilesRoot)
      || !isContained(cookie, privateRoot)) {
    throw new Error('XHS_REGISTERED_PATH_ESCAPES_PRIVATE_ROOT');
  }
  return { privateRoot, profilesRoot, profile, cookie };
}

function assertApprovedIdentity() {
  if (process.env.XHS_COLLECTION_ACCOUNT !== APPROVED_ACCOUNT
      || process.env.XHS_COLLECTION_REGION !== APPROVED_REGION
      || process.env.XHS_EXPECTED_COLLECTION_USER_ID !== APPROVED_USER_ID) {
    throw new Error('XHS_APPROVED_HK_INTL_IDENTITY_REQUIRED');
  }
}

// These environment values are consistency assertions passed by the Python
// SYSTEM owner after its account/Permission/registry gate. They are not an
// authorization source; callers must never use this guard instead of that gate.
export function registeredXhsProfile() {
  assertApprovedIdentity();
  const expected = registeredPaths().profile;
  const supplied = String(process.env.XHS_PROFILE_DIR || '').trim();
  if (!supplied || normalized(supplied) !== normalized(expected)) {
    throw new Error('XHS_REGISTERED_PROFILE_MISMATCH');
  }
  return expected;
}

export function registeredXhsCookieFile() {
  assertApprovedIdentity();
  const expected = registeredPaths().cookie;
  const supplied = String(process.env.XHS_COOKIE_FILE || '').trim();
  if (!supplied || normalized(supplied) !== normalized(expected)) {
    throw new Error('XHS_REGISTERED_COOKIE_FILE_MISMATCH');
  }
  return expected;
}

function allowedRednoteHostname(hostname) {
  const normalizedHost = String(hostname || '').toLowerCase().replace(/\.$/, '');
  return normalizedHost === 'rednote.com' || normalizedHost.endsWith('.rednote.com');
}

function validateCookieLocation(cookie) {
  const urlText = typeof cookie.url === 'string' ? cookie.url.trim() : '';
  const domainText = typeof cookie.domain === 'string' ? cookie.domain.trim() : '';
  const pathText = typeof cookie.path === 'string' ? cookie.path.trim() : '';

  if (urlText) {
    // Playwright accepts url OR domain+path, never both. Validate a supplied URL
    // independently so a valid domain cannot mask a conflicting/insecure URL.
    if (domainText || pathText) throw new Error('XHS_COOKIE_PLAYWRIGHT_LOCATION_CONFLICT');
    let target;
    try { target = new URL(urlText); } catch { throw new Error('XHS_COOKIE_URL_INVALID'); }
    if (target.protocol !== 'https:' || target.username || target.password
        || (target.port && target.port !== '443') || target.hash
        || !allowedRednoteHostname(target.hostname)) {
      throw new Error('XHS_COOKIE_URL_NOT_ALLOWED');
    }
    if (cookie.secure !== true) throw new Error('XHS_COOKIE_SECURE_REQUIRED');
    return;
  }

  if (!domainText || !pathText || !pathText.startsWith('/')) {
    throw new Error('XHS_COOKIE_DOMAIN_PATH_REQUIRED');
  }
  const domain = domainText.replace(/^\./, '').toLowerCase();
  if (!/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*rednote\.com$/.test(domain)
      || !allowedRednoteHostname(domain)) {
    throw new Error('XHS_COOKIE_DOMAIN_NOT_ALLOWED');
  }
  if (cookie.secure !== true) throw new Error('XHS_COOKIE_SECURE_REQUIRED');
}

export function assertApprovedCookiePayload(cookies) {
  assertApprovedIdentity();
  if (!Array.isArray(cookies) || cookies.length === 0) {
    throw new Error('XHS_COOKIE_PAYLOAD_REQUIRED');
  }
  const identity = cookies.filter(cookie =>
    String(cookie?.name || '').trim().toLowerCase() === 'x-user-id-pro');
  if (identity.length !== 1 || String(identity[0]?.value || '').trim() !== APPROVED_USER_ID) {
    throw new Error('XHS_COOKIE_IDENTITY_MISMATCH');
  }
  for (const cookie of cookies) {
    if (!cookie || typeof cookie !== 'object' || Array.isArray(cookie)) {
      throw new Error('XHS_COOKIE_INVALID');
    }
    validateCookieLocation(cookie);
  }
  return true;
}

export async function verifyRegisteredXhsBrowserContext(context) {
  assertApprovedIdentity();
  if (!context || typeof context.cookies !== 'function'
      || typeof context.pages !== 'function') {
    throw new Error('COLLECTOR_IDENTITY_CONTEXT_UNAVAILABLE');
  }

  let cookies;
  try {
    cookies = await context.cookies(['https://www.rednote.com']);
  } catch {
    throw new Error('COLLECTOR_IDENTITY_UNAVAILABLE');
  }
  if (!Array.isArray(cookies) || !cookies.some(cookie =>
    String(cookie?.name || '').toLowerCase() === 'web_session'
      && String(cookie?.value || '').trim())) {
    throw new Error('COLLECTOR_IDENTITY_NOT_VERIFIED');
  }
  const userIds = new Set(cookies
    .filter(cookie => String(cookie?.name || '').toLowerCase() === 'x-user-id-pro'
      && String(cookie?.value || '').trim())
    .map(cookie => String(cookie.value).trim().toLowerCase()));
  if (userIds.size !== 1 || !userIds.has(APPROVED_USER_ID)) {
    throw new Error('COLLECTOR_IDENTITY_MISMATCH');
  }
  const holderCountries = new Set(cookies
    .filter(cookie => String(cookie?.name || '').toLowerCase() === 'x-rednote-holderctry'
      && String(cookie?.value || '').trim())
    .map(cookie => String(cookie.value).trim().toUpperCase()));
  if (holderCountries.size > 0
      && (holderCountries.size !== 1 || !holderCountries.has('HK'))) {
    throw new Error('COLLECTOR_IDENTITY_MISMATCH');
  }

  let rednotePages;
  try {
    rednotePages = context.pages().filter(page => {
      const url = new URL(String(page.url() || ''));
      return url.protocol === 'https:' && url.hostname === 'www.rednote.com';
    });
  } catch {
    throw new Error('COLLECTOR_IDENTITY_NOT_VERIFIED');
  }
  if (rednotePages.length === 0) {
    throw new Error('COLLECTOR_IDENTITY_NOT_VERIFIED');
  }

  const selfIds = new Set();
  try {
    for (const page of rednotePages) {
      const candidates = await page.locator('a.link-wrapper, a.bottom-channel').evaluateAll(els =>
        els.map(el => ({
          classes: Array.from(el.classList || []),
          text: (el.innerText || el.textContent || '').trim(),
          href: el.getAttribute('href') || '',
        })));
      for (const item of candidates || []) {
        const classes = new Set(item.classes || []);
        if (String(item.text || '').replace(/\s+/g, '') !== '我'
            || (!classes.has('link-wrapper') && !classes.has('bottom-channel'))) continue;
        const href = new URL(String(item.href || ''), 'https://www.rednote.com');
        if (href.protocol !== 'https:' || href.hostname !== 'www.rednote.com'
            || href.username || href.password || href.port || href.search || href.hash) {
          throw new Error('COLLECTOR_IDENTITY_MISMATCH');
        }
        const match = href.pathname.match(/^\/user\/profile\/([0-9a-f]{24})\/?$/i);
        if (!match) throw new Error('COLLECTOR_IDENTITY_MISMATCH');
        selfIds.add(match[1].toLowerCase());
      }
    }
  } catch (error) {
    if (/^COLLECTOR_IDENTITY_/.test(String(error?.message || ''))) throw error;
    throw new Error('COLLECTOR_IDENTITY_NOT_VERIFIED');
  }
  if (selfIds.size !== 1 || !selfIds.has(APPROVED_USER_ID)) {
    throw new Error(selfIds.size ? 'COLLECTOR_IDENTITY_MISMATCH' : 'COLLECTOR_IDENTITY_NOT_VERIFIED');
  }

  return {
    account: APPROVED_ACCOUNT,
    region: APPROVED_REGION,
    source_host: 'www.rednote.com',
    verification_method: 'registered_context_cookie_and_self_profile',
    identity_fingerprint_sha256: crypto.createHash('sha256').update(APPROVED_USER_ID).digest('hex'),
  };
}

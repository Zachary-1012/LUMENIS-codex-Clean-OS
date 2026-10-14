import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import test, { afterEach, beforeEach } from 'node:test';
import {
  assertApprovedCookiePayload,
  registeredXhsCookieFile,
  registeredXhsProfile,
  verifyRegisteredXhsBrowserContext,
} from '../xhs_profile_guard.js';

const require = createRequire(import.meta.url);
const rednoteCollector = require('../rednote_collector.cjs');
const { connectRegisteredWorker } = rednoteCollector;

const identity = '6a3cef27000000000e03b800';
const envNames = [
  'ZBC_DATA_DIR', 'ZBC_DB_PATH', 'XHS_COLLECTION_ACCOUNT',
  'XHS_COLLECTION_REGION', 'XHS_EXPECTED_COLLECTION_USER_ID',
  'XHS_PROFILE_DIR', 'XHS_COOKIE_FILE', 'XHS_CDP_URL', 'XHS_COLLECTION_HOST',
];
let previousEnv;
let root;
let profile;
let cookieFile;

beforeEach(() => {
  previousEnv = Object.fromEntries(envNames.map(name => [name, process.env[name]]));
  root = fs.mkdtempSync(path.join(os.tmpdir(), 'lumenis-xhs-profile-'));
  profile = path.join(root, 'private', 'profiles', 'xhs-retinaut');
  cookieFile = path.join(root, 'private', 'xhs_cookie_retinaut.txt');
  fs.mkdirSync(profile, { recursive: true });
  fs.writeFileSync(cookieFile, 'synthetic-test-placeholder', 'utf8');
  process.env.ZBC_DATA_DIR = root;
  delete process.env.ZBC_DB_PATH;
  process.env.XHS_COLLECTION_ACCOUNT = 'XHS_RETINAUT';
  process.env.XHS_COLLECTION_REGION = 'intl';
  process.env.XHS_EXPECTED_COLLECTION_USER_ID = identity;
  process.env.XHS_PROFILE_DIR = profile;
  process.env.XHS_COOKIE_FILE = cookieFile;
  process.env.XHS_CDP_URL = 'http://127.0.0.1:9234';
  process.env.XHS_COLLECTION_HOST = 'www.rednote.com';
});

afterEach(() => {
  for (const name of envNames) {
    if (previousEnv[name] === undefined) delete process.env[name];
    else process.env[name] = previousEnv[name];
  }
  if (root) fs.rmSync(root, { recursive: true, force: true });
});

function syntheticCookies(overrides = {}) {
  return [{
    name: 'x-user-id-pro', value: identity,
    domain: '.rednote.com', path: '/', secure: true,
    ...overrides,
  }];
}

function syntheticBrowserContext({ userId = identity, profileId = identity, host = 'www.rednote.com' } = {}) {
  const page = {
    url: () => `https://${host}/explore`,
    locator: selector => ({
      evaluateAll: async () => {
        assert.equal(selector, 'a.link-wrapper, a.bottom-channel');
        return [{ classes: ['link-wrapper'], text: '我', href: `/user/profile/${profileId}` }];
      },
    }),
  };
  return {
    cookies: async () => [
      { name: 'web_session', value: 'synthetic-session' },
      { name: 'x-user-id-pro', value: userId },
      { name: 'x-rednote-holderctry', value: 'HK' },
    ],
    pages: () => [page],
  };
}

test('resolves only the registered HK/intl profile and cookie paths', () => {
  assert.equal(registeredXhsProfile(), fs.realpathSync(profile));
  assert.equal(registeredXhsCookieFile(), fs.realpathSync(cookieFile));
  process.env.XHS_PROFILE_DIR = path.join(root, 'private', 'profiles', 'other');
  assert.throws(registeredXhsProfile, /XHS_REGISTERED_PROFILE_MISMATCH/);
  process.env.XHS_PROFILE_DIR = profile;
  process.env.XHS_COOKIE_FILE = path.join(root, 'private', 'other-cookie.txt');
  assert.throws(registeredXhsCookieFile, /XHS_REGISTERED_COOKIE_FILE_MISMATCH/);
});

test('resolves junction targets and rejects a profile redirected outside the registered profiles root', t => {
  const outside = path.join(root, 'outside-profile');
  fs.mkdirSync(outside);
  fs.rmSync(profile, { recursive: true, force: true });
  try {
    fs.symlinkSync(outside, profile, 'junction');
  } catch (error) {
    if (['EPERM', 'EACCES', 'ENOTSUP'].includes(error?.code)) {
      t.skip(`junction creation unavailable in this environment: ${error.code}`);
      return;
    }
    throw error;
  }
  assert.throws(registeredXhsProfile, /XHS_REGISTERED_PATH_ESCAPES_PRIVATE_ROOT/);
});

test('accepts only the approved synthetic identity and secure RedNote domain cookies', () => {
  assert.equal(assertApprovedCookiePayload(syntheticCookies()), true);
  assert.equal(assertApprovedCookiePayload([{
    name: 'x-user-id-pro', value: identity,
    url: 'https://www.rednote.com/explore', secure: true,
  }]), true);
});

test('rejects foreign, insecure, credential-bearing, conflicting or malformed cookie targets', () => {
  const rejected = [
    [{ domain: '.rednote.com', path: '/', url: 'http://evil.example/path' }],
    [{ domain: '.rednote.com', path: '/', url: 'https://evil.example/path', secure: true }],
    [{ url: 'https://user:secret@rednote.com/', secure: true }],
    [{ url: 'https://rednote.com:444/', secure: true }],
    [{ url: 'https://rednote.com/', secure: false }],
    [{ domain: '.rednote.com', path: '/', secure: false }],
    [{ domain: '.rednote.com.evil.example', path: '/', secure: true }],
    [{ domain: '.rednote.com', path: '/', url: 'https://www.rednote.com/', secure: true }],
  ];
  for (const [override] of rejected) {
    assert.throws(() => assertApprovedCookiePayload(syntheticCookies(override)));
  }
  assert.throws(() => assertApprovedCookiePayload(syntheticCookies({ value: '61d58d560000000010005a8a' })), /XHS_COOKIE_IDENTITY_MISMATCH/);
});

test('rejects identity declarations outside the approved server-bound account labels', () => {
  process.env.XHS_COLLECTION_ACCOUNT = 'XHS_CN_PRIMARY';
  assert.throws(registeredXhsProfile, /XHS_APPROVED_HK_INTL_IDENTITY_REQUIRED/);
  process.env.XHS_COLLECTION_ACCOUNT = 'XHS_RETINAUT';
  process.env.XHS_COLLECTION_REGION = 'cn';
  assert.throws(() => assertApprovedCookiePayload(syntheticCookies()), /XHS_APPROVED_HK_INTL_IDENTITY_REQUIRED/);
});

test('verifies the attached browser cookies and existing RedNote self-profile before use', async () => {
  const evidence = await verifyRegisteredXhsBrowserContext(syntheticBrowserContext());
  assert.deepEqual(evidence, {
    account: 'XHS_RETINAUT', region: 'intl', source_host: 'www.rednote.com',
    verification_method: 'registered_context_cookie_and_self_profile',
    identity_fingerprint_sha256: crypto.createHash('sha256').update(identity).digest('hex'),
  });
  await assert.rejects(verifyRegisteredXhsBrowserContext(
    syntheticBrowserContext({ userId: '61d58d560000000010005a8a' })),
  /COLLECTOR_IDENTITY_MISMATCH/);
  await assert.rejects(verifyRegisteredXhsBrowserContext(
    syntheticBrowserContext({ host: 'www.xiaohongshu.com' })),
  /COLLECTOR_IDENTITY_NOT_VERIFIED/);
});

test('CJS collector rejects an unregistered dynamic endpoint before connecting', async () => {
  let connectCalls = 0;
  const result = await rednoteCollector.collect({
    keyword: 'synthetic test query', maxDetails: 1, maxScroll: 0,
    registeredWorkerResolver: async () => ({
      available: false, code: 'XHS_REGISTERED_WORKER_UNAVAILABLE',
    }),
    browserConnector: { connectOverCDP: async () => {
      connectCalls += 1;
      throw new Error('must not connect');
    } },
  });
  assert.equal(result.ok, false);
  assert.equal(result.code, 'XHS_REGISTERED_WORKER_UNAVAILABLE');
  assert.equal(connectCalls, 0);
});

test('legacy synchronous search rejects an unregistered local worker before connection', async () => {
  let connectCalls = 0;
  const result = await connectRegisteredWorker('http://127.0.0.1:9234', {
    registeredWorkerResolver: async () => ({
      available: false, code: 'XHS_REGISTERED_WORKER_UNAVAILABLE',
    }),
    browserConnector: { connectOverCDP: async () => {
      connectCalls += 1;
      throw new Error('must not connect');
    } },
  });
  assert.deepEqual(result, { ok: false, code: 'XHS_REGISTERED_WORKER_UNAVAILABLE' });
  assert.equal(connectCalls, 0);
});

test('legacy synchronous search rejects a remote endpoint before resolving or connecting', async () => {
  let resolverCalls = 0;
  let connectCalls = 0;
  const result = await connectRegisteredWorker('https://remote-worker.invalid', {
    registeredWorkerResolver: async () => {
      resolverCalls += 1;
      return { available: true };
    },
    browserConnector: { connectOverCDP: async () => {
      connectCalls += 1;
      throw new Error('must not connect');
    } },
  });
  assert.deepEqual(result, { ok: false,
    code: 'COLLECTOR_REMOTE_WORKER_IDENTITY_UNVERIFIED' });
  assert.equal(resolverCalls, 0);
  assert.equal(connectCalls, 0);
});

test('legacy sync-search caller uses the shared gate and has no browser or cookie fallback', () => {
  const source = fs.readFileSync(new URL('../xhs_cookie_search.js', import.meta.url), 'utf8');
  assert.match(source, /connectRegisteredWorker\(cdpUrl,\s*\{\s*browserConnector:\s*chromium\s*\}\)/);
  assert.doesNotMatch(source, /launchPersistentContext|addCookies/);
});

test('sync-search releases only its task page and CDP client after navigation failures', () => {
  const source = fs.readFileSync(new URL('../xhs_cookie_search.js', import.meta.url), 'utf8');
  const finallyStart = source.indexOf('  } finally {', source.indexOf('let page=null;'));
  const resultWrite = source.indexOf('\n  writeResult(output,result);', finallyStart);
  assert.ok(finallyStart >= 0 && resultWrite > finallyStart,
    'page and client cleanup must run from a finally block');
  const cleanup = source.slice(finallyStart, resultWrite);
  assert.match(cleanup, /if \(page\)[\s\S]*?await page\.close\(\)/);
  assert.match(cleanup, /await browser\.disconnect\(\)/);
  assert.doesNotMatch(source, /process\.exit\(/);
  assert.match(source, /catch\(error\)\s*\{\s*exitCode=1;[\s\S]*?error_code:'NAV_FAILED'/);
});

test('CJS collector rejects a remote endpoint before connecting', async () => {
  let connectCalls = 0;
  process.env.XHS_CDP_URL = 'https://remote-worker.invalid';
  const result = await rednoteCollector.collect({
    keyword: 'synthetic test query', maxDetails: 1, maxScroll: 0,
    browserConnector: { connectOverCDP: async () => {
      connectCalls += 1;
      throw new Error('must not connect');
    } },
  });
  assert.equal(result.ok, false);
  assert.equal(result.code, 'COLLECTOR_REMOTE_WORKER_IDENTITY_UNVERIFIED');
  assert.equal(connectCalls, 0);
});

test('CJS collector refuses to create or navigate a collection page before actual identity verification', async () => {
  let newPageCalls = 0;
  let collectionNavigationCalls = 0;
  const page = {
    url: () => 'https://www.rednote.com/explore',
    locator: () => ({ evaluateAll: async () => [] }),
    goto: async () => { collectionNavigationCalls += 1; },
  };
  const context = {
    cookies: async () => [
      { name: 'web_session', value: 'synthetic-session' },
      { name: 'x-user-id-pro', value: '61d58d560000000010005a8a' },
      { name: 'x-rednote-holderctry', value: 'HK' },
    ],
    pages: () => [page],
    newPage: async () => { newPageCalls += 1; throw new Error('unexpected collection page'); },
  };
  const result = await rednoteCollector.collect({
    keyword: 'synthetic test query', maxDetails: 1, maxScroll: 0,
    registeredWorkerResolver: async () => ({
      available: true, account: 'XHS_RETINAUT', browser: 'edge', port: 9234,
      endpoint: 'http://127.0.0.1:9234', profile, pid: 12345,
      headless: true, loopback_only: true,
    }),
    browserConnector: { connectOverCDP: async () => ({ contexts: () => [context] }) },
  });
  assert.equal(result.ok, false);
  assert.equal(result.code, 'COLLECTOR_IDENTITY_MISMATCH');
  assert.deepEqual(result.notes, []);
  assert.equal(newPageCalls, 0);
  assert.equal(collectionNavigationCalls, 0);
});

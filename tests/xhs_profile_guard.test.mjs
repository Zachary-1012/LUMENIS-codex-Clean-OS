import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test, { afterEach, beforeEach } from 'node:test';
import {
  assertApprovedCookiePayload,
  registeredXhsCookieFile,
  registeredXhsProfile,
} from '../xhs_profile_guard.js';

const identity = '6a3cef27000000000e03b800';
const envNames = [
  'ZBC_DATA_DIR', 'ZBC_DB_PATH', 'XHS_COLLECTION_ACCOUNT',
  'XHS_COLLECTION_REGION', 'XHS_EXPECTED_COLLECTION_USER_ID',
  'XHS_PROFILE_DIR', 'XHS_COOKIE_FILE',
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

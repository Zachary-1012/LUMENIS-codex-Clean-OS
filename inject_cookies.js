// Cookie 注入仅允许写入经过服务端注册身份校验的香港/国际 RedNote Profile。
import { assertApprovedCookiePayload, registeredXhsProfile } from './xhs_profile_guard.js';

const userDataDir = registeredXhsProfile();
const raw = process.env.XHS_COOKIES_JSON || '';
if (!raw) {
  console.error('[inject] 未提供 XHS_COOKIES_JSON。为避免 Cookie 泄露，不再把登录凭据硬编码进脚本。');
  process.exit(2);
}
let cookies;
try { cookies = JSON.parse(raw); } catch (e) { console.error('[inject] Cookie JSON 无效:', e.message); process.exit(2); }
if (!Array.isArray(cookies) || !cookies.length) { console.error('[inject] Cookie 必须是非空数组'); process.exit(2); }
try { assertApprovedCookiePayload(cookies); }
catch { console.error('[inject] Cookie 身份或域与已登记的香港/国际 RedNote 来源不匹配。'); process.exit(2); }

async function main() {
  const { chromium } = await import('playwright');
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: true,
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage'],
  });
  await context.addCookies(cookies);
  const page = context.pages()[0] || await context.newPage();
  await page.goto('https://www.rednote.com/explore', {waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForTimeout(2500);
  const loginBtn = await page.locator('#login-btn').count();
  console.log(loginBtn > 0 ? '[inject] ⚠️ 仍未登录，Cookie 可能已过期。' : '[inject] ✅ 登录态已写入本地 Chromium profile。');
  await context.close();
}
main().catch(e => { console.error('[inject] ERROR:',e.message); process.exit(1); });

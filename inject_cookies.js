// 安全版 Cookie 注入：不再把真实登录 Cookie 写进源码。
// 使用：XHS_COOKIES_JSON='[{"name":"web_session","value":"...","domain":".xiaohongshu.com","path":"/"}]' node inject_cookies.js
import { chromium } from 'playwright';

const userDataDir = (process.env.XHS_PROFILE_DIR || '').trim();
if (!userDataDir) {
  console.error('[inject] XHS_PROFILE_DIR_REQUIRED: use the profile registered for the selected account.');
  process.exit(2);
}
const raw = process.env.XHS_COOKIES_JSON || '';
if (!raw) {
  console.error('[inject] 未提供 XHS_COOKIES_JSON。为避免 Cookie 泄露，不再把登录凭据硬编码进脚本。');
  process.exit(2);
}
let cookies;
try { cookies = JSON.parse(raw); } catch (e) { console.error('[inject] Cookie JSON 无效:', e.message); process.exit(2); }
if (!Array.isArray(cookies) || !cookies.length) { console.error('[inject] Cookie 必须是非空数组'); process.exit(2); }

async function main() {
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: true,
    args: ['--no-sandbox','--disable-setuid-sandbox','--disable-dev-shm-usage'],
  });
  await context.addCookies(cookies);
  const page = context.pages()[0] || await context.newPage();
  await page.goto('https://www.xiaohongshu.com/explore', {waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForTimeout(2500);
  const loginBtn = await page.locator('#login-btn').count();
  console.log(loginBtn > 0 ? '[inject] ⚠️ 仍未登录，Cookie 可能已过期。' : '[inject] ✅ 登录态已写入本地 Chromium profile。');
  await context.close();
}
main().catch(e => { console.error('[inject] ERROR:',e.message); process.exit(1); });

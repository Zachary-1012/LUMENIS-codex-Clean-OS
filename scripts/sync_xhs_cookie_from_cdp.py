# -*- coding: utf-8 -*-
"""从 9222 真人持久 Profile 同步新鲜小红书 Cookie 到 headless 采集通道使用的静态 header。

背景：采集走 headless + 注入静态 cookie（data/private/xhs_cookie_header.txt）。真人在 9222 窗口
重新登录/会话轮换后，静态 header 会旧化为 website-login/error?type=51「安全限制」（搜索 API 0 调用）。

合并策略（关键）：
- 9222 浏览器 Http cookie 提供“会轮换的新鲜登录态”（web_session/a1/gid/webId 等），优先级最高；
- 旧 header 补充浏览器 cookie 库不持有、但本地白名单/设备需要的稳定字段（如 x-user-id-pro、
  customerClientId）；当前文件缺失时自动从最近 .bak 备份补齐；
- 只连本机 CDP 读取已有合法登录态，不打印 cookie 值，文件在 data/private（不进 git），覆盖前备份；
- 9222 必须已由人工完成合法登录；不破解、不绕过任何平台验证。

用法：
  .venv\\Scripts\\python.exe scripts\\sync_xhs_cookie_from_cdp.py
  .venv\\Scripts\\python.exe scripts\\sync_xhs_cookie_from_cdp.py --dry-run
"""
import argparse
import glob
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, 'data', 'private', 'xhs_cookie_header.txt')
# 必须具备的登录态
REQUIRED = ('web_session',)
# 浏览器 Http cookie 库通常不持有、需要从旧 header 延续的稳定账号/设备字段
ACCOUNT_KEYS = ('x-user-id-pro', 'customerClientId')
ALLOWED_USER_ID = '61d58d560000000010005a8a'


def fetch_cdp_cookies(cdp_url: str):
    from playwright.sync_api import sync_playwright
    jar = {}
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(cdp_url)
        try:
            for ctx in b.contexts:
                for c in ctx.cookies():
                    if 'xiaohongshu.com' in c.get('domain', '') and c.get('name') and c.get('value'):
                        jar[c['name']] = c['value']
        finally:
            b.close()
    return jar


def read_header(path: str):
    m = {}
    if path and os.path.exists(path):
        for pair in open(path, 'r', encoding='utf-8').read().split(';'):
            if '=' in pair:
                k, v = pair.strip().split('=', 1)
                m[k.strip()] = v.strip()
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cdp', default='http://127.0.0.1:9222')
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    jar = fetch_cdp_cookies(args.cdp)
    print(f'9222 新鲜 Http cookie 项数 = {len(jar)}')
    missing = [k for k in REQUIRED if k not in jar]
    if missing:
        print(f'[ABORT] 9222 真人 profile 缺少登录态 {missing}；请先在 9222 窗口人工登录小红书后重试。')
        return 2

    # 旧 header 打底（补浏览器不持有的稳定账号字段）；缺账号字段时从最近备份补
    old = read_header(args.out)
    need = [k for k in ACCOUNT_KEYS if k not in old]
    if need:
        for bak in sorted(glob.glob(args.out + '.bak*'), reverse=True):
            bm = read_header(bak)
            for k in [x for x in need if x in bm]:
                old[k] = bm[k]
            need = [k for k in ACCOUNT_KEYS if k not in old]
            if not need:
                break

    merged = {**old, **jar}  # 9222 新鲜值覆盖同名旧值
    inherited = sorted(k for k in merged if k not in jar)
    print(f'合并后总项数 = {len(merged)}；由旧文件延续的稳定字段 = {inherited}')
    if 'x-user-id-pro' not in merged:
        print('[WARN] 仍缺 x-user-id-pro，本地账号白名单 verify_account 会不通过；请检查备份或人工补充。')
    elif merged.get('x-user-id-pro') != ALLOWED_USER_ID:
        print('[WARN] x-user-id-pro 与白名单账号不一致（只显示是否匹配，不打印值）。')
    else:
        print('x-user-id-pro 与白名单账号匹配 OK')
    header = '; '.join(f'{k}={v}' for k, v in sorted(merged.items()))

    if args.dry_run:
        print('[DRY-RUN] 未写入。键列表 =', sorted(merged.keys()))
        return 0

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    if os.path.exists(args.out):
        bak = f'{args.out}.bak{time.strftime("%Y%m%d%H%M%S")}'
        with open(args.out, 'rb') as fsrc, open(bak, 'wb') as fdst:
            fdst.write(fsrc.read())
        print('已备份旧 header ->', os.path.basename(bak))
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(header)
    print('[OK] 已写入合并 cookie header，项数 =', len(merged), '->', os.path.relpath(args.out, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())

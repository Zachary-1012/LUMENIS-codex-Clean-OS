# -*- coding: utf-8 -*-
"""
update_reference.py —— GitHub 参考仓库一键更新脚本  v5.8.4
================================================================
作用：
  1) 读取 reference_repos.json（5 大分类的种子仓库清单）；
  2) 调 GitHub REST API 拉取每个仓库的最新 star、最近提交(pushed_at)、
     更新时间、语言、描述、是否归档等；
  3) 按 5 大分类的 search_queries 自动搜索新的高 star 仓库并去重补入；
  4) 更新前自动备份旧 data/reference_db.json 到 backups/reference/；
  5) 重建 data/reference_db.json（机器读）与 reference_catalog.md（人读目录）。

用法：
  python update_reference.py                # 更新 + 搜新仓库
  python update_reference.py --no-search    # 只更新清单内仓库，不搜新
  python update_reference.py --top 8        # 每个分类最多自动补 8 个新仓库(默认6)
  python update_reference.py --offline      # 不联网，仅用现有 db 重建 catalog
  python update_reference.py --min-stars 500

可选环境变量：
  GITHUB_TOKEN=ghp_xxx   提升 API 限额（匿名 60 次/小时，带 token 5000 次/小时）
"""
import os
import sys
import json
import time
import shutil
import argparse
import urllib.request
import urllib.parse
import urllib.error
import datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(ROOT, 'reference_repos.json')
DB = os.path.join(ROOT, 'data', 'reference_db.json')
CATALOG = os.path.join(ROOT, 'reference_catalog.md')
BACKUP_DIR = os.path.join(ROOT, 'backups', 'reference')
API = 'https://api.github.com'
TOKEN = os.getenv('GITHUB_TOKEN', '').strip()


def log(msg):
    print(f'[{dt.datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)


def http_json(url, retries=2, timeout=15):
    """带 token、重试、限流处理的 GET JSON。"""
    headers = {'Accept': 'application/vnd.github+json',
               'User-Agent': 'lumenis-reference-updater'}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            reset = e.headers.get('X-RateLimit-Reset')
            remain = e.headers.get('X-RateLimit-Remaining')
            if e.code in (403, 429) and remain == '0' and reset:
                wait = max(0, int(reset) - int(time.time())) + 2
                if wait <= 120:
                    log(f'  触发限流，等待 {wait}s 到限额重置…')
                    time.sleep(wait)
                    continue
                else:
                    raise RuntimeError(f'GitHub 限流，需等到 {reset}（{wait}s 后），可设置 GITHUB_TOKEN')
            if e.code == 404:
                return {'_missing': True, '_url': url}
            last_err = f'HTTP {e.code}'
        except Exception as e:
            last_err = str(e)
        time.sleep(1.2 * (attempt + 1))
    return {'_error': last_err, '_url': url}


def fetch_repo(full_name):
    d = http_json(f'{API}/repos/{full_name}')
    if d.get('_missing'):
        return {'full_name': full_name, 'ok': False, 'error': '404 仓库不存在或已改名'}
    if d.get('_error'):
        return {'full_name': full_name, 'ok': False, 'error': d['_error']}
    return {
        'ok': True,
        'full_name': d.get('full_name', full_name),
        'html_url': d.get('html_url', f'https://github.com/{full_name}'),
        'description': d.get('description') or '',
        'language': d.get('language') or '',
        'stars': d.get('stargazers_count', 0),
        'forks': d.get('forks_count', 0),
        'open_issues': d.get('open_issues_count', 0),
        'archived': bool(d.get('archived')),
        'pushed_at': d.get('pushed_at', ''),
        'updated_at': d.get('updated_at', ''),
        'created_at': d.get('created_at', ''),
        'license': (d.get('license') or {}).get('spdx_id') if d.get('license') else '',
        'topics': d.get('topics', []),
    }


def search_new(query, min_stars, top, known):
    q = urllib.parse.quote(f'{query} stars:>={min_stars}')
    url = f'{API}/search/repositories?q={q}&sort=stars&order=desc&per_page={top}'
    d = http_json(url)
    out = []
    if not d or d.get('_error') or 'items' not in d:
        return out
    for it in d['items'][:top]:
        fn = it['full_name']
        if fn.lower() in known:
            continue
        known.add(fn.lower())
        out.append({
            'ok': True, 'full_name': fn, 'html_url': it['html_url'],
            'description': it.get('description') or '', 'language': it.get('language') or '',
            'stars': it.get('stargazers_count', 0), 'forks': it.get('forks_count', 0),
            'open_issues': it.get('open_issues_count', 0), 'archived': bool(it.get('archived')),
            'pushed_at': it.get('pushed_at', ''), 'updated_at': it.get('updated_at', ''),
            'created_at': it.get('created_at', ''),
            'license': (it.get('license') or {}).get('spdx_id') if it.get('license') else '',
            'topics': it.get('topics', []), 'auto_discovered': True,
        })
    return out


def backup_old():
    if not os.path.exists(DB):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(BACKUP_DIR, f'reference_db_{ts}.json')
    shutil.copy2(DB, dst)
    return dst


def build_catalog(db):
    lines = ['# GitHub 参考仓库目录（自动生成）', '',
             f'> 由 `update_reference.py` 于 {db["generated_at"]} 生成；共 {db["summary"]["total"]} 个仓库（自动发现 {db["summary"]["auto_discovered"]}）。',
             '> 字段：⭐ star · 最近提交 pushed_at · 语言 · 归档状态。', '']
    for cat in db['categories']:
        repos = cat['repos']
        repos.sort(key=lambda x: x.get('stars', 0), reverse=True)
        lines += [f'## {cat["name"]}', '', f'共 {len(repos)} 个。', '']
        lines += ['| 仓库 | ⭐Star | 最近提交 | 语言 | 归档 | 说明 |', '|---|--:|---|---|---|---|']
        for r in repos:
            if not r.get('ok'):
                lines.append(f'| `{r["full_name"]}` | - | - | - | - | ⚠️ {r.get("error","拉取失败")} |')
                continue
            pushed = (r.get('pushed_at') or '')[:10]
            desc = (r.get('description') or '').replace('|', '/').replace('\n', ' ')[:60]
            arc = '⛔归档' if r.get('archived') else ''
            tag = ' 🆕' if r.get('auto_discovered') else ''
            lines.append(f'| [{r["full_name"]}{tag}]({r["html_url"]}) | {r["stars"]:,} | {pushed} | {r.get("language","")} | {arc} | {desc} |')
        lines.append('')
    with open(CATALOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-search', action='store_true', help='不自动搜新仓库')
    ap.add_argument('--offline', action='store_true', help='离线：仅用现有 db 重建 catalog')
    ap.add_argument('--top', type=int, default=6, help='每分类自动补新仓库上限')
    ap.add_argument('--min-stars', type=int, default=300, help='自动搜新仓库的最低 star')
    args = ap.parse_args()

    if args.offline:
        if not os.path.exists(DB):
            log('无 data/reference_db.json，无法离线重建'); return 1
        with open(DB, encoding='utf-8') as f:
            db = json.load(f)
        build_catalog(db)
        log(f'离线重建 {CATALOG}'); return 0

    with open(SEED, encoding='utf-8') as f:
        seed = json.load(f)
    cats_meta = seed['categories']
    seeds = seed['repos']
    known = {s['full_name'].lower() for s in seeds}

    # 分类 -> 种子仓库
    by_cat = {c['key']: [] for c in cats_meta}
    for s in seeds:
        by_cat.setdefault(s['category'], []).append(s['full_name'])

    bk = backup_old()
    if bk:
        log(f'已备份旧库 -> {os.path.relpath(bk, ROOT)}')

    out_cats = []
    total = auto = fail = 0
    for c in cats_meta:
        key = c['key']
        log(f'== 分类 {c["name"]} ==')
        repos = []
        for fn in by_cat.get(key, []):
            r = fetch_repo(fn)
            repos.append(r); total += 1
            if r.get('ok'):
                log(f'   ✓ {fn}  ⭐{r["stars"]}  pushed {r["pushed_at"][:10]}')
            else:
                fail += 1; log(f'   ✗ {fn}  {r.get("error")}')
            time.sleep(0.3)
        if not args.no_search:
            for q in c.get('search_queries', []):
                found = search_new(q, args.min_stars, args.top, known)
                for r in found:
                    r['category'] = key
                    repos.append(r); total += 1; auto += 1
                    log(f'   🆕 {r["full_name"]} ⭐{r["stars"]}')
                time.sleep(1.5)  # search API 限速更保守
        for r in repos:
            r.setdefault('category', key)
        out_cats.append({'key': key, 'name': c['name'], 'repos': repos})

    db = {
        'generated_at': dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {'total': total, 'auto_discovered': auto, 'failed': fail,
                    'min_stars': args.min_stars},
        'categories': out_cats,
    }
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with open(DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    build_catalog(db)
    log(f'完成：总 {total}，自动发现 {auto}，失败 {fail}')
    log(f'机器库 -> {os.path.relpath(DB, ROOT)}')
    log(f'人读目录 -> {os.path.relpath(CATALOG, ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

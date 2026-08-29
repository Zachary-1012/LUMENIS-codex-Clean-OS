"""
广州太古汇舆情监测系统 - RedNote 采集模块
使用 rednote-cli 浏览器实例 + 自定义 Playwright 搜索脚本
采集小红书广州太古汇相关笔记
"""
import subprocess
import json
import os
import re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEARCH_SCRIPT = os.path.join(SCRIPT_DIR, 'xhs_search_v2.js')
INSTANCE_NAME = 'taikoo'

# 监测关键词组
MONITOR_KEYWORDS = [
    '广州太古汇',
    '太古汇 投诉',
    '太古汇 避雷',
    '太古汇 活动',
    '太古汇 新店',
    '太古汇 方所',
    '太古汇 停车',
]

def _check_profile_lock():
    """检查持久化 Chromium profile 是否可能被其他进程占用。

    旧版会直接删除 SingletonLock/SingletonCookie/SingletonSocket。
    这在 Windows 上尤其危险：如果另一个 Chromium 实例正在使用 profile，
    强删锁文件可能导致 profile 损坏或两个浏览器同时写入。现在只做检测，
    真正的锁冲突交给 Playwright 返回错误。
    """
    lock_dir = os.path.expanduser('~/.skills-router/rednote/instances/taikoo')
    return any(os.path.exists(os.path.join(lock_dir, f)) for f in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'))

def search_xiaohongshu(keyword, max_scroll=4, output_path=None):
    """
    使用自定义脚本搜索小红书
    返回 dict: {keyword, total, notes: [...]}
    """
    profile_locked = _check_profile_lock()

    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, 'data', f'search_{int(datetime.now().timestamp())}.json')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        'node', SEARCH_SCRIPT,
        '--keyword', keyword,
        '--output', output_path,
        '--max-scroll', str(max_scroll),
    ]

    try:
        if profile_locked:
            # 不主动删除锁；Playwright 的持久化 profile 可能确实被另一个实例占用。
            # 仍然尝试启动，由浏览器决定是否可以安全复用。
            pass
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or '').strip()
            return {'keyword': keyword, 'total': 0, 'notes': [], 'error': err[-800:] or f'Node exited with code {result.returncode}'}

        # 解析 stdout 中的 JSON
        stdout = result.stdout.strip()
        # 找到第一个 { 开始的 JSON
        idx = stdout.find('{')
        if idx >= 0:
            data = json.loads(stdout[idx:])
            return data
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': 'No JSON output'}
    except subprocess.TimeoutExpired:
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': 'Timeout'}
    except Exception as e:
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': str(e)}


def collect_all(keywords=None, max_scroll=4):
    """
    批量采集所有关键词
    返回去重后的笔记列表
    """
    if keywords is None:
        keywords = MONITOR_KEYWORDS

    all_notes = {}
    collection_results = []

    for kw in keywords:
        print(f"[Collector] 搜索: {kw}")
        result = search_xiaohongshu(kw, max_scroll=max_scroll)
        count = result.get('total', 0)
        error = result.get('error', '')
        collection_results.append({'keyword': kw, 'count': count, 'error': error})
        print(f"[Collector]   -> {count} 条 {'(错误: '+error+')' if error else ''}")

        for note in result.get('notes', []):
            nid = note.get('note_id')
            if nid and nid not in all_notes:
                # 标记来源关键词
                note['source_keyword'] = kw
                all_notes[nid] = note

    notes_list = list(all_notes.values())
    print(f"[Collector] 去重后共 {len(notes_list)} 条笔记")
    return notes_list, collection_results


def import_from_file(filepath):
    """从已有的搜索结果 JSON 文件导入数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('notes', [])

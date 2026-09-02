# -*- coding: utf-8 -*-
"""runtime_bin 统一 Node 解析器单测。

回归背景：topic_campaign 等模块曾用裸 'node' 走 subprocess，生产常驻进程
PATH 缺 node 时抛 WinError 2，导致 topic_campaign_snapshots 326 条中 310 条 error。
"""
import os
import sys
import subprocess

import pytest

import runtime_bin


@pytest.fixture(autouse=True)
def _clear_cache():
    runtime_bin.resolve_node.cache_clear()
    yield
    runtime_bin.resolve_node.cache_clear()


def test_resolve_node_returns_runnable():
    node = runtime_bin.resolve_node()
    assert node, '必须解析到一个可用 node（PATH 或项目内置 nodejs/）'
    if node != 'node':
        assert os.path.isfile(node), f'解析结果应是真实文件: {node}'
    # 解析到的 node 必须真的能跑通 --version
    out = subprocess.run([node, '--version'], capture_output=True, text=True, timeout=15)
    assert out.returncode == 0
    assert out.stdout.strip().startswith('v')


def test_candidates_include_builtin_nodejs():
    cands = runtime_bin._candidate_paths()
    root = os.path.dirname(os.path.abspath(runtime_bin.__file__))
    exe = 'node.exe' if sys.platform.startswith('win') else 'node'
    builtin = os.path.join(root, 'nodejs', exe)
    assert builtin in cands, '候选必须包含项目内置 nodejs/，作为脱离 PATH 的确定性兜底'


def test_explicit_env_has_top_priority(monkeypatch, tmp_path):
    fake = tmp_path / ('node.exe' if sys.platform.startswith('win') else 'node')
    fake.write_text('placeholder')
    monkeypatch.setenv('NODE_EXE', str(fake))
    runtime_bin.resolve_node.cache_clear()
    assert runtime_bin.resolve_node() == str(fake)


def test_diagnostics_structure():
    diag = runtime_bin.node_diagnostics()
    assert set(diag) >= {'resolved', 'candidates', 'builtin_exists', 'platform'}
    assert isinstance(diag['candidates'], list) and diag['candidates']


def test_node_or_raise_returns_path():
    node = runtime_bin.node_or_raise()
    assert node


def test_topic_campaign_uses_resolver_not_bare_node():
    """回归：topic_campaign 内不得再出现裸 ['node', ...] 子进程命令。"""
    here = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(os.path.dirname(here), 'topic_campaign.py')
    with open(src_path, encoding='utf-8') as f:
        src = f.read()
    assert "_node_bin()" in src, 'topic_campaign 必须通过 _node_bin() 解析 node'
    assert "['node', script" not in src, '不得残留裸 node 子进程命令'

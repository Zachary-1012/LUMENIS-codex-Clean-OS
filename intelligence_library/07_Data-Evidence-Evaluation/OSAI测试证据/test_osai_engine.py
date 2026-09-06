# -*- coding: utf-8 -*-
"""OSAI 自主执行闭环 v1 测试（确定性部分，可离线运行；不依赖智谱）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import config, evidence, research, tools


def test_config_paths():
    assert os.path.isdir(config.ZBC_ROOT), "ZBC 路径不存在"
    assert os.path.isdir(config.OSAI_ROOT), "OSAI 路径不存在"
    assert os.path.exists(config.PYTHON), "ZBC 解释器不存在"
    assert os.path.isdir(config.LEARNING_DIR), "learning-feed 目录不存在"


def test_tools_git_status():
    out = tools.git_status(config.OSAI_ROOT)
    assert isinstance(out, str)


def test_tools_read_write_tmp():
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.txt")
    tools.write_text(p, "hello")
    assert tools.read_text(p) == "hello"
    tools.append_text(p, " world")
    assert tools.read_text(p) == "hello world"


def test_research_knowledge_search():
    hits = research.knowledge_search(["营销"], limit=3)
    assert isinstance(hits, list)
    assert len(hits) >= 1, "learning-feed 应存在营销知识库条目"


def test_research_inbox_safe():
    # inbox 目录不存在也应安全返回空
    inbox = research.absorb_inbox()
    assert isinstance(inbox, list)


def test_evidence_record_creates_file():
    import tempfile
    # 用临时证据目录（覆盖 config.EVIDENCE_DIR）
    tmp = tempfile.mkdtemp()
    old = config.EVIDENCE_DIR
    config.EVIDENCE_DIR = tmp
    try:
        p = evidence.record("TEST-ROUND", "测试任务", [{"stage": "测试", "status": "ok", "detail": "x"}],
                            result="ok", repo="OSAI")
        assert os.path.exists(p)
        txt = open(p, encoding="utf-8").read()
        assert "TEST-ROUND" in txt and "测试任务" in txt
    finally:
        config.EVIDENCE_DIR = old


def test_agent_plan_without_key_degrades():
    # 无 API key 时 plan 必须降级（返回 None 或 skip），不抛异常、不阻断
    import os
    os.environ.pop("ZHIPU_API_KEY", None)
    d, provider = None, None
    try:
        from osai_engine import agent
        d, provider = agent.plan("测试", "ctx")
    except Exception as e:
        assert False, "plan 不应抛异常: %s" % e
    assert d is None or d.get("action") in ("skip", "git_commit_push", "run_pytest",
                                            "research", "write_evidence", "write_patch")


def test_rules_injected_into_system():
    """踩坑规则已固化进 agent system（rules.py 非空且 _SYSTEM 包含规则提示）。"""
    from osai_engine import agent, rules
    assert rules.RULES and len(rules.RULES) >= 5, "规则列表不应为空"
    assert "seed" in rules.rules_brief().lower() or "shuffle" in rules.rules_brief().lower()
    assert "glm-4.7" in rules.rules_brief() or "思考模型" in rules.rules_brief()
    assert "OSAI 工程执行规则" in agent._SYSTEM, "规则未注入 agent system prompt"

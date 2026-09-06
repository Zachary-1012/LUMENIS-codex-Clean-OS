# -*- coding: utf-8 -*-
"""web_monitor.py — 网页话题发现兼容层。

历史模块，原文件已重构为 web_monitor_v570.py。
本文件提供 reprocess.py 等旧代码依赖的 discover() / feedback_keywords() 兼容接口。
实现为安全存根：返回空结果，不影响核心舆情链路。
新代码请直接使用 web_topic_discovery.py 或 web_monitor_v570.py。
"""
from __future__ import annotations
from typing import Any, Dict, List


def discover(limit: int = 20) -> List[Dict[str, Any]]:
    """发现网页话题（兼容存根，返回空列表）。"""
    return []


def feedback_keywords(items: List[Dict[str, Any]] = None) -> List[str]:
    """从话题项中提取反馈关键词（兼容存根，返回空列表）。"""
    return []

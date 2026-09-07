# -*- coding: utf-8 -*-
"""agent_capability 测试共享 fixture — 复用 agent_memory 的临时DB fixture。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从 agent_memory 的 conftest 导入共享 fixture
from tests.agent_memory.conftest import temp_db, seeded_db

__all__ = ["temp_db", "seeded_db"]

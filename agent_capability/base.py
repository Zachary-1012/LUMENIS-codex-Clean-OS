# -*- coding: utf-8 -*-
"""agent_capability 基础工具。"""
from __future__ import annotations

import sqlite3
from typing import Optional


def get_db_connection(db_path: str):
    """获取 SQLite 连接。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

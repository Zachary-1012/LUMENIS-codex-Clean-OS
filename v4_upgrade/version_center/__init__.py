# -*- coding: utf-8 -*-
"""V4 版本中心（Version Center）——系统内置的 GitHub 源码版本保险库。

能力：状态总览、版本历史、一键保存版本（安全闸 + commit + push）、检查更新、
拉取、回滚（默认保留历史的 revert）、自动保存守护。
源码与 Cookie/密钥/数据库严格分离，敏感内容双保险拦截、绝不入库。
"""
from .routes import version_bp
from .git_manager import GitVersionManager, gm
from .watcher import start_version_watcher

__all__ = ["version_bp", "GitVersionManager", "gm", "start_version_watcher"]

"""全网采集中心子包：页面路由（采集 API 复用主蓝图 /v4/adapters/*）。"""
from .routes import collect_bp

__all__ = ["collect_bp"]

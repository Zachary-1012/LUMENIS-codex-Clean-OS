"""V4 AI Hub —— 统一智能服务总线。

定位（不重复造轮子）：
- 复用主系统 intelligence.py 与唯一 SYSTEM AI Gateway；不发现或回退退役 Provider；
- 复用 function_registry.py（用户问题 → 系统内功能/品牌/案例/笔记/事件真实数据）；
- 复用 ai_analyzer / ai_gateway_v570（可审计的本地规则分析，外部 AI 全部退出时系统仍完整可跑）。

AI 只做"增强通道"，绝不成为核心依赖；任何对外结论都以系统内可核对数据为准，不补造事实。
"""
from .routes import ai_bp
from . import service, shadow

__all__ = ["ai_bp", "service", "shadow"]

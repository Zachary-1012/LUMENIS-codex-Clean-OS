# -*- coding: utf-8 -*-
"""ProxyPool 可插拔代理池（v1.0）。

设计原则（与《可插拔 ProxyPool 补丁1.0》一致）：
- 默认关闭（PROXY_POOL_ENABLED=false 时，系统行为与无代理版本完全一致）；
- 只做合法网络出口管理 / 健康检查 / 故障切换，不实现任何验证码绕过、指纹伪装、风控绕过；
- 敏感信息（VLESS UUID/Reality/账号密码）一律不进源码，只通过本地 v2rayN/Xray 端口或 .env 注入；
- 代理异常自动冷却并切换，最终按平台策略决定是否回退直连，绝不让舆情主系统崩溃；
- GitHub 免费公开节点只能“人工审核后”通过 config/proxy_nodes.json 导入，本模块不自动抓取未知节点。
"""
from .manager import proxy_manager, ProxyUnavailable
from .models import ProxyNode
from .adapters import create_session, request, safe_request

__all__ = ["proxy_manager", "ProxyUnavailable", "ProxyNode",
           "create_session", "request", "safe_request"]

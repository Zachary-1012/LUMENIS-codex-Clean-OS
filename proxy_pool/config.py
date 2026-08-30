# -*- coding: utf-8 -*-
"""ProxyPool 配置：全部可经环境变量 / .env 覆盖，敏感信息不硬编码。"""
import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


class ProxyConfig:
    # 总开关：默认关闭。关闭时 get_requests_proxies 永远返回 None，系统等同直连原版。
    ENABLED = env_bool("PROXY_POOL_ENABLED", False)

    # direct：不使用代理；local：使用本机 v2rayN/Xray 暴露的 HTTP/SOCKS 端口（付费 VLESS 落地）
    MODE = os.getenv("PROXY_POOL_MODE", "direct").strip().lower()

    HTTP_PROXY = os.getenv("PROXY_HTTP", "").strip()
    SOCKS_PROXY = os.getenv("PROXY_SOCKS", "").strip()

    # 健康检查：默认走 gstatic generate_204（验证“能否通过该节点出海”）。可经 env 改成自有稳定地址。
    HEALTHCHECK_URL = os.getenv("PROXY_HEALTHCHECK_URL", "https://www.gstatic.com/generate_204").strip()
    HEALTHCHECK_TIMEOUT = float(os.getenv("PROXY_HEALTHCHECK_TIMEOUT", "8"))

    FAILURE_THRESHOLD = int(os.getenv("PROXY_FAILURE_THRESHOLD", "3"))
    RECOVERY_THRESHOLD = int(os.getenv("PROXY_RECOVERY_THRESHOLD", "2"))
    COOLDOWN_SECONDS = int(os.getenv("PROXY_COOLDOWN_SECONDS", "300"))

    # 代理全部不可用时，是否允许回退直连（总闸）。平台级仍可在 safe_request 用 allow_direct=False 收紧。
    ALLOW_DIRECT_FALLBACK = env_bool("PROXY_ALLOW_DIRECT_FALLBACK", True)

    # 兼容现有适配器历史变量：GOOGLE_PROXY / OPENAI_PROXY（去 http(s):// 前缀的逻辑在 loader 内处理）
    LEGACY_PROXY = os.getenv("GOOGLE_PROXY", "").strip() or os.getenv("OPENAI_PROXY", "").strip()

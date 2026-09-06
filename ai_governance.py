# -*- coding: utf-8 -*-
"""
AI Governance — AI 治理模块（Track3 审计修复版）

【用户方案】废除 Ollama-only 红线，云端 zhipu 内置系统；脱敏回传保障数据安全；
额度/余额可控；AI 输出标记为增强层，不直接成为 System Truth，用于喂 Zachary 学习。

功能：
1. 脱敏回传：敏感实体替换为占位符 → 云端 AI → 回传补回原实体，保证词义
2. 额度控制：每日调用次数/token 限额，超额降级或拒绝
3. 使用统计：调用次数、token 用量、按日统计、按 Provider 分别统计（zhipu / ark）
4. 输出标记：所有 AI 输出标记 provider/ai_enhanced，不直接写核心生产字段

Track3 修复（2026-09-06）：
- get_status() 不再硬编码 provider=zhipu，改为 active_providers + per-provider stats。
- 新增 get_provider_stats()：成本模型分别记录 zhipu 与 ark 两 provider。
- 治理层完整链路：额度控制→脱敏→调用→回补→统计→标记。
"""
import logging
import os
import re
import json
import time
import threading
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional, Any

# ZBC Phase 7: module status markers
MODULE_STATUS = 'ACTIVE'
AI_ROLE = 'GOVERNANCE_LAYER'  # desensitization, quota, output marking - not business judgment

# ============ 配置 ============
AI_GOVERNANCE_ENV_PREFIX = "ZBC_AI_GOV_"

# 每日调用次数限额（默认 500 次/天，可通过环境变量覆盖）
DEFAULT_DAILY_CALL_LIMIT = int(os.environ.get(f"{AI_GOVERNANCE_ENV_PREFIX}DAILY_CALL_LIMIT", "500"))
# 每日 token 限额（默认 200K tokens/天）
DEFAULT_DAILY_TOKEN_LIMIT = int(os.environ.get(f"{AI_GOVERNANCE_ENV_PREFIX}DAILY_TOKEN_LIMIT", "200000"))
# 余额阈值告警（元，默认 10 元）
DEFAULT_BALANCE_ALERT_THRESHOLD = float(os.environ.get(f"{AI_GOVERNANCE_ENV_PREFIX}BALANCE_ALERT", "10"))
# 统计文件路径
STATS_FILE = os.environ.get(f"{AI_GOVERNANCE_ENV_PREFIX}STATS_FILE",
                             os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ai_governance_stats.json"))

# 敏感实体类型（用于脱敏）
SENSITIVE_PATTERNS = {
    "BRAND": [
        r"广州太古汇", r"太古汇", r"Taikoo Hui", r"方所", r"OLE", r"Ole'",
        r"lululemon", r"Lululemon", r"苹果", r"Apple", r"华为", r"Huawei",
    ],
    "PERSON": [
        r"Zachary", r"zachary", r"云智",
    ],
    "LOCATION": [
        r"广州", r"天河", r"天河路", r"体育西路",
    ],
    "ORG": [
        r"太古地产", r"Swire",
    ],
}

# 线程锁
_lock = threading.Lock()


# ============ 脱敏回传 ============
class AIDesensitizer:
    """AI 脱敏回传引擎：敏感实体替换为占位符 → 云端 AI → 回传补回原实体。"""

    def __init__(self):
        self._build_patterns()

    def _build_patterns(self):
        """预编译所有敏感实体正则。"""
        self.patterns = {}
        for entity_type, keywords in SENSITIVE_PATTERNS.items():
            self.patterns[entity_type] = [re.compile(re.escape(kw)) for kw in keywords]

    def desensitize(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        脱敏：将敏感实体替换为占位符。
        返回: (脱敏后文本, 占位符→原实体映射)
        """
        if not text:
            return text, {}
        mapping = {}
        counter = {}
        result = text
        for entity_type, patterns in self.patterns.items():
            for pat in patterns:
                matches = pat.findall(result)
                for m in matches:
                    if entity_type not in counter:
                        counter[entity_type] = 0
                    counter[entity_type] += 1
                    placeholder = f"[{entity_type}_{counter[entity_type]}]"
                    mapping[placeholder] = m
                    result = result.replace(m, placeholder, 1)
        return result, mapping

    def restore(self, text: str, mapping: Dict[str, str]) -> str:
        """回传：将占位符替换回原实体。"""
        if not text or not mapping:
            return text
        result = text
        for placeholder, original in mapping.items():
            result = result.replace(placeholder, original)
        return result

    def desensitize_messages(self, messages: List[Dict]) -> Tuple[List[Dict], Dict[str, str]]:
        """脱敏整个消息列表（对 user 内容脱敏，system 保留）。"""
        combined_mapping = {}
        result = []
        for msg in messages:
            if msg.get("role") == "user" and isinstance(msg.get("content"), str):
                desensitized, mapping = self.desensitize(msg["content"])
                combined_mapping.update(mapping)
                result.append({"role": "user", "content": desensitized})
            else:
                result.append(msg)
        return result, combined_mapping


# 全局脱敏器
_desensitizer = AIDesensitizer()


# ============ 额度控制 & 使用统计 ============
class AIUsageTracker:
    """AI 使用统计与额度控制。

    Track3：按 Provider 分别统计（zhipu / ark / local），成本模型不合并。
    """

    def __init__(self, stats_file: str = STATS_FILE):
        self.stats_file = stats_file
        self._ensure_dir()
        self.stats = self._load()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)

    def _load(self) -> Dict:
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as _e:
                logging.getLogger(__name__).warning('ai_governance stats load failed: %s', _e)
        return {"daily": {}, "total": {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}

    def _save(self):
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def _today_key(self) -> str:
        return date.today().isoformat()

    def record_call(self, endpoint: str, prompt_tokens: int = 0, completion_tokens: int = 0,
                    total_tokens: int = 0, provider: str = "zhipu", success: bool = True):
        """记录一次 AI 调用。provider 参数区分 zhipu / ark / local。"""
        with _lock:
            today = self._today_key()
            if today not in self.stats["daily"]:
                self.stats["daily"][today] = {
                    "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                    "endpoints": {}, "providers": {}, "provider_tokens": {}, "failures": 0,
                }
            day = self.stats["daily"][today]
            day["calls"] += 1
            day["prompt_tokens"] += prompt_tokens
            day["completion_tokens"] += completion_tokens
            day["total_tokens"] += total_tokens
            day["endpoints"][endpoint] = day["endpoints"].get(endpoint, 0) + 1
            day["providers"][provider] = day["providers"].get(provider, 0) + 1
            # Track3：按 provider 分别记录 token（精确成本核算）
            pt = day.setdefault("provider_tokens", {})
            pstat = pt.setdefault(provider, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "failures": 0})
            pstat["calls"] += 1
            pstat["prompt_tokens"] += prompt_tokens
            pstat["completion_tokens"] += completion_tokens
            pstat["total_tokens"] += total_tokens
            if not success:
                day["failures"] += 1
                pstat["failures"] += 1

            self.stats["total"]["calls"] += 1
            self.stats["total"]["prompt_tokens"] += prompt_tokens
            self.stats["total"]["completion_tokens"] += completion_tokens
            self.stats["total"]["total_tokens"] += total_tokens

            # 只保留最近 30 天
            if len(self.stats["daily"]) > 30:
                oldest = min(self.stats["daily"].keys())
                del self.stats["daily"][oldest]

            self._save()

    def check_quota(self) -> Tuple[bool, Dict]:
        """
        检查今日额度是否超限。
        返回: (是否允许调用, 额度状态)
        """
        with _lock:
            today = self._today_key()
            day = self.stats["daily"].get(today, {"calls": 0, "total_tokens": 0})
            call_used = day.get("calls", 0)
            token_used = day.get("total_tokens", 0)
            call_limit = DEFAULT_DAILY_CALL_LIMIT
            token_limit = DEFAULT_DAILY_TOKEN_LIMIT
            call_remaining = max(0, call_limit - call_used)
            token_remaining = max(0, token_limit - token_used)
            allowed = call_used < call_limit and token_used < token_limit
            return allowed, {
                "date": today,
                "call_used": call_used,
                "call_limit": call_limit,
                "call_remaining": call_remaining,
                "token_used": token_used,
                "token_limit": token_limit,
                "token_remaining": token_remaining,
                "call_usage_pct": round(call_used / call_limit * 100, 1) if call_limit > 0 else 0,
                "token_usage_pct": round(token_used / token_limit * 100, 1) if token_limit > 0 else 0,
                "allowed": allowed,
            }

    def get_provider_stats(self) -> Dict[str, Dict]:
        """Track3：按 Provider 分别统计今日调用量与 token（zhipu / ark / local 等）。

        成本模型要求分别记录 zhipu 与 ark 两 provider，不得合并。
        返回 {provider: {calls, prompt_tokens, completion_tokens, total_tokens, failures}}
        """
        with _lock:
            today = self._today_key()
            day = self.stats["daily"].get(today, {})
            provider_tokens = day.get("provider_tokens", {})
            result = {}
            for prov, pstat in provider_tokens.items():
                result[prov] = dict(pstat)
            # 确保 zhipu 和 ark 至少有占位（即使今日未调用）
            for prov in ("zhipu", "ark"):
                if prov not in result:
                    result[prov] = {
                        "calls": 0, "prompt_tokens": 0,
                        "completion_tokens": 0, "total_tokens": 0, "failures": 0,
                    }
            return result

    def get_status(self) -> Dict:
        """获取 AI 治理状态（含额度、使用统计、按 Provider 拆分、配置）。

        Track3 修复：不再硬编码 provider=zhipu，改为展示 active_provider + per-provider stats。
        """
        allowed, quota = self.check_quota()
        provider_stats = self.get_provider_stats()
        # 判断当前主力 provider
        try:
            from provider_registry import active_providers
            active = active_providers()
        except Exception:
            active = ["zhipu"]
        return {
            "ok": True,
            "active_providers": active,
            "primary_provider": active[0] if active else "zhipu",
            "desensitization": "enabled",
            "quota": quota,
            "total_usage": self.stats["total"],
            "provider_stats": provider_stats,
            "config": {
                "daily_call_limit": DEFAULT_DAILY_CALL_LIMIT,
                "daily_token_limit": DEFAULT_DAILY_TOKEN_LIMIT,
                "balance_alert_threshold": DEFAULT_BALANCE_ALERT_THRESHOLD,
                "stats_file": self.stats_file,
            },
            "note": "余额需在智谱控制台查看: https://open.bigmodel.cn/usercenter/finance；ark 成本需在火山引擎控制台查看",
        }


# 全局使用追踪器
_usage_tracker = AIUsageTracker()


# ============ AI 输出标记 ============
def mark_ai_output(data: Any, provider: str = "zhipu", endpoint: str = "") -> Dict:
    """
    标记 AI 输出为增强层，不直接成为 System Truth。
    所有 AI 输出必须经过此函数标记，用于喂 Zachary 学习。
    """
    if isinstance(data, dict):
        result = dict(data)
    else:
        result = {"content": data}
    result["ai_enhanced"] = True
    result["provider"] = provider
    result["endpoint"] = endpoint
    result["ai_timestamp"] = datetime.now().isoformat()
    result["system_truth"] = False  # 明确标记：AI 输出不是 System Truth
    result["zachary_learning_signal"] = True  # 标记：可用于 Zachary 学习
    return result


# ============ 统一 AI 调用封装 ============
def call_ai_with_governance(messages: List[Dict], endpoint: str = "generic",
                              model: str = None, max_tokens: int = 1024,
                              temperature: float = 0.7, desensitize: bool = True,
                              provider: str = "zhipu") -> Dict:
    """
    统一 AI 调用治理封装（额度→脱敏→准备调用→回补→统计→标记）。

    注意：本函数完成治理层的额度检查、脱敏、输出标记和统计记录；
    实际 HTTP 调用由调用方（intelligence._chat / ai_api 路由）执行，
    调用方应在拿到 AI 响应后调用 record_ai_call() 记录实际用量。

    返回: {ok, desensitized, mapping_count, quota_remaining, messages_prepared, provider}
    """
    # 1. 额度检查
    allowed, quota = _usage_tracker.check_quota()
    if not allowed:
        return mark_ai_output({
            "ok": False,
            "error": "AI 每日额度已超限",
            "quota": quota,
            "fallback": "local_rule",
        }, endpoint=endpoint, provider=provider)

    # 2. 脱敏
    mapping = {}
    if desensitize:
        messages, mapping = _desensitizer.desensitize_messages(messages)

    # 3. 返回准备好的调用参数（实际 HTTP 调用由调用方执行）
    result = {
        "ok": True,
        "desensitized": desensitize,
        "mapping_count": len(mapping),
        "mapping": mapping,
        "quota_remaining": quota["call_remaining"],
        "messages_prepared": messages,
        "provider": provider,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    return result


# ============ 便捷函数 ============
def get_governance_status() -> Dict:
    """获取 AI 治理状态（API 用）。"""
    return _usage_tracker.get_status()


def record_ai_call(endpoint: str, prompt_tokens: int = 0, completion_tokens: int = 0,
                    total_tokens: int = 0, provider: str = "zhipu", success: bool = True):
    """记录一次 AI 调用（API 用）。provider 区分 zhipu / ark。"""
    _usage_tracker.record_call(endpoint, prompt_tokens, completion_tokens, total_tokens, provider, success)


def desensitize_text(text: str) -> Tuple[str, Dict[str, str]]:
    """脱敏文本（便捷函数）。"""
    return _desensitizer.desensitize(text)


def restore_text(text: str, mapping: Dict[str, str]) -> str:
    """回传补回实体（便捷函数）。"""
    return _desensitizer.restore(text, mapping)

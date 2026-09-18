# -*- coding: utf-8 -*-
"""ResponseAnalyzer：把 HTTP 状态码 / 页面文本 / 异常统一归类为采集状态机状态。

只做识别与归因，不实现任何验证码绕过、指纹伪装或风控对抗。
输出 (state, reason_code, reason_text)，供限速器/熔断/健康中心/Auth Recovery 使用。
"""
import re
from .state import CollectState


# 归因码 -> 状态；顺序即优先级（越靠前越确定、越需要停）
class Reason:
    IP_RISK_300012 = 'IP_RISK_300012'
    IP_BLOCKED = 'IP_BLOCKED'
    RATE_LIMITED = 'RATE_LIMITED'
    NEED_CAPTCHA = 'NEED_CAPTCHA'
    AUTH_EXPIRED = 'AUTH_EXPIRED'
    FORBIDDEN = 'FORBIDDEN'
    NETWORK = 'NETWORK'
    EMPTY = 'EMPTY_LOAD'
    HEALTHY = 'HEALTHY'


_IP_PATTERNS = [
    (re.compile(r'300012'), Reason.IP_RISK_300012),
    (re.compile(r'ip[^\n]{0,6}(存在风险|风险|异常|被封|受限)', re.I), Reason.IP_BLOCKED),
    (re.compile(r'(安全限制|访问受限|当前访问出现异常|账号异常|blocked|access denied)', re.I), Reason.IP_BLOCKED),
]
_RATE_PATTERNS = [
    re.compile(r'(访问过于频繁|操作频繁|请求过于频繁|too many requests|rate ?limit|频繁访问|稍后再试)', re.I),
]
_CAPTCHA_PATTERNS = [
    re.compile(r'(验证码|安全验证|请完成验证|请通过验证|滑块|拖动|人机验证|captcha|verify\s*it|challenge|are\s*you\s*a\s*robot|安全检测)', re.I),
]
_AUTH_PATTERNS = [
    re.compile(r'(登录已失效|请先登录|未登录|登录状态失效|login\s*required|sign\s*in\s*to|not\s*logged\s*in|会话已过期|session\s*expired)', re.I),
]


class ResponseAnalyzer:
    """无状态分类器，可被任意采集器复用。"""

    @staticmethod
    def classify(status_code=200, text='', error=None, has_content=False, retry_after=None):
        """返回 dict: {state, reason, detail, should_stop}。

        :param status_code: HTTP 状态码（拿不到可传 0）
        :param text: 响应正文/页面可见文本片段
        :param error: 捕获到的异常对象或字符串（网络层）
        :param has_content: 是否确实解析到业务内容（用于区分真空与风控空）
        :param retry_after: 服务端 Retry-After 指示的等待秒数（可选，用于授权冷却时长）
        """
        body = (text or '')
        low = body

        # 1) 网络层错误（异常优先判定为可重试，不诬陷平台风控）
        if error is not None:
            es = str(error)
            if re.search(r'(timeout|timed out|超时|connection|reset|refused|unreachable|断开|网络)', es, re.I):
                return {'state': CollectState.NETWORK_ERROR, 'reason': Reason.NETWORK,
                        'detail': es[:160], 'should_stop': False}

        # 2) IP 风险 / 300012 / 安全限制 —— 最高优先熔断
        for pat, code in _IP_PATTERNS:
            m = pat.search(low)
            if m:
                return {'state': CollectState.COOLDOWN, 'reason': code,
                        'detail': m.group(0)[:60], 'should_stop': True}

        # 3) 人机验证 —— 暂停等合法人工，绝不绕过
        for pat in _CAPTCHA_PATTERNS:
            m = pat.search(low)
            if m:
                return {'state': CollectState.NEED_VERIFY, 'reason': Reason.NEED_CAPTCHA,
                        'detail': m.group(0)[:60], 'should_stop': True}

        # 4) 登录失效
        for pat in _AUTH_PATTERNS:
            m = pat.search(low)
            if m:
                return {'state': CollectState.AUTH_REQUIRED, 'reason': Reason.AUTH_EXPIRED,
                        'detail': m.group(0)[:60], 'should_stop': True}
        if status_code in (401,):
            return {'state': CollectState.AUTH_REQUIRED, 'reason': Reason.AUTH_EXPIRED,
                    'detail': f'HTTP {status_code}', 'should_stop': True}
        if status_code in (403,):
            return {'state': CollectState.COOLDOWN, 'reason': Reason.FORBIDDEN,
                    'detail': f'HTTP {status_code} 拒绝访问', 'should_stop': True}

        # 5) 频控：429 立即返回（原先被后续 EMPTY/HEALTHY 分支吞掉，导致频控信号丢失）
        if status_code == 429:
            _ra = {'retry_after': retry_after} if retry_after else {}
            return {'state': CollectState.WARNING, 'reason': Reason.RATE_LIMITED,
                    'detail': 'HTTP 429', 'should_stop': False, **_ra}
        for pat in _RATE_PATTERNS:
            m = pat.search(low)
            if m:
                return {'state': CollectState.WARNING, 'reason': Reason.RATE_LIMITED,
                        'detail': m.group(0)[:60], 'should_stop': False}

        # 6) 网络层状态码
        if status_code in (0,) or (status_code >= 500):
            return {'state': CollectState.NETWORK_ERROR, 'reason': Reason.NETWORK,
                    'detail': f'HTTP {status_code}', 'should_stop': False}

        # 7) 200 但无内容：区分“加载失败”而非健康（交由上层决定是否重试/冷却）
        if not has_content and not body.strip():
            return {'state': CollectState.NETWORK_ERROR, 'reason': Reason.EMPTY,
                    'detail': '响应为空', 'should_stop': False}

        return {'state': CollectState.HEALTHY, 'reason': Reason.HEALTHY,
                'detail': 'ok', 'should_stop': False}

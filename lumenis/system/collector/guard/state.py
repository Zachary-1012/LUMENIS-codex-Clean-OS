# -*- coding: utf-8 -*-
"""Collector Guard 采集状态机定义。

状态分层（与用户口径一致，三类风险绝不混为“0 条舆情”）：
- HEALTHY        正常采集
- WARNING        轻度风险（偶发 429/访问频繁但仍取到内容）：降低频率
- COOLDOWN       熔断冷却（300012 / IP 风险 / 安全限制 / 连续频繁）：延长冷却，停止危险请求
- PAUSED         主动暂停（连续失败达阈值，由限速器/外部指令决定）
- AUTH_REQUIRED  登录态失效（401/403/未登录/登录跳转）：转 Auth Recovery，不跳页
- NEED_VERIFY    需要合法人机验证（验证码/安全验证/challenge）：暂停等待人工，绝不绕过
- NETWORK_ERROR  网络层错误（超时/连接重置）：可退避重试，不计入平台风控

设计原则：只识别、不绕过；任何状态都必须可被上层显式区分并落库/上健康中心。
"""


class CollectState:
    HEALTHY = 'healthy'
    WARNING = 'warning'
    COOLDOWN = 'cooldown'
    PAUSED = 'paused'
    AUTH_REQUIRED = 'auth_required'
    NEED_VERIFY = 'need_verify'
    NETWORK_ERROR = 'network_error'

    ALL = (HEALTHY, WARNING, COOLDOWN, PAUSED, AUTH_REQUIRED, NEED_VERIFY, NETWORK_ERROR)

    # 哪些状态必须立即停止继续发请求（熔断/等待人工），不得伪装成正常空结果
    STOP_REQUEST = (COOLDOWN, PAUSED, AUTH_REQUIRED, NEED_VERIFY)

    # 风险类状态（用于健康中心红点/黄点）
    RISK = (WARNING, COOLDOWN, PAUSED, AUTH_REQUIRED, NEED_VERIFY, NETWORK_ERROR)

    @classmethod
    def label(cls, state):
        return {
            cls.HEALTHY: '正常',
            cls.WARNING: '轻度风险·降频',
            cls.COOLDOWN: '熔断冷却',
            cls.PAUSED: '已暂停',
            cls.AUTH_REQUIRED: '登录失效',
            cls.NEED_VERIFY: '需要人机验证',
            cls.NETWORK_ERROR: '网络异常',
        }.get(state, state)

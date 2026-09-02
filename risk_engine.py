"""风险/日报兼容层 v5.6.3。

保留历史 `_subject_sql_and_values()` 命名，并把报告层统一转发到 daily_report/report_engine。

【职责边界声明（P1-4，2026-09-02 据运行时事实校正）】本模块为历史命名兼容层，仅做入口转发，不承担独立风险计算。
- 现役「采集风险状态/熔断」权威：collector_guard/guard.py 的 CollectorGuard = state.CollectState 七态
  + analyzer.ResponseAnalyzer 响应分类 + rate_limiter.AdaptiveRateLimiter（连续失败阈值→动态降频→冷却/熔断→恢复），
  采集主链 collector.py 默认启用（TAIKOO_COLLECTOR_GUARD=1）。
- collector_guard/risk_engine.py 的 RiskEngine（0-100 连续分 + 五档 + 硬信号，tests/test_risk_engine.py 7 用例覆盖）
  是【已实现、已测、当前未接管】的增强评分器：不被 CollectorGuard 实例化，不影响现役七态熔断；
  未来若需连续分，须先旁路验证再接入，不得直接替换现役状态机。
- 报告与风险口径：daily_report.py / report_engine.py（DB 统计口径强写回，防 AI 误写）。
本模块 build_daily_report / _subject_sql_and_values 仅保持历史调用点兼容，不得作为新业务口径依据。
"""
from subject_rules import subject_sql_and_values, SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS
import daily_report


def _subject_sql_and_values(alias=''):
    return subject_sql_and_values(alias)


def build_daily_report(date_str=None):
    return daily_report.generate_daily_digest(date_str)

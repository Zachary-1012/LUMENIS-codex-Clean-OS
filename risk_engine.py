"""风险/日报兼容层 v5.6.3。

保留历史 `_subject_sql_and_values()` 命名，并把报告层统一转发到 daily_report/report_engine。

【职责边界声明（P1-4）】本模块为历史命名兼容层，仅做入口转发，不承担独立风险计算。
- 采集风险计算权威入口：collector_guard/risk_engine.py（RiskEngine，0-100 连续分 + 五档 + 硬信号熔断）；
- 报告与风险口径：daily_report.py / report_engine.py（DB 统计口径强写回，防 AI 误写）。
本模块 build_daily_report / _subject_sql_and_values 仅保持历史调用点兼容，不得作为新业务口径依据。
"""
from subject_rules import subject_sql_and_values, SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS
import daily_report


def _subject_sql_and_values(alias=''):
    return subject_sql_and_values(alias)


def build_daily_report(date_str=None):
    return daily_report.generate_daily_digest(date_str)

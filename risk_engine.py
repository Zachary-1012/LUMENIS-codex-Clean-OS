"""风险/日报兼容层 v5.6.3。

保留历史 `_subject_sql_and_values()` 命名，并把报告层统一转发到 daily_report/report_engine。
"""
from subject_rules import subject_sql_and_values, SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS
import daily_report


def _subject_sql_and_values(alias=''):
    return subject_sql_and_values(alias)


def build_daily_report(date_str=None):
    return daily_report.generate_daily_digest(date_str)

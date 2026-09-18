"""
报告导出脚本
导出日报、周报、月报、年报
版本: v5.8.0
"""

import sys
import os
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def export_report(report_type='daily', date=None, format='word'):
    """导出报告"""
    print("=" * 60)
    print("广州太古汇舆情监测系统 - 报告导出")
    print(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"报告类型: {report_type}")
    print(f"报告日期: {date or '默认'}")
    print(f"导出格式: {format}")
    print("=" * 60)
    print()

    # 确定报告周期
    if report_type == 'daily':
        if date:
            period_start = date
            period_end = date
        else:
            period_start = datetime.now().strftime('%Y-%m-%d')
            period_end = period_start
        report_title = f"广州太古汇舆情日报 - {period_start}"
    elif report_type == 'weekly':
        if date:
            # 解析为周的开始日期
            d = datetime.strptime(date, '%Y-%m-%d')
            period_start = (d - timedelta(days=d.weekday())).strftime('%Y-%m-%d')
            period_end = (d + timedelta(days=6-d.weekday())).strftime('%Y-%m-%d')
        else:
            now = datetime.now()
            period_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
            period_end = (now + timedelta(days=6-now.weekday())).strftime('%Y-%m-%d')
        report_title = f"广州太古汇舆情周报 - {period_start} 至 {period_end}"
    elif report_type == 'monthly':
        if date:
            year, month = date.split('-')[:2]
            period_start = f"{year}-{month}-01"
            if month == '12':
                period_end = f"{int(year)+1}-01-01"
            else:
                period_end = f"{year}-{int(month)+1:02d}-01"
        else:
            now = datetime.now()
            period_start = now.strftime('%Y-%m-01')
            if now.month == 12:
                period_end = f"{now.year+1}-01-01"
            else:
                period_end = f"{now.year}-{now.month+1:02d}-01"
        report_title = f"广州太古汇舆情月报 - {period_start[:7]}"
    elif report_type == 'yearly':
        if date:
            year = date[:4]
        else:
            year = str(datetime.now().year)
        period_start = f"{year}-01-01"
        period_end = f"{int(year)+1}-01-01"
        report_title = f"广州太古汇舆情年报 - {year}"
    else:
        print(f"❌ 不支持的报告类型: {report_type}")
        return False

    print(f"报告周期: {period_start} 至 {period_end}")
    print()

    # 唯一导出 Owner：lumenis.shared.reporting.export_engine
    format_key = {
        'word': 'docx',
        'docx': 'docx',
        'excel': 'xlsx',
        'xlsx': 'xlsx',
        'csv': 'csv',
    }.get((format or '').lower())
    if not format_key:
        print(f"❌ 不支持的格式: {format}")
        return False

    try:
        from lumenis.shared.reporting.export_engine import export_report as canonical_export_report
        result = canonical_export_report(
            report_type,
            period_start,
            period_end,
            (format_key,),
        )
        output_path = (result.get('files') or {}).get(format_key)
        verification = (result.get('artifact_verified') or {}).get(format_key) or {}
        if not output_path:
            print("❌ 导出失败：未生成 artifact 路径")
            return False
        if verification.get('valid') is not True:
            print(f"❌ 导出失败：artifact 未通过真实性校验: {verification}")
            return False
        print(f"✅ 报告导出成功: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Shared Reporting 导出失败: {e}")
        return False

if __name__ == '__main__':
    report_type = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    date = sys.argv[2] if len(sys.argv) > 2 else None
    format = sys.argv[3] if len(sys.argv) > 3 else 'word'

    success = export_report(report_type, date, format)
    sys.exit(0 if success else 1)
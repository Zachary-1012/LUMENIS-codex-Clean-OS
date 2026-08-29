@echo off
chcp 65001 >nul
title 广州太古汇舆情监测系统 v5.3.2 - 生成日报
echo ============================================
echo   广州太古汇舆情监测系统 v5.3.2
echo   生成智能日报
echo ============================================
echo.

cd /d "%~dp0\.."

echo [1/3] 运行AI过滤层...
python -c "import ai_filter; print(ai_filter.run_filter_batch(limit=500))"
if errorlevel 1 (
    echo [警告] AI过滤层运行失败，继续生成日报...
)

echo.
echo [2/3] 生成智能日报...
python -c "import daily_report, json; d = daily_report.generate_daily_digest(); print(json.dumps({'date': d['digest_date'], 'effective': d['effective_count'], 'risk_index': d['risk_index']}, ensure_ascii=False, indent=2))"
if errorlevel 1 (
    echo [错误] 日报生成失败
    pause
    exit /b 1
)

echo.
echo [3/3] 生成传统报告（日/周/月/年）...
python -c "import app; app._generate_all_reports(); print('报告生成完成')"

echo.
echo ============================================
echo   日报生成完成！
echo   可在系统"报告中心"查看
echo ============================================
echo.
pause

# -*- coding: utf-8 -*-
"""批量修复报告和AI模块的代码问题。"""
import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. report_engine.py: 添加 logger, started_at/finished_at/status, 修复裸 except
# ============================================================
print("=== Fixing report_engine.py ===")
path = os.path.join(BASE, "report_engine.py")
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 添加 logger（如果还没有）
if "logger = logging.getLogger" not in src:
    src = src.replace(
        "import report_artifact as ra\n\nREPORT_TYPES",
        "import report_artifact as ra\n\nlogger = logging.getLogger(__name__)\n\nREPORT_TYPES"
    )

# 在 generate_report 开头添加 started_at
if "started_at = datetime.now().isoformat()" not in src:
    src = src.replace(
        "def generate_report(report_type: str, start: str | None = None, end: str | None = None):\n    if report_type not in REPORT_TYPES:\n        raise ValueError(f'无效报告类型: {report_type}')\n    if not start or not end:\n        start, end = period_for(report_type)",
        "def generate_report(report_type: str, start: str | None = None, end: str | None = None):\n    started_at = datetime.now().isoformat()\n    if report_type not in REPORT_TYPES:\n        raise ValueError(f'无效报告类型: {report_type}')\n    if not start or not end:\n        start, end = period_for(report_type)"
    )

# 修复 ai_filter 裸 except
src = src.replace(
    "    try:\n        ai_filter.run_filter_batch(limit=500)\n    except Exception:\n        # 无 AI / 过滤器异常不能阻塞规则版报告生成。\n        pass",
    "    try:\n        ai_filter.run_filter_batch(limit=500)\n    except Exception as _e:\n        logger.warning('ai_filter.run_filter_batch failed (non-blocking): %s', _e)"
)

# 修复 marketing_calendar 裸 except
src = src.replace(
    "    except Exception:\n        report['marketing_nodes'] = {\"nodes\": [], \"themes\": [], \"tonality_advice\": \"\",",
    "    except Exception as _e:\n        logger.warning('marketing_calendar import failed (non-blocking): %s', _e)\n        report['marketing_nodes'] = {\"nodes\": [], \"themes\": [], \"tonality_advice\": \"\","
)

# 修复 emv 裸 except
src = src.replace(
    "    except Exception:\n        report['emv'] = {\"status\": \"NOT_AVAILABLE\"",
    "    except Exception as _e:\n        logger.warning('emv aggregate failed (non-blocking): %s', _e)\n        report['emv'] = {\"status\": \"NOT_AVAILABLE\""
)

# 在 return 前添加 finished_at/status
if "finished_at" not in src:
    src = src.replace(
    "    digest = None\n    if report_type == 'daily':\n        digest = daily_report.generate_daily_digest(end)\n    return report, digest",
    "    digest = None\n    if report_type == 'daily':\n        digest = daily_report.generate_daily_digest(end)\n    report['started_at'] = started_at\n    report['finished_at'] = datetime.now().isoformat()\n    report['status'] = 'success'\n    report['error'] = None\n    return report, digest"
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  report_engine.py fixed")

# ============================================================
# 2. report_api.py: 修复裸 except
# ============================================================
print("=== Fixing report_api.py ===")
path = os.path.join(BASE, "report_api.py")
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

src = src.replace(
    "        except: events=0",
    "        except Exception as _e:\n            import logging as _log; _log.getLogger(__name__).warning('events count query failed: %s', _e); events=0"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  report_api.py fixed")

# ============================================================
# 3. ai_governance.py: 修复 _load 裸 except
# ============================================================
print("=== Fixing ai_governance.py ===")
path = os.path.join(BASE, "ai_governance.py")
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

src = src.replace(
    "            except Exception:\n                pass\n        return {\"daily\": {}",
    "            except Exception as _e:\n                logging.getLogger(__name__).warning('ai_governance stats load failed: %s', _e)\n        return {\"daily\": {}"
)

# 添加 import logging 如果没有
if "import logging" not in src:
    src = src.replace("import os\nimport re", "import logging\nimport os\nimport re")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  ai_governance.py fixed")

# ============================================================
# 4. ark_llm.py: 修复裸 except
# ============================================================
print("=== Fixing ark_llm.py ===")
path = os.path.join(BASE, "ark_llm.py")
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 修复 json parse 裸 except
src = src.replace(
    "                except:\n                    pass\n            return {\"error\": \"json_parse_failed\"",
    "                except Exception as _e:\n                    logger.warning('ark_llm json re-parse failed: %s', _e)\n            return {\"error\": \"json_parse_failed\""
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  ark_llm.py fixed")

print("\nAll fixes applied.")

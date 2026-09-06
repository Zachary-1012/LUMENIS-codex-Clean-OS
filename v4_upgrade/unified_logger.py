"""
统一日志模块 - yyds-logger 渐进式替换方案
==========================================
设计目标：
1. 与现有 logging 模块接口兼容（info/warning/error/debug/exception）
2. 支持渐进式替换：现有代码无需改动，新代码可直接用
3. 多实例物理隔离：采集/分析/审计/系统 四个logger实例
4. JSON结构化输出（生产环境）+ 控制台彩色（开发环境）
5. request_id 全链路追踪注入
6. 按sink独立级别：控制台WARNING，文件DEBUG

接入方式（不改动现有代码）：
    # 在 app.py 顶部添加一行
    from unified_logger import patch_logging
    patch_logging()  # 之后所有 logging.getLogger 自动走yyds-logger

    # 新代码直接用
    from unified_logger import get_logger
    logger = get_logger("collector", request_id="task_001")
    logger.info("采集任务开始")

依赖：pip install yyds-logger win32_setctime (Windows)
"""
import os
import sys
import logging
from contextlib import contextmanager

try:
    from yyds_logger import YydsLogger
    _YYDS_AVAILABLE = True
except ImportError:
    _YYDS_AVAILABLE = False

# 环境判断
ENV = os.environ.get("APP_ENV", "dev")  # dev / prod
IS_PROD = ENV == "prod"
LOG_DIR = os.environ.get("LOG_DIR", "logs")

# 实例缓存
_loggers = {}
_request_id_var = None

if _YYDS_AVAILABLE:
    try:
        from yyds_logger import YydsLogger as _Yyds
        # Do not create and close a probe logger at import time.  Some logger
        # backends attach a handler to the active stdout/stderr stream; closing
        # that handler closes pytest's capture stream and aborts the whole test
        # run.  A class-level context variable is safe to inspect, while an
        # instance can still expose one when a real logger is created.
        _request_id_var = getattr(_Yyds, "request_id_var", None)
    except Exception:
        pass


class UnifiedLogger:
    """统一日志接口，兼容logging，底层用yyds-logger"""

    def __init__(self, name, log_dir=None, request_id=None):
        global _request_id_var
        self.name = name
        self.log_dir = log_dir or LOG_DIR
        self._request_id = request_id
        self._yyds = None
        self._std_logger = None

        if _YYDS_AVAILABLE:
            try:
                self._yyds = YydsLogger(
                    file_name=name,
                    log_dir=self.log_dir,
                    serialize=IS_PROD,  # 生产环境JSON结构化
                    console_level="WARNING" if IS_PROD else "DEBUG",
                    file_level="DEBUG",
                    language="zh",
                )
                if _request_id_var is None:
                    _request_id_var = getattr(self._yyds, "request_id_var", None)
                if request_id and _request_id_var:
                    _request_id_var.set(request_id)
            except Exception as e:
                # yyds初始化失败，回退标准logging
                self._std_logger = logging.getLogger(name)
                self._std_logger.warning(f"yyds-logger初始化失败，回退标准logging: {e}")
        else:
            self._std_logger = logging.getLogger(name)

    def _log(self, level, message, **kwargs):
        if self._yyds:
            # yyds-logger的bind方法用于结构化字段
            if kwargs:
                self._yyds.bind(**kwargs).log(level, message)
            else:
                self._yyds.log(level, message)
        elif self._std_logger:
            self._std_logger.log(level, message, extra=kwargs)

    def info(self, message, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def debug(self, message, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def exception(self, message, **kwargs):
        if self._yyds:
            self._yyds.exception(message)
        elif self._std_logger:
            self._std_logger.exception(message, **kwargs)

    def critical(self, message, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def set_request_id(self, request_id):
        """设置当前链路的request_id"""
        self._request_id = request_id
        if _request_id_var:
            _request_id_var.set(request_id)

    def flush(self):
        if self._yyds:
            self._yyds.flush()

    def close(self):
        if self._yyds:
            try:
                self._yyds.close()
            except Exception:
                pass


def get_logger(name="app", request_id=None):
    """获取logger实例，同名复用"""
    key = f"{name}:{request_id or 'default'}"
    if key not in _loggers:
        _loggers[key] = UnifiedLogger(name, request_id=request_id)
    return _loggers[key]


@contextmanager
def request_context(request_id):
    """request_id上下文管理器，with块内所有日志自动带request_id"""
    token = None
    if _request_id_var:
        token = _request_id_var.set(request_id)
    try:
        yield
    finally:
        if token and _request_id_var:
            _request_id_var.reset(token)


def patch_logging():
    """
    补丁模式：拦截标准logging，让现有代码自动走yyds-logger
    不改动任何现有import logging的代码
    """
    if not _YYDS_AVAILABLE:
        print("[unified_logger] yyds-logger未安装，使用标准logging", file=sys.stderr)
        return

    original_getLogger = logging.getLogger

    def patched_getLogger(name=None):
        if name and name in ("collector", "analyzer", "audit", "risk", "v4_upgrade"):
            return get_logger(name)
        return original_getLogger(name)

    logging.getLogger = patched_getLogger
    print(f"[unified_logger] 已启用yyds-logger (env={ENV}, dir={LOG_DIR})", file=sys.stderr)


# 预定义四个核心实例（多实例物理隔离）
collector_logger = get_logger("collector")      # 采集模块
analyzer_logger = get_logger("analyzer")        # 分析模块
audit_logger = get_logger("audit")              # 审计日志
system_logger = get_logger("system")            # 系统运行


if __name__ == "__main__":
    # 自测
    print("=== yyds-logger 统一模块自测 ===")
    print(f"yyds可用: {_YYDS_AVAILABLE}")
    print(f"环境: {ENV}")

    log = get_logger("selftest", request_id="test-001")
    log.info("测试info")
    log.warning("测试warning")
    log.error("测试error")
    log.debug("测试debug")

    with request_context("ctx-002"):
        log.info("在request_context内")

    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("捕获异常")

    log.flush()
    print("自测完成，日志文件在 logs/ 目录")

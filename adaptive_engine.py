"""
自动调节引擎 v1.0
5层闭环架构 - 第一层：自动调节
功能：
根据7个指标动态调整5个参数

指标：
  ├── 最近采集成功率
  ├── 请求失败率
  ├── 页面响应时间
  ├── 登录态有效性
  ├── 验证码/风控迹象
  ├── 当前任务耗时
  └── 上一次采集时间

策略调整：
  ├── 请求间隔（正常2s → 风控10s → 恢复2s）
  ├── 重试次数（正常3次 → 失败1次 → 恢复3次）
  ├── 并发数（正常2 → 风控1 → 恢复2）
  ├── 任务暂停时间（正常0 → 风控30min → 恢复0）
  └── 下一次采集时间（正常2h → 失败4h → 恢复2h）

不需要登录，本地运行即可
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from enum import Enum

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class RiskLevel(Enum):
    """风控等级"""
    NONE = 0      # 正常
    LOW = 1       # 低风险
    MEDIUM = 2    # 中风险
    HIGH = 3      # 高风险
    CRITICAL = 4  # 严重风险（暂停采集）


class StrategyLevel(Enum):
    """策略等级"""
    NORMAL = "normal"           # 正常策略
    CAUTIOUS = "cautious"       # 谨慎策略
    CONSERVATIVE = "conservative"  # 保守策略
    SUSPENDED = "suspended"     # 暂停策略


class AdaptiveEngine:
    """自动调节引擎"""

    def __init__(self):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.status_file = os.path.join(self.root_dir, 'data', 'adaptive_status.json')
        self.history_file = os.path.join(self.root_dir, 'data', 'adaptive_history.json')

        # 默认策略参数
        self.default_strategy = {
            'request_delay': 55,          # 请求间隔（秒）- 用户指定55s
            'max_retries': 3,             # 最大重试次数
            'max_concurrent': 2,          # 最大并发数
            'pause_minutes': 0,           # 任务暂停时间（分钟）
            'next_collect_hours': 2,      # 下一次采集间隔（小时）
            'max_scroll': 6,              # 最大滚动次数
            'max_details': 20             # 最大详情页抓取数
        }

        # 各等级策略参数
        self.strategy_params = {
            StrategyLevel.NORMAL.value: {
                'request_delay': 55,
                'max_retries': 3,
                'max_concurrent': 2,
                'pause_minutes': 0,
                'next_collect_hours': 2,
                'max_scroll': 6,
                'max_details': 20
            },
            StrategyLevel.CAUTIOUS.value: {
                'request_delay': 5,
                'max_retries': 2,
                'max_concurrent': 1,
                'pause_minutes': 10,
                'next_collect_hours': 3,
                'max_scroll': 4,
                'max_details': 10
            },
            StrategyLevel.CONSERVATIVE.value: {
                'request_delay': 10,
                'max_retries': 1,
                'max_concurrent': 1,
                'pause_minutes': 30,
                'next_collect_hours': 4,
                'max_scroll': 2,
                'max_details': 5
            },
            StrategyLevel.SUSPENDED.value: {
                'request_delay': 30,
                'max_retries': 0,
                'max_concurrent': 0,
                'pause_minutes': 120,
                'next_collect_hours': 8,
                'max_scroll': 0,
                'max_details': 0
            }
        }

        # 加载状态
        self.status = self._load_status()

    def _load_status(self):
        """加载状态"""
        default_status = {
            'current_strategy': StrategyLevel.NORMAL.value,
            'risk_level': RiskLevel.NONE.value,
            'current_params': self.default_strategy.copy(),
            'metrics': {
                'recent_success_rate': 100,
                'request_failure_rate': 0,
                'avg_response_time': 2.0,
                'login_valid': True,
                'risk_detected': False,
                'last_task_duration': 0,
                'last_collect_time': None
            },
            'history': [],
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                # 合并默认值，确保新增的字段（如request_delay=55）生效
                merged = default_status.copy()
                merged.update(loaded)
                # 合并current_params，用新的默认值更新旧的参数
                if 'current_params' in loaded:
                    merged_params = self.default_strategy.copy()
                    merged_params.update(loaded['current_params'])
                    merged['current_params'] = merged_params
                # 合并metrics
                if 'metrics' in loaded:
                    merged_metrics = default_status['metrics'].copy()
                    merged_metrics.update(loaded['metrics'])
                    merged['metrics'] = merged_metrics
                return merged
        except Exception:
            pass

        return default_status

    def _save_status(self):
        """保存状态"""
        try:
            self.status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AdaptiveEngine] 保存状态失败: {e}", flush=True)

    def _record_history(self, event, details=None):
        """记录历史"""
        history_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event': event,
            'details': details or {},
            'strategy_before': self.status['current_strategy'],
            'risk_level_before': self.status['risk_level']
        }

        self.status['history'].append(history_entry)
        # 只保留最近100条
        self.status['history'] = self.status['history'][-100:]

        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.status['history'], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def update_metrics(self, success_rate=None, failure_rate=None, response_time=None,
                       login_valid=None, risk_detected=None, task_duration=None):
        """更新指标"""
        metrics = self.status['metrics']

        if success_rate is not None:
            metrics['recent_success_rate'] = max(0, min(100, success_rate))
        if failure_rate is not None:
            metrics['request_failure_rate'] = max(0, min(100, failure_rate))
        if response_time is not None:
            metrics['avg_response_time'] = max(0, response_time)
        if login_valid is not None:
            metrics['login_valid'] = login_valid
        if risk_detected is not None:
            metrics['risk_detected'] = risk_detected
        if task_duration is not None:
            metrics['last_task_duration'] = task_duration
            metrics['last_collect_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 根据指标重新评估风险等级和策略
        self._evaluate_risk_and_strategy()
        self._save_status()

    def _evaluate_risk_and_strategy(self):
        """根据指标评估风险等级和策略"""
        metrics = self.status['metrics']
        old_risk = self.status['risk_level']
        old_strategy = self.status['current_strategy']

        # 计算风险分数
        risk_score = 0

        # 成功率低于90%增加风险
        if metrics['recent_success_rate'] < 50:
            risk_score += 3
        elif metrics['recent_success_rate'] < 70:
            risk_score += 2
        elif metrics['recent_success_rate'] < 90:
            risk_score += 1

        # 失败率高于20%增加风险
        if metrics['request_failure_rate'] > 50:
            risk_score += 3
        elif metrics['request_failure_rate'] > 30:
            risk_score += 2
        elif metrics['request_failure_rate'] > 20:
            risk_score += 1

        # 响应时间超过5秒增加风险
        if metrics['avg_response_time'] > 10:
            risk_score += 2
        elif metrics['avg_response_time'] > 5:
            risk_score += 1

        # 登录失效直接高风险
        if not metrics['login_valid']:
            risk_score += 4

        # 检测到风控直接高风险
        if metrics['risk_detected']:
            risk_score += 4

        # 确定风险等级
        if risk_score >= 8:
            new_risk = RiskLevel.CRITICAL.value
        elif risk_score >= 5:
            new_risk = RiskLevel.HIGH.value
        elif risk_score >= 3:
            new_risk = RiskLevel.MEDIUM.value
        elif risk_score >= 1:
            new_risk = RiskLevel.LOW.value
        else:
            new_risk = RiskLevel.NONE.value

        # 确定策略等级
        if new_risk == RiskLevel.CRITICAL.value:
            new_strategy = StrategyLevel.SUSPENDED.value
        elif new_risk == RiskLevel.HIGH.value:
            new_strategy = StrategyLevel.CONSERVATIVE.value
        elif new_risk == RiskLevel.MEDIUM.value:
            new_strategy = StrategyLevel.CAUTIOUS.value
        else:
            new_strategy = StrategyLevel.NORMAL.value

        # 更新状态
        self.status['risk_level'] = new_risk
        self.status['current_strategy'] = new_strategy
        self.status['current_params'] = self.strategy_params[new_strategy].copy()

        # 如果策略变化，记录历史
        if new_risk != old_risk or new_strategy != old_strategy:
            self._record_history('strategy_change', {
                'old_risk': old_risk,
                'new_risk': new_risk,
                'old_strategy': old_strategy,
                'new_strategy': new_strategy,
                'risk_score': risk_score,
                'metrics': metrics.copy()
            })
            print(f"[AdaptiveEngine] 策略变化: {old_strategy}({old_risk}) -> {new_strategy}({new_risk})", flush=True)

    def get_current_params(self):
        """获取当前策略参数"""
        return self.status['current_params'].copy()

    def get_current_strategy(self):
        """获取当前策略等级"""
        return self.status['current_strategy']

    def get_risk_level(self):
        """获取当前风险等级"""
        return self.status['risk_level']

    def get_metrics(self):
        """获取当前指标"""
        return self.status['metrics'].copy()

    def get_status(self):
        """获取完整状态"""
        return self.status.copy()

    def can_collect_now(self):
        """判断现在是否可以采集"""
        params = self.get_current_params()
        metrics = self.get_metrics()

        # 如果暂停策略，不允许采集
        if self.status['current_strategy'] == StrategyLevel.SUSPENDED.value:
            return False, '当前为暂停策略，不允许采集'

        # 如果有暂停时间，检查是否在暂停期
        if params['pause_minutes'] > 0 and metrics['last_collect_time']:
            try:
                last_time = datetime.strptime(metrics['last_collect_time'], '%Y-%m-%d %H:%M:%S')
                if datetime.now() - last_time < timedelta(minutes=params['pause_minutes']):
                    remaining = params['pause_minutes'] - (datetime.now() - last_time).total_seconds() / 60
                    return False, f'暂停期中，还需等待 {remaining:.1f} 分钟'
            except Exception:
                pass

        # 如果登录失效，不允许采集
        if not metrics['login_valid']:
            return False, '登录态失效，不允许采集'

        return True, '可以采集'

    def report_collection_result(self, success, notes_count=0, duration=0, error=None):
        """报告采集结果，用于动态调整策略"""
        # 更新成功率（滑动窗口，最近10次）
        if not hasattr(self, '_recent_results'):
            self._recent_results = []

        self._recent_results.append(1 if success else 0)
        if len(self._recent_results) > 10:
            self._recent_results = self._recent_results[-10:]

        success_rate = (sum(self._recent_results) / len(self._recent_results)) * 100
        failure_rate = 100 - success_rate

        # 检测风控迹象
        risk_detected = False
        if error:
            error_lower = str(error).lower()
            risk_keywords = ['验证码', 'captcha', '风控', 'risk', '频繁', 'frequency', '限制', 'limit', '429', '403']
            if any(kw in error_lower for kw in risk_keywords):
                risk_detected = True

        # 更新指标
        self.update_metrics(
            success_rate=success_rate,
            failure_rate=failure_rate,
            response_time=duration / max(notes_count, 1) if notes_count > 0 else duration,
            risk_detected=risk_detected,
            task_duration=duration
        )

        return self.get_current_params()

    def reset_to_normal(self):
        """重置为正常策略（人工确认后使用）"""
        self.status['current_strategy'] = StrategyLevel.NORMAL.value
        self.status['risk_level'] = RiskLevel.NONE.value
        self.status['current_params'] = self.default_strategy.copy()
        self.status['metrics']['risk_detected'] = False
        self._recent_results = []
        self._record_history('manual_reset', {'reason': '人工重置为正常策略'})
        self._save_status()
        print("[AdaptiveEngine] 已人工重置为正常策略", flush=True)


# 全局实例
adaptive_engine = AdaptiveEngine()

print("[AdaptiveEngine] 自动调节引擎已加载", flush=True)
print(f"[AdaptiveEngine] 当前策略: {adaptive_engine.get_current_strategy()}, 风险等级: {adaptive_engine.get_risk_level()}", flush=True)

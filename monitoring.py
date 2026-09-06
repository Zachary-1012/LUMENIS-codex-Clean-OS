"""
广州太古汇舆情监测系统 - 监控告警模块
系统运行状态监控、健康检查、告警通知

使用方法：
    from monitoring import SystemMonitor
    
    monitor = SystemMonitor()
    health = monitor.check_health()
    alerts = monitor.check_alerts()
"""

import os
import logging
import sys
import json
import time
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'monitor.db')
LOG_DIR = os.path.join(BASE_DIR, 'logs')


logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class AlertType(Enum):
    """告警类型"""
    SYSTEM = 'system'           # 系统运行
    COLLECTION = 'collection'   # 采集异常
    DATABASE = 'database'       # 数据库异常
    AI = 'ai'                   # AI分析异常
    REPORT = 'report'           # 报告生成异常
    PUBLIC_OPINION = 'public_opinion'  # 舆情风险
    NETWORK = 'network'         # 网络异常


@dataclass
class Alert:
    """告警对象"""
    id: str
    level: AlertLevel
    type: AlertType
    title: str
    message: str
    created_at: str
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'level': self.level.value,
            'type': self.type.value,
            'title': self.title,
            'message': self.message,
            'created_at': self.created_at,
            'acknowledged': self.acknowledged,
            'acknowledged_at': self.acknowledged_at,
            'metadata': self.metadata or {}
        }


@dataclass
class HealthStatus:
    """健康状态"""
    status: str  # healthy/degraded/unhealthy
    checks: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'checks': self.checks,
            'timestamp': self.timestamp
        }


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化监控器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path or DB_PATH
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._monitoring = False
        self._monitor_thread = None
        
        # 确保日志目录存在
        os.makedirs(LOG_DIR, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def check_database(self) -> Dict[str, Any]:
        """检查数据库状态"""
        result = {
            'name': 'database',
            'status': 'unknown',
            'message': '',
            'details': {}
        }
        
        try:
            if not os.path.exists(self.db_path):
                result['status'] = 'error'
                result['message'] = '数据库文件不存在'
                return result
            
            conn = self.get_connection()
            
            # 检查连接
            cursor = conn.execute("SELECT 1")
            cursor.fetchone()
            
            # 统计表数量
            cursor = conn.execute("SELECT COUNT(*) as count FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()['count']
            
            # 统计笔记数量
            try:
                cursor = conn.execute("SELECT COUNT(*) as count FROM notes")
                note_count = cursor.fetchone()['count']
            except:
                note_count = 0
            
            # 数据库大小
            db_size = os.path.getsize(self.db_path) / 1024 / 1024
            
            conn.close()
            
            result['status'] = 'healthy'
            result['message'] = f'数据库正常，{table_count}个表，{note_count}条笔记'
            result['details'] = {
                'table_count': table_count,
                'note_count': note_count,
                'size_mb': round(db_size, 2)
            }
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'数据库检查失败: {str(e)}'
        
        return result
    
    def check_collection(self) -> Dict[str, Any]:
        """检查采集状态"""
        result = {
            'name': 'collection',
            'status': 'unknown',
            'message': '',
            'details': {}
        }
        
        try:
            conn = self.get_connection()
            
            # 最近采集记录
            try:
                cursor = conn.execute(
                    "SELECT * FROM collection_logs ORDER BY id DESC LIMIT 1"
                )
                last_log = cursor.fetchone()
                
                if last_log:
                    result['details']['last_collection'] = dict(last_log)
                    
                    # 检查是否超过24小时未采集
                    if 'created_at' in last_log.keys():
                        last_time = datetime.fromisoformat(last_log['created_at'].replace('Z', '+00:00').replace('+00:00', ''))
                        hours_since = (datetime.now() - last_time).total_seconds() / 3600
                        
                        if hours_since > 24:
                            result['status'] = 'warning'
                            result['message'] = f'已{hours_since:.1f}小时未采集'
                        else:
                            result['status'] = 'healthy'
                            result['message'] = f'采集正常，最近一次{hours_since:.1f}小时前'
                    else:
                        result['status'] = 'healthy'
                        result['message'] = '有采集记录'
                else:
                    result['status'] = 'warning'
                    result['message'] = '无采集记录'
            except Exception as e:
                result['status'] = 'warning'
                result['message'] = f'采集日志查询失败: {str(e)}'
            
            conn.close()
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'采集检查失败: {str(e)}'
        
        return result
    
    def check_ai_analysis(self) -> Dict[str, Any]:
        """检查AI分析状态"""
        result = {
            'name': 'ai_analysis',
            'status': 'unknown',
            'message': '',
            'details': {}
        }
        
        try:
            conn = self.get_connection()
            
            # AI过滤日志统计
            try:
                cursor = conn.execute(
                    "SELECT filter_result, COUNT(*) as count FROM ai_filter_log GROUP BY filter_result"
                )
                ai_stats = {row['filter_result']: row['count'] for row in cursor.fetchall()}
                result['details']['ai_stats'] = ai_stats
                
                total = sum(ai_stats.values())
                if total > 0:
                    result['status'] = 'healthy'
                    result['message'] = f'AI分析正常，共{total}条记录'
                else:
                    result['status'] = 'warning'
                    result['message'] = '无AI分析记录'
            except Exception as e:
                result['status'] = 'warning'
                result['message'] = f'AI日志查询失败: {str(e)}'
            
            conn.close()
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'AI检查失败: {str(e)}'
        
        return result
    
    def check_reports(self) -> Dict[str, Any]:
        """检查报告生成状态"""
        result = {
            'name': 'reports',
            'status': 'unknown',
            'message': '',
            'details': {}
        }
        
        try:
            conn = self.get_connection()
            
            try:
                cursor = conn.execute(
                    "SELECT report_type, COUNT(*) as count FROM daily_reports GROUP BY report_type"
                )
                report_stats = {row['report_type']: row['count'] for row in cursor.fetchall()}
                result['details']['report_stats'] = report_stats
                
                total = sum(report_stats.values())
                if total > 0:
                    result['status'] = 'healthy'
                    result['message'] = f'报告正常，共{total}份报告'
                else:
                    result['status'] = 'warning'
                    result['message'] = '无报告记录'
            except Exception as e:
                result['status'] = 'warning'
                result['message'] = f'报告查询失败: {str(e)}'
            
            conn.close()
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'报告检查失败: {str(e)}'
        
        return result
    
    def check_public_opinion_risk(self) -> Dict[str, Any]:
        """检查舆情风险"""
        result = {
            'name': 'public_opinion',
            'status': 'unknown',
            'message': '',
            'details': {}
        }
        
        try:
            conn = self.get_connection()
            
            # 高风险笔记
            try:
                cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM notes WHERE risk_level = 'high' AND negative_confirmed != 2"
                )
                high_risk_count = cursor.fetchone()['count']
                
                # 今日负面笔记
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM notes WHERE sentiment = 'negative' AND DATE(publish_date) = ?",
                    (today,)
                )
                today_negative = cursor.fetchone()['count']
                
                result['details'] = {
                    'high_risk_count': high_risk_count,
                    'today_negative': today_negative
                }
                
                if high_risk_count > 10:
                    result['status'] = 'warning'
                    result['message'] = f'高风险笔记{high_risk_count}条，需关注'
                elif today_negative > 5:
                    result['status'] = 'warning'
                    result['message'] = f'今日负面笔记{today_negative}条'
                else:
                    result['status'] = 'healthy'
                    result['message'] = '舆情风险可控'
                    
            except Exception as e:
                result['status'] = 'warning'
                result['message'] = f'舆情查询失败: {str(e)}'
            
            conn.close()
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'舆情检查失败: {str(e)}'
        
        return result
    
    def check_health(self) -> HealthStatus:
        """
        综合健康检查
        
        Returns:
            健康状态对象
        """
        checks = {
            'database': self.check_database(),
            'collection': self.check_collection(),
            'ai_analysis': self.check_ai_analysis(),
            'reports': self.check_reports(),
            'public_opinion': self.check_public_opinion_risk(),
        }
        
        # 综合状态判断
        statuses = [c['status'] for c in checks.values()]
        
        if 'error' in statuses:
            overall_status = 'unhealthy'
        elif 'warning' in statuses:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        return HealthStatus(
            status=overall_status,
            checks=checks,
            timestamp=datetime.now().isoformat()
        )
    
    def add_alert(
        self,
        level: AlertLevel,
        alert_type: AlertType,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """
        添加告警
        
        Args:
            level: 告警级别
            alert_type: 告警类型
            title: 告警标题
            message: 告警消息
            metadata: 附加数据
        
        Returns:
            告警对象
        """
        alert = Alert(
            id=f'alert_{int(time.time() * 1000)}',
            level=level,
            type=alert_type,
            title=title,
            message=message,
            created_at=datetime.now().isoformat(),
            metadata=metadata
        )
        
        with self._lock:
            self.alerts.insert(0, alert)
            # 只保留最近100条
            if len(self.alerts) > 100:
                self.alerts = self.alerts[:100]
        
        # 触发回调
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except:
                pass
        
        return alert
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        alert_type: Optional[AlertType] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 50
    ) -> List[Alert]:
        """
        获取告警列表
        
        Args:
            level: 按级别过滤
            alert_type: 按类型过滤
            acknowledged: 按确认状态过滤
            limit: 返回数量
        
        Returns:
            告警列表
        """
        with self._lock:
            alerts = self.alerts.copy()
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        if alert_type:
            alerts = [a for a in alerts if a.type == alert_type]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        确认告警
        
        Args:
            alert_id: 告警ID
        
        Returns:
            是否成功
        """
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_at = datetime.now().isoformat()
                    return True
        return False
    
    def register_alert_callback(self, callback: Callable):
        """注册告警回调"""
        self.alert_callbacks.append(callback)
    
    def start_monitoring(self, interval: int = 60):
        """
        启动后台监控
        
        Args:
            interval: 检查间隔（秒）
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor_loop():
            while self._monitoring:
                try:
                    health = self.check_health()
                    
                    # 检查是否有需要告警的情况
                    for check_name, check in health.checks.items():
                        if check['status'] == 'error':
                            self.add_alert(
                                AlertLevel.ERROR,
                                AlertType.SYSTEM,
                                f'{check_name}异常',
                                check['message'],
                                check.get('details', {})
                            )
                        elif check['status'] == 'warning':
                            self.add_alert(
                                AlertLevel.WARNING,
                                AlertType.SYSTEM,
                                f'{check_name}警告',
                                check['message'],
                                check.get('details', {})
                            )
                    
                    # 写入健康日志
                    health_log = os.path.join(LOG_DIR, 'health.log')
                    with open(health_log, 'a', encoding='utf-8') as f:
                        f.write(f"{datetime.now().isoformat()} | {health.status} | {json.dumps(health.checks, ensure_ascii=False)}\n")
                    
                except Exception as e:
                    print(f"监控异常: {e}")
                
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        print(f"✅ 系统监控已启动，间隔{interval}秒")
    
    def stop_monitoring(self):
        """停止后台监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("✅ 系统监控已停止")
    
    def get_monitoring_report(self) -> Dict[str, Any]:
        """获取监控报告"""
        health = self.check_health()
        alerts = self.get_alerts(limit=20)
        
        return {
            'health': health.to_dict(),
            'alerts': [a.to_dict() for a in alerts],
            'alert_summary': {
                'total': len(alerts),
                'unacknowledged': len([a for a in alerts if not a.acknowledged]),
                'critical': len([a for a in alerts if a.level == AlertLevel.CRITICAL]),
                'error': len([a for a in alerts if a.level == AlertLevel.ERROR]),
                'warning': len([a for a in alerts if a.level == AlertLevel.WARNING]),
            },
            'generated_at': datetime.now().isoformat()
        }


# 全局监控器实例
_global_monitor: Optional[SystemMonitor] = None


def get_monitor() -> SystemMonitor:
    """获取全局监控器"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SystemMonitor()
    return _global_monitor


if __name__ == '__main__':
    # 测试监控模块
    print("=" * 60)
    print("🔍 系统监控测试")
    print("=" * 60)
    
    monitor = SystemMonitor()
    
    # 健康检查
    print("\n💚 健康检查:")
    health = monitor.check_health()
    print(f"  状态: {health.status}")
    for name, check in health.checks.items():
        print(f"  {name}: {check['status']} - {check['message']}")
    
    # 监控报告
    print("\n📊 监控报告:")
    report = monitor.get_monitoring_report()
    print(f"  告警总数: {report['alert_summary']['total']}")
    print(f"  未确认: {report['alert_summary']['unacknowledged']}")
    
    print("\n✅ 监控模块测试完成")

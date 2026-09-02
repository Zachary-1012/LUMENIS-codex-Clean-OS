"""
自动修复引擎 v1.0
5层闭环架构 - 第二层：自动修复
功能：
1. Health Check健康检查
2. 异常检测
3. 判断（可自动修/需人工介入）
4. 修复（重启/重试/重连）
5. 验证
6. 记录

可自动修复（6类）：
- 进程崩溃 → 重启进程 → 验证端口 → 记录
- 临时网络失败 → 重试3次 → 指数退避 → 记录
- 数据库连接断开 → 重连 → 验证查询 → 记录
- 单次任务超时 → 终止任务 → 重新执行 → 记录
- 推送失败 → 重试3次 → 切换备用渠道 → 记录
- 临时API错误 → 重试 → 降级处理 → 记录

需人工介入（6类）：
- 核心数据库结构改变 → 保存现场 → 告警 → 等待
- 主体过滤规则异常 → 保存现场 → 告警 → 等待
- 风险评分逻辑异常 → 保存现场 → 告警 → 等待
- 大量数据异常删除 → 立即停止 → 告警 → 等待
- 登录账号失效 → 保存Cookie状态 → 告警 → 等待
- 小红书新风控机制 → 暂停采集 → 告警 → 等待

不需要登录，本地运行即可
"""

import os
import sys
import time
import json
import socket
import sqlite3
import subprocess
import threading
from datetime import datetime
from enum import Enum

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class FixStatus(Enum):
    """修复状态"""
    PENDING = "pending"
    FIXING = "fixing"
    FIXED = "fixed"
    FAILED = "failed"
    NEED_MANUAL = "need_manual"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AutoRecoveryEngine:
    """自动修复引擎"""

    def __init__(self):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(self.root_dir, 'data', 'logs')
        os.makedirs(self.log_dir, exist_ok=True)

        self.recovery_log_file = os.path.join(self.log_dir, 'auto_recovery.log')
        self.alerts_file = os.path.join(self.root_dir, 'data', 'alerts.json')

        # 修复统计
        self.stats = {
            'total_checks': 0,
            'total_fixes': 0,
            'successful_fixes': 0,
            'failed_fixes': 0,
            'manual_interventions': 0,
            'last_check': None,
            'last_fix': None
        }

        # 最大重试次数
        self.max_retries = 3
        # 自动修复前是否备份
        self.backup_before_fix = True
        # 需人工介入的模块列表
        self.manual_intervention_modules = [
            'database_schema',
            'subject_filter_rules',
            'risk_scoring_logic',
            'bulk_data_deletion',
            'login_account',
            'xhs_anti_bot'
        ]

    def log(self, level, message, module=None, details=None):
        """记录日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        if module:
            log_entry += f" [模块: {module}]"
        if details:
            log_entry += f" [详情: {json.dumps(details, ensure_ascii=False)}]"

        print(log_entry, flush=True)

        try:
            with open(self.recovery_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"写入日志失败: {e}", flush=True)

    def add_alert(self, level, module, message, need_manual=False):
        """添加告警"""
        try:
            alerts = []
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    alerts = json.load(f)

            alert = {
                'id': int(time.time()),
                'level': level.value if isinstance(level, AlertLevel) else level,
                'module': module,
                'message': message,
                'need_manual': need_manual,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'active'
            }
            alerts.append(alert)

            # 只保留最近100条
            alerts = alerts[-100:]

            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(alerts, f, ensure_ascii=False, indent=2)

            return alert
        except Exception as e:
            self.log('error', f'添加告警失败: {e}', module='alerts')
            return None

    def check_port(self, host='127.0.0.1', port=8201, timeout=3):
        """检查端口是否可连接"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def check_process(self, process_name='python'):
        """检查进程是否运行"""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {process_name}.exe', '/FO', 'CSV', '/NH'],
                capture_output=True, text=True, timeout=5
            )
            return process_name in result.stdout.lower()
        except Exception:
            return False

    def check_database(self):
        """检查数据库连接"""
        try:
            db_path = os.path.join(self.root_dir, 'data', 'monitor.db')
            if not os.path.exists(db_path):
                return False, '数据库文件不存在'

            conn = sqlite3.connect(db_path, timeout=5)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM notes")
            count = c.fetchone()[0]
            conn.close()
            return True, f'数据库正常，笔记数: {count}'
        except Exception as e:
            return False, f'数据库连接失败: {str(e)}'

    def check_cdp(self):
        """检查CDP浏览器"""
        return self.check_port(port=9222)

    def backup_database(self):
        """备份数据库（自动修复前）"""
        if not self.backup_before_fix:
            return None

        try:
            db_path = os.path.join(self.root_dir, 'data', 'monitor.db')
            if not os.path.exists(db_path):
                return None

            backup_dir = os.path.join(self.root_dir, 'data', 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'before_recovery_{timestamp}.db')

            import shutil
            shutil.copy2(db_path, backup_path)

            self.log('info', f'数据库已备份: {backup_path}', module='backup')
            return backup_path
        except Exception as e:
            self.log('error', f'数据库备份失败: {e}', module='backup')
            return None

    def fix_process_crash(self, module='system'):
        """修复进程崩溃 - 重启进程"""
        self.log('info', f'检测到进程崩溃，尝试重启...', module=module)

        # 备份数据库
        self.backup_database()

        try:
            # 启动系统
            python_path = os.path.join(self.root_dir, '.venv', 'Scripts', 'python.exe')
            if not os.path.exists(python_path):
                python_path = 'python'

            subprocess.Popen(
                [python_path, 'app.py', '--host', '0.0.0.0', '--port', '8201'],
                cwd=self.root_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # 等待启动并验证
            for i in range(30):
                time.sleep(2)
                if self.check_port(port=8201):
                    self.log('info', f'进程重启成功，已等待 {i*2+2} 秒', module=module)
                    return True, '进程重启成功'

            return False, '进程重启超时，端口未响应'
        except Exception as e:
            return False, f'进程重启失败: {str(e)}'

    def fix_database_connection(self, module='database'):
        """修复数据库连接断开 - 重连并验证"""
        self.log('info', '检测到数据库连接断开，尝试重连...', module=module)

        for attempt in range(self.max_retries):
            try:
                db_path = os.path.join(self.root_dir, 'data', 'monitor.db')
                conn = sqlite3.connect(db_path, timeout=10)
                c = conn.cursor()
                c.execute("SELECT 1")
                result = c.fetchone()
                conn.close()

                if result and result[0] == 1:
                    self.log('info', f'数据库重连成功（第{attempt+1}次尝试）', module=module)
                    return True, '数据库重连成功'
            except Exception as e:
                self.log('warning', f'数据库重连第{attempt+1}次失败: {e}', module=module)
                time.sleep(2 ** attempt)  # 指数退避

        return False, f'数据库重连失败，已重试{self.max_retries}次'

    def fix_network_failure(self, module='network'):
        """修复临时网络失败 - 重试3次，指数退避"""
        self.log('info', '检测到网络失败，等待重试...', module=module)

        # 网络问题通常是临时的，等待后重试
        for attempt in range(self.max_retries):
            wait_time = 2 ** attempt
            self.log('info', f'等待 {wait_time} 秒后重试（第{attempt+1}次）', module=module)
            time.sleep(wait_time)

            # 检查网络是否恢复
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=5)
                self.log('info', '网络已恢复', module=module)
                return True, '网络已恢复'
            except Exception:
                continue

        return False, f'网络恢复失败，已重试{self.max_retries}次'

    def fix_cdp_crash(self, module='cdp'):
        """修复CDP浏览器崩溃 - 重启浏览器"""
        self.log('info', '检测到CDP浏览器崩溃，尝试重启...', module=module)

        try:
            # 启动Edge浏览器带CDP端口
            edge_paths = [
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
            ]

            edge_path = None
            for p in edge_paths:
                if os.path.exists(p):
                    edge_path = p
                    break

            if not edge_path:
                return False, '未找到Edge浏览器'

            user_data_dir = os.path.join(self.root_dir, 'edge-cdp-profile')
            os.makedirs(user_data_dir, exist_ok=True)

            subprocess.Popen([
                edge_path,
                '--remote-debugging-port=9222',
                f'--user-data-dir={user_data_dir}',
                '--no-first-run',
                '--no-default-browser-check',
                '--remote-allow-origins=*'
            ])

            # 等待启动并验证
            for i in range(15):
                time.sleep(2)
                if self.check_cdp():
                    self.log('info', f'CDP浏览器重启成功', module=module)
                    return True, 'CDP浏览器重启成功'

            return False, 'CDP浏览器重启超时'
        except Exception as e:
            return False, f'CDP浏览器重启失败: {str(e)}'

    def health_check(self):
        """全面健康检查"""
        self.stats['total_checks'] += 1
        self.stats['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        results = {
            'timestamp': self.stats['last_check'],
            'system_port': self.check_port(port=8201),
            'cdp_port': self.check_cdp(),
            'database': self.check_database()[0],
            'alerts': self.get_active_alerts()
        }

        # 判断是否需要修复
        issues = []
        if not results['system_port']:
            issues.append({'module': 'system', 'issue': '系统端口未响应', 'fixable': True})
        if not results['cdp_port']:
            issues.append({'module': 'cdp', 'issue': 'CDP端口未响应', 'fixable': True})
        if not results['database'][0] if isinstance(results['database'], tuple) else not results['database']:
            issues.append({'module': 'database', 'issue': '数据库连接异常', 'fixable': True})

        results['issues'] = issues
        results['needs_fix'] = len(issues) > 0

        return results

    def auto_repair(self, issue):
        """自动修复单个问题"""
        module = issue.get('module')
        issue_desc = issue.get('issue')
        fixable = issue.get('fixable', True)

        # 检查是否需要人工介入
        if module in self.manual_intervention_modules:
            self.log('warning', f'模块 {module} 需要人工介入，不自动修复', module=module)
            self.add_alert(AlertLevel.ERROR, module, f'{issue_desc}（需要人工介入）', need_manual=True)
            self.stats['manual_interventions'] += 1
            return FixStatus.NEED_MANUAL, '需要人工介入'

        if not fixable:
            self.log('warning', f'问题不可自动修复: {issue_desc}', module=module)
            self.add_alert(AlertLevel.WARNING, module, issue_desc, need_manual=True)
            return FixStatus.NEED_MANUAL, '问题不可自动修复'

        self.stats['total_fixes'] += 1
        self.log('info', f'开始自动修复: {issue_desc}', module=module)

        # 根据模块选择修复方法
        fix_methods = {
            'system': self.fix_process_crash,
            'cdp': self.fix_cdp_crash,
            'database': self.fix_database_connection,
            'network': self.fix_network_failure
        }

        fix_method = fix_methods.get(module)
        if not fix_method:
            self.log('error', f'未找到模块 {module} 的修复方法', module=module)
            self.stats['failed_fixes'] += 1
            return FixStatus.FAILED, f'未找到修复方法'

        # 执行修复
        success, message = fix_method(module)

        if success:
            self.stats['successful_fixes'] += 1
            self.stats['last_fix'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log('info', f'自动修复成功: {message}', module=module)
            self.add_alert(AlertLevel.INFO, module, f'自动修复成功: {message}')
            return FixStatus.FIXED, message
        else:
            self.stats['failed_fixes'] += 1
            self.log('error', f'自动修复失败: {message}', module=module)
            self.add_alert(AlertLevel.ERROR, module, f'自动修复失败: {message}（需要人工介入）', need_manual=True)
            self.stats['manual_interventions'] += 1
            return FixStatus.FAILED, message

    def run_recovery_cycle(self):
        """运行一次完整的修复周期"""
        self.log('info', '开始自动修复周期...', module='recovery')

        # 1. 健康检查
        health = self.health_check()

        if not health['needs_fix']:
            self.log('info', '系统健康，无需修复', module='recovery')
            return {'status': 'healthy', 'issues': []}

        # 2. 逐个修复
        results = []
        for issue in health['issues']:
            fix_status, message = self.auto_repair(issue)
            results.append({
                'issue': issue,
                'status': fix_status.value,
                'message': message
            })

        # 3. 再次验证
        time.sleep(5)
        final_health = self.health_check()

        return {
            'status': 'repaired' if not final_health['needs_fix'] else 'partial',
            'initial_issues': health['issues'],
            'repair_results': results,
            'final_health': final_health
        }

    def get_active_alerts(self):
        """获取活跃告警"""
        try:
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    alerts = json.load(f)
                return [a for a in alerts if a.get('status') == 'active']
        except Exception:
            pass
        return []

    def get_stats(self):
        """获取修复统计"""
        return self.stats.copy()

    def start_background_monitor(self, interval=60):
        """启动后台监控线程"""
        def monitor_loop():
            self.log('info', f'后台监控已启动，间隔 {interval} 秒', module='monitor')
            while True:
                try:
                    self.run_recovery_cycle()
                except Exception as e:
                    self.log('error', f'监控周期异常: {e}', module='monitor')
                time.sleep(interval)

        thread = threading.Thread(target=monitor_loop, daemon=True, name='auto-recovery-monitor')
        thread.start()
        return thread


# 全局实例
recovery_engine = AutoRecoveryEngine()

print("[AutoRecovery] 自动修复引擎已加载", flush=True)

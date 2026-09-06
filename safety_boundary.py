"""
[Legacy] 边界控制引擎 v1.0（Legacy 保留）

⚠️ Legacy 模块：Phase 3 后，统一安全边界由 security_boundary.py（四层架构）编排。本模块保留自动修复边界控制（自动/人工区分、备份、重试、确认流程），与全局 SecurityBoundary 互补，不替代、不删除。

边界控制引擎 v1.0
5层闭环架构 - 第五层：边界控制
功能：
区分"可自动修"和"需人工介入"，防止越修越坏

安全边界规则：
  ├── 自动修复前必须备份现场
  ├── 自动修复最多重试3次，失败则转人工
  ├── 涉及数据删除/修改的操作必须人工确认
  ├── 涉及规则/逻辑改变的操作必须人工确认
  ├── 自动修复操作必须记录完整日志
  └── 人工介入操作必须有确认流程

告警级别：
  ├── INFO（信息）：正常运行记录
  ├── WARNING（警告）：自动修复成功，需关注
  ├── ERROR（错误）：自动修复失败，需人工介入
  └── CRITICAL（严重）：系统核心功能异常，立即告警

不需要登录，本地运行即可
"""

import os
import sys
import json
import time
import shutil
import hashlib
from datetime import datetime
from enum import Enum

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class OperationType(Enum):
    """操作类型"""
    READ = "read"                    # 只读操作（可自动）
    RESTART = "restart"              # 重启进程（可自动）
    RETRY = "retry"                  # 重试操作（可自动）
    RECONNECT = "reconnect"          # 重连操作（可自动）
    DATA_MODIFY = "data_modify"      # 数据修改（需人工确认）
    DATA_DELETE = "data_delete"      # 数据删除（需人工确认）
    RULE_CHANGE = "rule_change"      # 规则改变（需人工确认）
    SCHEMA_CHANGE = "schema_change"  # 数据库结构改变（需人工确认）
    CONFIG_CHANGE = "config_change"  # 配置改变（需人工确认）
    BULK_OPERATION = "bulk_operation"  # 批量操作（需人工确认）


class SafetyLevel(Enum):
    """安全级别"""
    SAFE = "safe"                    # 安全，可自动执行
    CAUTION = "caution"              # 谨慎，自动执行但记录详细日志
    NEED_CONFIRM = "need_confirm"    # 需要人工确认
    FORBIDDEN = "forbidden"          # 禁止自动执行


class BoundaryControlEngine:
    """边界控制引擎"""

    def __init__(self):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_dir = os.path.join(self.root_dir, 'data', 'logs')
        os.makedirs(self.log_dir, exist_ok=True)

        self.boundary_log_file = os.path.join(self.log_dir, 'boundary_control.log')
        self.pending_confirmations_file = os.path.join(self.root_dir, 'data', 'pending_confirmations.json')
        self.file_integrity_file = os.path.join(self.root_dir, 'data', 'file_integrity.json')

        # 操作类型与安全级别映射
        self.operation_safety = {
            OperationType.READ.value: SafetyLevel.SAFE,
            OperationType.RESTART.value: SafetyLevel.CAUTION,
            OperationType.RETRY.value: SafetyLevel.SAFE,
            OperationType.RECONNECT.value: SafetyLevel.SAFE,
            OperationType.DATA_MODIFY.value: SafetyLevel.NEED_CONFIRM,
            OperationType.DATA_DELETE.value: SafetyLevel.FORBIDDEN,
            OperationType.RULE_CHANGE.value: SafetyLevel.NEED_CONFIRM,
            OperationType.SCHEMA_CHANGE.value: SafetyLevel.FORBIDDEN,
            OperationType.CONFIG_CHANGE.value: SafetyLevel.NEED_CONFIRM,
            OperationType.BULK_OPERATION.value: SafetyLevel.NEED_CONFIRM
        }

        # 最大自动重试次数
        self.max_auto_retries = 3
        # 自动修复前是否备份
        self.backup_before_auto_fix = True
        # 备份保留天数
        self.backup_retention_days = 7

        # 加载待确认操作
        self.pending_confirmations = self._load_pending_confirmations()

    def _load_pending_confirmations(self):
        """加载待确认操作"""
        try:
            if os.path.exists(self.pending_confirmations_file):
                with open(self.pending_confirmations_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_pending_confirmations(self):
        """保存待确认操作"""
        try:
            with open(self.pending_confirmations_file, 'w', encoding='utf-8') as f:
                json.dump(self.pending_confirmations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[BoundaryControl] 保存待确认操作失败: {e}", flush=True)

    def log(self, level, message, operation_type=None, details=None):
        """记录边界控制日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        if operation_type:
            log_entry += f" [操作: {operation_type}]"
        if details:
            log_entry += f" [详情: {json.dumps(details, ensure_ascii=False)}]"

        print(log_entry, flush=True)

        try:
            with open(self.boundary_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"[BoundaryControl] 写入日志失败: {e}", flush=True)

    def get_safety_level(self, operation_type):
        """获取操作的安全级别"""
        if isinstance(operation_type, OperationType):
            operation_type = operation_type.value
        return self.operation_safety.get(operation_type, SafetyLevel.NEED_CONFIRM)

    def can_auto_execute(self, operation_type, retry_count=0):
        """判断是否可以自动执行操作"""
        safety_level = self.get_safety_level(operation_type)

        # 禁止自动执行的操作
        if safety_level == SafetyLevel.FORBIDDEN:
            return False, '该操作禁止自动执行，必须人工介入'

        # 需要人工确认的操作
        if safety_level == SafetyLevel.NEED_CONFIRM:
            return False, '该操作需要人工确认'

        # 超过最大重试次数
        if retry_count >= self.max_auto_retries:
            return False, f'已超过最大自动重试次数({self.max_auto_retries})，需人工介入'

        # 谨慎操作，自动执行但记录详细日志
        if safety_level == SafetyLevel.CAUTION:
            return True, '谨慎操作，自动执行但记录详细日志'

        # 安全操作
        return True, '安全操作，可自动执行'

    def request_confirmation(self, operation_type, description, affected_items=None, risk_assessment=None):
        """请求人工确认"""
        confirmation = {
            'id': int(time.time()),
            'operation_type': operation_type.value if isinstance(operation_type, OperationType) else operation_type,
            'description': description,
            'affected_items': affected_items or [],
            'risk_assessment': risk_assessment or '未评估',
            'status': 'pending',  # pending/approved/rejected
            'requested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'confirmed_at': None,
            'confirmed_by': None
        }

        self.pending_confirmations.append(confirmation)
        self._save_pending_confirmations()

        self.log('warning', f'请求人工确认: {description}', operation_type=confirmation['operation_type'])

        return confirmation

    def approve_confirmation(self, confirmation_id, confirmed_by='user'):
        """批准确认"""
        for conf in self.pending_confirmations:
            if conf['id'] == confirmation_id and conf['status'] == 'pending':
                conf['status'] = 'approved'
                conf['confirmed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conf['confirmed_by'] = confirmed_by
                self._save_pending_confirmations()
                self.log('info', f'人工确认已批准: {conf["description"]}', operation_type=conf['operation_type'])
                return True
        return False

    def reject_confirmation(self, confirmation_id, rejected_by='user', reason=''):
        """拒绝确认"""
        for conf in self.pending_confirmations:
            if conf['id'] == confirmation_id and conf['status'] == 'pending':
                conf['status'] = 'rejected'
                conf['confirmed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conf['confirmed_by'] = rejected_by
                conf['reject_reason'] = reason
                self._save_pending_confirmations()
                self.log('warning', f'人工确认已拒绝: {conf["description"]}, 原因: {reason}', operation_type=conf['operation_type'])
                return True
        return False

    def get_pending_confirmations(self):
        """获取待确认操作"""
        return [c for c in self.pending_confirmations if c['status'] == 'pending']

    def backup_before_operation(self, operation_type, description):
        """操作前备份现场"""
        if not self.backup_before_auto_fix:
            return None

        safety_level = self.get_safety_level(operation_type)
        if safety_level == SafetyLevel.SAFE:
            return None  # 安全操作不需要备份

        try:
            backup_dir = os.path.join(self.root_dir, 'data', 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"before_{operation_type}_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            os.makedirs(backup_path, exist_ok=True)

            # 备份数据库
            db_path = os.path.join(self.root_dir, 'data', 'monitor.db')
            if os.path.exists(db_path):
                shutil.copy2(db_path, os.path.join(backup_path, 'monitor.db'))

            # 备份配置
            config_path = os.path.join(self.root_dir, '.env')
            if os.path.exists(config_path):
                shutil.copy2(config_path, os.path.join(backup_path, '.env'))

            # 记录备份信息
            backup_info = {
                'backup_path': backup_path,
                'operation_type': operation_type,
                'description': description,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(os.path.join(backup_path, 'backup_info.json'), 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)

            self.log('info', f'操作前备份完成: {backup_path}', operation_type=operation_type)

            # 清理旧备份
            self._cleanup_old_backups(backup_dir)

            return backup_path
        except Exception as e:
            self.log('error', f'操作前备份失败: {e}', operation_type=operation_type)
            return None

    def _cleanup_old_backups(self, backup_dir):
        """清理旧备份"""
        try:
            if not os.path.exists(backup_dir):
                return

            cutoff = datetime.now() - timedelta(days=self.backup_retention_days)
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                if os.path.isdir(item_path):
                    # 检查备份信息
                    info_path = os.path.join(item_path, 'backup_info.json')
                    if os.path.exists(info_path):
                        with open(info_path, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        created = datetime.strptime(info['created_at'], '%Y-%m-%d %H:%M:%S')
                        if created < cutoff:
                            shutil.rmtree(item_path)
                            self.log('info', f'清理旧备份: {item_path}')
        except Exception as e:
            self.log('error', f'清理旧备份失败: {e}')

    def calculate_file_hash(self, file_path):
        """计算文件哈希（用于完整性校验）"""
        try:
            if not os.path.exists(file_path):
                return None
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return None

    def verify_file_integrity(self, file_path, expected_hash=None):
        """验证文件完整性"""
        current_hash = self.calculate_file_hash(file_path)
        if current_hash is None:
            return False, '文件不存在'

        if expected_hash:
            return current_hash == expected_hash, '哈希匹配' if current_hash == expected_hash else '哈希不匹配，文件可能被篡改'

        return True, '文件存在'

    def baseline_file_integrity(self, files=None):
        """建立文件完整性基线"""
        if files is None:
            # 默认监控关键文件
            files = [
                'app.py',
                'database.py',
                'collector.py',
                'ai_analyzer.py',
                '.env'
            ]

        baseline = {}
        for file_name in files:
            file_path = os.path.join(self.root_dir, file_name)
            if os.path.exists(file_path):
                baseline[file_name] = {
                    'hash': self.calculate_file_hash(file_path),
                    'size': os.path.getsize(file_path),
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                }

        try:
            with open(self.file_integrity_file, 'w', encoding='utf-8') as f:
                json.dump({'baseline': baseline, 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f, ensure_ascii=False, indent=2)
            self.log('info', f'文件完整性基线已建立，监控 {len(baseline)} 个文件')
        except Exception as e:
            self.log('error', f'保存文件完整性基线失败: {e}')

        return baseline

    def check_file_integrity(self):
        """检查文件完整性"""
        try:
            if not os.path.exists(self.file_integrity_file):
                return {'status': 'no_baseline', 'message': '未建立完整性基线'}

            with open(self.file_integrity_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            baseline = data.get('baseline', {})
            issues = []

            for file_name, file_info in baseline.items():
                file_path = os.path.join(self.root_dir, file_name)
                if not os.path.exists(file_path):
                    issues.append({'file': file_name, 'issue': '文件缺失'})
                    continue

                current_hash = self.calculate_file_hash(file_path)
                if current_hash != file_info['hash']:
                    issues.append({'file': file_name, 'issue': '哈希不匹配，文件可能被篡改'})

            return {
                'status': 'ok' if not issues else 'issues_found',
                'checked_files': len(baseline),
                'issues': issues,
                'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def execute_with_boundary(self, operation_type, operation_func, description, retry_count=0, **kwargs):
        """带边界控制的执行操作"""
        # 1. 检查是否可以自动执行
        can_execute, reason = self.can_auto_execute(operation_type, retry_count)

        if not can_execute:
            # 需要人工确认
            confirmation = self.request_confirmation(
                operation_type,
                description,
                risk_assessment=reason
            )
            self.log('warning', f'操作需要人工确认: {description}, 原因: {reason}', operation_type=operation_type.value if isinstance(operation_type, OperationType) else operation_type)
            return {
                'status': 'need_confirmation',
                'confirmation_id': confirmation['id'],
                'message': reason
            }

        # 2. 操作前备份
        backup_path = self.backup_before_operation(operation_type, description)

        # 3. 执行操作
        try:
            self.log('info', f'开始执行操作: {description}', operation_type=operation_type.value if isinstance(operation_type, OperationType) else operation_type)
            result = operation_func(**kwargs)
            self.log('info', f'操作执行成功: {description}', operation_type=operation_type.value if isinstance(operation_type, OperationType) else operation_type)
            return {
                'status': 'success',
                'result': result,
                'backup_path': backup_path
            }
        except Exception as e:
            self.log('error', f'操作执行失败: {description}, 错误: {e}', operation_type=operation_type.value if isinstance(operation_type, OperationType) else operation_type)
            # 重试
            if retry_count < self.max_auto_retries:
                self.log('info', f'准备重试 ({retry_count+1}/{self.max_auto_retries}): {description}')
                time.sleep(2 ** retry_count)  # 指数退避
                return self.execute_with_boundary(operation_type, operation_func, description, retry_count+1, **kwargs)
            else:
                # 超过重试次数，请求人工确认
                confirmation = self.request_confirmation(
                    operation_type,
                    f'{description} (重试{self.max_auto_retries}次后失败)',
                    risk_assessment=f'自动重试失败，错误: {str(e)}'
                )
                return {
                    'status': 'failed_need_confirmation',
                    'confirmation_id': confirmation['id'],
                    'error': str(e),
                    'backup_path': backup_path
                }

    def get_stats(self):
        """获取统计信息"""
        return {
            'total_pending_confirmations': len(self.get_pending_confirmations()),
            'max_auto_retries': self.max_auto_retries,
            'backup_before_auto_fix': self.backup_before_auto_fix,
            'backup_retention_days': self.backup_retention_days,
            'operation_types': len(self.operation_safety),
            'forbidden_operations': len([k for k, v in self.operation_safety.items() if v == SafetyLevel.FORBIDDEN]),
            'need_confirm_operations': len([k for k, v in self.operation_safety.items() if v == SafetyLevel.NEED_CONFIRM])
        }


# 全局实例
boundary_control_engine = BoundaryControlEngine()

print("[BoundaryControl] 边界控制引擎已加载", flush=True)

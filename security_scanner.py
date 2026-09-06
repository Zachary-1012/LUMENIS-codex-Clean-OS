"""
[Legacy] 自动杀毒安全检查模块 v1.0（应用层安全扫描器 · 非网络WAF）

⚠️ 重要声明：本模块是**应用层安全扫描器**（代码静态扫描/敏感信息检测/完整性校验），**不是网络 WAF**。网络 WAF 应由反向代理/云厂商提供。Phase 3 后，统一安全边界由 security_boundary.py（EdgeLayer 明确标注为应用层占位）编排，本模块保留静态扫描能力，不替代、不删除。

自动杀毒安全检查模块 v1.0
功能：
1. 文件完整性校验（防止代码被篡改）
2. 恶意代码扫描（检测危险函数/命令）
3. 敏感信息泄露检测（API Key/密码/Token）
4. 依赖包安全检查
5. 定期自动扫描
6. 安全报告生成
"""

import os
import logging
import sys
import re
import json
import hashlib
import subprocess
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


logger = logging.getLogger(__name__)

class SecurityScanner:
    """安全扫描器"""

    def __init__(self):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.root_dir, 'data')
        self.security_dir = os.path.join(self.data_dir, 'security')
        os.makedirs(self.security_dir, exist_ok=True)

        self.baseline_file = os.path.join(self.security_dir, 'file_baseline.json')
        self.scan_log_file = os.path.join(self.security_dir, 'scan_log.json')

        # 危险函数/模式列表
        self.dangerous_patterns = [
            (r'os\.system\(', 'os.system命令执行'),
            (r'subprocess\.call\(', 'subprocess.call命令执行'),
            (r'subprocess\.Popen\(', 'subprocess.Popen命令执行'),
            (r'eval\(', 'eval函数执行'),
            (r'exec\(', 'exec函数执行'),
            (r'__import__\(', '动态导入'),
            (r'pickle\.loads\(', 'pickle反序列化（可能RCE）'),
            (r'yaml\.load\(', 'yaml.load（可能RCE）'),
            (r'shell=True', 'shell=True命令注入风险'),
            (r'input\(', 'input用户输入（可能注入）'),
        ]

        # 敏感信息模式
        self.sensitive_patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([^"\']{8,})["\']', 'API Key'),
            (r'(?i)(secret|token)\s*[:=]\s*["\']([^"\']{8,})["\']', 'Secret/Token'),
            (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']([^"\']{6,})["\']', '密码'),
            (r'(?i)(private[_-]?key)\s*[:=]\s*["\']([^"\']{16,})["\']', '私钥'),
            (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
            (r'sk-[a-zA-Z0-9]{20,}', 'OpenAI API Key'),
        ]        # S2 增强：Agent/AI 供应链风险模式（对照 GitHub 标杆 SkillSpector 思路）
        # 1) 国产云平台密钥（火山方舟 ark- / 智谱 id.secret）
        # 2) Prompt Injection 风险（skill/plugin 供应链投毒迹象）
        # 3) 数据外泄迹象（webhook/异常 exfiltration URL）
        self.agent_risk_patterns = [
            (r'\bark-[0-9a-f]{8,}-[0-9a-f]{4,}', 'VolcanoARK API Key (火山方舟)'),
            (r'\b[0-9a-f]{32}\.[0-9a-zA-Z]{20,}', 'ZhipuGLM API Key (智谱)'),
            (r'(?i)ignore\s+(all\s+)?previous\s+(instructions|prompts?|directions)', 'Prompt Injection: 忽略历史指令'),
            (r'(?i)you\s+are\s+now\s+(?:a|an)?\s*(?:free|unleashed|no\s*lim)', 'Prompt Injection: 角色越权引导'),
            (r'(?i)exfiltrate|exfiltration|steal\s+credentials|send\s+(?:all|the)\s+(?:data|tokens|secrets)', '数据外泄指令'),
            (r'https?://[\w.-]+\.(?:ngrok\.io|webhook\.site|requestbin\.com|pipedream\.net|webhook\.me)', '外泄/回调 URL'),
            (r'(?i)(?:set|change|override)\s+(?:system\s+)?prompt\s*[:=]', 'Prompt 覆盖指令'),
        ]



        # 扫描的文件扩展名
        self.scan_extensions = ['.py', '.js', '.html', '.css', '.json', '.yml', '.yaml', '.env', '.cfg', '.ini', '.md']

        # 排除的目录
        self.exclude_dirs = ['.venv', 'node_modules', '__pycache__', '.git', 'data', 'logs', 'backups', '.ollama']

    def _load_json(self, path, default):
        """加载JSON文件"""
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _save_json(self, path, data):
        """保存JSON文件"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[Security] 保存文件失败: {e}", flush=True)
            return False

    def _calculate_file_hash(self, file_path):
        """计算文件SHA256哈希"""
        try:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return None

    def _get_scan_files(self):
        """获取需要扫描的文件列表"""
        files = []
        for root, dirs, filenames in os.walk(self.root_dir):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.scan_extensions:
                    files.append(os.path.join(root, filename))
        return files

    # ============================================
    # 1. 文件完整性校验
    # ============================================

    def create_baseline(self):
        """创建文件完整性基线"""
        files = self._get_scan_files()
        baseline = {}
        for file_path in files:
            rel_path = os.path.relpath(file_path, self.root_dir)
            file_hash = self._calculate_file_hash(file_path)
            if file_hash:
                baseline[rel_path] = {
                    'hash': file_hash,
                    'size': os.path.getsize(file_path),
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                }

        baseline_data = {
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file_count': len(baseline),
            'files': baseline
        }
        self._save_json(self.baseline_file, baseline_data)
        print(f"[Security] 文件完整性基线已创建，共 {len(baseline)} 个文件", flush=True)
        return baseline_data

    def verify_integrity(self):
        """校验文件完整性"""
        baseline = self._load_json(self.baseline_file, {})
        if not baseline or 'files' not in baseline:
            return {'status': 'no_baseline', 'message': '未创建完整性基线，请先创建基线'}

        baseline_files = baseline['files']
        issues = []
        current_files = {}

        # 检查现有文件
        for rel_path, info in baseline_files.items():
            file_path = os.path.join(self.root_dir, rel_path)
            if not os.path.exists(file_path):
                issues.append({'file': rel_path, 'issue': '文件缺失', 'severity': 'high'})
                continue

            current_hash = self._calculate_file_hash(file_path)
            current_files[rel_path] = current_hash

            if current_hash != info['hash']:
                issues.append({
                    'file': rel_path,
                    'issue': '文件被修改',
                    'severity': 'medium',
                    'old_hash': info['hash'][:16] + '...',
                    'new_hash': current_hash[:16] + '...' if current_hash else 'None'
                })

        # 检查新增文件
        all_files = self._get_scan_files()
        for file_path in all_files:
            rel_path = os.path.relpath(file_path, self.root_dir)
            if rel_path not in baseline_files:
                issues.append({'file': rel_path, 'issue': '新增文件', 'severity': 'low'})

        return {
            'status': 'pass' if not issues else 'issues_found',
            'checked_files': len(baseline_files),
            'issues_count': len(issues),
            'issues': issues[:50],  # 最多返回50个
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    # ============================================
    # 2. 恶意代码扫描
    # ============================================

    def scan_dangerous_code(self):
        """扫描危险代码"""
        files = self._get_scan_files()
        findings = []

        for file_path in files:
            try:
                rel_path = os.path.relpath(file_path, self.root_dir)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern, description in self.dangerous_patterns:
                        if re.search(pattern, line):
                            findings.append({
                                'file': rel_path,
                                'line': line_num,
                                'code': line.strip()[:100],
                                'issue': description,
                                'severity': 'medium'
                            })
            except Exception:
                continue

        return {
            'status': 'pass' if not findings else 'issues_found',
            'scanned_files': len(files),
            'findings_count': len(findings),
            'findings': findings[:50],
            'scanned_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    # ============================================
    # 3. 敏感信息泄露检测
    # ============================================

    def scan_sensitive_info(self):
        """扫描敏感信息泄露"""
        files = self._get_scan_files()
        findings = []

        for file_path in files:
            try:
                rel_path = os.path.relpath(file_path, self.root_dir)
                # 跳过.env文件（这是正常的配置文件）
                if rel_path.endswith('.env') or 'config' in rel_path.lower():
                    continue

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for pattern, description in self.sensitive_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # 检查是否在注释中（简单判断）
                        line_num = content[:match.start()].count('\n') + 1
                        findings.append({
                            'file': rel_path,
                            'line': line_num,
                            'issue': description,
                            'severity': 'high',
                            'preview': match.group(0)[:50] + '...'
                        })

                # S2：Agent/AI 供应链风险扫描（medium severity）
                for pattern, description in self.agent_risk_patterns:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count('\n') + 1
                        findings.append({
                            'file': rel_path,
                            'line': line_num,
                            'issue': description,
                            'severity': 'medium',
                            'preview': match.group(0)[:50] + '...'
                        })
            except Exception:
                continue

        return {
            'status': 'pass' if not findings else 'issues_found',
            'scanned_files': len(files),
            'findings_count': len(findings),
            'findings': findings[:50],
            'scanned_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    # ============================================
    # 4. 依赖包安全检查
    # ============================================

    def check_dependencies(self):
        """检查依赖包安全性"""
        requirements_file = os.path.join(self.root_dir, 'requirements.txt')
        if not os.path.exists(requirements_file):
            return {'status': 'no_requirements', 'message': '未找到requirements.txt'}

        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            # 检查已知有安全问题的包（简化版）
            risky_packages = {
                'requests': '2.20.0',  # 低于此版本有安全问题
                'urllib3': '1.24.2',
                'flask': '1.0.0',
                'jinja2': '2.10.1',
                'pyyaml': '5.1',
            }

            findings = []
            for pkg in packages:
                pkg_name = pkg.split('==')[0].split('>=')[0].split('<=')[0].strip().lower()
                if pkg_name in risky_packages:
                    findings.append({
                        'package': pkg,
                        'issue': f'{pkg_name} 可能存在已知安全问题，建议升级到 {risky_packages[pkg_name]} 以上',
                        'severity': 'medium'
                    })

            return {
                'status': 'pass' if not findings else 'issues_found',
                'total_packages': len(packages),
                'findings_count': len(findings),
                'findings': findings,
                'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    # ============================================
    # 5. 完整安全扫描
    # ============================================

    def full_scan(self):
        """执行完整安全扫描"""
        print("[Security] 开始完整安全扫描...", flush=True)

        results = {
            'scan_id': int(datetime.now().timestamp()),
            'scanned_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'integrity': self.verify_integrity(),
            'dangerous_code': self.scan_dangerous_code(),
            'sensitive_info': self.scan_sensitive_info(),
            'dependencies': self.check_dependencies()
        }

        # 计算总体风险等级
        total_issues = (
            results['integrity'].get('issues_count', 0) +
            results['dangerous_code'].get('findings_count', 0) +
            results['sensitive_info'].get('findings_count', 0) +
            results['dependencies'].get('findings_count', 0)
        )

        if total_issues == 0:
            results['overall_risk'] = 'low'
            results['overall_status'] = 'pass'
        elif total_issues < 5:
            results['overall_risk'] = 'medium'
            results['overall_status'] = 'warning'
        else:
            results['overall_risk'] = 'high'
            results['overall_status'] = 'fail'

        results['total_issues'] = total_issues

        # 记录扫描日志
        scan_log = self._load_json(self.scan_log_file, [])
        scan_log.append({
            'scan_id': results['scan_id'],
            'scanned_at': results['scanned_at'],
            'overall_status': results['overall_status'],
            'overall_risk': results['overall_risk'],
            'total_issues': total_issues
        })
        scan_log = scan_log[-100:]  # 只保留最近100条
        self._save_json(self.scan_log_file, scan_log)

        print(f"[Security] 扫描完成，总问题数: {total_issues}, 风险等级: {results['overall_risk']}", flush=True)
        return results

    # ============================================
    # 6. 获取扫描历史
    # ============================================

    def get_scan_history(self, limit=20):
        """获取扫描历史"""
        scan_log = self._load_json(self.scan_log_file, [])
        return scan_log[-limit:]


# 全局实例
security_scanner = SecurityScanner()

print("[Security] 自动杀毒安全检查模块已加载", flush=True)

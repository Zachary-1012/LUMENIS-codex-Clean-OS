# -*- coding: utf-8 -*-
"""
LUMENIS Shared Learning Collector — 代码库学习采集模块
【目标】全量学习内部代码库 + 针对性学习（ChatGPT/Codex编程设计/交互/可进化板块）
【安全】学习结果仅存入学习数据库，不污染生产代码；使用按次计费额度（2次预留）
【原则】先扫描代码库提取架构事实 → 再用AI学习分析 → 存储可复用知识
"""
import os
import re
import json
import time
import ast
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# ============ 配置 ============
PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
LEARNING_DB_PATH = os.environ.get(
    'ZBC_LEARNING_DB_PATH',
    os.path.join(PROJECT_ROOT, 'data', 'learning_database.json')
)
# 按次计费学习预留次数（用户指定2次用于ChatGPT/Codex学习采集）
RESERVED_LEARNING_CALLS = 2
# 扫描排除目录
EXCLUDE_DIRS = {'.venv', 'node_modules', '__pycache__', '.git', 'staging', 'logs', 'data', '.pytest_cache'}
# 扫描文件类型
SCAN_EXTENSIONS = {'.py', '.html', '.css', '.js', '.json', '.md', '.yml', '.yaml'}


# ============ 代码库扫描器 ============
class CodebaseScanner:
    """扫描内部代码库，提取架构事实、模式、最佳实践。"""

    def __init__(self, root: str = PROJECT_ROOT):
        self.root = root
        self.stats = {
            'total_files': 0,
            'by_extension': {},
            'total_lines': 0,
            'modules': [],
            'apis': [],
            'routes': [],
            'models': [],
            'patterns': [],
        }

    def scan(self, max_files: int = 500) -> Dict[str, Any]:
        """全量扫描代码库。"""
        files = self._collect_files(max_files)
        for fpath in files:
            try:
                self._analyze_file(fpath)
            except Exception as e:
                pass  # 跳过分析失败的文件
        self.stats['scan_time'] = datetime.now().isoformat()
        self.stats['project_root'] = self.root
        return self.stats

    def _collect_files(self, max_files: int) -> List[str]:
        """收集需要扫描的文件。"""
        result = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            # 排除目录
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith('.')]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in SCAN_EXTENSIONS:
                    fpath = os.path.join(dirpath, fname)
                    result.append(fpath)
                    if len(result) >= max_files:
                        return result
        return result

    def _analyze_file(self, fpath: str):
        """分析单个文件。"""
        ext = os.path.splitext(fpath)[1].lower()
        rel_path = os.path.relpath(fpath, self.root)

        # 统计
        self.stats['total_files'] += 1
        self.stats['by_extension'][ext] = self.stats['by_extension'].get(ext, 0) + 1

        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            lines = content.count('\n') + 1
            self.stats['total_lines'] += lines
        except Exception:
            return

        # Python 文件：提取模块、类、函数、路由
        if ext == '.py':
            self._analyze_python(fpath, rel_path, content)

        # HTML 文件：提取页面结构
        elif ext == '.html':
            self._analyze_html(rel_path, content)

        # CSS 文件：提取样式模式
        elif ext == '.css':
            self._analyze_css(rel_path, content)

        # JS 文件：提取交互逻辑
        elif ext == '.js':
            self._analyze_js(rel_path, content)

    def _analyze_python(self, fpath: str, rel_path: str, content: str):
        """分析Python文件。"""
        # 提取路由（@app.route / @blueprint.route）
        routes = re.findall(r'@(?:app|bp|\w+_bp)\.route\([\'"]([^\'"]+)[\'"]', content)
        for route in routes:
            self.stats['routes'].append({'path': route, 'file': rel_path})

        # 提取类定义
        classes = re.findall(r'class\s+(\w+)', content)
        for cls in classes:
            self.stats['models'].append({'name': cls, 'file': rel_path, 'type': 'class'})

        # 提取函数定义
        funcs = re.findall(r'def\s+(\w+)', content)
        if len(funcs) > 3:  # 只记录函数较多的模块
            self.stats['modules'].append({
                'file': rel_path,
                'functions': funcs[:20],
                'function_count': len(funcs),
            })

        # 提取API端点定义
        api_defs = re.findall(r'def\s+(api_\w+|.*_api\w*)', content)
        for api in api_defs[:10]:
            self.stats['apis'].append({'name': api, 'file': rel_path})

    def _analyze_html(self, rel_path: str, content: str):
        """分析HTML文件。"""
        # 提取页面标题
        titles = re.findall(r'<title>([^<]+)</title>', content)
        # 提取主要组件
        components = re.findall(r'class="([^"]*(?:panel|card|modal|sidebar|topbar)[^"]*)"', content)
        if titles or components:
            self.stats['patterns'].append({
                'file': rel_path,
                'type': 'ui_page',
                'title': titles[0] if titles else '',
                'components': list(set(components))[:10],
            })

    def _analyze_css(self, rel_path: str, content: str):
        """分析CSS文件。"""
        # 提取CSS变量（Design Tokens）
        tokens = re.findall(r'--([\w-]+)\s*:', content)
        if tokens:
            self.stats['patterns'].append({
                'file': rel_path,
                'type': 'design_tokens',
                'tokens': list(set(tokens))[:30],
                'token_count': len(set(tokens)),
            })

    def _analyze_js(self, rel_path: str, content: str):
        """分析JS文件。"""
        # 提取函数
        funcs = re.findall(r'function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?\(', content)
        func_names = [f[0] or f[1] for f in funcs if f[0] or f[1]]
        if func_names:
            self.stats['patterns'].append({
                'file': rel_path,
                'type': 'js_interaction',
                'functions': func_names[:20],
                'function_count': len(func_names),
            })


# ============ 学习分析器 ============
class LearningAnalyzer:
    """使用AI对扫描结果进行学习分析，提取可复用知识。"""

    def __init__(self):
        self.scanner = CodebaseScanner()
        self.scan_result = None

    def scan_and_learn(self, use_ai: bool = False) -> Dict[str, Any]:
        """扫描代码库并学习分析。"""
        # 第一步：扫描代码库（不需要AI额度）
        self.scan_result = self.scanner.scan()

        result = {
            'scan': self.scan_result,
            'learning': {
                'architecture_summary': self._generate_architecture_summary(),
                'key_patterns': self._extract_key_patterns(),
                'reusable_components': self._extract_reusable_components(),
                'improvement_opportunities': self._identify_improvements(),
            },
            'ai_analysis': None,
            'learned_at': datetime.now().isoformat(),
        }

        # 第二步：可选AI深度分析（消耗按次计费额度）
        if use_ai:
            result['ai_analysis'] = self._ai_deep_analysis()

        # 存储学习结果
        self._save_learning(result)
        return result

    def _generate_architecture_summary(self) -> Dict[str, Any]:
        """生成架构摘要。"""
        s = self.scan_result
        return {
            'total_files': s['total_files'],
            'total_lines': s['total_lines'],
            'by_extension': s['by_extension'],
            'route_count': len(s['routes']),
            'module_count': len(s['modules']),
            'class_count': len(s['models']),
            'tech_stack': self._detect_tech_stack(),
        }

    def _detect_tech_stack(self) -> Dict[str, str]:
        """检测技术栈。"""
        stack = {}
        s = self.scan_result
        if s['by_extension'].get('.py', 0) > 10:
            stack['backend'] = 'Python/Flask'
        if s['by_extension'].get('.html', 0) > 0:
            stack['frontend'] = 'HTML/Jinja + 原生JS/CSS'
        if s['by_extension'].get('.css', 0) > 0:
            stack['styling'] = 'Custom CSS + Design Tokens'
        if any('playwright' in str(m).lower() for m in s['modules']):
            stack['browser'] = 'Playwright + CDP'
        if any('sqlite' in str(m).lower() for m in s['modules']):
            stack['database'] = 'SQLite'
        return stack

    def _extract_key_patterns(self) -> List[Dict[str, Any]]:
        """提取关键模式。"""
        patterns = []
        s = self.scan_result

        # Design Tokens 模式
        token_patterns = [p for p in s['patterns'] if p.get('type') == 'design_tokens']
        if token_patterns:
            patterns.append({
                'category': 'design_system',
                'name': 'Design Token System',
                'description': f'发现{len(token_patterns)}个CSS Token文件，共{sum(p.get("token_count",0) for p in token_patterns)}个Token',
                'files': [p['file'] for p in token_patterns],
                'reusability': 'high',
            })

        # UI 页面模式
        ui_patterns = [p for p in s['patterns'] if p.get('type') == 'ui_page']
        if ui_patterns:
            patterns.append({
                'category': 'ui_architecture',
                'name': 'Page Component System',
                'description': f'发现{len(ui_patterns)}个UI页面，使用panel/card/modal/sidebar/topbar组件体系',
                'reusability': 'high',
            })

        # JS 交互模式
        js_patterns = [p for p in s['patterns'] if p.get('type') == 'js_interaction']
        if js_patterns:
            patterns.append({
                'category': 'interaction',
                'name': 'JS Interaction Layer',
                'description': f'发现{len(js_patterns)}个JS交互模块，共{sum(p.get("function_count",0) for p in js_patterns)}个函数',
                'reusability': 'medium',
            })

        return patterns

    def _extract_reusable_components(self) -> List[Dict[str, Any]]:
        """提取可复用组件。"""
        components = []
        s = self.scan_result

        # 从路由提取API组件
        if s['routes']:
            components.append({
                'type': 'api_layer',
                'name': 'Flask API Routes',
                'count': len(s['routes']),
                'description': f'{len(s["routes"])}个API路由，可统一为/api/v1/版本化管理',
                'reusability': 'high',
            })

        # 从模块提取服务组件
        if s['modules']:
            top_modules = sorted(s['modules'], key=lambda x: x.get('function_count', 0), reverse=True)[:5]
            components.append({
                'type': 'service_layer',
                'name': 'Core Service Modules',
                'count': len(s['modules']),
                'top_modules': [m['file'] for m in top_modules],
                'reusability': 'high',
            })

        return components

    def _identify_improvements(self) -> List[Dict[str, Any]]:
        """识别改进机会。"""
        improvements = []
        s = self.scan_result

        # 重复代码检测（简单启发式）
        if s['total_files'] > 50:
            improvements.append({
                'area': 'code_organization',
                'issue': '文件数量较多，可能存在重复实现',
                'suggestion': '建立模块归属矩阵，识别重复能力并收敛',
                'priority': 'medium',
            })

        # CSS Token 统一
        token_files = [p for p in s['patterns'] if p.get('type') == 'design_tokens']
        if len(token_files) > 1:
            improvements.append({
                'area': 'design_system',
                'issue': f'发现{len(token_files)}个CSS Token文件，可能存在Token冲突',
                'suggestion': '统一为单一zb-theme.css作为最终主题覆盖层',
                'priority': 'high',
            })

        # API 版本化
        if s['routes']:
            unversioned = [r for r in s['routes'] if '/api/' in r['path'] and '/v1/' not in r['path']]
            if unversioned:
                improvements.append({
                    'area': 'api_governance',
                    'issue': f'发现{len(unversioned)}个未版本化API路由',
                    'suggestion': '统一为/api/v1/前缀，通过version管理API变化',
                    'priority': 'medium',
                })

        return improvements

    def _ai_deep_analysis(self) -> Optional[Dict[str, Any]]:
        """使用AI进行深度分析（消耗按次计费额度）。"""
        try:
            import ai_resource_packs
            import intelligence

            # 检查按次计费额度
            quota = ai_resource_packs.check_quota('per_call', 1)
            if not quota['allowed']:
                return {'error': f'按次计费额度不足: {quota["reason"]}'}

            # 构建分析提示词
            scan_summary = json.dumps(self._generate_architecture_summary(), ensure_ascii=False, indent=2)
            key_patterns = json.dumps(self._extract_key_patterns()[:3], ensure_ascii=False, indent=2)

            system_prompt = """你是资深软件架构师和AI学习助手。请分析以下代码库扫描结果，提取：
1. 核心架构模式和设计决策
2. 可复用的组件和服务
3. 最佳实践和编码规范
4. ChatGPT/Codex式编程设计功能的可借鉴点
5. 交互设计和用户体验的可进化方向
6. 系统可进化板块的建议（模块化/插件化/AI增强）

输出严格JSON格式，包含以上6个方面的分析。"""

            user_prompt = f"""代码库架构摘要：
{scan_summary}

关键模式：
{key_patterns}

请进行深度分析，重点关注可复用知识和可进化方向。"""

            # 调用AI
            result, provider = intelligence._chat(system_prompt, user_prompt, 0.3, 3000)

            # 记录使用
            ai_resource_packs.record_usage('per_call', 1, endpoint='learning_analysis', detail='代码库深度学习分析')

            # 解析结果
            try:
                analysis = json.loads(result)
            except Exception:
                analysis = {'raw_result': result}

            return {
                'provider': provider,
                'analysis': analysis,
                'quota_used': 1,
            }
        except Exception as e:
            return {'error': str(e)}

    def _save_learning(self, result: Dict[str, Any]):
        """保存学习结果到学习数据库。"""
        try:
            os.makedirs(os.path.dirname(LEARNING_DB_PATH), exist_ok=True)
            # 加载现有学习数据库
            db = {'learnings': [], 'metadata': {}}
            if os.path.exists(LEARNING_DB_PATH):
                try:
                    with open(LEARNING_DB_PATH, 'r', encoding='utf-8') as f:
                        db = json.load(f)
                except Exception:
                    pass

            # 添加新学习记录
            learning_id = f'LEARN-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
            result['learning_id'] = learning_id
            db['learnings'].insert(0, result)
            # 只保留最近20条
            db['learnings'] = db['learnings'][:20]
            db['metadata']['last_updated'] = datetime.now().isoformat()
            db['metadata']['total_learnings'] = len(db['learnings'])

            with open(LEARNING_DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[Learning] 保存失败: {e}')


# ============ 便捷函数 ============
def run_learning_scan(use_ai: bool = False) -> Dict[str, Any]:
    """运行学习扫描（便捷入口）。"""
    analyzer = LearningAnalyzer()
    return analyzer.scan_and_learn(use_ai=use_ai)


def get_learning_history() -> Dict[str, Any]:
    """获取学习历史。"""
    if os.path.exists(LEARNING_DB_PATH):
        try:
            with open(LEARNING_DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'learnings': [], 'metadata': {}}


if __name__ == '__main__':
    print('=== LUMENIS Shared Learning Collector ===')
    result = run_learning_scan(use_ai=False)
    print(f'扫描完成: {result["scan"]["total_files"]} 文件, {result["scan"]["total_lines"]} 行')
    print(f'技术栈: {result["learning"]["architecture_summary"]["tech_stack"]}')
    print(f'关键模式: {len(result["learning"]["key_patterns"])} 个')
    print(f'改进机会: {len(result["learning"]["improvement_opportunities"])} 个')
    print(f'学习结果已保存到: {LEARNING_DB_PATH}')

"""广州太古汇舆情监测系统 v4：本地动态版 + 定时采集 + 严格主体过滤。"""
import os, sys, json, threading, time, shutil, sqlite3, secrets, argparse, concurrent.futures, subprocess, csv, io, re
from pathlib import Path

def _load_dotenv(path='.env'):
    if not os.path.exists(path): return
    try:
        for line in open(path,encoding='utf-8'):
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k,v=line.split('=',1); k=k.strip(); v=v.strip().strip('\"').strip("'")
            if k and k not in os.environ: os.environ[k]=v
    except Exception as e: print('[ENV] load failed:',e)

_load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# === 生产稳定性：原生崩溃(C段错误/被信号终止)默认无任何 Python 堆栈，是历史上“进程静默消失”无线索的根因。
# faulthandler 在解释器层把崩溃瞬间全部线程栈写入 logs/faulthandler.log；threading.excepthook 兜住后台线程未捕获异常。 ===
import faulthandler as _faulthandler
import traceback as _fault_tb
try:
    _LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(_LOG_DIR, exist_ok=True)
    _fault_fh = open(os.path.join(_LOG_DIR, 'faulthandler.log'), 'a', encoding='utf-8')
    _faulthandler.enable(file=_fault_fh, all_threads=True)
except Exception as _fault_e:
    print('[FaultHandler] enable failed:', _fault_e)

def _thread_excepthook(args):
    try:
        import logging as _logging
        _logging.getLogger('threading').error(
            'Uncaught in thread %s: %s: %s\n%s', getattr(args.thread, 'name', args.thread),
            getattr(args.exc_type, '__name__', args.exc_type), args.exc_value,
            ''.join(_fault_tb.format_tb(args.exc_traceback)))
    except Exception:
        pass
threading.excepthook = _thread_excepthook

from datetime import datetime, timedelta
import dev_exec_core
# 统一 Node 解析（PATH 优先，项目内置 nodejs/ 兜底），避免常驻进程 PATH 缺 node 抛 WinError 2
try:
    from runtime_bin import resolve_node as _resolve_node
    _NODE_BIN = _resolve_node() or 'node'
except Exception:
    _NODE_BIN = 'node'
from flask import Flask, jsonify, request, send_from_directory, send_file, Response, redirect
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# === v5.9.9 统一日志增强：yyds-logger补丁模式，一行启用，不影响现有logging调用 ===
# 多实例隔离/JSON结构化/request_id/按sink级别/异常捕获，所有后续模块自动受益
try:
    os.environ.setdefault("APP_ENV", "prod")
    os.environ.setdefault("LOG_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
    from v4_upgrade.unified_logger import patch_logging
    patch_logging()
    print("[UnifiedLogger] yyds-logger补丁已启用（JSON结构化+多实例隔离+request_id）")
except Exception as _log_e:
    print(f"[UnifiedLogger] 启用失败（不影响系统运行）: {_log_e}")
import database as db
import ai_analyzer
import collector
import intelligence
import function_registry
import reprocess
import xhs_cookie_bridge
import ai_filter
import daily_report
import report_engine
import topic_campaign
import app_evidence
import swire_group
import weekly_events
import browser_discovery
# P1-A(2026-09-02): ai_gateway_v570已废弃，统一到intelligence.py
import memory_optimizer
import stability_monitor
import web_monitor_v570
import system_health_api
import architecture_api
import evaluation_system
import settings_module
import export_report
import security_scanner
import runtime_preflight  # ZBIP Runtime Integrity Preflight（统一启动闸门；默认只记录不阻断，ZBC_PREFLIGHT_ENFORCE=1 时 P0 阻断）
import local_ai_client
import pr_case_integration
import system_features_api
import auth_recovery_api  # V3.0 P0: Auth Recovery Center
import xhs_p0_orchestrator
import collector_automation
import ai_learning_engine
import public_opinion_cases
# ProxyPool 可插拔代理池（可选；导入失败不影响系统启动；总开关默认关闭，关闭时等同直连原版）
try:
    from proxy_pool import proxy_manager as _proxy_mgr
    from proxy_pool.loader import load_proxy_nodes as _load_proxy_nodes
    from proxy_pool.config import ProxyConfig as _ProxyCfg
    PROXY_POOL_AVAILABLE = True
except Exception as _pe:
    _proxy_mgr = None; _load_proxy_nodes = None; _ProxyCfg = None
    PROXY_POOL_AVAILABLE = False
    print('[ProxyPool] 模块不可用（不影响系统运行）:', _pe)
# 豆包AI API（可选辅助功能，导入失败不影响系统启动）
try:
    import ark_llm
    ARK_LLM_AVAILABLE = True
except Exception as e:
    ark_llm = None
    ARK_LLM_AVAILABLE = False
    print(f'[ARK] 豆包AI模块导入失败（不影响系统运行）: {e}')
from subject_rules import SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit, subject_sql_and_values

app=Flask(__name__, static_folder='static', static_url_path='/static')
# 全局上传大小限制：500MB（对齐 INGESTION_AND_TERMINOLOGY_STANDARD）
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
# 注册系统控制中心蓝图
app.register_blueprint(system_health_api.system_health_bp)
# 注册5层闭环架构蓝图
app.register_blueprint(architecture_api.architecture_bp)
# 注册设置模块蓝图
app.register_blueprint(settings_module.settings_bp)
# 注册导出报告模块蓝图
app.register_blueprint(export_report.export_bp)
# 注册公关案例整合模块蓝图
app.register_blueprint(pr_case_integration.pr_case_bp)
# 注册系统功能API蓝图
app.register_blueprint(system_features_api.system_features_bp)
# V3.0 P0: Auth Recovery Center（认证恢复中心）
app.register_blueprint(auth_recovery_api.auth_recovery_bp)
import data_query_api
data_query_api.register_data_query_api(app)  # P1-10 拆分批1: 数据只读查询
import collection_api
collection_api.register_collection_api(app)  # P1-10 拆分批2a: 采集器状态/启停

# Zachary OS AI：系统内置浏览器（小红书/rednote 不跳转外部，系统内完成）
try:
    import internal_browser
    internal_browser.register_internal_browser(app)
except Exception as _ib_e:
    print(f"[internal_browser] blueprint register failed: {_ib_e}")

# Zachary OS AI：系统内置浏览器实时画面流（Screencast over SSE，持久连接主动推帧）
try:
    import internal_browser_stream
    internal_browser_stream.register_stream(app)
except Exception as _ibs_e:
    print(f"[internal_browser_stream] blueprint register failed: {_ibs_e}")

# Zachary OS AI：Evidence 查询 API（只读证据接口）
try:
    import evidence_api
    evidence_api.register_evidence_api(app)
except Exception as _ev_e:
    print(f"[evidence_api] blueprint register failed: {_ev_e}")

# Zachary OS AI：Browser Runtime API（只读，对齐 CTR-BROWSER-RUNTIME-P0-01）
try:
    import browser_runtime_api
    browser_runtime_api.register_browser_runtime_api(app)
except Exception as _br_e:
    print(f"[browser_runtime_api] blueprint register failed: {_br_e}")

# V3.0 影子板块：品牌营销知识库API
@app.route('/api/brand-knowledge/stats')
def brand_knowledge_stats():
    """品牌知识库统计"""
    try:
        from brand_knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        return jsonify({'ok': True, 'data': kb.get_stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/brand-knowledge/search')
def brand_knowledge_search():
    """品牌知识库搜索"""
    try:
        from brand_knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        keyword = request.args.get('q', '')
        category = request.args.get('category', '')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        results = kb.search(keyword=keyword, category=category, limit=limit, offset=offset)
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# V3.0 影子板块：案例深度拆解API
@app.route('/api/case-analysis/stats')
def case_analysis_stats():
    """案例深度拆解库统计"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        return jsonify({'ok': True, 'data': analysis.get_stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/list')
def case_analysis_list():
    """案例深度拆解列表（支持筛选）"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        case_type = request.args.get('type', '')
        industry = request.args.get('industry', '')
        brand = request.args.get('brand', '')
        min_quality = request.args.get('min_quality', 0)
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        results = analysis.list_cases(
            case_type=case_type or '',
            industry=industry or '',
            brand=brand or '',
            min_quality_score=float(min_quality) if min_quality else 0,
            limit=limit,
            offset=offset,
        )
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/detail')
def case_analysis_detail():
    """案例深度拆解详情"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        case_id = request.args.get('id', '')
        if not case_id:
            return jsonify({'ok': False, 'error': '缺少案例ID参数'}), 400
        result = analysis.get_case(case_id)
        if not result:
            return jsonify({'ok': False, 'error': f'案例 {case_id} 不存在'}), 404
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/search')
def case_analysis_search():
    """案例深度拆解搜索"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        keyword = request.args.get('q', '')
        if not keyword:
            return jsonify({'ok': False, 'error': '缺少搜索关键词'}), 400
        results = analysis.search_cases(keyword)
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/methodology')
def case_analysis_methodology():
    """获取所有可复用方法论"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        results = analysis.get_all_methodologies()
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/system-insights')
def case_analysis_system_insights():
    """获取所有对Z-Brand系统的启示"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        results = analysis.get_all_system_insights()
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/template-match', methods=['GET', 'POST'])
def case_analysis_template_match():
    """按事件/场景匹配可复用处置模板（学习资产：9模板 + 危机SOP）"""
    try:
        from case_templates import match_templates
        if request.method == 'POST':
            d = request.get_json(silent=True) or {}
            kw = str(d.get('keyword') or d.get('query') or '')
            cat = str(d.get('category') or '')
        else:
            kw = request.args.get('keyword', '')
            cat = request.args.get('category', '')
        results = match_templates(kw, cat)
        return jsonify({'ok': True, 'total': len(results), 'templates': results})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/case-analysis/crisis-sop')
def case_analysis_crisis_sop():
    """危机公关处置SOP（结构化阶段 + KPI）"""
    try:
        from case_templates import get_crisis_sop
        return jsonify({'ok': True, 'sop': get_crisis_sop()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/case-analysis/ai-evaluate', methods=['POST'])
def case_analysis_ai_evaluate():
    """案例库 AI 评估：4维评分(影响/创新/可复制/风险) + 推荐处置模板 + 建议（智谱增强层）"""
    try:
        data = request.get_json(silent=True) or {}
        case_id = str(data.get('case_id') or '')
        if not case_id:
            return jsonify({'ok': False, 'error': '缺少 case_id'}), 400
        from case_deep_analysis import get_case_analysis
        from case_ai_evaluate import evaluate_case
        case = get_case_analysis().get_case(case_id)
        if not case:
            return jsonify({'ok': False, 'error': '案例不存在'}), 404
        result = evaluate_case(case)
        result['case_id'] = case_id
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# V3.0 传播主体分类器API
@app.route('/api/subject-classifier/classify', methods=['POST'])
def subject_classify():
    """传播主体分类"""
    try:
        from subject_classifier import get_subject_classifier
        clf = get_subject_classifier()
        data = request.get_json() or {}
        result = clf.classify(
            author_name=data.get('author_name', ''),
            author_desc=data.get('author_desc', ''),
            followers=int(data.get('followers', 0)),
            is_verified=bool(data.get('is_verified', False)),
            verified_type=data.get('verified_type', ''),
            content_pattern=data.get('content_pattern', ''),
        )
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/subject-classifier/types')
def subject_types():
    """获取所有主体类型"""
    try:
        from subject_classifier import SubjectClassifier
        return jsonify({
            'ok': True,
            'subject_types': SubjectClassifier.get_all_subject_types(),
            'content_types': SubjectClassifier.get_all_content_types(),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# V3.0 事件关系图谱API
@app.route('/api/event-graph/stats')
def event_graph_stats():
    """事件图谱统计"""
    try:
        from event_graph import get_event_graph
        graph = get_event_graph()
        return jsonify({'ok': True, 'data': graph.get_stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-graph/events')
def event_graph_events():
    """获取所有事件"""
    try:
        from event_graph import get_event_graph
        graph = get_event_graph()
        event_type = request.args.get('type', '')
        if event_type:
            events = graph.get_events_by_type(event_type)
        else:
            events = list(graph.events.values())
        evs = [e.to_dict() for e in events]
        # Topic 标签增强（c-TF-IDF 只读，内存增强不改 DB）：为每事件生成 topic_label 供前端/报告
        try:
            from scripts.topic_cluster import enrich_events_with_labels
            evs = enrich_events_with_labels(evs, top_k=4)
        except Exception:
            pass
        return jsonify({'ok': True, 'events': evs, 'count': len(evs)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-graph/chain/<event_id>')
def event_graph_chain(event_id):
    """获取事件链"""
    try:
        from event_graph import get_event_graph
        graph = get_event_graph()
        max_depth = int(request.args.get('max_depth', 5))
        chain = graph.get_event_chain(event_id, max_depth)
        return jsonify({'ok': True, 'chain': [e.to_dict() for e in chain], 'count': len(chain)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-graph/types')
def event_graph_types():
    """获取所有事件类型和关系类型"""
    try:
        from event_graph import EventGraph
        return jsonify({
            'ok': True,
            'event_types': EventGraph.get_all_event_types(),
            'relation_types': EventGraph.get_all_relation_types(),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# V3.0 事件关系图谱写入API（v5.9.9 新增数据库持久化）
@app.route('/api/event-graph/events', methods=['POST'])
def event_graph_create_event():
    """创建新事件"""
    try:
        from event_graph import get_event_graph
        data = request.get_json() or {}
        event_type = data.get('event_type', '')
        title = data.get('title', '')
        if not event_type or not title:
            return jsonify({'ok': False, 'error': 'event_type 和 title 不能为空'}), 400
        graph = get_event_graph()
        event = graph.create_event(
            event_type=event_type, title=title,
            description=data.get('description', ''),
            event_time=data.get('event_time'),
            source=data.get('source', 'manual'),
            status=data.get('status', 'ongoing'),
            metadata=data.get('metadata'),
            source_event_id=data.get('source_event_id'),
        )
        return jsonify({'ok': True, 'data': event.to_dict(), 'message': '事件创建成功'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-graph/relations', methods=['POST'])
def event_graph_add_relation():
    """添加事件关系"""
    try:
        from event_graph import get_event_graph
        data = request.get_json() or {}
        source_id = data.get('source_event_id', '')
        target_id = data.get('target_event_id', '')
        relation_type = data.get('relation_type', '')
        if not source_id or not target_id or not relation_type:
            return jsonify({'ok': False, 'error': '参数不能为空'}), 400
        graph = get_event_graph()
        relation = graph.add_relation(
            source_id=source_id, target_id=target_id,
            relation_type=relation_type,
            evidence=data.get('evidence', ''),
            confidence=data.get('confidence', 0.5),
        )
        if not relation:
            return jsonify({'ok': False, 'error': '源事件或目标事件不存在'}), 404
        return jsonify({'ok': True, 'data': relation.to_dict(), 'message': '关系添加成功'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/creative/ideas', methods=['POST'])
def creative_ideas():
    """创意卡生成：输入品牌/品类/圈层/热点/调性(可选关键词从DB提信号)→ 原创创意方向。"""
    try:
        from scripts.idea_generator import generate_ideas, signals_from_db
        data = request.get_json() or {}
        brand = data.get('brand', '')
        category = data.get('category', '通用')
        circle = data.get('circle', '都市职场')
        tonality = data.get('tonality', 'premium')
        hotspot = data.get('hotspot', '')
        n = min(int(data.get('n', 3)), 5)
        keyword = data.get('keyword', '')
        if not brand:
            return jsonify({'ok': False, 'error': 'brand 不能为空'}), 400
        if keyword:
            signals = signals_from_db(data.get('db', 'data/monitor.db'), keyword, circle, hotspot)
        else:
            signals = {'topics': data.get('topics', []), 'sentiment': data.get('sentiment', 'neutral'),
                       'negative_rate': data.get('negative_rate', 0.0), 'risk_events': data.get('risk_events', 0),
                       'circle': circle, 'hotspot': hotspot, 'volume_notes': data.get('volume_notes', 0)}
        result = generate_ideas(brand, category, signals, n, tonality)
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/creative/video-script', methods=['POST'])
def creative_video_script():
    """视频创意脚本生成：TVC/概念片/小红书/抖音 → 分镜头脚本+标题候选+投放建议。"""
    try:
        from scripts.video_script import generate_video_script, VIDEO_TYPES
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}
        brand = data.get('brand', '')
        if not brand:
            return jsonify({'ok': False, 'error': 'brand 不能为空'}), 400
        vt = data.get('video_type', 'tvc')
        if vt not in VIDEO_TYPES:
            return jsonify({'ok': False, 'error': 'video_type 仅支持: %s' % list(VIDEO_TYPES.keys())}), 400
        result = generate_video_script(
            brand, data.get('category', '通用'), data.get('circle', '都市职场'),
            data.get('tonality', 'premium'), vt, data.get('product_point', ''),
            data.get('hotspot', ''), data.get('n_shots') or None)
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/creative/social-ops', methods=['POST'])
def creative_social_ops():
    """多平台社媒运营策略：小红书/抖音/IG/FB/X/公众号 → 生态/栏目/爆款公式/投放/度量。"""
    try:
        from scripts.social_ops import generate_social_ops, generate_social_matrix, PLATFORMS
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}
        brand = data.get('brand', '')
        if not brand:
            return jsonify({'ok': False, 'error': 'brand 不能为空'}), 400
        platform = data.get('platform', '')
        if platform and platform not in PLATFORMS:
            return jsonify({'ok': False, 'error': 'platform 仅支持: %s' % list(PLATFORMS.keys())}), 400
        if platform:
            result = generate_social_ops(brand, platform, data.get('circle', '都市职场'),
                                         data.get('tonality', 'premium'), data.get('hotspot', ''))
        else:
            result = generate_social_matrix(brand, None, data.get('circle', '都市职场'),
                                            data.get('tonality', 'premium'), data.get('hotspot', ''))
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/creative/pitch-analyze', methods=['POST'])
def creative_pitch_analyze():
    """方案需求拆解：接受 text 或上传文件(multipart file) → 要素提取+对标拆解+创意+方案脉络。"""
    try:
        from scripts.pitch_parser import analyze_pitch, analyze_pitch_file
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}
        text = data.get('text', '')
        brand_hint = data.get('brand', '')
        hotspot = data.get('hotspot', '')
        n = min(int(data.get('n', 3)), 5)
        file = request.files.get('file') if hasattr(request, 'files') else None
        if file and file.filename:
            import os, tempfile
            tmp = os.path.join(tempfile.gettempdir(), 'pitch_%s' % file.filename)
            file.save(tmp)
            result = analyze_pitch_file(tmp, brand_hint, n, hotspot)
            os.remove(tmp)
        elif text.strip():
            result = analyze_pitch(text, brand_hint, n, hotspot)
        else:
            return jsonify({'ok': False, 'error': '需要 text 或上传文件'}), 400
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-graph/import', methods=['POST'])
def event_graph_import_existing():
    """从现有events表导入事件"""
    try:
        from event_graph import get_event_graph, reset_event_graph
        data = request.get_json() or {}
        limit = int(data.get('limit', 20))
        reset_event_graph()
        graph = get_event_graph()
        imported = graph.import_from_existing_events(limit=limit)
        stats = graph.get_stats()
        return jsonify({'ok': True, 'imported': imported, 'stats': stats, 'message': f'成功导入 {imported} 条事件'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-graph/rebuild-relations', methods=['POST'])
def event_graph_rebuild_relations():
    """GAP-07：基于时间+主题词双证据保守重算 follow/derive/parallel；
    不自动生成 trigger（强因果保留人工），只清理并重算 [auto] 关系，幂等可重复。"""
    try:
        from event_graph import get_event_graph
        data = request.get_json(silent=True) or {}
        graph = get_event_graph()
        result = graph.infer_and_link_relations(
            days_window=int(data.get('days_window', 21)),
            parallel_hours=float(data.get('parallel_hours', 36)),
            persist=True, drop_auto_first=True)
        return jsonify({'ok': True, 'result': result, 'stats': graph.get_stats()})
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'days_window/parallel_hours 必须为数值'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== v4 report_center 标准化报告：只读旁路预览（不改既有 daily/brand 报告路由、不抢 RPT Owner、不写库/不导出/不自动发送）=====
@app.route('/api/v2/report-center/preview')
def report_center_preview():
    import re as _re
    period = (request.args.get('period') or 'daily').strip().lower()
    brand_mode = (request.args.get('brand_mode') or 'cth').strip().lower()
    if period not in ('daily', 'weekly', 'monthly', 'yearly', 'event'):
        return jsonify({'ok': False, 'error': 'period 非法，仅 daily/weekly/monthly/yearly/event'}), 400
    if brand_mode not in ('cth', 'zbmp'):
        return jsonify({'ok': False, 'error': 'brand_mode 仅支持 cth/zbmp'}), 400
    sd = (request.args.get('start_date') or '').strip()
    ed = (request.args.get('end_date') or '').strip()
    _dr = _re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if sd and not _dr.match(sd):
        return jsonify({'ok': False, 'error': 'start_date 需 YYYY-MM-DD'}), 400
    if ed and not _dr.match(ed):
        return jsonify({'ok': False, 'error': 'end_date 需 YYYY-MM-DD'}), 400
    try:
        from v4_upgrade.report_center import ReportGenerator
        rep = ReportGenerator(brand_mode=brand_mode).generate(
            period, start_date=sd or None, end_date=ed or None)
        return jsonify({'ok': True, 'report': rep,
                        'note': '只读旁路预览，不替代既有报告 Owner（GAP-10 边界）'})
    except ValueError as ve:
        return jsonify({'ok': False, 'error': str(ve)}), 400
    except Exception:
        app.logger.exception('report_center preview failed')
        return jsonify({'ok': False, 'error': '报告生成失败，请查看服务端日志'}), 500

# ===== Global BIL 全球品牌智能：research-stage 只读（从 seed JSON 读，不建表/不写库/不联网，不参与生产口径）=====
@app.route('/api/v2/global-bil/overview')
@app.route('/api/v2/global-bil/<resource>')
def global_bil_read(resource='overview'):
    try:
        from v4_upgrade.global_bil import load_resource, overview, _FILES
        if resource == 'overview':
            return jsonify({'ok': True, 'stage': 'research', 'overview': overview()})
        if resource not in _FILES:
            return jsonify({'ok': False, 'error': 'resource 非法，仅 overview/benchmarks/mechanisms/cases'}), 400
        data = load_resource(resource)
        if data is None:
            return jsonify({'ok': False, 'error': 'BIL seed 未就绪'}), 404
        return jsonify({'ok': True, 'stage': 'research', 'resource': resource, 'data': data})
    except Exception:
        app.logger.exception('global_bil read failed')
        return jsonify({'ok': False, 'error': 'BIL 读取失败，请查看服务端日志'}), 500

@app.route('/api/event-graph/events/<event_id>', methods=['DELETE'])
def event_graph_delete_event(event_id):
    """删除事件（同时删除关联关系）"""
    try:
        from event_graph import get_event_graph
        import sqlite3 as _sq3
        graph = get_event_graph()
        if event_id not in graph.events:
            return jsonify({'ok': False, 'error': '事件不存在'}), 404
        del graph.events[event_id]
        graph.relations = [r for r in graph.relations
                          if r.source_event.event_id != event_id and r.target_event.event_id != event_id]
        _dbp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db')
        with _sq3.connect(_dbp) as conn:
            conn.execute("DELETE FROM event_graph_events WHERE event_id=?", (event_id,))
            conn.execute("DELETE FROM event_graph_relations WHERE source_event_id=? OR target_event_id=?", (event_id, event_id))
            conn.commit()
        return jsonify({'ok': True, 'message': '事件已删除'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# V3.0 品牌分析报告API
@app.route('/api/brand-report/generate', methods=['POST'])
def brand_report_generate():
    """生成品牌分析报告"""
    try:
        from brand_report_generator import BrandReportGenerator
        data = request.get_json() or {}
        generator = BrandReportGenerator(
            brand_name=data.get('brand_name', 'Z-Brand'),
            report_period=data.get('report_period', ''),
        )
        # 设置各部分数据
        if 'executive_summary' in data:
            es = data['executive_summary']
            generator.set_executive_summary(
                core_findings=es.get('core_findings', []),
                key_metrics=es.get('key_metrics', {}),
                action_items=es.get('action_items', []),
            )
        if 'communication_analysis' in data:
            ca = data['communication_analysis']
            generator.set_communication_analysis(
                subject_distribution=ca.get('subject_distribution', {}),
                channel_analysis=ca.get('channel_analysis', {}),
                effect_evaluation=ca.get('effect_evaluation', {}),
                content_type_distribution=ca.get('content_type_distribution', {}),
            )
        if 'market_intelligence' in data:
            mi = data['market_intelligence']
            generator.set_market_intelligence(
                competitor_updates=mi.get('competitor_updates', []),
                industry_trends=mi.get('industry_trends', []),
                opportunities=mi.get('opportunities', []),
                threats=mi.get('threats', []),
            )
        if 'public_opinion_analysis' in data:
            po = data['public_opinion_analysis']
            generator.set_public_opinion_analysis(
                sentiment_distribution=po.get('sentiment_distribution', {}),
                hot_topics=po.get('hot_topics', []),
                key_influencers=po.get('key_influencers', []),
                risk_warnings=po.get('risk_warnings', []),
            )
        if 'event_graph_analysis' in data:
            eg = data['event_graph_analysis']
            generator.set_event_graph_analysis(
                marketing_events=eg.get('marketing_events', []),
                propagation_events=eg.get('propagation_events', []),
                opinion_events=eg.get('opinion_events', []),
                event_chains=eg.get('event_chains', []),
            )
        if 'recommendations' in data:
            rec = data['recommendations']
            generator.set_recommendations(
                short_term=rec.get('short_term', []),
                medium_term=rec.get('medium_term', []),
                long_term=rec.get('long_term', []),
            )
        report = generator.generate_report()
        return jsonify({'ok': True, 'report': report, 'report_id': report['report_id']})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/brand-report/export/<report_id>')
def brand_report_export(report_id):
    """导出品牌分析报告（JSON/Markdown）"""
    try:
        from brand_report_generator import BrandReportGenerator
        format_type = request.args.get('format', 'json')
        # 这里简化处理，实际应从存储中读取报告
        generator = BrandReportGenerator()
        if format_type == 'markdown':
            filepath = f'data/brand_report_{report_id}.md'
            generator.export_markdown(filepath)
            return jsonify({'ok': True, 'format': 'markdown', 'filepath': filepath})
        else:
            filepath = f'data/brand_report_{report_id}.json'
            generator.export_json(filepath)
            return jsonify({'ok': True, 'format': 'json', 'filepath': filepath})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

APP_VERSION='5.9.9'
APP_HOST=os.getenv('TAIKOO_HOST','0.0.0.0')
APP_PORT=int(os.getenv('TAIKOO_PORT','8200'))
AUTH_USER=os.getenv('TAIKOO_AUTH_USER','')
AUTH_PASSWORD=os.getenv('TAIKOO_AUTH_PASSWORD','')

def _proxy_health_loop(interval=300):
    # 独立守护线程做节点健康巡检，与核心采集调度解耦，任何异常都不影响主系统
    while True:
        try:
            time.sleep(interval)
            if _proxy_mgr is not None and _proxy_mgr.nodes:
                _proxy_mgr.check_all()
        except Exception:
            time.sleep(60)

if PROXY_POOL_AVAILABLE:
    try:
        _load_proxy_nodes()
        if _proxy_mgr.nodes:
            threading.Thread(target=_proxy_health_loop,
                             args=(int(os.getenv('PROXY_HEALTH_INTERVAL', '300')),),
                             daemon=True).start()
        print('[ProxyPool] 节点加载完成 enabled=%s mode=%s 节点数=%d'
              % (_ProxyCfg.ENABLED, _ProxyCfg.MODE, len(_proxy_mgr.nodes)))
    except Exception as _le:
        print('[ProxyPool] 节点加载失败（不影响系统运行）:', _le)

@app.route('/api/proxy/status')
def proxy_status_api():
    if not PROXY_POOL_AVAILABLE:
        return jsonify({'success': False, 'error': 'proxy_pool_unavailable'})
    return jsonify({'success': True, 'status': _proxy_mgr.status()})

@app.route('/api/proxy/check', methods=['POST'])
def proxy_check_api():
    if not PROXY_POOL_AVAILABLE:
        return jsonify({'success': False, 'error': 'proxy_pool_unavailable'})
    try:
        return jsonify({'success': True, 'results': _proxy_mgr.check_all()})
    except Exception as ex:
        return jsonify({'success': False, 'error': str(ex)})

def _auth_enabled():
    return bool(AUTH_USER and AUTH_PASSWORD)


def _subject_sql_and_values(alias=''):
    """系统历史兼容入口：所有 API 统计统一调用主体硬过滤。"""
    return subject_sql_and_values(alias)

@app.route('/api/auth/config')
def auth_config_api():
    """P0-B(2026-09-02): 前端 Auth 动态注入端点 — 前端从此读取凭证，前端代码库不再硬编码任何凭证。
    放行认证（列入 _basic_auth 白名单），仅返回 auth_enabled + auth_header。
    auth_header 仅在认证开启时返回；凭证单一来源在此端点（后端环境变量），可动态轮换/环境分离。
    """
    if not _auth_enabled():
        return jsonify({'ok': True, 'auth_enabled': False, 'auth_header': ''})
    try:
        import base64 as _b64
        header = 'Basic ' + _b64.b64encode(('%s:%s' % (AUTH_USER, AUTH_PASSWORD)).encode('utf-8')).decode('ascii')
        return jsonify({'ok': True, 'auth_enabled': True, 'auth_header': header})
    except Exception as _e:
        return jsonify({'ok': True, 'auth_enabled': True, 'auth_header': '', 'error': str(_e)})


@app.before_request
def _basic_auth():
    # /v4 升级模块使用独立 token/密钥认证（自带登录页），不走现网 HTTP Basic；其余路由维持 Basic 兜底不变
    # /api/auth/config 放行：前端 Auth 动态注入端点（P0-B），返回凭证供前端读取
    if not _auth_enabled() or request.path in ('/healthz', '/api/auth/config') or request.path.startswith('/v4/') or request.path.startswith('/static/'):
        return None
    auth=request.authorization
    if auth and secrets.compare_digest(auth.username or '', AUTH_USER) and secrets.compare_digest(auth.password or '', AUTH_PASSWORD):
        return None
    # 统一认证 Contract（V1.0 基线）：Basic 之外也认可 v4 有效会话（Bearer/同名 session cookie），
    # 使手机端登录 v4 后根级只读健康 API（/api/platform-health 等）可被全局 Auth 健康中心取到；
    # 未登录/无效会话仍 401，安全等级不降，现网 HTTP Basic 行为完全保留。
    try:
        from v4_upgrade.auth.service import get_current_user
        if get_current_user():
            return None
    except Exception:
        pass
    return ('需要登录', 401, {'WWW-Authenticate':'Basic realm=TaikooMonitor'})
class ProxyPrefixMiddleware:
    def __init__(self,wsgi_app): self.wsgi_app=wsgi_app
    def __call__(self,environ,start_response):
        path=environ.get('PATH_INFO','')
        for prefix in ('/proxy/8200','/absproxy/8200'):
            if path.startswith(prefix): environ['PATH_INFO']=path[len(prefix):] or '/'; break
        return self.wsgi_app(environ,start_response)
app.wsgi_app=ProxyPrefixMiddleware(app.wsgi_app)
db.init_db()

# ===== GAP-10 报告路由收敛 P0：RFC 8594/9745 弃用信号（纯增量，不改任何业务逻辑，可一键回滚删除本块）=====
# 行业标准（Stripe/GitHub/Google）：Deprecation(宣布日期, RFC 9745) + Sunset(移除日期, RFC 8594)
#   + Link(替代端点, rel=successor-version)。仅对已确认的"重复实现"路由打标，
#   特殊报告/列表/验证/旁路预览绝不误标。当前 Sunset 为占位远期日期，实际退役需用户签字后另定。
_DEPRECATED_EXACT = {
    '/api/brand-report/generate',
    '/api/report/daily',
    '/api/report/generate',
    '/api/report/export',
    '/api/v2/report/export',
}
_DEPRECATED_PREFIX = ('/api/brand-report/export/', '/api/reports/')
_REPORT_SUNSET = 'Wed, 31 Dec 2026 23:59:59 GMT'

def _is_deprecated_report_path(path):
    if path in _DEPRECATED_EXACT:
        return True
    for p in _DEPRECATED_PREFIX:
        if path.startswith(p):
            return True
    # /api/report/v2/<type> 已弃用，但 /api/report/v2/stats 保留
    if path.startswith('/api/report/v2/') and not path.startswith('/api/report/v2/stats'):
        return True
    return False

@app.after_request
def _report_deprecation_headers(resp):
    try:
        path = request.path
        if _is_deprecated_report_path(path):
            resp.headers['Deprecation'] = 'Wed, 03 Sep 2026 00:00:00 GMT'
            resp.headers['Sunset'] = _REPORT_SUNSET
            resp.headers['X-Deprecated'] = 'true'
            if path.startswith('/api/brand-report/'):
                resp.headers['Link'] = '</api/report-center/generate>; rel="successor-version"'
            elif path.startswith('/api/report/') or path.startswith('/api/v2/report/') or path.startswith('/api/reports/'):
                resp.headers['Link'] = '</api/report-center/generate>; rel="successor-version"'
    except Exception:
        pass  # 绝不因标记失败影响响应
    return resp

collect_tasks={}; _task_lock=threading.Lock(); _collect_lock=threading.Lock()
topic_campaign.register_topic_campaign(app, _collect_lock)
app_evidence.register_app_evidence(app)
swire_group.register_swire_group(app)

def _strict_verify(note):
    title=note.get('title','') or ''; content=note.get('content','') or ''
    return ai_analyzer.verify_taikoo_location(title,content)

def _run_collect_task(task_id,keywords,max_scroll):
    started=time.time()
    try:
        with _task_lock: collect_tasks[task_id].update(status='web-discovery',message='正在检索公开网页舆情并提取事件关键词…',progress=5)
        # 全网发现是辅助能力，不能阻塞小红书主采集链。
        web_result={'fetched':0,'keywords':[],'error':'disabled_or_timeout'}
        if os.getenv('TAIKOO_WEB_DISCOVERY','1').lower() not in ('0','false','no','off'):
            _ex=concurrent.futures.ThreadPoolExecutor(max_workers=1)
            _future=_ex.submit(reprocess.discover_web,limit=80,translate=False)
            try:
                web_result=_future.result(timeout=max(5,int(os.getenv('TAIKOO_WEB_DISCOVERY_TIMEOUT','8'))))
            except concurrent.futures.TimeoutError:
                _future.cancel()
                web_result={'fetched':0,'keywords':[],'error':'timeout'}
            except Exception as _e:
                web_result={'fetched':0,'keywords':[],'error':str(_e)}
            finally:
                # 不等待超时任务结束，避免采集锁被“假超时”长期占用。
                _ex.shutdown(wait=False, cancel_futures=True)
        # 反馈词先清洗英文停用词/单字符/纯符号噪声并限量，避免无意义词拖慢采集、徒增风控暴露
        feedback=[]
        for _x in db.get_feedback_keywords(12):
            _kw=(_x.get('keyword') or '').strip()
            if _kw and _kw not in keywords and not collector._is_noise_keyword(_kw):
                feedback.append(_kw)
            if len(feedback)>=6:
                break
        effective=list(dict.fromkeys(list(keywords)+feedback))[:20]
        with _task_lock: collect_tasks[task_id].update(status='collecting',message=f'全网发现完成，正在用 {len(effective)} 个关键词回搜小红书…',progress=18,web_discovered=web_result.get('fetched',0),feedback_keywords=feedback)
        notes,results=collector.collect_all(keywords=effective,max_scroll=max_scroll)
        verified=[]; rejected=0
        for n in notes:
            ok,reason=ai_analyzer.verify_taikoo_location(n.get('title',''),n.get('content',''))
            n['is_taikoo_verified']=1 if ok else 0; n['verify_reason']=reason; n['source_platform']='xhs'
            if ok: verified.append(n)
            else: rejected+=1
        with _task_lock: collect_tasks[task_id].update(status='saving',message=f'采集 {len(notes)} 条，通过主体硬过滤 {len(verified)} 条',progress=45,collected=len(notes),verified=len(verified),rejected=rejected)
        inserted=updated=0
        for note in verified:
            _,is_new=db.insert_note(note); inserted += int(is_new); updated += int(not is_new)
        for r in results:
            # 六态归一化：SUCCESS/EMPTY/AUTH_REQUIRED/CAPTCHA/BLOCKED/NETWORK_ERROR，绝不含糊记成 error
            _err = (r.get('error') or '')
            cstate = collector.classify_collect_state(_err, r.get('guard_state', ''), r.get('count', 0))
            db.log_collection(r['keyword'], r.get('count', 0), cstate, _err)
            # 需人工介入的态：自动创建统一恢复任务（幂等，已存在则复用；BLOCKED 只冷却不开浏览器），
            # 这样夜间失效也会保留登录/验证入口，手机打开即可恢复，而不是次日才发现失败。
            if cstate in ('AUTH_REQUIRED', 'CAPTCHA', 'BLOCKED'):
                try:
                    from v4_upgrade.adapters import auth_recovery as _ar
                    _ar.request_recovery('xiaohongshu', source_state=cstate, detail=_err)
                    print(f'[Collect] 检测到 {cstate}，已自动创建登录/验证恢复任务（{r.get("keyword","")}）')
                except Exception as _re:  # 恢复通道异常绝不影响采集主流程
                    print('[Collect] 自动创建恢复任务失败(不影响主流程):', _re)
        with _task_lock: collect_tasks[task_id].update(status='ai-review',message='正在进行AI/规则复核、去噪、正负面判断与事件提示…',progress=62,inserted=inserted,updated=updated)
        with db.get_db() as conn:
            clause,sp=_subject_sql_and_values(); rows=conn.execute(f"SELECT * FROM notes WHERE is_taikoo_verified=1 AND (ai_analyzed_at='' OR ai_analyzed_at IS NULL) AND {clause} ORDER BY id DESC LIMIT 500",tuple(sp)).fetchall()
        analyzed=0; rejected_ai=0
        for row in rows:
            result=reprocess.analyze_note_row(row,translate=False)
            analyzed += 1; rejected_ai += int(result=='rejected')
        events=reprocess.build_cross_platform_events()
        with _task_lock: collect_tasks[task_id].update(status='reporting',message='正在生成日报/周报/月报/年报…',progress=90,analyzed=analyzed,rejected_ai=rejected_ai,events=len(events))
        _generate_all_reports()
        with _task_lock: collect_tasks[task_id].update(status='done',message=f'完成：全网发现{web_result.get("fetched",0)}，小红书原始{len(notes)}，有效{len(verified)}，新增{inserted}，更新{updated}，AI复核{analyzed}，事件{len(events)}',progress=100,finished_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),duration_seconds=round(time.time()-started,1))
    except Exception as e:
        with _task_lock: collect_tasks[task_id].update(status='error',message=str(e),error=str(e),finished_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        db.log_collection(','.join(keywords[:3]),0,'error',str(e))
    finally:
        try: _collect_lock.release()
        except RuntimeError: pass

def _generate_all_reports():
    return report_engine.generate_all()

# ========== rednote CDP 采集 ==========
REDNOTE_SCRIPT = Path(__file__).parent / 'rednote_collector.cjs'

def run_rednote_collect(keyword='广州太古汇', max_scroll=3, max_details=10, cdp_url=None):
    """使用 rednote_collector.cjs 通过 CDP 连接已登录浏览器采集真实数据"""
    cdp_url = cdp_url or os.getenv('XHS_CDP_URL', 'http://127.0.0.1:9222')
    if not REDNOTE_SCRIPT.exists():
        return {'ok': False, 'error': f'rednote_collector.cjs 不存在: {REDNOTE_SCRIPT}'}
    env = os.environ.copy()
    env['XHS_CDP_URL'] = cdp_url
    out_file = Path(__file__).parent / 'data' / f'rednote_{datetime.now():%Y%m%d_%H%M%S}.json'
    cmd = [_NODE_BIN, str(REDNOTE_SCRIPT), '--keyword', keyword, '--output', str(out_file),
           '--max-scroll', str(max_scroll), '--max-details', str(max_details)]
    try:
        p = subprocess.run(cmd, cwd=str(Path(__file__).parent), capture_output=True, text=True, timeout=1800, env=env)
        stdout = (p.stdout or '')
        marker = '---RESULT_JSON---'
        if marker in stdout:
            data = json.loads(stdout[stdout.index(marker)+len(marker):].strip())
        elif out_file.exists():
            data = json.loads(out_file.read_text(encoding='utf-8'))
        else:
            data = {'ok': False, 'error': (p.stderr or stdout)[-1000:]}
        data['_returncode'] = p.returncode
        return data
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': '采集超时（300秒）'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def persist_rednote_data(data, subject_hit_fn=None):
    """将 rednote 采集结果入库"""
    if not data or not data.get('ok'):
        return {'ok': False, 'error': data.get('error', '采集失败') if data else '无数据'}
    if data.get('verification_required'):
        return {'ok': False, 'status': 'verification_required', 'reason': '需要人工验证'}
    notes = data.get('notes', [])
    persisted = 0
    comments_total = 0
    for n in notes:
        if subject_hit_fn:
            full_text = (n.get('title','') + ' ' + n.get('desc','') + ' ' + n.get('detail_title','')).lower()
            if not subject_hit_fn(full_text):
                continue
        try:
            note_data = {
                'note_id': n.get('note_id',''),
                'title': n.get('detail_title') or n.get('title',''),
                'content': n.get('desc','') or n.get('content',''),
                'url': n.get('url',''),
                'cover': n.get('cover',''),
                'author_id': n.get('author_id',''),
                'author_nickname': n.get('detail_author') or n.get('author',''),
                'author_avatar': n.get('author_avatar',''),
                'likes': int(n.get('likes',0) or 0),
                'comments': int(n.get('comments',0) or 0),
                'collects': int(n.get('collects',0) or 0),
                'shares': int(n.get('shares',0) or 0),
                'xsec_token': n.get('xsec_token',''),
                'publish_date': n.get('detail_publish_time') or n.get('publish_time',''),
                'publish_datetime': n.get('detail_publish_time') or n.get('publish_time',''),
                'source_platform': 'xhs',
                'is_taikoo_verified': 1,
                'verify_reason': 'rednote采集主体命中',
                'data_quality_status': n.get('quality_status','unknown'),
                'data_quality_score': float(n.get('quality_score',0) or 0),
                'collector_version': n.get('collector_version','rednote-v1.0'),
                'captured_at': n.get('captured_at') or datetime.now().isoformat(),
                'detail_fetched_at': n.get('detail_fetched_at') or datetime.now().isoformat(),
                'comments_collected': int(n.get('comment_count',0) or 0),
            }
            db.insert_note(note_data)
            persisted += 1
            # 保存评论
            comments = n.get('comment_list') or n.get('comments_data') or []
            if comments:
                db.upsert_note_comments(n.get('note_id',''), comments)
                comments_total += len(comments)
            # 保存质量日志
            db.save_collector_quality(n.get('note_id',''), {
                'status': n.get('quality_status','unknown'),
                'score': float(n.get('quality_score',0) or 0),
                'detail_status': 'success' if n.get('detail_fetched') else 'failed',
                'comments_collected': int(n.get('comment_count',0) or 0),
                'collector_version': n.get('collector_version','rednote-v1.0'),
            })
        except Exception as e:
            print(f'[rednote] 入库失败 {n.get("note_id","")}: {e}')
    return {'ok': True, 'persisted': persisted, 'comments': comments_total, 'total': len(notes)}

# ========== 舆情预警通知 ==========
ALERTS_FILE = Path(__file__).parent / 'data' / 'alerts.json'

def _load_alerts():
    if ALERTS_FILE.exists():
        try: return json.loads(ALERTS_FILE.read_text(encoding='utf-8'))
        except: return []
    return []

def _save_alerts(alerts):
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERTS_FILE.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding='utf-8')

def check_and_create_alerts():
    """检查高风险/高影响力/上升过快的笔记，创建预警通知"""
    alerts = _load_alerts()
    existing_ids = {a.get('note_id') for a in alerts}
    new_alerts = []
    try:
        high_risk = db.get_high_risk_notes(50)
        hot_notes = db.get_hot_notes(20)
        for note in high_risk + hot_notes:
            nid = note.get('note_id') or note.get('id')
            if not nid or str(nid) in existing_ids: continue
            risk = note.get('risk_level','')
            likes = int(note.get('likes',0) or 0)
            comments = int(note.get('comments',0) or 0)
            influence = likes + comments * 3
            alert_type = 'risk' if risk in ('high','critical') else ('influence' if influence > 500 else 'rising')
            alert = {
                'id': f"alert_{nid}_{datetime.now():%Y%m%d%H%M%S}",
                'note_id': str(nid),
                'title': note.get('title','')[:80],
                'type': alert_type,
                'risk_level': risk,
                'influence': influence,
                'likes': likes,
                'comments': comments,
                'message': f"{'高风险' if alert_type=='risk' else '高影响力'}舆情：{note.get('title','')[:50]}",
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'read': False,
            }
            alerts.append(alert)
            new_alerts.append(alert)
            existing_ids.add(str(nid))
        if new_alerts:
            _save_alerts(alerts)
    except Exception as e:
        print(f'[Alerts] 检查预警失败: {e}')
    return new_alerts

# ========== 报告导出（表格模式） ==========
# ========== 品牌目录与业态匹配 ==========
BRAND_DIR_FILE = Path(__file__).parent / 'data' / 'brand_directory.json'
_brand_cache = None

def _load_brands():
    global _brand_cache
    if _brand_cache is not None:
        return _brand_cache
    if BRAND_DIR_FILE.exists():
        try:
            data = json.loads(BRAND_DIR_FILE.read_text(encoding='utf-8'))
            _brand_cache = data.get('brands', [])
        except Exception as e:
            print(f'[Brand] 加载品牌目录失败: {e}')
            _brand_cache = []
    else:
        _brand_cache = []
    return _brand_cache

def _match_brand(note):
    """根据笔记标题/正文/作者匹配场内品牌，返回品牌名和业态"""
    brands = _load_brands()
    text = (note.get('title', '') + ' ' + note.get('content', '') + ' ' + note.get('desc', '') + ' ' + note.get('author_nickname', '')).lower()
    matched = []
    for b in brands:
        brand_en = b['brand_en'].lower()
        brand_cn = b.get('brand_cn', '').lower()
        if (brand_en and len(brand_en) > 2 and brand_en in text) or (brand_cn and len(brand_cn) > 1 and brand_cn in text):
            matched.append(b)
    if matched:
        # 取第一个匹配的品牌
        return matched[0]['brand_cn'] or matched[0]['brand_en'], matched[0]['category']
    return '', ''

def _classify_category(note):
    """太古汇核心业态分类：零售品牌、餐饮、商场服务、活动/展览、环境/设施、安全/突发事件"""
    brand, brand_category = _match_brand(note)
    if brand_category == '餐饮':
        return '餐饮'
    if brand_category in ('女装', '男装', '鞋包皮具', '珠宝钟表', '运动休闲', '童装玩具', '生活时尚', '美容护理'):
        return '零售品牌'
    # 关键词匹配
    text = (note.get('title', '') + ' ' + note.get('content', '') + ' ' + note.get('desc', '')).lower()
    if any(k in text for k in ['停车', '会员', '积分', '客服', '服务台', '投诉', '服务态度']):
        return '商场服务'
    if any(k in text for k in ['活动', '展览', '快闪', '排队', '规则', '奖品', '现场', '十五周年', '周年庆']):
        return '活动/展览'
    if any(k in text for k in ['卫生', '空调', '母婴室', '导视', '厕所', '洗手间', '环境', '设施']):
        return '环境/设施'
    if any(k in text for k in ['安全', '突发', '事故', '受伤', '盗窃', '纠纷', '打架']):
        return '安全/突发事件'
    return '其他'

def _calc_alert_level(stats, notes):
    """判断舆情等级：🔴重大 / 🟡关注 / 🟢平稳"""
    negative = stats.get('negative', 0)
    high_risk = stats.get('high_risk', 0)
    total = stats.get('total', len(notes))
    if total == 0:
        return '🟢平稳', '本期无监测数据'
    neg_ratio = negative / total if total > 0 else 0
    if high_risk >= 3 or neg_ratio >= 0.3:
        return '🔴重大', f'负面占比{neg_ratio*100:.0f}%，高风险{high_risk}条，需立即响应'
    if high_risk >= 1 or neg_ratio >= 0.15:
        return '🟡关注', f'负面占比{neg_ratio*100:.0f}%，高风险{high_risk}条，需持续关注'
    return '🟢平稳', f'负面占比{neg_ratio*100:.0f}%，整体舆情平稳'

def _generate_core_conclusion(stats, notes, category_stats):
    """生成1句话核心结论"""
    total = stats.get('total', len(notes))
    negative = stats.get('negative', 0)
    max_engagement = max([int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3 for n in notes], default=0)
    # 找最高负面业态
    top_category = max(category_stats.items(), key=lambda x: x[1].get('negative',0), default=(None, {}))
    top_cat_name = top_category[0] if top_category[0] else '综合'
    top_cat_neg = top_category[1].get('negative', 0) if top_category[1] else 0
    # 判断是否扩散
    spreading = '已出现扩散' if max_engagement > 500 else '暂无扩散'
    return f'本期共监测小红书舆情{total}条，负面{negative}条，主要集中在【{top_cat_name}】，最高互动{max_engagement}，{spreading}。'

# ========== v5.4 品牌业态统计 ==========
@app.route('/api/brand-stats')
def api_brand_stats():
    """场内品牌及9大业态统计，对应rednote笔记数量"""
    brands = _load_brands()
    notes = db.get_notes_by_date_range((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'))
    
    # 9大业态统计
    category_stats = {}
    category_order = ['女装', '男装', '餐饮', '珠宝钟表', '美容护理', '运动休闲', '鞋包皮具', '童装玩具', '生活时尚']
    for cat in category_order:
        category_stats[cat] = {'brand_count': 0, 'note_count': 0, 'negative_count': 0, 'engagement': 0, 'brands': []}
    
    for b in brands:
        cat = b.get('category', '')
        if cat in category_stats:
            category_stats[cat]['brand_count'] += 1
            category_stats[cat]['brands'].append(b)
    
    # 匹配笔记
    brand_note_map = {}
    for n in notes:
        brand, brand_category = _match_brand(n)
        if brand and brand_category in category_stats:
            category_stats[brand_category]['note_count'] += 1
            if n.get('sentiment') == 'negative':
                category_stats[brand_category]['negative_count'] += 1
            category_stats[brand_category]['engagement'] += int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
            if brand not in brand_note_map:
                brand_note_map[brand] = {'note_count': 0, 'negative_count': 0, 'engagement': 0, 'category': brand_category}
            brand_note_map[brand]['note_count'] += 1
            if n.get('sentiment') == 'negative':
                brand_note_map[brand]['negative_count'] += 1
            brand_note_map[brand]['engagement'] += int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
    
    # 品牌TOP10
    top_brands = sorted(brand_note_map.items(), key=lambda x: x[1]['note_count'], reverse=True)[:10]
    top_brands_list = [{'brand': b, **stats} for b, stats in top_brands]
    
    # 业态分布（用于扇形图）
    pie_data = []
    total_notes = sum(cs['note_count'] for cs in category_stats.values())
    for cat in category_order:
        cs = category_stats[cat]
        percentage = round(cs['note_count'] / total_notes * 100, 1) if total_notes > 0 else 0
        pie_data.append({'category': cat, 'note_count': cs['note_count'], 'brand_count': cs['brand_count'], 'percentage': percentage, 'negative_count': cs['negative_count']})
    
    # 趋势数据（最近7天）
    trend_data = []
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        day_notes = [n for n in notes if n.get('publish_date', '').startswith(date)]
        trend_data.append({'date': date, 'note_count': len(day_notes), 'negative_count': sum(1 for n in day_notes if n.get('sentiment')=='negative')})
    
    return jsonify({
        'ok': True,
        'total_brands': len(brands),
        'total_notes': len(notes),
        'categories': category_stats,
        'pie_data': pie_data,
        'trend_data': trend_data,
        'top_brands': top_brands_list,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# ========== 报告导出（太古汇舆情汇报模板） ==========
def export_report_to_csv(report_type='daily', date_str=None):
    """按太古汇舆情汇报模板导出CSV：核心结论→数据概览→分业态分布→重点负面帖→舆情归因→应对动作"""
    now = datetime.now()
    date_str = date_str or now.strftime('%Y-%m-%d')
    if report_type == 'daily':
        start = end = date_str
        period_label = f'{date_str.replace("-", ".")}'
    elif report_type == 'weekly':
        start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
        end = date_str
        period_label = f'{start.replace("-",".")} – {end.replace("-",".")}'
    elif report_type == 'monthly':
        start = now.replace(day=1).strftime('%Y-%m-%d')
        end = date_str
        period_label = f'{start.replace("-",".")} – {end.replace("-",".")}'
    elif report_type == 'yearly':
        start = now.replace(month=1, day=1).strftime('%Y-%m-%d')
        end = date_str
        period_label = f'{start.replace("-",".")} – {end.replace("-",".")}'
    else:
        start = end = date_str
        period_label = date_str

    notes = db.get_notes_by_date_range(start, end)
    stats = db.get_stats_by_date_range(start, end)

    # 计算环比（上一周期）
    try:
        if report_type == 'daily':
            prev_start = prev_end = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        elif report_type == 'weekly':
            prev_start = (now - timedelta(days=now.weekday()+7)).strftime('%Y-%m-%d')
            prev_end = (now - timedelta(days=now.weekday()+1)).strftime('%Y-%m-%d')
        elif report_type == 'monthly':
            prev_month = now.month - 1 if now.month > 1 else 12
            prev_year = now.year if now.month > 1 else now.year - 1
            prev_start = f'{prev_year}-{prev_month:02d}-01'
            prev_end = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            prev_start = prev_end = start
        prev_notes = db.get_notes_by_date_range(prev_start, prev_end)
        prev_stats = db.get_stats_by_date_range(prev_start, prev_end)
    except:
        prev_stats = {'total': 0, 'negative': 0, 'positive': 0, 'high_risk': 0, 'total_engagement': 0}

    # 分业态统计
    category_stats = {}
    category_order = ['零售品牌', '餐饮', '商场服务', '活动/展览', '环境/设施', '安全/突发事件', '其他']
    for n in notes:
        cat = _classify_category(n)
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'negative': 0, 'positive': 0, 'engagement': 0, 'topics': [], 'brands': []}
        category_stats[cat]['total'] += 1
        sent = n.get('sentiment', '')
        if sent == 'negative': category_stats[cat]['negative'] += 1
        elif sent == 'positive': category_stats[cat]['positive'] += 1
        category_stats[cat]['engagement'] += int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
        brand, _ = _match_brand(n)
        if brand and brand not in category_stats[cat]['brands']:
            category_stats[cat]['brands'].append(brand)

    # 舆情等级
    alert_level, alert_desc = _calc_alert_level(stats, notes)
    # 核心结论
    core_conclusion = _generate_core_conclusion(stats, notes, category_stats)

    output = io.StringIO()
    # 写入BOM以便Excel正确识别中文
    output.write('\ufeff')
    writer = csv.writer(output)

    # ===== 表头 =====
    report_title = '舆情日报' if report_type == 'daily' else ('舆情专报' if report_type in ('weekly',) else f'舆情{report_type}报')
    writer.writerow([f'【{report_title}】'])
    writer.writerow([f'汇报周期：{period_label}'])
    writer.writerow(['汇报人：舆情监测系统'])
    writer.writerow([f'舆情等级：{alert_level} — {alert_desc}'])
    writer.writerow([])

    # ===== 1. 核心结论 =====
    writer.writerow(['1. 核心结论（1句话）'])
    writer.writerow([core_conclusion])
    writer.writerow([])

    # ===== 2. 数据概览 =====
    writer.writerow(['2. 数据概览'])
    writer.writerow(['指标', '本期', '环比'])
    cur_total = stats.get('total', len(notes))
    prev_total = prev_stats.get('total', 0)
    cur_neg = stats.get('negative', 0)
    prev_neg = prev_stats.get('negative', 0)
    cur_pos = stats.get('positive', 0)
    max_eng = max([int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3 for n in notes], default=0)
    def pct_change(cur, prev):
        if prev == 0: return '—' if cur == 0 else '+∞'
        change = (cur - prev) / prev * 100
        return f'{"+" if change >= 0 else ""}{change:.1f}%'
    writer.writerow(['总提及量', cur_total, pct_change(cur_total, prev_total)])
    writer.writerow(['负面量', cur_neg, pct_change(cur_neg, prev_neg)])
    neg_ratio = f'{(cur_neg/cur_total*100):.1f}%' if cur_total > 0 else '0%'
    prev_neg_ratio = f'{(prev_neg/prev_total*100):.1f}%' if prev_total > 0 else '0%'
    writer.writerow(['负面占比', neg_ratio, f'{"+" if float(neg_ratio.strip("%")) >= float(prev_neg_ratio.strip("%")) else ""}{float(neg_ratio.strip("%"))-float(prev_neg_ratio.strip("%")):.1f}pp'])
    writer.writerow(['最高单条互动', max_eng, '—'])
    writer.writerow([])

    # ===== 3. 分业态舆情分布 =====
    writer.writerow(['3. 分业态舆情分布（太古汇核心维度）'])
    writer.writerow(['业态/模块', '提及量', '负面量', '主要话题/品牌', '等级'])
    for cat in category_order:
        if cat not in category_stats: continue
        cs = category_stats[cat]
        neg = cs['negative']
        total = cs['total']
        if neg >= 3 or (total > 0 and neg/total >= 0.3):
            level = '🔴'
        elif neg >= 1 or (total > 0 and neg/total >= 0.15):
            level = '🟡'
        else:
            level = '🟢'
        topics = '、'.join(cs['brands'][:3]) if cs['brands'] else '—'
        writer.writerow([cat, total, neg, topics, level])
    writer.writerow([])

    # ===== 4. 重点负面帖清单 =====
    writer.writerow(['4. 重点负面帖清单'])
    writer.writerow(['序号', '业态', '笔记标题', '发布时间', '互动量', '核心诉求', '处理状态'])
    negative_notes = [n for n in notes if n.get('sentiment') == 'negative' or n.get('risk_level') in ('high', 'critical')]
    negative_notes.sort(key=lambda x: int(x.get('likes',0) or 0) + int(x.get('comments',0) or 0)*3, reverse=True)
    for i, n in enumerate(negative_notes[:15], 1):
        cat = _classify_category(n)
        engagement = int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
        # 核心诉求（从内容提取前30字）
        content = n.get('content', '') or n.get('desc', '') or n.get('summary', '') or ''
        core_demand = content[:40] + '...' if len(content) > 40 else content
        writer.writerow([i, cat, n.get('title', '')[:50], n.get('publish_date', ''), engagement, core_demand, '待处理'])
    if not negative_notes:
        writer.writerow(['—', '—', '本期无重点负面帖', '—', '—', '—', '—'])
    writer.writerow([])

    # ===== 5. 舆情归因 =====
    writer.writerow(['5. 舆情归因'])
    # 高发业态
    if category_stats:
        top_cat = max(category_stats.items(), key=lambda x: x[1]['negative'])
        total_neg = sum(cs['negative'] for cs in category_stats.values())
        high_cat_ratio = f'{(top_cat[1]["negative"]/total_neg*100):.0f}%' if total_neg > 0 else '0%'
        writer.writerow([f'高发业态：{top_cat[0]}（占负面{high_cat_ratio}）'])
    else:
        writer.writerow(['高发业态：—'])
    # 触发类型
    trigger_types = []
    for n in negative_notes[:10]:
        text = (n.get('title','') + ' ' + n.get('content','') + ' ' + n.get('desc','')).lower()
        if any(k in text for k in ['服务态度', '店员', '客服', '态度差']): trigger_types.append('服务态度')
        elif any(k in text for k in ['活动', '规则', '排队', '奖品']): trigger_types.append('活动规则')
        elif any(k in text for k in ['空调', '卫生', '设施', '厕所', '母婴室']): trigger_types.append('硬件设施')
        elif any(k in text for k in ['品牌', '专柜', '缺货', '价格']): trigger_types.append('品牌商户')
        elif any(k in text for k in ['价格', '贵', '涨价']): trigger_types.append('价格争议')
    trigger_str = ' / '.join(list(dict.fromkeys(trigger_types))[:4]) if trigger_types else '综合'
    writer.writerow([f'触发类型：{trigger_str}'])
    writer.writerow(['传播路径：素人发帖 → 评论区共鸣 → KOC/本地号转发'])
    writer.writerow([])

    # ===== 6. 应对动作 & 下一步 =====
    writer.writerow(['6. 应对动作 & 下一步'])
    writer.writerow(['已执行：系统自动采集、分类、风险标记，高风险内容已推送预警'])
    writer.writerow(['待执行：重点负面帖人工复核与回复（责任部门：公关部/运营部/对接人/截止时间：24小时内）'])
    # 风险预警
    risk_warnings = []
    if any('十五周年' in (n.get('title','')+n.get('content','')) for n in notes):
        risk_warnings.append('广州太古汇15周年庆活动期间，预计客流激增，需提前准备停车/排队话术，提高危机敏感意识')
    if category_stats.get('活动/展览', {}).get('negative', 0) > 0:
        risk_warnings.append('活动/展览类负面上升，建议现场增派人手疏导，优化活动规则说明')
    if max_eng > 500:
        risk_warnings.append('出现高互动内容，需密切关注传播趋势，必要时启动公关响应')
    if not risk_warnings:
        risk_warnings.append('暂无特殊风险预警，保持常规监测频率')
    writer.writerow([f'风险预警：{"；".join(risk_warnings)}'])
    writer.writerow([])
    writer.writerow([f'报告生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow(['数据来源：小红书/rednote 真实采集 · 太古汇场内品牌目录（2026.08.20更新）'])

    filename = f'太古汇{report_title}_{date_str}.csv'
    return output.getvalue(), filename

@app.route('/')
def index(): return send_from_directory('static','index.html')
@app.route('/favicon.ico')
def favicon():
    # 消除浏览器自动请求 favicon 产生的 404 控制台报错
    return Response(status=204)
@app.route('/api/report/daily')
def api_report_daily():
    """日报弹窗：只含“昨天+当天发布”的有效舆情笔记（过期笔记不弹窗，仅入库做案例）。
    一天两窗口（凌晨/晚间），是否已看过由前端按 日期+窗口 归档。"""
    def _num(v):
        try: return int(v or 0)
        except (TypeError,ValueError): return 0
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        today_d = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception:
        today_d = datetime.now().date()
    yesterday_s = (today_d - timedelta(days=1)).strftime('%Y-%m-%d')
    today_s = today_d.strftime('%Y-%m-%d')
    now_h = datetime.now().hour
    window = 'morning' if now_h < 15 else 'evening'  # 15点前=早间窗口，之后=晚间窗口
    clause, sp = _subject_sql_and_values()
    sql = ("SELECT * FROM notes WHERE COALESCE(is_duplicate,0)=0 AND COALESCE(noise_type,'')='' "
           "AND substr(COALESCE(publish_date,publish_datetime,collected_at,''),1,10) IN (?,?) "
           f"AND {clause} ORDER BY substr(COALESCE(publish_date,publish_datetime,''),1,10) DESC, "
           "COALESCE(likes,0) DESC LIMIT 200")
    with db.get_db() as conn:
        rows_all = [dict(r) for r in conn.execute(sql, tuple([yesterday_s, today_s] + list(sp))).fetchall()]
    # 日报推送口径：只推送负面笔记（正面/中性仅作背景统计，不进推送列表）
    rows = [n for n in rows_all if n.get('sentiment') == 'negative']
    # 负面按 风险等级→风险分→互动量 排序，高风险优先推送
    _rl_order = {'high': 0, 'medium': 1, 'low': 2}
    rows.sort(key=lambda n: (_rl_order.get(n.get('risk_level'), 3),
                             -_num(n.get('risk_score')),
                             -(_num(n.get('likes')) + _num(n.get('comments')) + _num(n.get('collects')) + _num(n.get('shares')))))
    def cnt(rs, s): return sum(1 for n in rs if n.get('sentiment') == s)
    total = len(rows_all); neg = cnt(rows_all, 'negative'); pos = cnt(rows_all, 'positive'); neu = cnt(rows_all, 'neutral')
    high = sum(1 for n in rows if n.get('risk_level') == 'high')
    today_cnt = sum(1 for n in rows_all if (n.get('publish_date') or n.get('publish_datetime') or '')[:10] == today_s)
    yest_cnt = total - today_cnt
    brief = []
    for n in rows[:30]:
        eng = _num(n.get('likes')) + _num(n.get('comments')) + _num(n.get('collects')) + _num(n.get('shares'))
        brief.append({'note_id': n.get('note_id'), 'title': n.get('title'), 'author': n.get('author_nickname'),
                      'sentiment': n.get('sentiment'), 'risk_level': n.get('risk_level'),
                      'risk_score': n.get('risk_score'), 'ai_reason': n.get('ai_reason') or '',
                      'publish_date': (n.get('publish_date') or n.get('publish_datetime') or '')[:10], 'engagement': eng})
    stats = {'total': total, 'negative': neg, 'positive': pos, 'neutral': neu, 'high_risk': high,
             'pushed': len(rows), 'today_count': today_cnt, 'yesterday_count': yest_cnt}
    if neg == 0:
        conclusion = (f"昨日与今日共收录有效笔记 {total} 篇（昨日 {yest_cnt}、今日 {today_cnt}；"
                      f"正面 {pos}、中性 {neu}），未发现负面舆情笔记。")
    else:
        conclusion = (f"昨日与今日共收录 {total} 篇，发现负面笔记 {neg} 篇（高风险 {high}），"
                      f"日报仅推送以下负面内容，按风险高低排序；正面 {pos}、中性 {neu} 篇不进推送。")
    return jsonify({'ok': True, 'date': today_s, 'window': window,
                    'report': {'date_range': f'{yesterday_s} 至 {today_s}', 'stats': stats,
                               'conclusion': conclusion, 'notes': brief}})

@app.route('/api/intelligence/refresh',methods=['POST'])
def api_intelligence_refresh():
    if not _collect_lock.acquire(blocking=False): return jsonify({'ok':False,'error':'已有任务运行中'}),409
    body=request.get_json(silent=True) or {}
    try: limit=max(1,min(10000,int(body.get('limit',5000))))
    except (TypeError,ValueError): limit=5000
    task_id=f"intel-{datetime.now():%Y%m%d%H%M%S}"
    with _task_lock: collect_tasks[task_id]={'task_id':task_id,'status':'pending','message':'智能刷新任务已创建','progress':0,'created_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    def worker():
        try:
            result=reprocess.full_refresh(limit=limit,web_limit=120,translate=False)
            with _task_lock: collect_tasks[task_id].update(status='done',progress=100,message='历史数据库AI复核、全网发现、跨平台事件聚合完成',result=result)
        except Exception as e:
            with _task_lock: collect_tasks[task_id].update(status='error',message=str(e),error=str(e))
        finally: _collect_lock.release()
    threading.Thread(target=worker,daemon=True).start()
    return jsonify({'ok':True,'task_id':task_id})

@app.route('/api/ai-governance/status')
def api_ai_governance_status():
    """AI 治理状态：额度/使用统计/配置/脱敏状态（余额需在智谱控制台查看）"""
    try:
        return jsonify(ai_governance.get_governance_status())
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai/status')
def api_ai_status():
    status = intelligence.ai_status()
    return jsonify({'ok': True, **status, 'interface': 'local-ai-gateway', 'fallback': 'local_rule', 'providers': ['ollama','lmstudio','llama_cpp','qwen','openai','deepseek']})

@app.route('/api/ai/test', methods=['POST'])
def api_ai_test():
    data = request.get_json(silent=True) or {}
    text = str(data.get('text') or '请用一句话说明广州太古汇舆情监测系统正在监测什么。').strip()[:1200]
    # AI 治理：额度检查
    allowed, quota = ai_governance._usage_tracker.check_quota()
    if not allowed:
        return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota}), 429
    # AI 治理：脱敏
    desensitized_text, mapping = ai_governance.desensitize_text(text)
    result = intelligence.test_connection(desensitized_text)
    # AI 治理：回传补回实体
    if isinstance(result, dict) and 'reply' in result:
        result['reply'] = ai_governance.restore_text(str(result['reply']), mapping)
    # AI 治理：记录使用统计
    ai_governance.record_ai_call('ai/test', prompt_tokens=len(text)//2,
                                   completion_tokens=len(str(result.get('reply','')))//2 if isinstance(result, dict) else 0,
                                   total_tokens=len(text)//2, provider=result.get('provider','zhipu') if isinstance(result, dict) else 'zhipu',
                                   success=True)
    # AI 治理：输出标记
    marked = ai_governance.mark_ai_output(result if isinstance(result, dict) else {'result': result},
                                             provider=result.get('provider','zhipu') if isinstance(result, dict) else 'zhipu',
                                             endpoint='ai/test')
    return jsonify(marked)

# ========== 豆包AI API（ark_llm）- 可选辅助功能 ==========
# 【S1 2026-09-02】云智(ARK)已停用，改用智谱(zhipu)驱动（intelligence 网关）。
# 保留路由名/响应结构与前端兼容；provider 字段标记真实来源（zhipu/local/rule）。
@app.route('/api/ark/status')
def api_ark_status():
    """AI API状态查询（智谱驱动）"""
    try:
        st = intelligence.ai_status()
        return jsonify({'ok': True, 'enabled': st.get('enabled'), 'provider': st.get('provider'),
                        'model': st.get('model'), 'runtime': st.get('runtime'),
                        'detail': st.get('detail', '')})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'provider': 'local_rule', 'enabled': False}), 500

@app.route('/api/ark/chat', methods=['POST'])
def api_ark_chat():
    """AI通用聊天（智谱驱动+AI治理：脱敏回传/额度控制/使用统计/输出标记）"""
    try:
        data = request.get_json(silent=True) or {}
        message = str(data.get('message') or data.get('text') or '').strip()
        if not message:
            return jsonify({'ok': False, 'error': '消息不能为空'}), 400
        system_prompt = data.get('system_prompt')
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota, 'fallback': 'local'}), 429
        # AI 治理：脱敏
        desensitized_msg, mapping = ai_governance.desensitize_text(message)
        raw, provider = intelligence._chat(system_prompt or '你是广州太古汇舆情监测系统的智能助手', desensitized_msg, 0.15, 1800)
        # AI 治理：回传补回实体
        reply = ai_governance.restore_text(raw.strip() if raw else 'AI引擎已就绪', mapping)
        # AI 治理：记录使用统计
        ai_governance.record_ai_call('ark/chat', prompt_tokens=len(message)//2,
                                       completion_tokens=len(reply)//2,
                                       total_tokens=(len(message)+len(reply))//2,
                                       provider=provider or 'local_rule', success=True)
        # AI 治理：输出标记
        result = ai_governance.mark_ai_output(
            {'ok': True, 'reply': reply, 'provider': provider or 'local_rule',
             'fallback': provider in ('rule', 'local_rule'), 'desensitized': bool(mapping)},
            provider=provider or 'local_rule', endpoint='ark/chat')
        return jsonify(result)
    except Exception as e:
        ai_governance.record_ai_call('ark/chat', provider='zhipu', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ark/sentiment', methods=['POST'])
def api_ark_sentiment():
    """AI舆情分析（智谱驱动+AI治理：脱敏回传/额度控制/使用统计/输出标记）"""
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get('text') or data.get('content') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': '文本不能为空'}), 400
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota}), 429
        # AI 治理：脱敏
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        result = intelligence.analyze_sentiment(desensitized_text)
        # AI 治理：回传补回实体
        if result.get('summary'):
            result['summary'] = ai_governance.restore_text(str(result['summary']), mapping)
        # AI 治理：记录使用统计
        ai_governance.record_ai_call('ark/sentiment', prompt_tokens=len(text)//2,
                                       completion_tokens=len(str(result.get('summary','')))//2,
                                       total_tokens=len(text)//2,
                                       provider=result.get('provider','zhipu'), success=True)
        # AI 治理：输出标记
        marked = ai_governance.mark_ai_output(
            {'ok': True, 'sentiment': result.get('sentiment'), 'label': result.get('label'),
             'summary': result.get('summary'), 'keywords': result.get('keywords'),
             'provider': result.get('provider'), 'fallback': result.get('provider') == 'rule',
             'desensitized': bool(mapping)},
            provider=result.get('provider','zhipu'), endpoint='ark/sentiment')
        return jsonify(marked)
    except Exception as e:
        ai_governance.record_ai_call('ark/sentiment', provider='zhipu', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ark/summary', methods=['POST'])
def api_ark_summary():
    """AI摘要生成（智谱驱动+AI治理：脱敏回传/额度控制/使用统计/输出标记）"""
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get('text') or data.get('content') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': '文本不能为空'}), 400
        max_length = data.get('max_length', 200)
        try:
            max_length = int(max_length)
        except Exception:
            max_length = 200
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota, 'fallback': 'local'}), 429
        # AI 治理：脱敏（敏感实体→占位符）
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        # 调用智谱
        summary = intelligence.generate_summary(desensitized_text, max_length=max_length)
        # AI 治理：回传补回实体
        summary = ai_governance.restore_text(summary, mapping)
        # AI 治理：记录使用统计
        ai_governance.record_ai_call('ark/summary', prompt_tokens=len(text)//2,
                                       completion_tokens=len(summary)//2,
                                       total_tokens=(len(text)+len(summary))//2,
                                       provider='zhipu', success=True)
        # AI 治理：输出标记（增强层，非 System Truth，可用于 Zachary 学习）
        result = ai_governance.mark_ai_output(
            {'ok': True, 'summary': summary, 'desensitized': bool(mapping),
             'quota_remaining': quota['call_remaining']},
            provider='zhipu', endpoint='ark/summary')
        return jsonify(result)
    except Exception as e:
        ai_governance.record_ai_call('ark/summary', provider='zhipu', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ark/keywords', methods=['POST'])
def api_ark_keywords():
    """AI关键词提取（智谱驱动+AI治理：脱敏回传/额度控制/使用统计/输出标记）"""
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get('text') or data.get('content') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': '文本不能为空'}), 400
        num_keywords = data.get('num_keywords', 10)
        try:
            num_keywords = int(num_keywords)
        except Exception:
            num_keywords = 10
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            # 额度超限直接回退本地
            topics = ai_analyzer.extract_topics(text, '')
            return jsonify({'ok': True, 'keywords': topics, 'provider': 'local',
                            'fallback': True, 'quota_exceeded': True}), 200
        # AI 治理：脱敏
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        # 调用智谱
        keywords = intelligence.extract_keywords(desensitized_text, num_keywords=num_keywords)
        if keywords:
            # AI 治理：回传补回实体（关键词列表）
            restored_keywords = [ai_governance.restore_text(kw, mapping) for kw in keywords]
            ai_governance.record_ai_call('ark/keywords', prompt_tokens=len(text)//2,
                                           completion_tokens=sum(len(k) for k in restored_keywords)//2,
                                           total_tokens=(len(text)+sum(len(k) for k in restored_keywords))//2,
                                           provider='zhipu', success=True)
            result = ai_governance.mark_ai_output(
                {'ok': True, 'keywords': restored_keywords, 'desensitized': bool(mapping),
                 'quota_remaining': quota['call_remaining']},
                provider='zhipu', endpoint='ark/keywords')
            return jsonify(result)
        # 回退本地规则提取
        topics = ai_analyzer.extract_topics(text, '')
        ai_governance.record_ai_call('ark/keywords', provider='local', success=True)
        return jsonify({'ok': True, 'keywords': topics, 'provider': 'local', 'fallback': True})
    except Exception as e:
        ai_governance.record_ai_call('ark/keywords', provider='zhipu', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== 采集器自动化 API ==========
@app.route('/api/collector/browser/start', methods=['POST'])
def api_collector_browser_start():
    """手动启动浏览器"""
    try:
        data = request.get_json(silent=True) or {}
        account = data.get('account', 'default')
        headless = data.get('headless', False)
        
        collector = collector_automation.get_collector_automation()
        collector.start_browser(account=account, headless=headless)
        return jsonify({'ok': True, 'message': '浏览器已启动'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/collector/browser/stop', methods=['POST'])
def api_collector_browser_stop():
    """手动关闭浏览器"""
    try:
        collector = collector_automation.get_collector_automation()
        collector.stop_browser()
        return jsonify({'ok': True, 'message': '浏览器已关闭'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== 双子星库 Contract · XHS Runtime 统一预检 & 双身份切换 ==========
@app.route('/api/xhs/runtime-check', methods=['GET', 'POST'])
def api_xhs_runtime_check():
    """XHS 运行时七态预检（前端轮询用）。

    query/body:
      account: 可选 · 显式指定要预检的身份（XHS_CN_PRIMARY / XHS_RETINAUT）
      quick:   可选 · 1/true 时跳过 CDP 端口 ping，用于高频轮询节省开销
    字段结构: ok / overall_state / checks[7] / account_status / circuit /
              active_account / allowed_accounts / cdp_online / user_paused / state_machine / evidence
    """
    try:
        data = {}
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
        account = (request.args.get('account') or data.get('account') or '').strip() or None
        quick = str(request.args.get('quick', '') or data.get('quick', '')).lower() in ('1', 'true', 'yes', 'on')
        # 按逻辑身份解析驻场端口（大陆9222/香港9223）；显式 XHS_CDP_URL 仍最优先
        cdp_url = os.getenv('XHS_CDP_URL') or xhs_cookie_bridge.cdp_url_for(account)
        result = xhs_cookie_bridge.runtime_preflight_check(account=account, cdp_url=cdp_url, quick=quick)
        # overall_state 对应 Auth Recovery Center：
        #   no_cookie / need_account / blocked → 需要前端弹扫码 / 验证入口
        #   ready / cooldown / user_paused → 正常态提示
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e),
                        'overall_state': 'error',
                        'evidence': f'XHS Runtime 预检异常：{type(e).__name__}: {str(e)[:200]}'}), 500


@app.route('/api/xhs/switch-account', methods=['POST'])
def api_xhs_switch_account():
    """双子星库 Contract：切换采集身份（硬白名单）。

    body:
      account: 必填 · XHS_CN_PRIMARY / XHS_RETINAUT 之一
    成功 → 设置模块级身份 + 环境变量；下次采集/同步自动使用。
    失败 → 保留原身份不动，返回友好错误（绝不静默切到其他身份）。
    """
    try:
        data = request.get_json(silent=True) or {}
        account = (data.get('account') or '').strip()
        if not account:
            return jsonify({'ok': False, 'error': '缺少 account 参数，必须显式指定双子星库白名单身份'}), 400
        ok_sel, msg_sel = xhs_cookie_bridge.select_account(account)
        if not ok_sel:
            return jsonify({'ok': False, 'error': msg_sel,
                            'allowed_accounts': list(xhs_cookie_bridge.ACCOUNT_PROFILES.keys())}), 400
        # 切换完成后再跑一次 quick 预检返回
        status = xhs_cookie_bridge.get_account_status()
        return jsonify({'ok': True,
                        'message': msg_sel,
                        'active_account': status.get('active_account'),
                        'allowed_accounts': list(xhs_cookie_bridge.ACCOUNT_PROFILES.keys()),
                        'account_status': status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/xhs/accounts', methods=['GET'])
def api_xhs_accounts():
    """双子星库 Contract：双身份白名单列表（前端身份切换 UI 源）。

    返回 allowed_accounts 逻辑名 + 每个身份的配置状态：
      - cookie_ready：Cookie 文件存在且非空
      - user_id_match：user_id 是否落在物理白名单里
      - can_use：是否可实际采集
      - active: 是否当前激活身份
    绝不返回真实 user_id 明文或 cookie 内容，仅返回是否命中 + 前 12 位预览。
    """
    try:
        import os as _os
        active = getattr(xhs_cookie_bridge, '_ACTIVE_ACCOUNT', None) or xhs_cookie_bridge.XHS_CN_PRIMARY_NAME
        accounts = []
        for name, (cookie_path, cdp_profile_dir) in xhs_cookie_bridge.ACCOUNT_PROFILES.items():
            c_ready = bool(cookie_path and _os.path.isfile(cookie_path) and
                           open(cookie_path, encoding='utf-8', errors='replace').read().strip())
            current_uid = None
            try:
                # 仅当身份为激活时读生效路径才是该身份的 uid；非激活身份临时切读
                if name != active:
                    override_bak = _os.environ.get('XHS_COOKIE_FILE_OVERRIDE', '')
                    _os.environ['XHS_COOKIE_FILE_OVERRIDE'] = str(cookie_path or '')
                    current_uid = xhs_cookie_bridge._get_current_user_id()
                    if override_bak: _os.environ['XHS_COOKIE_FILE_OVERRIDE'] = override_bak
                    elif 'XHS_COOKIE_FILE_OVERRIDE' in _os.environ: del _os.environ['XHS_COOKIE_FILE_OVERRIDE']
                else:
                    current_uid = xhs_cookie_bridge._get_current_user_id()
            except Exception:
                current_uid = None
            id_match = bool(current_uid and current_uid in xhs_cookie_bridge.ALLOWED_USER_IDS)
            _cdp_port = xhs_cookie_bridge.cdp_port_for(name)
            _cdp_online = False
            try:
                import socket as _sock
                with _sock.create_connection(('127.0.0.1', _cdp_port), timeout=0.4):
                    _cdp_online = True
            except Exception:
                _cdp_online = False
            accounts.append({
                'account': name,
                'active': (name == active),
                'cookie_ready': c_ready,
                'user_id_match': id_match,
                'user_id_preview': (current_uid[:12] + '...') if current_uid else None,
                'can_use': (c_ready and id_match),
                'cdp_port': _cdp_port,
                'cdp_online': _cdp_online,
                'cdp_profile_dir_exist': bool(cdp_profile_dir and _os.path.isdir(cdp_profile_dir)),
            })
        return jsonify({
            'ok': True,
            'active_account': active,
            'allowed_accounts': list(xhs_cookie_bridge.ACCOUNT_PROFILES.keys()),
            'accounts': accounts,
            'allowed_user_ids_preview': [x[:12] + '...' for x in xhs_cookie_bridge.ALLOWED_USER_IDS],
            'contract_version': 'Z-Brand-Core · 双子星库 Contract v1.0（仅 XHS_CN_PRIMARY + XHS_RETINAUT）',
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== Zachary OS AI · Resident Browser Health Monitor API ==========
@app.route('/api/resident/health', methods=['GET'])
def api_resident_health():
    """双身份驻场浏览器健康状态查询（三层：端口→CDP→登录态）。

    Query:
      account=XHS_CN_PRIMARY|XHS_RETINAUT  只查指定身份（缺省=全部）
      cache=1                                 只读上次持久化结果，不实时探测
    绝不返回 cookie 值，仅返回存在性/数量/状态分级。
    """
    try:
        import resident_health as rh
        account = request.args.get('account') or None
        use_cache = request.args.get('cache') in ('1', 'true', 'yes')
        if use_cache:
            return jsonify({'ok': True, 'cached': True, 'result': rh.status(use_cache=True)})
        if account:
            return jsonify({'ok': True, 'account': account, 'result': rh.check_account(account)})
        return jsonify({'ok': True, 'result': rh.check_all()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/resident/recover', methods=['POST'])
def api_resident_recover():
    """手动触发驻场浏览器自动恢复（DOWN/CDP_DEGRADED 时拉起；NEEDS_LOGIN 不自动恢复，需人工扫码）。

    Body JSON: {account: XHS_CN_PRIMARY|XHS_RETINAUT|null(全部), force: bool}
    恢复动作委托 scripts/start_resident_browsers.py（幂等），连续恢复超 3 次标记 UNRECOVERABLE。
    """
    try:
        import resident_health as rh
        data = request.get_json(silent=True) or {}
        account = data.get('account') or None
        force = bool(data.get('force', False))
        if account:
            return jsonify({'ok': True, 'account': account, 'result': rh.recover_account(account, force=force)})
        return jsonify({'ok': True, 'result': rh.recover_all(force=force)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ========== AI学习引擎与全网舆情检索 API ==========
@app.route('/api/ai-learning/status')
def api_ai_learning_status():
    """AI学习状态查询"""
    try:
        engine = ai_learning_engine.get_ai_learning_engine()
        status = engine.get_learning_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-learning/optimization/<operation_type>')
def api_ai_learning_optimization(operation_type):
    """获取操作优化建议"""
    try:
        engine = ai_learning_engine.get_ai_learning_engine()
        suggestion = engine.get_optimization_suggestion(operation_type)
        return jsonify({'ok': True, 'operation_type': operation_type, 'suggestion': suggestion})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/web-sentiment/search', methods=['POST'])
def api_web_sentiment_search():
    """全网舆情检索（使用豆包AI）"""
    try:
        data = request.get_json(silent=True) or {}
        keywords = data.get('keywords')
        platform = data.get('platform', 'all')
        limit = data.get('limit', 20)
        
        search = ai_learning_engine.get_web_sentiment_search()
        result = search.search_public_opinion(keywords=keywords, platform=platform, limit=limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/web-sentiment/history')
def api_web_sentiment_history():
    """全网舆情检索历史"""
    try:
        limit = request.args.get('limit', 20, type=int)
        search = ai_learning_engine.get_web_sentiment_search()
        history = search.get_search_history(limit=limit)
        return jsonify({'ok': True, 'history': history})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== 全网舆情案例数据库 API ==========
@app.route('/api/cases/stats')
def api_cases_stats():
    """舆情案例统计"""
    try:
        db = public_opinion_cases.get_case_db()
        stats = db.get_stats()
        return jsonify({'ok': True, **stats})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/list')
def api_public_cases_list():
    """舆情案例列表"""
    try:
        case_type = request.args.get('type')
        risk_level = request.args.get('risk')
        category = request.args.get('category')
        limit = request.args.get('limit', 100, type=int)
        
        db = public_opinion_cases.get_case_db()
        cases = db.get_cases(case_type=case_type, risk_level=risk_level, 
                            category=category, limit=limit)
        return jsonify({'ok': True, 'cases': cases, 'count': len(cases)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/import', methods=['POST'])
def api_cases_import():
    """导入舆情案例（重新导入所有案例）"""
    try:
        db = public_opinion_cases.get_case_db()
        count = db.import_all_cases()
        return jsonify({'ok': True, 'imported_count': count, 'message': f'成功导入{count}个案例'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/taikoo-hui')
def api_cases_taikoo_hui():
    """广州太古汇舆情案例"""
    try:
        db = public_opinion_cases.get_case_db()
        cases = db.get_cases(case_type='taikoo_hui', limit=50)
        return jsonify({'ok': True, 'cases': cases, 'count': len(cases)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/other-malls')
def api_cases_other_malls():
    """其他商业地产舆情案例"""
    try:
        db = public_opinion_cases.get_case_db()
        cases = db.get_cases(case_type='other_mall', limit=50)
        return jsonify({'ok': True, 'cases': cases, 'count': len(cases)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/brands')
def api_cases_brands():
    """品牌业态舆情案例"""
    try:
        db = public_opinion_cases.get_case_db()
        cases = db.get_cases(case_type='brand', limit=50)
        return jsonify({'ok': True, 'cases': cases, 'count': len(cases)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ========== 前端兼容路由别名 ==========

@app.route('/api/brand-industry/brands')
def api_brand_industry_brands_alias():
    """品牌业态-品牌列表（前端兼容）"""
    try:
        limit = request.args.get('limit', 50, type=int)
        with db.get_db() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM brand_industry_monitor ORDER BY note_count DESC LIMIT ?", (limit,)).fetchall()
            brands = [dict(r) for r in rows]
        return jsonify({'ok': True, 'brands': brands, 'count': len(brands)})
    except Exception as e:
        return jsonify({'ok': True, 'brands': [], 'count': 0, 'error': str(e)})

@app.route('/api/brand-industry/brands/<path:name>')
def api_brand_industry_brand_detail(name):
    """品牌业态-单品牌详情：基础信息 + 实时匹配该品牌的笔记统计与最近笔记"""
    try:
        with db.get_db() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM brand_industry_monitor WHERE brand_name_cn=? OR brand_name=? OR brand_name_cn LIKE ? OR brand_name LIKE ? LIMIT 1",
                (name, name, f"%{name}%", f"%{name}%")).fetchone()
            if not row:
                return jsonify({'ok': False, 'error': '品牌不存在'}), 404
            brand = dict(row)
            cn = (brand.get('brand_name_cn') or '').strip()
            en = (brand.get('brand_name') or '').strip()
            # 用品牌中/英文名在标题、正文、摘要中匹配（英文名过短易误匹配，要求长度>=3）
            keys = [k for k in [cn] if k]
            if len(en) >= 3:
                keys.append(en)
            where = " OR ".join(["(title LIKE ? OR content LIKE ? OR summary LIKE ? OR body LIKE ?)" for _ in keys])
            params = []
            for k in keys:
                params += [f"%{k}%"] * 4
            notes = []
            total = pos = neg = 0
            if keys:
                rows = conn.execute(
                    f"SELECT note_id,title,author_nickname,publish_date,sentiment,risk_level,likes,comments,url FROM notes WHERE {where} ORDER BY publish_date DESC LIMIT 30",
                    params).fetchall()
                notes = [dict(r) for r in rows]
                total = len(notes)
                pos = sum(1 for n in notes if n['sentiment'] == 'positive')
                neg = sum(1 for n in notes if n['sentiment'] == 'negative')
            # 字段对齐前端 viewBrand
            brand.update({
                'name': cn or en or name,
                'category': brand.get('industry') or '未分类',
                'total_notes': total,
                'positive': pos,
                'negative': neg,
                'neutral': total - pos - neg,
                'recent_notes': notes[:10],
            })
        return jsonify({'ok': True, 'brand': brand})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/brand-industry/stats')
def api_brand_industry_stats_alias():
    """品牌业态-统计（前端兼容）"""
    try:
        with db.get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor").fetchone()[0]
            industries = conn.execute("SELECT industry, COUNT(*) as cnt FROM brand_industry_monitor GROUP BY industry ORDER BY cnt DESC").fetchall()
            # 统计有负面/正面笔记的品牌数
            neg_brands = conn.execute("SELECT COUNT(DISTINCT brand_name_cn) FROM brand_industry_monitor WHERE negative_count > 0").fetchone()[0]
            pos_brands = conn.execute("SELECT COUNT(DISTINCT brand_name_cn) FROM brand_industry_monitor WHERE positive_count > 0").fetchone()[0]
            cat_count = len(industries)
        return jsonify({'ok': True, 'total': total, 'total_brands': total,
                        'negative': neg_brands, 'negative_brands': neg_brands,
                        'positive': pos_brands, 'positive_brands': pos_brands,
                        'categories': cat_count,
                        'industries': [dict(r) for r in industries]})
    except Exception as e:
        return jsonify({'ok': True, 'total': 0, 'total_brands': 0, 'negative': 0, 'positive': 0, 'categories': 0, 'industries': [], 'error': str(e)})

@app.route('/api/brand-industry/recompute', methods=['POST'])
def api_brand_industry_recompute():
    """品牌业态统计一键重算：用实时 LIKE 口径刷新预聚合字段，修复历史统计污染"""
    try:
        from brand_stats_recompute import recompute_brand_stats
        result = recompute_brand_stats(verbose=False)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/negative-review/stats')
def api_negative_review_stats():
    """负面审核统计"""
    try:
        with db.get_db() as conn:
            # 与负面审核列表同口径：仅太古汇主体、非重复非噪音的负面，避免全网案例混入导致数字与列表不一致
            clause, sp = _subject_sql_and_values(); sp = tuple(sp)
            base = f"sentiment='negative' AND COALESCE(is_duplicate,0)=0 AND COALESCE(noise_type,'')='' AND {clause}"
            total = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base}", sp).fetchone()[0]
            confirmed = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base} AND negative_confirmed=1", sp).fetchone()[0]
            rejected = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base} AND negative_confirmed=2", sp).fetchone()[0]
            pending = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base} AND (negative_confirmed=0 OR negative_confirmed IS NULL)", sp).fetchone()[0]
            high_risk = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base} AND risk_level='high'", sp).fetchone()[0]
        return jsonify({'ok': True, 'total': total, 'confirmed': confirmed, 'rejected': rejected, 'pending': pending, 'high_risk': high_risk})
    except Exception as e:
        return jsonify({'ok': True, 'total': 0, 'confirmed': 0, 'rejected': 0, 'pending': 0, 'high_risk': 0, 'error': str(e)})

@app.route('/api/reports')
def api_reports_list():
    """报告列表"""
    try:
        limit = request.args.get('limit', 10, type=int)
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'reports')
        reports = []
        if os.path.exists(report_dir):
            for f in sorted(os.listdir(report_dir), reverse=True)[:limit]:
                fpath = os.path.join(report_dir, f)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    reports.append({'name': f, 'size': stat.st_size, 'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')})
        return jsonify({'ok': True, 'reports': reports, 'count': len(reports)})
    except Exception as e:
        return jsonify({'ok': True, 'reports': [], 'count': 0, 'error': str(e)})

@app.route('/api/reports/<path:report_id>/download')
def api_report_download(report_id):
    """报告下载-取下载链接（前端 downloadReport 契约：返回 download_url）"""
    safe = os.path.basename(report_id)
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'reports')
    if not os.path.isfile(os.path.join(report_dir, safe)):
        return jsonify({'ok': False, 'error': '报告不存在'}), 404
    from urllib.parse import quote
    return jsonify({'ok': True, 'download_url': f'/api/reports/{quote(safe)}/file', 'name': safe})

@app.route('/api/reports/<path:report_id>/file')
def api_report_file(report_id):
    """报告文件实际下载"""
    safe = os.path.basename(report_id)
    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'reports')
    if not os.path.isfile(os.path.join(report_dir, safe)):
        return jsonify({'ok': False, 'error': '报告不存在'}), 404
    return send_from_directory(report_dir, safe, as_attachment=True)

# ===== GAP-04 三套 run-code 统一安全收口（单一安全策略，2026-09-01）=====
# 生产默认禁用服务端任意代码执行/写静态文件，消除 RCE 与持久化注入面；
# 仅本地开发显式 ZBC_DEV_EXEC=1 放行，且仍拦截危险构造并打印审计行。三入口统一走此闸门，
# 路由保留（前端得到明确 403 契约而非 404），不删除历史能力。
_DEV_EXEC_ENABLED = os.environ.get('ZBC_DEV_EXEC', '0') == '1'
_DEV_EXEC_BLOCK_RE = re.compile(
    r'(__[\w_]+__|\b(?:import|exec|eval|compile|open|globals|locals|vars|getattr|setattr|delattr|breakpoint)\b'
    r'|os\.|sys\.|subprocess|socket|shutil|pathlib|\.write(?:_text|_bytes)?\s*\(|rmtree|(?:unlink|remove)\s*\('
    r'|environ|urllib|requests\.|http\.client|pickle)',
    re.I)

def _dev_exec_guard(code):
    """统一代码执行闸门：None=放行(仅开发态)；否则返回 (response,403/400)。"""
    if not _DEV_EXEC_ENABLED:
        return jsonify({'ok': False, 'code': 'DEV_EXEC_DISABLED',
                        'error': '生产环境已禁用服务端任意代码执行/写文件（GAP-04 安全收口）；本地热更请显式设置 ZBC_DEV_EXEC=1',
                        'version': APP_VERSION}), 403
    if code is None or not str(code).strip():
        return jsonify({'ok': False, 'error': '代码不能为空'}), 400
    if _DEV_EXEC_BLOCK_RE.search(str(code)):
        print('[SEC][GAP-04] dev-exec blocked dangerous construct')
        return jsonify({'ok': False, 'code': 'DEV_EXEC_DANGEROUS',
                        'error': '开发态仍拦截危险构造（import/exec/eval/文件写/网络/反射等），请改用受控 API'}), 400
    return None

@app.route('/api/developer/run', methods=['POST'])
def api_developer_run():
    """GAP-04 统一收口点①（兼容保留）：生产永久禁用，开发态走统一闸门。"""
    data = request.get_json(silent=True) or {}
    guarded = _dev_exec_guard(data.get('code', ''))
    if guarded:
        return guarded
    return jsonify({'ok': False, 'code': 'DEV_EXEC_DISABLED',
                    'error': '该入口为兼容保留端点，生产不执行任意代码', 'version': APP_VERSION}), 403


@app.route('/api/settings')
def api_settings_get():
    """系统设置（前端兼容）"""
    try:
        config = {
            'version': APP_VERSION,
            'auto_collect': True,
            'collector_type': 'Playwright/XHS search + rednote CDP',
            'auth_enabled': bool(AUTH_USER and AUTH_PASSWORD),
            'ai_enabled': ARK_LLM_AVAILABLE,
        }
        return jsonify({'ok': True, 'settings': config})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/search', methods=['GET', 'POST'])
def api_unified_search():
    q = request.args.get('q','') if request.method=='GET' else str((request.get_json(silent=True) or {}).get('q',''))
    try: limit=max(1,min(30,int(request.args.get('limit',12))))
    except Exception: limit=12
    return jsonify(function_registry.search_targets(q, db=db, limit=limit))

@app.route('/api/function-map')
def api_function_map():
    return jsonify({'ok':True,'functions':function_registry.FUNCTION_MAP})

@app.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    data=request.get_json(silent=True) or {}
    text=str(data.get('message') or data.get('text') or '').strip()[:4000]
    if not text: return jsonify({'ok':False,'error':'问题不能为空'}),400
    context=function_registry.build_context(text, db)
    try: stats=db.get_stats()
    except Exception: stats={}
    history=data.get('history') or []
    if not isinstance(history,list): history=[]
    history_text=[]
    for item in history[-6:]:
        if isinstance(item,dict):
            role='用户' if item.get('role') in ('user','human') else '诺米'
            content=str(item.get('content') or '')[:800]
            if content: history_text.append(f'{role}：{content}')
    system='你是广州太古汇舆情监测系统的智能助手“诺米”。你拥有系统结构化检索能力。必须优先依据检索结果回答，不编造数据库事实；涉及舆情事实时明确区分“系统已监测”“用户描述”“待核验”。可以回答系统操作、品牌/业态、品牌官网、案例、公关回复、风险分析、报告、事件与架构问题。需要处置建议时使用：判断→依据→动作→责任方/时限→复盘指标。若没有足够数据，明确告诉用户缺什么，不要用常识冒充系统数据。'
    user=f'用户问题：{text}\n\n函数与数据检索结果：\n{context}\n\n当前统计：{json.dumps(stats,ensure_ascii=False,default=str)[:5000]}'
    if history_text: user += '\n\n最近对话：\n' + '\n'.join(history_text)
    try: raw,provider=intelligence._chat(system,user,0.15,1800)
    except Exception as exc: raw,provider=None,'rule'; print('[Nomi] chat failed:',exc)
    status=intelligence.ai_status()
    if raw: return jsonify({'ok':True,'reply':raw.strip(),'provider':provider,'ai_status':status,'context':context})
    fallback='我已完成系统检索，但当前可调用模型暂不可用。\n\n' + context
    return jsonify({'ok':True,'reply':fallback,'provider':'local_rule','ai_status':status,'context':context})

@app.route('/api/translate',methods=['POST'])
def api_translate():
    data=request.get_json(silent=True) or {}; text=str(data.get('text','')); target=str(data.get('target','en')).lower()
    if target not in ('zh','en','ko'): return jsonify({'ok':False,'error':'target 仅支持 zh/en/ko'}),400
    if not text: return jsonify({'ok':False,'error':'text不能为空'}),400
    if target=='zh': return jsonify({'ok':True,'target':'zh','text':text})
    if not intelligence.ai_enabled(): return jsonify({'ok':False,'error':'未配置AI provider/API Key'}),503
    return jsonify({'ok':True,'target':target,'text':intelligence.translate_text(text,target)})

@app.route('/api/report/<report_type>')
def api_report(report_type):
    # 避免与 /api/report/export 路由冲突
    if report_type == 'export':
        try:
            return api_report_export()
        except Exception as e:
            import traceback
            return jsonify({'ok': False, 'error': '导出函数调用失败: ' + str(e), 'traceback': traceback.format_exc()}), 500
    if report_type not in report_engine.REPORT_TYPES: return jsonify({'ok':False,'error':'无效报告类型'}),400
    try:
        bundle=report_engine.get_bundle(report_type, request.args.get('date') or None)
        return jsonify({'ok':bool(bundle.get('report')),'report':bundle.get('report'),'digest':bundle.get('digest'),'report_type':report_type})
    except Exception as exc:
        return jsonify({'ok':False,'error':str(exc)}),500

@app.route('/api/report/generate',methods=['POST'])
def api_generate_report():
    try:
        result=_generate_all_reports()
        return jsonify({'ok':True,'message':'日报/周报/月报/年报已生成','reports':result})
    except Exception as exc:
        return jsonify({'ok':False,'error':str(exc)}),500

# ===== 优化版报告API（v2）：按发布日期筛选，周期报告负面必须二次确认 =====
@app.route('/api/report/v2/<report_type>')
def api_report_v2(report_type):
    """优化版报告API
    - 日报：只包含当日或前一日发布的笔记（按publish_date筛选）
    - 周报/月报/年报：负面笔记必须是二次确认的（negative_confirmed=1）
    - 过期笔记：标记为历史案例，不进入日报
    """
    if report_type not in ('daily', 'weekly', 'monthly', 'yearly'):
        return jsonify({'ok': False, 'error': '无效报告类型'}), 400
    
    try:
        from report_filter import get_report_period, filter_notes_for_daily_report, filter_negative_for_period_report, classify_notes_by_age, get_daily_report_filter_stats
        
        date_str = request.args.get('date')
        start, end = get_report_period(report_type)
        
        # 获取该时间段内的所有笔记（按采集时间）
        all_notes = db.get_notes_by_date_range(start, end)
        
        if report_type == 'daily':
            # 日报：按发布日期筛选，只包含当日或前一日发布的笔记
            filtered_notes = filter_notes_for_daily_report(all_notes, include_yesterday=True)
            filter_stats = get_daily_report_filter_stats(all_notes)
            # 日报的负面笔记不要求二次确认（因为日报需要及时推送）
            _, negative_notes = filter_negative_for_period_report(filtered_notes, require_confirmed=False)
        else:
            # 周报/月报/年报：负面笔记必须是二次确认的
            filtered_notes = all_notes  # 周期报告不按发布日期筛选，按采集时间
            filter_stats = {'total_collected': len(all_notes)}
            _, negative_notes = filter_negative_for_period_report(filtered_notes, require_confirmed=True)
        
        # 按发布时间分类
        age_classification = classify_notes_by_age(all_notes)
        
        # 生成统计
        total = len(filtered_notes)
        positive = sum(1 for n in filtered_notes if n.get('sentiment') == 'positive')
        neutral = sum(1 for n in filtered_notes if n.get('sentiment') == 'neutral')
        negative_count = len(negative_notes)
        high_risk = sum(1 for n in filtered_notes if n.get('risk_level') == 'high')
        
        return jsonify({
            'ok': True,
            'report_type': report_type,
            'period': {'start': start, 'end': end},
            'filter_stats': filter_stats,
            'age_classification': {
                'recent': len(age_classification['recent']),
                'weekly': len(age_classification['weekly']),
                'monthly': len(age_classification['monthly']),
                'historical': len(age_classification['historical'])
            },
            'stats': {
                'total': total,
                'positive': positive,
                'neutral': neutral,
                'negative': negative_count,
                'negative_confirmed_required': report_type != 'daily',
                'high_risk': high_risk
            },
            'notes': filtered_notes[:100],  # 最多返回100条
            'negative_notes': negative_notes[:50],  # 二次确认的负面笔记
            'historical_notes': age_classification['historical'][:50]  # 历史案例笔记
        })
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/report/v2/stats')
def api_report_v2_stats():
    """报告筛选统计API"""
    try:
        from report_filter import get_daily_report_filter_stats, classify_notes_by_age
        
        # 获取最近7天的笔记
        from datetime import datetime, timedelta
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        all_notes = db.get_notes_by_date_range(start, end)
        
        daily_stats = get_daily_report_filter_stats(all_notes)
        age_classification = classify_notes_by_age(all_notes)
        
        # 负面确认统计
        negative_total = sum(1 for n in all_notes if n.get('sentiment') == 'negative')
        negative_confirmed = sum(1 for n in all_notes if n.get('sentiment') == 'negative' and n.get('negative_confirmed') == 1)
        negative_pending = sum(1 for n in all_notes if n.get('sentiment') == 'negative' and (n.get('negative_confirmed') == 0 or n.get('negative_confirmed') is None))
        
        return jsonify({
            'ok': True,
            'daily_filter': daily_stats,
            'age_classification': {
                'recent_2days': len(age_classification['recent']),
                'within_7days': len(age_classification['weekly']),
                'within_30days': len(age_classification['monthly']),
                'historical_over_30days': len(age_classification['historical'])
            },
            'negative_confirmation': {
                'total': negative_total,
                'confirmed': negative_confirmed,
                'pending': negative_pending,
                'confirmation_rate': round(negative_confirmed / negative_total * 100, 1) if negative_total > 0 else 0
            },
            'logic_explanation': {
                'daily_report': '只包含当日或前一日发布的笔记，过期笔记放入历史案例库',
                'weekly_monthly_yearly': '负面笔记必须是二次确认的（negative_confirmed=1）才能进入报告',
                'historical_notes': '发布时间超过7天的笔记标记为历史案例，不进入日报，但可在笔记库查看'
            }
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/notes/historical')
def api_notes_historical_v2():
    """历史案例笔记API v2（过期笔记，发布时间超过7天）"""
    try:
        from report_filter import classify_notes_by_age
        from datetime import datetime, timedelta
        
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        all_notes = db.get_notes_by_date_range(start, end)
        
        age_classification = classify_notes_by_age(all_notes)
        historical = age_classification['historical']
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        return jsonify({
            'ok': True,
            'total': len(historical),
            'page': page,
            'per_page': per_page,
            'notes': historical[start_idx:end_idx],
            'description': '历史案例笔记：发布时间超过7天，不进入日报，但可作为案例参考'
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500





@app.route('/api/platform-health')
def api_platform_health():
    """全局采集健康状态中心（只读）：逐平台状态 + 三类分清 + 动态调度，供首页健康小点与统一 Auth Modal。"""
    try:
        from platform_adapters.health_center import build_platform_health
        return jsonify(build_platform_health())
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 500

# ========== 网络自适应 & 本地缓存降级 API ==========
@app.route('/api/network/status')
def api_network_status():
    import network_adaptive
    return jsonify({'ok':True, **network_adaptive.get_network_status()})

@app.route('/api/network/reset', methods=['POST'])
def api_network_reset():
    import network_adaptive
    status = network_adaptive.reset_network_status()
    return jsonify({'ok':True, 'message':'网络状态已重置', **status})

@app.route('/api/cache/status')
def api_cache_status():
    import cache_manager
    return jsonify({'ok':True, **cache_manager.get_cache_status()})

@app.route('/api/cache/data')
def api_cache_data():
    import cache_manager
    query_type = request.args.get('type', 'stats')
    limit = request.args.get('limit', 50, type=int)
    result = cache_manager.get_cached_data(query_type, limit)
    return jsonify({'ok':True, **result})

@app.route('/api/cache/create', methods=['POST'])
def api_cache_create():
    import cache_manager
    result = cache_manager.create_snapshot()
    return jsonify({'ok':result.get('success', False), **result})

@app.route('/api/cache/snapshots')
def api_cache_snapshots():
    import cache_manager
    return jsonify({'ok':True, 'snapshots': cache_manager.list_snapshots()})

@app.route('/api/collect',methods=['POST'])
def api_collect():
    data=request.get_json(silent=True) or {}; keywords=data.get('keywords') or collector.MONITOR_KEYWORDS
    if isinstance(keywords,str): keywords=[x.strip() for x in keywords.split(',') if x.strip()]
    keywords=list(dict.fromkeys(keywords))[:20]
    try: max_scroll=max(1,min(20,int(data.get('max_scroll',4))))
    except (TypeError,ValueError): return jsonify({'ok':False,'error':'max_scroll 必须为整数'}),400
    if not keywords: return jsonify({'ok':False,'error':'关键词不能为空'}),400
    if not _collect_lock.acquire(blocking=False): return jsonify({'ok':False,'error':'已有采集任务正在运行，请稍后再试'}),409
    task_id=f"{datetime.now():%Y%m%d%H%M%S}{int(time.time()*1000)%1000:03d}"
    with _task_lock: collect_tasks[task_id]={'task_id':task_id,'status':'pending','message':'任务已创建','progress':0,'created_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'keywords':keywords}
    threading.Thread(target=_run_collect_task,args=(task_id,keywords,max_scroll),daemon=True).start()
    return jsonify({'ok':True,'task_id':task_id})
@app.route('/api/collect/status/<task_id>')
def api_collect_status(task_id):
    with _task_lock: task=collect_tasks.get(task_id)
    return (jsonify({'ok':True,'task':task}),200) if task else (jsonify({'ok':False,'error':'任务不存在'}),404)
@app.route('/api/collect/tasks')
def api_collect_tasks():
    with _task_lock: tasks=sorted(collect_tasks.values(),key=lambda x:x['created_at'],reverse=True)[:20]
    return jsonify({'ok':True,'tasks':tasks})
@app.route('/api/analyze',methods=['POST'])
def api_analyze():
    try: limit=max(1,min(5000,int((request.get_json(silent=True) or {}).get('limit',500))))
    except (TypeError,ValueError): return jsonify({'ok':False,'error':'limit 必须为整数'}),400
    clause,sp=_subject_sql_and_values(); with_db = db.get_db();
    with with_db as conn: rows=conn.execute(f"SELECT * FROM notes WHERE is_taikoo_verified=1 AND {clause} ORDER BY id ASC LIMIT ?",tuple(sp)+(limit,)).fetchall()
    counts={'accepted':0,'rejected':0,'errors':0}
    for row in rows:
        try: counts[reprocess.analyze_note_row(row,translate=False)] += 1
        except Exception as e: counts['errors'] += 1; print('[Analyze]',e)
    events=reprocess.build_cross_platform_events()
    return jsonify({'ok':True,'counts':counts,'events':len(events),'ai_enabled':intelligence.ai_enabled()})

def subject_hit_note_safe(note):
    return subject_hit(
        title=note.get('title',''), body=note.get('body',''), content=note.get('content',''),
        source_keyword=note.get('source_keyword',''), matched_keywords=note.get('matched_keywords','')
    )

@app.route('/api/note/<note_id>')
@app.route('/api/notes/<note_id>')
def api_note_detail(note_id):
    with db.get_db() as conn: row=conn.execute('SELECT * FROM notes WHERE note_id=?',(note_id,)).fetchone()
    note=db.note_to_dict(row) if row else None
    if note and not subject_hit_note_safe(note): note=None
    return (jsonify({'ok':True,'note':note}),200) if note else (jsonify({'ok':False,'error':'Not found'}),404)
@app.route('/api/historical-notes')
def api_historical_notes():
    now=datetime.now(); today=now.strftime('%Y-%m-%d'); period=request.args.get('period','daily')
    start=(now-timedelta(days=now.weekday())).strftime('%Y-%m-%d') if period=='weekly' else (now.replace(day=1).strftime('%Y-%m-%d') if period=='monthly' else today)
    return jsonify({'ok':True,'notes':db.get_historical_notes(start,today,100),'stats':db.get_historical_stats(start,today),'period_start':start,'period_end':today})
@app.route('/api/backup',methods=['POST'])
def api_backup():
    backup_dir=os.path.join(os.path.dirname(db.DB_PATH),'backups'); os.makedirs(backup_dir,exist_ok=True)
    dest=os.path.join(backup_dir,f"monitor-{datetime.now():%Y%m%d-%H%M%S}.db")
    db.backup_database(dest)
    # 只保留最近 30 份，避免长期运行把磁盘吃满。
    files=sorted((os.path.join(backup_dir,f) for f in os.listdir(backup_dir) if f.endswith('.db')), key=os.path.getmtime, reverse=True)
    for old_file in files[30:]:
        try: os.remove(old_file)
        except OSError: pass
    return jsonify({'ok':True,'file':os.path.basename(dest),'path':dest})

# ===== v5.7.0 八项升级 API =====
@app.route('/api/weekly/events')
def api_weekly_events_v570():
    start,end=weekly_events.natural_week()
    with db.get_db() as conn: payload=weekly_events.weekly_payload(conn,start,end)
    return jsonify({'ok':True,**payload})

@app.route('/api/web/browser-discovery',methods=['POST'])
def api_browser_discovery_v570():
    data=request.get_json(silent=True) or {}
    queries=data.get('queries') or ['广州太古汇 舆情','广州太古汇 投诉','广州太古汇 品牌','广州太古汇 餐饮','广州太古汇 活动']
    limit=max(10,min(200,int(data.get('limit') or os.getenv('WEB_BROWSER_DISCOVERY_LIMIT','80'))))
    items=browser_discovery.discover(queries,limit)
    return jsonify({'ok':True,'count':len(items),'items':items,'budget':'independent_browser_search'})

@app.route('/api/web/brand-industry/plan')
def api_brand_industry_plan_v570():
    brands=_load_brands()
    cats=sorted({b.get('category','') for b in brands if b.get('category')})
    qs=web_monitor_v570.brand_queries(brands,cats)
    return jsonify({'ok':True,'total_targets':len(qs),'brands':len(brands),'categories':cats,'batch_size':int(request.args.get('batch','12'))})

@app.route('/api/web/brand-industry/run',methods=['POST'])
def api_brand_industry_run_v570():
    data=request.get_json(silent=True) or {}
    brands=_load_brands()
    cats=sorted({b.get('category','') for b in brands if b.get('category')})
    batch=max(1,min(30,int(data.get('batch',12))))
    offset=max(0,int(data.get('offset',0)))
    items,total=web_monitor_v570.discover_brand_industry(brands,cats,batch,offset)
    saved=0
    for item in items:
        try: db.insert_web_mention(item); saved+=1
        except Exception: pass
    return jsonify({'ok':True,'fetched':len(items),'saved':saved,'total_targets':total,'next_offset':offset+batch if offset+batch<total else 0,'independent_budget':True})

@app.route('/api/notes/publish-buckets')
def api_publish_buckets_v570():
    date=request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    with db.get_db() as conn:
        same=[dict(r) for r in conn.execute("SELECT * FROM notes WHERE is_taikoo_verified=1 AND substr(COALESCE(publish_datetime,publish_date),1,10)=? ORDER BY collected_at DESC",(date,)).fetchall()]
        historical=[dict(r) for r in conn.execute("SELECT * FROM notes WHERE is_taikoo_verified=1 AND substr(COALESCE(publish_datetime,publish_date),1,10)<? AND substr(collected_at,1,10)=? ORDER BY collected_at DESC",(date,date)).fetchall()]
    return jsonify({'ok':True,'date':date,'published_today':same,'historical_collected_today':historical,'counts':{'published_today':len(same),'historical_collected_today':len(historical)}})

@app.route('/api/ai/providers')
def api_ai_providers_v570():
    try:
        local = ai_analyzer.ai_status() if hasattr(ai_analyzer, 'ai_status') else {'available': False, 'model': 'none', 'message': '本地AI未配置'}
    except Exception:
        local = {'available': False, 'model': 'none', 'message': '本地AI状态获取失败'}
    # P1-A(2026-09-02): ai_gateway_v570已废弃，统一到intelligence.py
    try:
        ai_stat = intelligence.ai_status()
        remote = [{
            'id': ai_stat.get('provider', 'unknown'),
            'name': f"AI Provider ({ai_stat.get('provider', 'unknown')})",
            'type': ai_stat.get('runtime', 'unknown'),
            'status': 'available' if ai_stat.get('enabled') else 'unavailable',
            'model': ai_stat.get('model', 'unknown')
        }] if ai_stat.get('enabled') else []
    except Exception:
        remote = []
    return jsonify({'ok': True, 'local': local, 'remote': remote})

@app.route('/api/ai/analyze-v570',methods=['POST'])
def api_ai_analyze_v570():
    # P1-A(2026-09-02): ai_gateway_v570已废弃，统一到intelligence._chat()
    data=request.get_json(silent=True) or {}
    text=data.get('text','')
    context=data.get('context','')
    if not text:
        return jsonify({'ok': False, 'text': text, 'context': context, 'provider': 'none', 'analysis': '', 'error': '文本为空'})
    try:
        system_prompt = "你是广州太古汇舆情分析助手。请分析以下内容的情感倾向、风险等级和关键要点。"
        user_prompt = f"内容：{text}\n上下文：{context or '无'}\n请给出：1)情感倾向 2)风险等级 3)关键要点 4)建议"
        raw, provider = intelligence._chat(system_prompt, user_prompt, 0.3, 800)
        return jsonify({'ok': True, 'text': text, 'context': context, 'provider': provider, 'analysis': raw or '', 'error': ''})
    except Exception as e:
        return jsonify({'ok': False, 'text': text, 'context': context, 'provider': 'none', 'analysis': '', 'error': str(e)})

@app.route('/api/trends/global')
def api_global_trends_v570():
    days=max(7,min(90,int(request.args.get('days','14'))))
    now=datetime.now()
    start=(now-timedelta(days=days-1)).strftime('%Y-%m-%d')
    end=now.strftime('%Y-%m-%d')
    with db.get_db() as conn:
        rows=conn.execute("SELECT publish_date,COUNT(*) total,SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) negative,SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) high FROM notes WHERE is_taikoo_verified=1 AND COALESCE(relevance_status,'relevant')!='irrelevant' AND publish_date BETWEEN ? AND ? GROUP BY publish_date ORDER BY publish_date",(start,end)).fetchall()
    data=[]
    for r in rows:
        total=r['total'] or 0
        data.append({'date':r['publish_date'],'total':total,'negative':r['negative'] or 0,'high':r['high'] or 0,'negative_pct':round((r['negative'] or 0)*100/total,1) if total else 0,'high_pct':round((r['high'] or 0)*100/total,1) if total else 0})
    return jsonify({'ok':True,'days':days,'data':data})

@app.route('/api/dashboard/changes')
def api_dashboard_changes_v570():
    stats=db.get_stats()
    now=datetime.now()
    return jsonify({'ok':True,'server_time':now.strftime('%Y-%m-%d %H:%M:%S'),'stats':stats,'version':APP_VERSION})

# ===== v5.7.1 笔记库查询 + 周期报告核对 =====
@app.route('/api/notes/library')
def api_notes_library_v571():
    """笔记库查询：支持按发布日期、采集日期、关键词、情感、风险等级筛选"""
    page=max(1,int(request.args.get('page',1)))
    per_page=max(10,min(100,int(request.args.get('per_page',20))))
    keyword=request.args.get('keyword','').strip()
    sentiment=request.args.get('sentiment','').strip()
    risk_level=request.args.get('risk_level','').strip()
    publish_start=request.args.get('publish_start','').strip()
    publish_end=request.args.get('publish_end','').strip()
    collect_start=request.args.get('collect_start','').strip()
    collect_end=request.args.get('collect_end','').strip()
    
    with db.get_db() as conn:
        cols=[r[1] for r in conn.execute('PRAGMA table_info(notes)').fetchall()]
        select_cols=[c for c in ['note_id','title','author_nickname','publish_date','collected_at','url','sentiment','risk_level','risk_score','summary','likes','comments','collects','shares','source_platform','negative_confirmed'] if c in cols]
        
        sql=f"SELECT {','.join(select_cols)} FROM notes WHERE 1=1"
        params=[]
        
        if keyword:
            sql+=" AND (title LIKE ? OR summary LIKE ? OR author_nickname LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
        if sentiment:
            sql+=" AND sentiment=?"
            params.append(sentiment)
        if risk_level:
            sql+=" AND risk_level=?"
            params.append(risk_level)
        if publish_start:
            sql+=" AND date(publish_date)>=date(?)"
            params.append(publish_start)
        if publish_end:
            sql+=" AND date(publish_date)<=date(?)"
            params.append(publish_end)
        if collect_start:
            sql+=" AND date(collected_at)>=date(?)"
            params.append(collect_start)
        if collect_end:
            sql+=" AND date(collected_at)<=date(?)"
            params.append(collect_end)
        
        # 总数
        count_sql=sql.replace(f"SELECT {','.join(select_cols)}", "SELECT COUNT(*)")
        total=conn.execute(count_sql, params).fetchone()[0]
        
        # 分页
        offset=(page-1)*per_page
        sql+=" ORDER BY collected_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        notes=[dict(r) for r in conn.execute(sql, params).fetchall()]
    
    return jsonify({'ok':True,'notes':notes,'total':total,'page':page,'per_page':per_page,'total_pages':(total+per_page-1)//per_page})

@app.route('/api/report/verify')
def api_report_verify_v571():
    """周期报告核对：检查指定周期内的报告数据准确性"""
    report_type=request.args.get('type','daily').strip()
    date=request.args.get('date','').strip() or datetime.now().strftime('%Y-%m-%d')
    
    # 计算周期
    if report_type=='daily':
        start=end=date
    elif report_type=='weekly':
        d=datetime.strptime(date,'%Y-%m-%d')
        start=(d-timedelta(days=d.weekday())).strftime('%Y-%m-%d')
        end=(d+timedelta(days=6-d.weekday())).strftime('%Y-%m-%d')
    elif report_type=='monthly':
        d=datetime.strptime(date,'%Y-%m-%d')
        start=d.replace(day=1).strftime('%Y-%m-%d')
        if d.month==12:
            end=d.replace(year=d.year+1,month=1,day=1)-timedelta(days=1)
        else:
            end=d.replace(month=d.month+1,day=1)-timedelta(days=1)
        end=end.strftime('%Y-%m-%d')
    else:
        return jsonify({'ok':False,'error':'type仅支持daily/weekly/monthly'}),400
    
    with db.get_db() as conn:
        # 按发布日期统计
        published=conn.execute("SELECT COUNT(*) FROM notes WHERE date(publish_date) BETWEEN ? AND ?",(start,end)).fetchone()[0]
        # 按采集日期统计
        collected=conn.execute("SELECT COUNT(*) FROM notes WHERE date(collected_at) BETWEEN ? AND ?",(start,end)).fetchone()[0]
        # 负面笔记（已二次确认）
        confirmed_negative=conn.execute("SELECT COUNT(*) FROM notes WHERE date(publish_date) BETWEEN ? AND ? AND sentiment='negative' AND negative_confirmed=1",(start,end)).fetchone()[0]
        # 待确认负面
        pending_negative=conn.execute("SELECT COUNT(*) FROM notes WHERE date(publish_date) BETWEEN ? AND ? AND sentiment='negative' AND negative_confirmed=0",(start,end)).fetchone()[0]
        # 高风险
        high_risk=conn.execute("SELECT COUNT(*) FROM notes WHERE date(publish_date) BETWEEN ? AND ? AND risk_level='high'",(start,end)).fetchone()[0]
        # 事件数
        try:
            events=conn.execute("SELECT COUNT(*) FROM events WHERE date(first_seen) BETWEEN ? AND ?",(start,end)).fetchone()[0]
        except: events=0
    
    return jsonify({
        'ok':True,
        'report_type':report_type,
        'period_start':start,
        'period_end':end,
        'published_in_period':published,
        'collected_in_period':collected,
        'confirmed_negative':confirmed_negative,
        'pending_negative':pending_negative,
        'high_risk':high_risk,
        'events':events,
        'warning': '报告应基于发布日期统计，采集日期仅作参考' if published!=collected else None
    })

@app.route('/remote')
def remote_access():
    """本地固定入口：自动跳转到当前Cloudflare隧道公网URL
    用于解决trycloudflare临时域名每次重启变化的问题。
    用户访问 http://127.0.0.1:8200/remote 即可自动跳转到最新的公网地址。
    """
    import os
    url_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tunnel_url.txt')
    try:
        if os.path.exists(url_file):
            with open(url_file, 'r', encoding='utf-8') as f:
                url = f.read().strip()
            if url and url.startswith('http'):
                return redirect(url, code=302)
    except Exception:
        pass
    # 隧道未启动时显示提示
    return jsonify({
        'ok': False,
        'message': '公网隧道未启动，请先运行 tunnel_guardian.py 启动隧道',
        'local_url': 'http://127.0.0.1:8200',
        'tunnel_url_file': url_file,
    }), 503


@app.route('/healthz')
def healthz():
    return jsonify({'ok':True,'version':APP_VERSION,'service':'taikoo-monitor'})

@app.route('/api/system/health')
def api_system_health():
    """产品级健康状态：区分‘系统正常’与‘数据源没有数据’。"""
    now=datetime.now()
    result={'version':APP_VERSION,'service':'taikoo-monitor','time':now.strftime('%Y-%m-%d %H:%M:%S')}
    try:
        stats=db.get_stats()
        latest=''
        with db.get_db() as conn:
            clause,sp=_subject_sql_and_values(); row=conn.execute(f"SELECT MAX(COALESCE(collected_at,publish_date)) AS latest, COUNT(*) AS total FROM notes WHERE is_taikoo_verified=1 AND {clause}",tuple(sp)).fetchone()
            latest=row['latest'] or ''
        result.update({'database':'ok','verified_notes':int(stats.get('verified_count',0) or 0),'latest_data':latest})
    except Exception as e:
        result.update({'database':'error','database_error':str(e)})
    result['ai']=intelligence.ai_status()
    result['web_discovery_enabled']=os.getenv('TAIKOO_WEB_DISCOVERY','1').lower() not in ('0','false','no','off')
    return jsonify({'ok':result.get('database')=='ok','health':result})

# ===== v5.3.2 智能日报 API =====
@app.route('/api/digest/today')
def api_digest_today():
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    digest = db.get_latest_digest(date_str)
    if not digest:
        # 尝试自动生成
        try:
            digest = daily_report.generate_daily_digest(date_str)
        except Exception as e:
            return jsonify({'ok':False,'error':str(e)}),500
    return jsonify({'ok':True,'digest':digest})

@app.route('/api/digest/generate', methods=['POST'])
def api_digest_generate():
    data = request.get_json(silent=True) or {}
    date_str = data.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        digest = daily_report.generate_daily_digest(date_str)
        return jsonify({'ok':True,'digest':digest,'message':'日报生成完成'})
    except Exception as e:
        return jsonify({'ok':False,'error':str(e)}),500

# ===== v5.3.2 AI过滤层 API =====
@app.route('/api/ai-filter/stats')
def api_ai_filter_stats():
    return jsonify({'ok':True,'stats':db.get_filter_stats()})

@app.route('/api/ai-filter/run', methods=['POST'])
def api_ai_filter_run():
    data = request.get_json(silent=True) or {}
    limit = max(1, min(2000, int(data.get('limit', 500))))
    def worker():
        try:
            ai_filter.run_filter_batch(limit)
        except Exception as e:
            print('[AIFilter] 运行失败:', e)
    threading.Thread(target=worker, daemon=True).start()
    return jsonify({'ok':True,'message':f'AI过滤任务已启动，处理 {limit} 条','limit':limit})

@app.route('/api/ai-filter/cleanup', methods=['POST'])
def api_ai_filter_cleanup():
    data = request.get_json(silent=True) or {}
    execute = bool(data.get('execute', False))
    result = ai_filter.cleanup_rejected_notes(dry_run=not execute)
    return jsonify({'ok':True,'result':result})

@app.route('/api/overview')
def api_overview():
    now=datetime.now()
    start=(now-timedelta(days=13)).strftime('%Y-%m-%d')
    end=now.strftime('%Y-%m-%d')
    with db.get_db() as conn:
        clause,sp=_subject_sql_and_values(); rows=conn.execute(f"SELECT publish_date, COUNT(*) total, SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) negative, SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) high FROM notes WHERE is_taikoo_verified=1 AND {clause} AND publish_date BETWEEN ? AND ? GROUP BY publish_date ORDER BY publish_date",tuple(sp)+(start,end)).fetchall()
        active=sum(1 for e in db.get_events(500) if e.get('status')=='active' and (e.get('last_seen') or '')>=start)
    by={r['publish_date']:{'total':r['total'] or 0,'negative':r['negative'] or 0,'high':r['high'] or 0} for r in rows}
    trend=[]
    for i in range(14):
        d=(now-timedelta(days=13-i)).strftime('%Y-%m-%d')
        x=by.get(d,{'total':0,'negative':0,'high':0})
        trend.append({'date':d,'label':d[5:],'total':x['total'],'negative':x['negative'],'high':x['high']})
    recent_negative=sum(x['negative'] for x in trend)
    return jsonify({'ok':True,'trend':trend,'active_events':active,'recent_negative':recent_negative})

@app.route('/api/status')
def api_status():
    stats=db.get_stats()
    with db.get_db() as conn:
        clause,sp=_subject_sql_and_values(); unanalyzed=conn.execute(f"SELECT COUNT(*) c FROM notes WHERE (ai_analyzed_at='' OR ai_analyzed_at IS NULL) AND is_taikoo_verified=1 AND {clause}",tuple(sp)).fetchone()['c']; last=conn.execute('SELECT * FROM collection_logs ORDER BY id DESC LIMIT 1').fetchone()
    return jsonify({'ok':True,'system':'广州太古汇舆情监测系统','version':APP_VERSION,'collector':'Playwright/XHS search + rednote CDP','analyzer':'AI provider + auditable rule fallback','qian_gua_integration':False,'data_source':'公开网页发现 → 关键词反馈 → 小红书/rednote浏览器采集','total_notes':stats['total'],'verified_notes':stats['verified_count'],'unanalyzed':unanalyzed,'last_collection':dict(last) if last else None,'server_time':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'ai_enabled':intelligence.ai_enabled(),'ai_detail':intelligence.ai_status().get('detail'),'ai_provider':intelligence.ai_status().get('provider'),'ai_model':intelligence.ai_status().get('model'),'web_sources':['Google News RSS','GDELT','custom RSS'],'rednote_cdp_enabled':bool(os.getenv('XHS_CDP_URL','')),'company_domain':os.getenv('TAIKOO_COMPANY_DOMAIN',''),'auto_interval_minutes':int(os.getenv('AUTO_INTERVAL_MINUTES','90'))})

# ===== v5.4 rednote CDP 采集 API =====
@app.route('/api/rednote/collect', methods=['POST'])
def api_rednote_collect():
    data = request.get_json(silent=True) or {}
    keyword = data.get('keyword', '广州太古汇')
    max_scroll = max(1, min(10, int(data.get('max_scroll', 3))))
    max_details = max(1, min(50, int(data.get('max_details', 10))))
    account = data.get('account', 'default')
    # 按逻辑身份解析驻场端口（大陆9222/香港9223）；显式传入/环境变量优先
    cdp_url = data.get('cdp_url') or os.getenv('XHS_CDP_URL') or xhs_cookie_bridge.cdp_url_for(account)
    persist = bool(data.get('persist', True))

    # Resident Browser：对应身份驻场实例不在线才拉起；在线直接附着复用
    auto_started_browser = False
    try:
        import collector_automation
        ca = collector_automation.get_collector_automation()
        _port = xhs_cookie_bridge.cdp_port_for(account)
        if not ca._is_browser_running(_port):
            start_result = ca.start_browser(account=account)
            if start_result:
                cdp_url = f'http://127.0.0.1:{ca._port_for(account)}'
                auto_started_browser = True
                app.logger.info(f'CDP驻场浏览器已启动: account={account} {cdp_url}')
            else:
                return jsonify({'ok': False, 'error': 'CDP驻场浏览器启动失败，请用统一驻场启动器或手动启动 Edge 调试模式'}), 500
    except Exception as e:
        return jsonify({'ok': False, 'error': f'CDP浏览器启动异常: {str(e)}'}), 500
    
    def worker():
        try:
            result = run_rednote_collect(keyword, max_scroll, max_details, cdp_url)
            if persist and result.get('ok'):
                def subject_hit(text):
                    # P0-02 收敛：统一委托 subject_rules 权威主体口径（排除词一票否决+正向词命中），
                    # 不再用 AI verify 替代，避免口径分叉（对账 GAP-P0-02）。
                    try:
                        from subject_rules import subject_hit_text
                        return subject_hit_text(text)
                    except Exception:
                        return False
                persist_rednote_data(result, subject_hit)
                check_and_create_alerts()
            return result
        finally:
            # Resident Browser 驻场策略：采集结束后保留登录窗口长期驻留（不关闭），
            # 生命周期交由统一驻场启动器 / start_production.ps1 管理，此处仅断开 CDP 附着。
            if auto_started_browser:
                app.logger.info('CDP驻场浏览器保留在线（Resident Browser，采集后不关闭）')
    if data.get('async', True):
        task_id = f"rednote-{datetime.now():%Y%m%d%H%M%S}"
        with _task_lock:
            collect_tasks[task_id] = {'task_id': task_id, 'status': 'running', 'message': f'rednote采集: {keyword}', 'progress': 10, 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'keywords': [keyword]}
        def run_with_status():
            try:
                result = worker()
                with _task_lock:
                    collect_tasks[task_id].update(status='done', message='rednote采集完成', progress=100, result_summary={'notes': len(result.get('notes',[])), 'ok': result.get('ok')})
            except Exception as e:
                with _task_lock:
                    collect_tasks[task_id].update(status='error', message=str(e), progress=0)
        threading.Thread(target=run_with_status, daemon=True).start()
        return jsonify({'ok': True, 'task_id': task_id, 'message': 'rednote采集任务已启动'})
    else:
        result = worker()
        return jsonify(result)

# ===== v5.4 舆情预警通知 API =====
@app.route('/api/alerts')
def api_alerts():
    unread_only = request.args.get('unread', '1') == '1'
    alerts = _load_alerts()
    if unread_only:
        alerts = [a for a in alerts if not a.get('read')]
    # 按时间倒序
    alerts.sort(key=lambda x: x.get('created_at',''), reverse=True)
    return jsonify({'ok': True, 'alerts': alerts[:50], 'unread_count': len([a for a in _load_alerts() if not a.get('read')])})

@app.route('/api/alerts/read', methods=['POST'])
def api_alerts_read():
    data = request.get_json(silent=True) or {}
    alert_id = data.get('alert_id')
    all_read = bool(data.get('all', False))
    alerts = _load_alerts()
    if all_read:
        for a in alerts: a['read'] = True
    elif alert_id:
        for a in alerts:
            if a.get('id') == alert_id or a.get('note_id') == alert_id:
                a['read'] = True
    _save_alerts(alerts)
    return jsonify({'ok': True, 'message': '已标记为已读', 'unread_count': len([a for a in alerts if not a.get('read')])})

@app.route('/api/alerts/refresh', methods=['POST'])
def api_alerts_refresh():
    new_alerts = check_and_create_alerts()
    return jsonify({'ok': True, 'new_alerts': len(new_alerts), 'alerts': new_alerts})

# ===== 测试API：最简单的Excel导出 =====
@app.route('/api/test/export')
def api_test_export():
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws['A1'] = '测试'
        ws['B1'] = '成功'
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        file_data = output.getvalue()
        resp = Response(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp.headers['Content-Disposition'] = 'attachment; filename="test.xlsx"'
        return resp
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500

# ===== 负面舆情二次确认 API =====
@app.route('/api/negative/pending')
def api_negative_pending():
    """获取负面笔记列表，支持status参数: pending/confirmed/rejected"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        status = request.args.get('status', 'pending')
        offset = (page - 1) * per_page
        conn = sqlite3.connect(db.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status == 'confirmed':
            where = "negative_confirmed=1"
        elif status == 'rejected':
            where = "negative_confirmed=2"
        else:
            where = "(negative_confirmed=0 OR negative_confirmed IS NULL)"
        
        # 与日报/统计同口径：只保留广州太古汇主体、非重复、非噪音的负面笔记；
        # 全网公关案例属“案例库”，不进入太古汇负面审核待办（否则详情接口会因主体过滤 404）
        clause, sp = _subject_sql_and_values()
        sp = list(sp)
        base_where = (f"sentiment='negative' AND {where} AND COALESCE(is_duplicate,0)=0 "
                      f"AND COALESCE(noise_type,'')='' AND {clause}")
        # 统计总数
        cursor.execute(f"SELECT COUNT(*) as cnt FROM notes WHERE {base_where}", tuple(sp))
        total = cursor.fetchone()['cnt']
        # 获取列表
        cursor.execute(f"""
            SELECT note_id, title, author_nickname, publish_date, url,
                   likes, comments, collects, shares, risk_level, risk_score,
                   summary, source_platform, collected_at, negative_confirmed
            FROM notes
            WHERE {base_where}
            ORDER BY CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                     COALESCE(risk_score,0) DESC, collected_at DESC
            LIMIT ? OFFSET ?
        """, tuple(sp) + (per_page, offset))
        notes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'ok': True, 'notes': notes, 'items': notes, 'total': total, 'page': page, 'per_page': per_page})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500
def _note_set_review(note_id, state, by='admin'):
    """GAP-09 笔记负面评审统一写路径（唯一 Owner）：新旧入口共用，消除重复 SQL。
    state=1 确认负面；state=2 驳回。写 notes.negative_confirmed 同一字段。"""
    if not note_id:
        return {'ok': False, 'error': '缺少note_id'}, 400, None
    conn = sqlite3.connect(db.DB_PATH)
    try:
        cur = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("UPDATE notes SET negative_confirmed=?, negative_confirmed_at=?, negative_confirmed_by=? WHERE note_id=?", (state, now, by, note_id))
        conn.commit()
        affected = cur.rowcount
        return {'ok': True, 'note_id': note_id, 'affected': affected}, 200, None
    except Exception as e:
        import traceback
        return {'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}, 500, None
    finally:
        conn.close()



@app.route('/api/negative/confirm', methods=['POST'])
def api_negative_confirm():
    """确认负面笔记（核准为负面）——GAP-09 收敛：走统一写路径 _note_set_review"""
    data = request.get_json() or {}
    resp, status, _ = _note_set_review(data.get('note_id'), 1)
    resp['confirmed'] = True
    return jsonify(resp), status

@app.route('/api/negative/reject', methods=['POST'])
def api_negative_reject():
    """驳回负面笔记（不是负面）——GAP-09 收敛：走统一写路径 _note_set_review"""
    data = request.get_json() or {}
    resp, status, _ = _note_set_review(data.get('note_id'), 2)
    resp['rejected'] = True
    return jsonify(resp), status

@app.route('/api/negative-review/<note_id>/confirm', methods=['POST'])
def api_negative_review_confirm(note_id):
    """负面审核-确认（RESTful 路径参数，兼容前端 NegativeReview.confirmItem）——GAP-09 收敛：走统一写路径"""
    resp, status, _ = _note_set_review(note_id, 1)
    resp['confirmed'] = True
    return jsonify(resp), status

@app.route('/api/negative-review/<note_id>/reject', methods=['POST'])
def api_negative_review_reject(note_id):
    """负面审核-驳回（RESTful 路径参数，兼容前端 NegativeReview.rejectItem）——GAP-09 收敛：走统一写路径"""
    resp, status, _ = _note_set_review(note_id, 2)
    resp['rejected'] = True
    return jsonify(resp), status

# ================= v5.8.2 事件负面二次确认（与笔记同口径，事件中心联动）=================
def _event_set_review(event_id, state, by='admin'):
    """事件二次确认。state=1确认负面时，联动确认其关联负面笔记（事件由笔记聚合，
    确认事件即确认其下笔记）；关联走 event_mentions，缺失时用事件关键词兜底匹配。
    返回 {'events':事件更新行数, 'notes':联动笔记数}"""
    conn = sqlite3.connect(db.DB_PATH); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 兼容主键 id 或 event_key，先定位到事件真实行
    try:
        row = cur.execute("SELECT * FROM events WHERE id=?", (int(event_id),)).fetchone()
    except (TypeError, ValueError):
        row = cur.execute("SELECT * FROM events WHERE event_key=?", (event_id,)).fetchone()
    if not row:
        conn.close(); return {'events': 0, 'notes': 0}
    ev = dict(row); real_id = ev['id']
    cur.execute("UPDATE events SET negative_confirmed=?, negative_confirmed_at=?, negative_confirmed_by=? WHERE id=?",
                (state, now, by, real_id))
    affected = cur.rowcount
    notes_affected = 0
    if state == 1:  # 仅“确认负面”联动笔记；驳回不强制改笔记，保留人工分别研判
        linked = [r[0] for r in cur.execute(
            "SELECT DISTINCT source_id FROM event_mentions WHERE event_id=?", (real_id,)).fetchall() if r[0]]
        if linked:
            qm = ','.join('?' * len(linked))
            cur.execute(f"UPDATE notes SET negative_confirmed=1, negative_confirmed_at=?, negative_confirmed_by=? "
                        f"WHERE note_id IN ({qm}) AND sentiment='negative' AND COALESCE(negative_confirmed,0)!=1",
                        [now, by] + linked)
            notes_affected = cur.rowcount
        if notes_affected == 0:  # 兜底：event_mentions 缺失时用事件关键词匹配负面笔记
            kws = []
            try:
                kws = [k for k in json.loads(ev.get('keywords') or '[]') if k]
            except Exception:
                kws = []
            if kws:
                cond = " OR ".join(["(title LIKE ? OR summary LIKE ? OR event_hint LIKE ?)"] * len(kws))
                params = []
                for k in kws:
                    params += [f"%{k}%"] * 3
                cur.execute(f"UPDATE notes SET negative_confirmed=1, negative_confirmed_at=?, negative_confirmed_by=? "
                            f"WHERE sentiment='negative' AND COALESCE(negative_confirmed,0)!=1 AND ({cond})",
                            [now, by] + params)
                notes_affected = cur.rowcount
    conn.commit(); conn.close()
    return {'events': affected, 'notes': notes_affected}

@app.route('/api/event-review/<event_id>/confirm', methods=['POST'])
def api_event_review_confirm(event_id):
    """确认事件负面（核准）——人工确认后该事件从待核实/待确认列表移除，并联动确认其关联负面笔记"""
    try:
        res = _event_set_review(event_id, 1)
        return jsonify({'ok': True, 'event_id': event_id, 'confirmed': True,
                        'affected': res['events'], 'notes_linked': res['notes']})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-review/<event_id>/reject', methods=['POST'])
def api_event_review_reject(event_id):
    """驳回事件（非负面/误报）——人工处理后不再出现在待确认列表（不联动改笔记，保留分别研判）"""
    try:
        res = _event_set_review(event_id, 2)
        return jsonify({'ok': True, 'event_id': event_id, 'rejected': True, 'affected': res['events']})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-review/pending')
def api_event_review_pending():
    """待人工确认的事件：风险事件且未二次确认（negative_confirmed=0），按风险/时间倒序"""
    try:
        limit = request.args.get('limit', 50, type=int)
        conn = sqlite3.connect(db.DB_PATH); conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT * FROM events
                               WHERE (negative_confirmed=0 OR negative_confirmed IS NULL)
                                 AND (risk_level IN ('high','medium') OR fact_status IN ('unconfirmed','partially_confirmed'))
                               ORDER BY risk_score DESC, last_seen DESC LIMIT ?""", (limit,)).fetchall()
        conn.close()
        return jsonify({'ok': True, 'total': len(rows), 'events': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-review/stats')
def api_event_review_stats():
    """事件负面确认统计：待确认/已确认/已驳回"""
    try:
        conn = sqlite3.connect(db.DB_PATH); cur = conn.cursor()
        pending = cur.execute("SELECT COUNT(*) FROM events WHERE (negative_confirmed=0 OR negative_confirmed IS NULL) AND risk_level IN('high','medium')").fetchone()[0]
        confirmed = cur.execute("SELECT COUNT(*) FROM events WHERE negative_confirmed=1").fetchone()[0]
        rejected = cur.execute("SELECT COUNT(*) FROM events WHERE negative_confirmed=2").fetchone()[0]
        conn.close()
        return jsonify({'ok': True, 'pending': pending, 'confirmed': confirmed, 'rejected': rejected})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/events/<event_id>/notes')
def api_event_notes(event_id):
    """事件关联的真实笔记：优先 event_mentions 关联表（event_id→note_id），
    关联缺失时用事件关键词兜底匹配。负面/高风险在前，供事件详情“查看相关笔记案例”。"""
    try:
        conn = sqlite3.connect(db.DB_PATH); conn.row_factory = sqlite3.Row; cur = conn.cursor()
        try:
            row = cur.execute("SELECT * FROM events WHERE id=?", (int(event_id),)).fetchone()
        except (TypeError, ValueError):
            row = cur.execute("SELECT * FROM events WHERE event_key=?", (event_id,)).fetchone()
        if not row:
            conn.close(); return jsonify({'ok': True, 'notes': [], 'total': 0, 'matched_by': 'none'})
        ev = dict(row); real_id = ev['id']
        order = ("CASE n.sentiment WHEN 'negative' THEN 0 WHEN 'neutral' THEN 1 ELSE 2 END, "
                 "CASE n.risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, "
                 "COALESCE(n.risk_score,0) DESC")
        notes = [dict(r) for r in cur.execute(f"""
            SELECT n.* FROM event_mentions m JOIN notes n ON n.note_id=m.source_id
            WHERE m.event_id=? ORDER BY {order} LIMIT 100""", (real_id,)).fetchall()]
        matched_by = 'event_mentions'
        if not notes:  # 兜底：事件关键词匹配标题/摘要/event_hint
            kws = []
            try:
                kws = [k for k in json.loads(ev.get('keywords') or '[]') if k]
            except Exception:
                kws = []
            if kws:
                cond = " OR ".join(["(n.title LIKE ? OR n.summary LIKE ? OR n.event_hint LIKE ?)"] * len(kws))
                params = []
                for k in kws:
                    params += [f"%{k}%"] * 3
                notes = [dict(r) for r in cur.execute(f"""
                    SELECT n.* FROM notes n WHERE COALESCE(n.is_duplicate,0)=0
                    AND ({cond}) ORDER BY {order} LIMIT 100""", params).fetchall()]
                matched_by = 'keywords'
        conn.close()
        return jsonify({'ok': True, 'notes': notes, 'total': len(notes), 'matched_by': matched_by})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/negative/stats')
def api_negative_stats():
    """获取负面舆情统计"""
    try:
        conn = sqlite3.connect(db.DB_PATH)
        cursor = conn.cursor()
        # 待确认
        cursor.execute("SELECT COUNT(*) FROM notes WHERE sentiment='negative' AND (negative_confirmed=0 OR negative_confirmed IS NULL)")
        pending = cursor.fetchone()[0]
        # 已确认
        cursor.execute("SELECT COUNT(*) FROM notes WHERE negative_confirmed=1")
        confirmed = cursor.fetchone()[0]
        # 已驳回
        cursor.execute("SELECT COUNT(*) FROM notes WHERE negative_confirmed=2")
        rejected = cursor.fetchone()[0]
        # 总负面
        cursor.execute("SELECT COUNT(*) FROM notes WHERE sentiment='negative'")
        total = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            'ok': True,
            'pending': pending,
            'confirmed': confirmed,
            'rejected': rejected,
            'total_negative': total
        })
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500

# ===== v5.3.2 报告导出模块（从monitor.db读取，支持DOCX/CSV/XLSX）=====
from report_export.report_engine import export_report as export_report_v532

@app.get("/api/reports/export")
def api_reports_export_v532():
    kind = request.args.get("type", "daily")
    fmt = request.args.get("format", "xlsx").lower()
    if fmt not in ("docx", "csv", "xlsx"):
        return jsonify({"ok": False, "error": "format 必须为 docx/csv/xlsx"}), 400
    try:
        result = export_report_v532(kind, request.args.get("start"), request.args.get("end"), (fmt,))
        file_path = result["files"][fmt]
        # 读取文件内容，使用英文文件名避免latin-1编码问题
        with open(file_path, 'rb') as f:
            file_data = f.read()
        from urllib.parse import quote
        safe_name = f"Taikoo_{kind}_{result['payload']['period_start']}_{result['payload']['period_end']}.{fmt}"
        resp = Response(file_data, mimetype={
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'csv': 'text/csv; charset=utf-8-sig',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }[fmt])
        resp.headers['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        resp.headers['Content-Length'] = str(len(file_data))
        return resp
    except Exception as e:
        import traceback
        return jsonify({"ok": False, "error": str(e), "traceback": traceback.format_exc()}), 500

@app.get("/api/reports/export-all")
def api_reports_export_all_v532():
    try:
        result = export_report_v532(request.args.get("type", "daily"), request.args.get("start"), request.args.get("end"), ("docx", "csv", "xlsx"))
        return jsonify({"ok": True, "files": result["files"], "payload": result["payload"]})
    except Exception as e:
        import traceback
        return jsonify({"ok": False, "error": str(e), "traceback": traceback.format_exc()}), 500

# ===== v5.6.4 报告导出 API（支持Word/Excel/CSV + 精确时间维度） =====
@app.route('/api/v2/report/export')
@app.route('/api/report/export')
def api_report_export():
    report_type = request.args.get('type', 'daily')
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    fmt = request.args.get('format', 'xlsx').lower()
    if report_type not in ('daily', 'weekly', 'monthly', 'yearly'):
        return jsonify({'ok': False, 'error': 'type 必须是 daily/weekly/monthly/yearly'}), 400
    if fmt not in ('xlsx', 'docx', 'csv'):
        return jsonify({'ok': False, 'error': 'format 仅支持 xlsx/docx/csv'}), 400
    # 精确时间维度计算
    now = datetime.now()
    ref_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else now
    if report_type == 'daily':
        start = end = ref_date.strftime('%Y-%m-%d')
        period_label = ref_date.strftime('%Y.%m.%d')
    elif report_type == 'weekly':
        # 自然周：周一到周日
        week_start = ref_date - timedelta(days=ref_date.weekday())
        week_end = week_start + timedelta(days=6)
        start = week_start.strftime('%Y-%m-%d')
        end = week_end.strftime('%Y-%m-%d')
        period_label = f'{week_start.strftime("%Y.%m.%d")} – {week_end.strftime("%Y.%m.%d")}'
    elif report_type == 'monthly':
        # 自然月：1号到月末
        month_start = ref_date.replace(day=1)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year+1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month+1)
        month_end = next_month - timedelta(days=1)
        start = month_start.strftime('%Y-%m-%d')
        end = month_end.strftime('%Y-%m-%d')
        period_label = f'{month_start.strftime("%Y.%m.%d")} – {month_end.strftime("%Y.%m.%d")}'
    elif report_type == 'yearly':
        # 自然年：1.1到12.31
        year_start = ref_date.replace(month=1, day=1)
        year_end = ref_date.replace(month=12, day=31)
        start = year_start.strftime('%Y-%m-%d')
        end = year_end.strftime('%Y-%m-%d')
        period_label = f'{year_start.strftime("%Y.%m.%d")} – {year_end.strftime("%Y.%m.%d")}'
    # 生成报告数据
    notes = db.get_notes_by_date_range(start, end)
    stats = db.get_stats_by_date_range(start, end) or {}
    category_stats = {}
    category_order = ['零售品牌', '餐饮', '商场服务', '活动/展览', '环境/设施', '安全/突发事件', '其他']
    for n in notes:
        cat = _classify_category(n)
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'negative': 0, 'positive': 0, 'engagement': 0}
        category_stats[cat]['total'] += 1
        if n.get('sentiment') == 'negative': category_stats[cat]['negative'] += 1
        elif n.get('sentiment') == 'positive': category_stats[cat]['positive'] += 1
        category_stats[cat]['engagement'] += int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
    alert_level, alert_desc = _calc_alert_level(stats, notes)
    total = stats.get('total', len(notes))
    negative = stats.get('negative', sum(1 for n in notes if n.get('sentiment')=='negative'))
    positive = stats.get('positive', sum(1 for n in notes if n.get('sentiment')=='positive'))
    max_engage = max([int(n.get('likes',0) or 0)+int(n.get('comments',0) or 0)*3 for n in notes], default=0)
    report_title = {'daily':'daily','weekly':'weekly','monthly':'monthly','yearly':'yearly'}[report_type]
    safe_name = re.sub(r'[^0-9A-Za-z_-]+','_',f'Taikoo_{report_title}_{start}')[:80]
    # 确保文件名完全ASCII
    from urllib.parse import quote
    ascii_filename = safe_name
    # 按格式导出
    if fmt == 'csv':
        csv_content, _ = export_report_to_csv(report_type, date_str)
        from flask import Response
        resp = Response(csv_content, mimetype='text/csv; charset=utf-8-sig')
        resp.headers['Content-Disposition'] = f'attachment; filename="{ascii_filename}.csv"'
        return resp
    elif fmt == 'xlsx':
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = report_title
            # 样式
            title_font = Font(name='微软雅黑', size=16, bold=True, color='FFFFFF')
            header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
            normal_font = Font(name='微软雅黑', size=10)
            title_fill = PatternFill(start_color='1a1a2e', end_color='1a1a2e', fill_type='solid')
            header_fill = PatternFill(start_color='2563eb', end_color='2563eb', fill_type='solid')
            center = Alignment(horizontal='center', vertical='center', wrap_text=True)
            left = Alignment(horizontal='left', vertical='center', wrap_text=True)
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            row = 1
            # 标题
            ws.merge_cells(f'A{row}:F{row}')
            ws[f'A{row}'] = f'【广州太古汇{report_title}】'
            ws[f'A{row}'].font = title_font
            ws[f'A{row}'].fill = title_fill
            ws[f'A{row}'].alignment = center
            ws.row_dimensions[row].height = 35
            row += 1
            # 基本信息
            info = [('汇报周期', period_label), ('汇报人', '舆情监测系统'), ('舆情等级', f'{alert_level} — {alert_desc}')]
            for k, v in info:
                ws[f'A{row}'] = k; ws[f'A{row}'].font = Font(name='微软雅黑', size=10, bold=True)
                ws.merge_cells(f'B{row}:F{row}'); ws[f'B{row}'] = v; ws[f'B{row}'].font = normal_font
                row += 1
            row += 1
            # 1. 核心结论
            ws.merge_cells(f'A{row}:F{row}')
            ws[f'A{row}'] = '1. 核心结论'
            ws[f'A{row}'].font = header_font; ws[f'A{row}'].fill = header_fill; ws[f'A{row}'].alignment = left
            row += 1
            core = f'本期共监测小红书舆情{total}条，负面{negative}条，主要集中在【{max(category_stats, key=lambda k: category_stats[k]["total"]) if category_stats else "综合"}】，最高互动{max_engage}，{"已出现扩散" if negative > 5 else "暂无扩散"}。'
            ws.merge_cells(f'A{row}:F{row}'); ws[f'A{row}'] = core; ws[f'A{row}'].font = normal_font; ws[f'A{row}'].alignment = left
            ws.row_dimensions[row].height = 40
            row += 2
            # 2. 数据概览
            ws.merge_cells(f'A{row}:F{row}')
            ws[f'A{row}'] = '2. 数据概览'
            ws[f'A{row}'].font = header_font; ws[f'A{row}'].fill = header_fill
            row += 1
            data_headers = ['指标', '本期', '环比', '指标', '本期', '环比']
            for c, h in enumerate(data_headers, 1):
                cell = ws.cell(row=row, column=c, value=h)
                cell.font = Font(name='微软雅黑', size=10, bold=True); cell.alignment = center; cell.border = thin_border
            row += 1
            data_rows = [
                ('总提及量', total, '—', '负面量', negative, '—'),
                ('负面占比', f'{round(negative/total*100,1) if total else 0}%', '—', '最高单条互动', max_engage, '—'),
                ('正面量', positive, '—', '有效舆情', total, '—'),
            ]
            for dr in data_rows:
                for c, v in enumerate(dr, 1):
                    cell = ws.cell(row=row, column=c, value=v)
                    cell.font = normal_font; cell.alignment = center; cell.border = thin_border
                row += 1
            row += 1
            # 3. 分业态舆情分布
            ws.merge_cells(f'A{row}:F{row}')
            ws[f'A{row}'] = '3. 分业态舆情分布'
            ws[f'A{row}'].font = header_font; ws[f'A{row}'].fill = header_fill
            row += 1
            cat_headers = ['业态/模块', '提及量', '负面量', '正面量', '互动量', '等级']
            for c, h in enumerate(cat_headers, 1):
                cell = ws.cell(row=row, column=c, value=h)
                cell.font = Font(name='微软雅黑', size=10, bold=True); cell.alignment = center; cell.border = thin_border
            row += 1
            for cat in category_order:
                if cat in category_stats:
                    cs = category_stats[cat]
                    level = '🔴' if cs['negative'] > 3 else ('🟡' if cs['negative'] > 0 else '🟢')
                    vals = [cat, cs['total'], cs['negative'], cs['positive'], cs['engagement'], level]
                    for c, v in enumerate(vals, 1):
                        cell = ws.cell(row=row, column=c, value=v)
                        cell.font = normal_font; cell.alignment = center; cell.border = thin_border
                    row += 1
            row += 1
            # 4. 重点笔记清单
            ws.merge_cells(f'A{row}:F{row}')
            ws[f'A{row}'] = '4. 重点笔记清单'
            ws[f'A{row}'].font = header_font; ws[f'A{row}'].fill = header_fill
            row += 1
            note_headers = ['序号', '标题', '作者', '发布时间', '互动量', '情感']
            for c, h in enumerate(note_headers, 1):
                cell = ws.cell(row=row, column=c, value=h)
                cell.font = Font(name='微软雅黑', size=10, bold=True); cell.alignment = center; cell.border = thin_border
            row += 1
            for i, n in enumerate(notes[:20], 1):
                engage = int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
                vals = [i, (n.get('title') or '无标题')[:40], n.get('author_nickname') or '未知', n.get('publish_date') or '—', engage, n.get('sentiment') or '中性']
                for c, v in enumerate(vals, 1):
                    cell = ws.cell(row=row, column=c, value=v)
                    cell.font = normal_font; cell.alignment = center if c != 2 else left; cell.border = thin_border
                row += 1
            # 列宽
            ws.column_dimensions['A'].width = 18
            ws.column_dimensions['B'].width = 35
            ws.column_dimensions['C'].width = 15
            ws.column_dimensions['D'].width = 15
            ws.column_dimensions['E'].width = 12
            ws.column_dimensions['F'].width = 10
            # 使用BytesIO在内存中创建文件，避免磁盘IO问题
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            file_data = output.getvalue()
            resp = Response(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            resp.headers['Content-Disposition'] = f'attachment; filename="{ascii_filename}.xlsx"'
            resp.headers['Content-Length'] = str(len(file_data))
            return resp
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            return jsonify({'ok': False, 'error': 'Excel导出失败：' + str(exc), 'traceback': tb}), 500
    elif fmt == 'docx':
        try:
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            doc = Document()
            # 标题
            title = doc.add_heading(f'广州太古汇{report_title}', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            # 基本信息
            doc.add_paragraph(f'汇报周期：{period_label}')
            doc.add_paragraph(f'汇报人：舆情监测系统')
            doc.add_paragraph(f'舆情等级：{alert_level} — {alert_desc}')
            doc.add_paragraph()
            # 1. 核心结论
            doc.add_heading('1. 核心结论', level=1)
            core = f'本期共监测小红书舆情{total}条，负面{negative}条，主要集中在【{max(category_stats, key=lambda k: category_stats[k]["total"]) if category_stats else "综合"}】，最高互动{max_engage}，{"已出现扩散" if negative > 5 else "暂无扩散"}。'
            doc.add_paragraph(core)
            # 2. 数据概览
            doc.add_heading('2. 数据概览', level=1)
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = '指标'; hdr[1].text = '本期'; hdr[2].text = '指标'; hdr[3].text = '本期'
            data_pairs = [('总提及量', str(total), '负面量', str(negative)), ('负面占比', f'{round(negative/total*100,1) if total else 0}%', '最高互动', str(max_engage)), ('正面量', str(positive), '有效舆情', str(total))]
            for dp in data_pairs:
                row = table.add_row().cells
                for i, v in enumerate(dp): row[i].text = v
            # 3. 分业态分布
            doc.add_heading('3. 分业态舆情分布', level=1)
            table2 = doc.add_table(rows=1, cols=5)
            table2.style = 'Table Grid'
            hdr2 = table2.rows[0].cells
            for i, h in enumerate(['业态', '提及量', '负面量', '正面量', '互动量']): hdr2[i].text = h
            for cat in category_order:
                if cat in category_stats:
                    cs = category_stats[cat]
                    row = table2.add_row().cells
                    row[0].text = cat; row[1].text = str(cs['total']); row[2].text = str(cs['negative']); row[3].text = str(cs['positive']); row[4].text = str(cs['engagement'])
            # 4. 重点笔记
            doc.add_heading('4. 重点笔记清单', level=1)
            for i, n in enumerate(notes[:15], 1):
                engage = int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
                p = doc.add_paragraph()
                p.add_run(f'{i}. {n.get("title") or "无标题"}').bold = True
                doc.add_paragraph(f'   作者：{n.get("author_nickname") or "未知"} | 发布：{n.get("publish_date") or "—"} | 互动：{engage} | 情感：{n.get("sentiment") or "中性"}')
            # 使用BytesIO在内存中创建文件
            output = io.BytesIO()
            doc.save(output)
            output.seek(0)
            file_data = output.getvalue()
            resp = Response(file_data, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            resp.headers['Content-Disposition'] = f'attachment; filename="{ascii_filename}.docx"'
            resp.headers['Content-Length'] = str(len(file_data))
            return resp
        except Exception as exc:
            return jsonify({'ok': False, 'error': 'Word导出失败：' + str(exc)}), 500

# ===== v5.4 系统配置 API =====
@app.route('/api/system/config')
def api_system_config():
    return jsonify({
        'ok': True,
        'version': APP_VERSION,
        'company_domain': os.getenv('TAIKOO_COMPANY_DOMAIN', ''),
        'company_name': os.getenv('TAIKOO_COMPANY_NAME', '广州太古汇'),
        'rednote_cdp_url': os.getenv('XHS_CDP_URL', ''),
        'auto_interval_minutes': int(os.getenv('AUTO_INTERVAL_MINUTES', '90')),
        'daily_report_push_hour': int(os.getenv('DAILY_REPORT_HOUR', '9')),
        'ai_enabled': intelligence.ai_enabled(),
        'ai_provider': intelligence.ai_status().get('provider'),
        'web_discovery_enabled': os.getenv('TAIKOO_WEB_DISCOVERY','1').lower() not in ('0','false','no','off'),
        'monitor_keywords': collector.MONITOR_KEYWORDS if hasattr(collector, 'MONITOR_KEYWORDS') else ['广州太古汇'],
    })

@app.route('/api/system/config', methods=['POST'])
def api_system_config_update():
    data = request.get_json(silent=True) or {}
    # 只允许更新非敏感配置到 .env
    env_path = Path(__file__).parent / '.env'
    updates = {}
    for key in ('TAIKOO_COMPANY_DOMAIN', 'TAIKOO_COMPANY_NAME', 'XHS_CDP_URL', 'AUTO_INTERVAL_MINUTES', 'DAILY_REPORT_HOUR'):
        if key in data:
            updates[key] = str(data[key])
            os.environ[key] = str(data[key])
    if updates and env_path.exists():
        content = env_path.read_text(encoding='utf-8')
        for k, v in updates.items():
            if k in content:
                content = '\n'.join([f'{k}={v}' if line.startswith(k+'=') else line for line in content.split('\n')])
            else:
                content += f'\n{k}={v}'
        env_path.write_text(content, encoding='utf-8')
    return jsonify({'ok': True, 'message': '配置已更新', 'updated': updates})

# ========== v5.4 增项接口配置 ==========
CONFIG_FILE = Path(__file__).parent / 'data' / 'system_config.json'

def _load_config():
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        except: pass
    return {'company_domain': '', 'company_name': '广州太古汇', 'push_emails': [], 'cdp_url': 'http://127.0.0.1:9222', 'auto_interval': 90, 'daily_push_hour': 9}

def _save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')

@app.route('/api/config/company-domain', methods=['GET', 'POST'])
def api_company_domain():
    config = _load_config()
    if request.method == 'GET':
        return jsonify({'ok': True, 'domain': config.get('company_domain', ''), 'name': config.get('company_name', '广州太古汇'), 'configured': bool(config.get('company_domain', ''))})
    data = request.get_json(silent=True) or {}
    action = data.get('action', 'update')
    if action == 'delete':
        config['company_domain'] = ''
        config['company_name'] = '广州太古汇'
        _save_config(config)
        return jsonify({'ok': True, 'message': '公司域名已删除'})
    domain = (data.get('domain') or '').strip()
    name = (data.get('name') or '广州太古汇').strip()
    if not domain:
        return jsonify({'ok': False, 'error': '域名不能为空'}), 400
    config['company_domain'] = domain
    config['company_name'] = name
    _save_config(config)
    return jsonify({'ok': True, 'message': '公司域名已配置，后期一键可用', 'domain': domain, 'name': name})

@app.route('/api/config/emails', methods=['GET', 'POST', 'DELETE'])
def api_push_emails():
    config = _load_config()
    if request.method == 'GET':
        return jsonify({'ok': True, 'emails': config.get('push_emails', []), 'count': len(config.get('push_emails', []))})
    data = request.get_json(silent=True) or {}
    if request.method == 'DELETE':
        email = (data.get('email') or '').strip()
        if email and email in config.get('push_emails', []):
            config['push_emails'].remove(email)
            _save_config(config)
            return jsonify({'ok': True, 'message': f'邮箱 {email} 已删除', 'emails': config['push_emails']})
        return jsonify({'ok': False, 'error': '邮箱不存在'}), 404
    # POST: 添加邮箱
    email = (data.get('email') or '').strip()
    if not email or '@' not in email:
        return jsonify({'ok': False, 'error': '请输入有效的邮箱地址'}), 400
    if 'push_emails' not in config:
        config['push_emails'] = []
    if email in config['push_emails']:
        return jsonify({'ok': False, 'error': '该邮箱已存在'}), 409
    config['push_emails'].append(email)
    _save_config(config)
    return jsonify({'ok': True, 'message': f'邮箱 {email} 已添加', 'emails': config['push_emails'], 'count': len(config['push_emails'])})

@app.route('/api/config/run-code', methods=['POST'])
def api_run_code():
    """GAP-04 统一收口点②：运行代码热更新（调用 dev_exec_core 统一执行核心）。"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    if not code or len(code.strip()) < 5:
        return jsonify({'ok': False, 'error': '请输入有效的Python代码'}), 400
    resp, status = dev_exec_core.execute_dev_code_safe(
        code, 'python', backup=False, app=app, db=db, guard_func=_dev_exec_guard,
        endpoint='/api/config/run-code'
    )
    # GAP-04 修复: guard 返回 (Flask Response, status) 时不可再 jsonify
    if hasattr(resp, 'get_data'):
        return resp, status
    return jsonify(resp), status

@app.route('/api/config/brand-directory')
def api_brand_directory():
    """场内品牌目录查询"""
    brands = _load_brands()
    return jsonify({'ok': True, 'total': len(brands), 'brands': brands[:50], 'updated_at': '2026-08-20'})

# ===== v5.4 品牌进场退场管理（增删改查） =====
@app.route('/api/brands')
def api_brands_list():
    """品牌列表查询，支持搜索、业态筛选、分页"""
    brands = _load_brands()
    keyword = request.args.get('keyword', '').lower()
    category = request.args.get('category', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, int(request.args.get('per_page', 50)))
    filtered = brands
    if keyword:
        filtered = [b for b in filtered if keyword in b.get('brand_en','').lower() or keyword in b.get('brand_cn','').lower()]
    if category:
        filtered = [b for b in filtered if b.get('category') == category]
    total = len(filtered)
    start = (page-1)*per_page
    paged = filtered[start:start+per_page]
    categories = sorted(list(set(b.get('category','') for b in brands if b.get('category'))))
    return jsonify({'ok': True, 'total': total, 'brands': paged, 'page': page, 'per_page': per_page, 'categories': categories})

@app.route('/api/brands', methods=['POST'])
def api_brand_add():
    """添加新品牌（进场）"""
    global _brand_cache
    data = request.get_json(silent=True) or {}
    brand_en = (data.get('brand_en') or '').strip()
    brand_cn = (data.get('brand_cn') or '').strip()
    category = (data.get('category') or '').strip()
    shop = (data.get('shop') or '').strip()
    floor = (data.get('floor') or '').strip()
    if not brand_en:
        return jsonify({'ok': False, 'error': '品牌英文名不能为空'}), 400
    if not category:
        return jsonify({'ok': False, 'error': '业态分类不能为空'}), 400
    brands = _load_brands()
    if any(b['brand_en'].lower() == brand_en.lower() for b in brands):
        return jsonify({'ok': False, 'error': '该品牌已存在'}), 409
    new_brand = {
        'brand_en': brand_en,
        'brand_cn': brand_cn,
        'shop': shop,
        'category': category,
        'floor': floor,
        'is_taikoo_brand': True,
        'added_at': datetime.now().isoformat(),
    }
    brands.append(new_brand)
    _save_brands(brands)
    _brand_cache = None  # 清除缓存
    return jsonify({'ok': True, 'message': f'品牌 {brand_cn or brand_en} 已进场', 'brand': new_brand, 'total': len(brands)})

@app.route('/api/brands/<brand_en>', methods=['PUT'])
def api_brand_update(brand_en):
    """更新品牌信息"""
    global _brand_cache
    data = request.get_json(silent=True) or {}
    brands = _load_brands()
    found = None
    for b in brands:
        if b['brand_en'].lower() == brand_en.lower():
            found = b
            break
    if not found:
        return jsonify({'ok': False, 'error': '品牌不存在'}), 404
    for key in ('brand_cn', 'category', 'shop', 'floor'):
        if key in data:
            found[key] = data[key]
    _save_brands(brands)
    _brand_cache = None
    return jsonify({'ok': True, 'message': '品牌信息已更新', 'brand': found})

@app.route('/api/brands/<brand_en>', methods=['DELETE'])
def api_brand_delete(brand_en):
    """删除品牌（退场）"""
    global _brand_cache
    brands = _load_brands()
    original_len = len(brands)
    brands = [b for b in brands if b['brand_en'].lower() != brand_en.lower()]
    if len(brands) == original_len:
        return jsonify({'ok': False, 'error': '品牌不存在'}), 404
    _save_brands(brands)
    _brand_cache = None
    return jsonify({'ok': True, 'message': f'品牌已退场', 'total': len(brands)})

def _save_brands(brands):
    """保存品牌目录到JSON文件"""
    category_stats = {}
    for b in brands:
        cat = b.get('category', '')
        category_stats[cat] = category_stats.get(cat, 0) + 1
    result = {
        'updated_at': datetime.now().strftime('%Y-%m-%d'),
        'total_brands': len(brands),
        'categories': category_stats,
        'brands': brands
    }
    BRAND_DIR_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

# ===== v5.4 官方信息采集（官网+微博+微信） =====
OFFICIAL_INFO_FILE = Path(__file__).parent / 'data' / 'official_info.json'

@app.route('/api/official-info')
def api_official_info():
    """官方动态信息查询（官网活动、微博、微信）"""
    source = request.args.get('source', 'all')
    limit = min(50, int(request.args.get('limit', 20)))
    info_list = []
    if OFFICIAL_INFO_FILE.exists():
        try:
            info_list = json.loads(OFFICIAL_INFO_FILE.read_text(encoding='utf-8'))
        except:
            info_list = []
    if source != 'all':
        info_list = [i for i in info_list if i.get('source') == source]
    # 按采集时间倒序
    info_list.sort(key=lambda x: x.get('collected_at', ''), reverse=True)
    return jsonify({'ok': True, 'total': len(info_list), 'items': info_list[:limit], 'sources': ['taikoo_official', 'weibo_official', 'wechat_service', 'wechat_subscribe']})

@app.route('/api/official-info/collect', methods=['POST'])
def api_official_collect():
    """触发官方信息采集"""
    try:
        from collector_v2.official_info_scraper import OfficialInfoScraper
        scraper = OfficialInfoScraper(db=db)
        results = scraper.collect_all()
        return jsonify({'ok': True, 'message': f'采集完成，共{len(results)}条', 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== v5.4 全网舆情案例库（模块二） =====
CASE_LIBRARY_FILE = Path(__file__).parent / 'data' / 'case_library.json'

def _load_cases():
    if CASE_LIBRARY_FILE.exists():
        try:
            data = json.loads(CASE_LIBRARY_FILE.read_text(encoding='utf-8'))
            return data.get('cases', [])
        except:
            return []
    return []

def _save_cases(cases):
    categories = sorted(list(set(c.get('category','') for c in cases if c.get('category'))))
    result = {
        'updated_at': datetime.now().strftime('%Y-%m-%d'),
        'total_cases': len(cases),
        'categories': categories,
        'cases': cases
    }
    CASE_LIBRARY_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

@app.route('/api/cases')
def api_cases_list():
    """案例库列表查询，支持搜索、分类筛选、分页"""
    cases = _load_cases()
    keyword = request.args.get('keyword', '').lower()
    category = request.args.get('category', '')
    level = request.args.get('level', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, int(request.args.get('per_page', 20)))
    filtered = cases
    if keyword:
        filtered = [c for c in filtered if keyword in c.get('title','').lower() or keyword in c.get('event','').lower() or keyword in c.get('taikoo_insight','').lower()]
    if category:
        filtered = [c for c in filtered if c.get('category') == category]
    if level:
        filtered = [c for c in filtered if level in c.get('level','')]
    total = len(filtered)
    start = (page-1)*per_page
    paged = filtered[start:start+per_page]
    categories = sorted(list(set(c.get('category','') for c in cases if c.get('category'))))
    return jsonify({'ok': True, 'total': total, 'cases': paged, 'page': page, 'per_page': per_page, 'categories': categories})

@app.route('/api/cases/<case_id>')
def api_case_detail(case_id):
    """案例详情查询"""
    cases = _load_cases()
    case = next((c for c in cases if c.get('id') == case_id), None)
    if not case:
        return jsonify({'ok': False, 'error': '案例不存在'}), 404
    return jsonify({'ok': True, 'case': case})

@app.route('/api/cases', methods=['POST'])
def api_case_add():
    """添加新案例（重大事件收录）"""
    data = request.get_json(silent=True) or {}
    cases = _load_cases()
    # 自动生成ID
    existing_ids = [c.get('id','C-00') for c in cases]
    max_num = max([int(id.replace('C-','')) for id in existing_ids if id.startswith('C-')] + [0])
    new_id = f'C-{max_num+1:02d}'
    new_case = {
        'id': new_id,
        'category': data.get('category', ''),
        'title': data.get('title', ''),
        'location': data.get('location', ''),
        'time': data.get('time', datetime.now().strftime('%Y.%m')),
        'level': data.get('level', '🟡'),
        'event': data.get('event', ''),
        'spread_path': data.get('spread_path', ''),
        'response': data.get('response', ''),
        'effect': data.get('effect', ''),
        'taikoo_insight': data.get('taikoo_insight', ''),
        'reply_formula': data.get('reply_formula', ''),
        'taboo': data.get('taboo', ''),
        'added_at': datetime.now().isoformat(),
    }
    if not new_case['title']:
        return jsonify({'ok': False, 'error': '案例标题不能为空'}), 400
    cases.append(new_case)
    _save_cases(cases)
    return jsonify({'ok': True, 'message': f'案例 {new_id} 已添加', 'case': new_case, 'total': len(cases)})

@app.route('/api/cases/match')
def api_case_match():
    """根据关键词/场景匹配同类案例（专报案例对标用）"""
    keyword = request.args.get('keyword', '').lower()
    category = request.args.get('category', '')
    cases = _load_cases()
    matched = []
    if keyword:
        matched = [c for c in cases if keyword in c.get('title','').lower() or keyword in c.get('event','').lower() or keyword in c.get('category','').lower()]
    elif category:
        matched = [c for c in cases if category in c.get('category','')]
    # 按等级排序，高风险优先
    level_order = {'🔴': 0, '🟡': 1, '🟢': 2}
    matched.sort(key=lambda x: level_order.get(x.get('level','🟢'), 3))
    return jsonify({'ok': True, 'total': len(matched), 'cases': matched[:5]})

# ===== v5.4 舆情事件专报自动生成（模块一1.2） =====
@app.route('/api/special-report/generate', methods=['POST'])
def api_generate_special_report():
    """自动生成舆情事件专报，自动匹配案例库
    触发条件：单条负面互动≥500 / 负面≥3条集中爆发 / 涉及安全歧视违法 / 本地KOC转发 / 集团媒体问询
    """
    data = request.get_json(silent=True) or {}
    keyword = data.get('keyword', '')
    note_id = data.get('note_id', '')
    event_title = data.get('event_title', '')

    # 获取相关笔记
    notes = []
    if note_id:
        note = db.get_note_by_id(note_id) if hasattr(db, 'get_note_by_id') else None
        if note:
            notes = [note]
    if not notes and keyword:
        notes = db.search_notes_by_keyword(keyword, 20) if hasattr(db, 'search_notes_by_keyword') else []
    if not notes:
        # 获取最近的高风险/负面笔记
        notes = db.get_high_risk_notes(10)

    if not notes:
        return jsonify({'ok': False, 'error': '未找到相关舆情数据'}), 404

    # 统计数据
    total = len(notes)
    negative_notes = [n for n in notes if n.get('sentiment') == 'negative' or n.get('risk_level') in ('high', 'critical')]
    negative_count = len(negative_notes)
    max_engagement = max([int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3 for n in notes], default=0)
    high_risk_count = len([n for n in notes if n.get('risk_level') in ('high', 'critical')])

    # 判断舆情等级
    if high_risk_count >= 3 or max_engagement >= 500 or negative_count >= 3:
        level = '🔴重大'
    elif high_risk_count >= 1 or negative_count >= 1:
        level = '🟡关注'
    else:
        level = '🟢平稳'

    # 事件概述
    main_note = notes[0]
    event_name = event_title or main_note.get('title', '')[:50] or keyword or '广州太古汇舆情事件'
    first_date = main_note.get('publish_date', datetime.now().strftime('%Y-%m-%d'))
    platform = main_note.get('source_platform', 'xhs')

    # 传播路径分析
    spread_path = f'{platform}素人发帖 → 评论区共鸣 → 本地KOC/号转发 → 跨平台扩散 → 媒体关注 → 集团问询'
    if max_engagement > 500:
        spread_path += '（已达到高传播阈值）'

    # 案例对标：自动匹配案例库
    match_keyword = keyword or event_name
    cases = _load_cases()
    matched_cases = []
    if match_keyword:
        matched_cases = [c for c in cases if any(kw in match_keyword.lower() for kw in c.get('title','').lower().split()[:3]) or
                         any(kw in c.get('category','').lower() for kw in match_keyword.lower().split()[:2])]
    # 如果匹配不到，按负面类型匹配
    if not matched_cases and negative_notes:
        # 判断负面类型
        text = ' '.join([n.get('title','') + n.get('content','') for n in negative_notes[:3]]).lower()
        if any(kw in text for kw in ['服务', '态度', '歧视', '柜姐', '店员']):
            matched_cases = [c for c in cases if '服务态度' in c.get('category','')]
        elif any(kw in text for kw in ['活动', '排队', '安全', '秩序', '拥挤']):
            matched_cases = [c for c in cases if '活动' in c.get('category','') or '安全' in c.get('category','')]
        elif any(kw in text for kw in ['食品', '卫生', '老鼠', '异物']):
            matched_cases = [c for c in cases if '食品' in c.get('category','')]
        else:
            matched_cases = [c for c in cases if c.get('level') == '🔴'][:3]
    matched_cases = matched_cases[:3]

    # toC影响评估
    toc_impact = '中等' if negative_count >= 2 else '较低'
    toc_detail = f'负面笔记{negative_count}条，最高互动{max_engagement}，品牌好感度可能受影响，到店意愿短期下降'
    if max_engagement > 500:
        toc_impact = '较高'
        toc_detail += '，高传播内容可能引发口碑扩散'

    # toB影响评估
    tob_impact = '中等' if high_risk_count >= 1 else '较低'
    tob_detail = '商户关系可能受影响，集团层面可能问询，招商和合作方关注'
    if level == '🔴重大':
        tob_impact = '较高'
        tob_detail += '，重大事件可能影响租金营收和监管风险'

    # 综合评级
    comprehensive_level = level

    # 应对策略（参考案例库启示）
    strategies = []
    for c in matched_cases:
        insight = c.get('taikoo_insight', '')
        if insight:
            # 提取前两条启示
            lines = [l.strip() for l in insight.split('②') if l.strip()]
            for line in lines[:2]:
                if line and line not in strategies:
                    strategies.append(line)
    if not strategies:
        strategies = [
            '第一时间共情致歉，不回避不辩解',
            '说明已采取动作和核查进度，不敷衍',
            '给出可检验的整改方案，将危机转为改进契机',
        ]

    # 风险预警
    risk_warnings = []
    if max_engagement > 200:
        risk_warnings.append('高互动内容需密切关注传播趋势，必要时启动公关响应')
    if negative_count >= 2:
        risk_warnings.append('负面内容集中，需警惕评论区共鸣引发二次传播')
    if any('安全' in (n.get('title','')+n.get('content','')) for n in notes):
        risk_warnings.append('涉及安全类话题，敏感度高，需最高优先级处理')
    if not risk_warnings:
        risk_warnings.append('暂无特殊风险预警，保持常规监测频率')

    # 生成专报
    report = {
        'report_type': 'special',
        'report_title': f'【舆情专报】{event_name}',
        'level': level,
        'event_name': event_name,
        'first_platform': platform,
        'first_date': first_date,
        'current_volume': total,
        'max_engagement': max_engagement,
        'negative_count': negative_count,
        'high_risk_count': high_risk_count,
        'spread_path': spread_path,
        'matched_cases': [{'id': c['id'], 'title': c['title'], 'level': c['level'], 'insight': c.get('taikoo_insight','')[:100]} for c in matched_cases],
        'toc_impact': toc_impact,
        'toc_detail': toc_detail,
        'tob_impact': tob_impact,
        'tob_detail': tob_detail,
        'comprehensive_level': comprehensive_level,
        'strategies': strategies,
        'risk_warnings': risk_warnings,
        'related_notes': [{'note_id': n.get('note_id',''), 'title': n.get('title','')[:50], 'engagement': int(n.get('likes',0) or 0)+int(n.get('comments',0) or 0)*3, 'sentiment': n.get('sentiment',''), 'risk_level': n.get('risk_level','')} for n in notes[:10]],
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    return jsonify({'ok': True, 'report': report, 'matched_cases_count': len(matched_cases)})


def _smtp_settings():
    return {'host':os.getenv('SMTP_HOST','').strip(),'port':int(os.getenv('SMTP_PORT','465') or 465),'user':os.getenv('SMTP_USER','').strip(),'password':os.getenv('SMTP_PASSWORD',''),'from':os.getenv('SMTP_FROM','').strip(),'ssl':os.getenv('SMTP_SSL','1').lower() not in ('0','false','no')}

@app.route('/api/config/email-settings', methods=['GET','POST'])
def api_email_settings():
    if request.method=='GET':
        st=_smtp_settings()
        return jsonify({'ok':True,'configured':bool(st['host'] and st['user'] and st['password']),'host':st['host'],'port':st['port'],'user':st['user'],'from':st['from'] or st['user'],'ssl':st['ssl']})
    data=request.get_json(silent=True) or {}
    cfg={'host':str(data.get('host','')).strip(),'port':int(data.get('port',465) or 465),'user':str(data.get('user','')).strip(),'from':str(data.get('from','')).strip(),'ssl':bool(data.get('ssl',True))}
    path=Path(__file__).parent/'data'/'email_smtp.json'
    path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    return jsonify({'ok':True,'message':'SMTP非敏感配置已保存；密码请写入SMTP_PASSWORD环境变量。'})

def _send_daily_email():
    st=_smtp_settings()
    cfg_path=Path(__file__).parent/'data'/'email_smtp.json'
    if cfg_path.exists():
        try: st.update(json.loads(cfg_path.read_text(encoding='utf-8')))
        except Exception: pass
    recipients=[x for x in _load_config().get('push_emails',[]) if '@' in x]
    if not recipients or not (st.get('host') and st.get('user') and st.get('password')):
        return {'sent':0,'skipped':'SMTP未配置或未设置收件邮箱'}
    date_str=(datetime.now()-timedelta(days=1)).strftime('%Y-%m-%d')
    try: digest=daily_report.generate_daily_digest(date_str)
    except Exception: digest={}
    body=('广州太古汇小红书舆情日报｜'+date_str+'\n\n'
          '总监测：'+str(digest.get('total_found','—'))+'\n'
          '有效舆情：'+str(digest.get('effective_count','—'))+'\n'
          '负面：'+str(digest.get('negative_count','—'))+'\n'
          '高风险：'+str(digest.get('risk_count','—'))+'\n\n'
          '管理层摘要：\n'+str(digest.get('executive_summary') or digest.get('ai_summary') or '请登录系统查看完整日报。'))
    msg=EmailMessage(); msg['Subject']='【广州太古汇舆情日报】'+date_str; msg['From']=st.get('from') or st['user']; msg['To']=', '.join(recipients); msg.set_content(body)
    try:
        if st.get('ssl'):
            with smtplib.SMTP_SSL(st['host'],int(st.get('port',465)),timeout=20) as server:
                server.login(st['user'],st['password']); server.send_message(msg)
        else:
            with smtplib.SMTP(st['host'],int(st.get('port',587)),timeout=20) as server:
                server.starttls(); server.login(st['user'],st['password']); server.send_message(msg)
        return {'sent':len(recipients),'recipients':recipients}
    except Exception as exc:
        print('[Email] send failed:',exc); return {'sent':0,'error':str(exc)}

# ===== v5.7.0 周报邮件功能 =====
def _send_weekly_email():
    st=_smtp_settings()
    cfg_path=Path(__file__).parent/'data'/'email_smtp.json'
    if cfg_path.exists():
        try: st.update(json.loads(cfg_path.read_text(encoding='utf-8')))
        except Exception: pass
    recipients=[x for x in _load_config().get('push_emails',[]) if '@' in x]
    if not recipients or not (st.get('host') and st.get('user') and st.get('password')):
        return {'sent':0,'skipped':'SMTP未配置或未设置收件邮箱'}
    
    # 计算自然周（周一到周日）
    today=datetime.now().date()
    monday=today - timedelta(days=today.weekday())
    sunday=monday + timedelta(days=6)
    week_str=f'{monday.strftime("%Y-%m-%d")} 至 {sunday.strftime("%Y-%m-%d")}'
    
    # 获取周报数据
    try:
        with db.get_db() as conn:
            weekly_data=weekly_events.weekly_payload(conn, str(monday), str(sunday))
    except Exception as e:
        print('[Weekly] 获取周报数据失败:', e)
        weekly_data={}
    
    # 统计
    total_notes=weekly_data.get('total_notes', 0)
    negative_count=weekly_data.get('negative_count', 0)
    high_risk_count=weekly_data.get('high_risk_count', 0)
    events=weekly_data.get('events', [])
    urgent_events=[e for e in events if e.get('urgency')=='紧急' or e.get('priority')=='high']
    normal_events=[e for e in events if e not in urgent_events]
    
    # 构建邮件正文
    body_lines=[
        f'广州太古汇舆情周报｜{week_str}',
        '',
        '【数据概览】',
        f'总监测笔记：{total_notes}条',
        f'负面笔记：{negative_count}条',
        f'高风险笔记：{high_risk_count}条',
        f'舆情事件：{len(events)}个（紧急{len(urgent_events)}个，一般{len(normal_events)}个）',
        '',
    ]
    
    if urgent_events:
        body_lines.append('【紧急事件】')
        for i, ev in enumerate(urgent_events[:5], 1):
            body_lines.append(f'{i}. {ev.get("title","未知事件")}（风险：{ev.get("risk_level","-")}，关联笔记：{ev.get("note_count",0)}条）')
        body_lines.append('')
    
    if normal_events:
        body_lines.append('【一般事件】')
        for i, ev in enumerate(normal_events[:5], 1):
            body_lines.append(f'{i}. {ev.get("title","未知事件")}（风险：{ev.get("risk_level","-")}，关联笔记：{ev.get("note_count",0)}条）')
        body_lines.append('')
    
    body_lines.append('请登录系统查看完整周报及事件详情。')
    body='\n'.join(body_lines)
    
    msg=EmailMessage()
    msg['Subject']=f'【广州太古汇舆情周报】{week_str}'
    msg['From']=st.get('from') or st['user']
    msg['To']=', '.join(recipients)
    msg.set_content(body)
    
    try:
        if st.get('ssl'):
            with smtplib.SMTP_SSL(st['host'],int(st.get('port',465)),timeout=20) as server:
                server.login(st['user'],st['password']); server.send_message(msg)
        else:
            with smtplib.SMTP(st['host'],int(st.get('port',587)),timeout=20) as server:
                server.starttls(); server.login(st['user'],st['password']); server.send_message(msg)
        print(f'[Weekly] 周报邮件已发送给 {len(recipients)} 人')
        return {'sent':len(recipients),'recipients':recipients,'week':week_str}
    except Exception as exc:
        print('[Weekly] send failed:',exc); return {'sent':0,'error':str(exc)}

@app.route('/api/weekly/send-email', methods=['POST'])
def api_send_weekly_email():
    result=_send_weekly_email()
    return jsonify({'ok': result.get('sent',0)>0, **result})

# ===== 定时任务辅助函数 =====
def _generate_daily_report(date_str=None):
    """生成指定日期的日报（保存到数据库和文件）"""
    try:
        date_str = date_str or datetime.now().strftime('%Y-%m-%d')
        # 调用daily_report模块生成日报摘要
        digest = daily_report.generate_daily_digest(date_str)
        # 保存到日报表
        try:
            with db.get_db() as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO daily_reports (date, title, summary, data_json, created_at) VALUES (?, ?, ?, ?, ?)',
                    (date_str, f'舆情日报 {date_str}', digest.get('summary', ''), 
                     json.dumps(digest, ensure_ascii=False), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                conn.commit()
        except Exception as e:
            print(f'[Report] 日报保存到数据库失败: {e}')
        print(f'[Report] 日报生成完成: {date_str}')
        return True
    except Exception as e:
        print(f'[Report] 日报生成失败: {e}')
        return False

def _generate_weekly_report():
    """生成周报（保存到数据库）"""
    try:
        now = datetime.now()
        week_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
        week_end = now.strftime('%Y-%m-%d')
        # 调用weekly_events模块生成周报
        try:
            with db.get_db() as conn:
                payload = weekly_events.weekly_payload(conn, week_start, week_end)
            # 保存到数据库
            with db.get_db() as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO weekly_reports (week_start, week_end, title, summary, data_json, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (week_start, week_end, f'舆情周报 {week_start}~{week_end}', 
                     f'本周共{payload.get("total_events", 0)}个事件，其中紧急{payload.get("urgent_count", 0)}个',
                     json.dumps(payload, ensure_ascii=False), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                conn.commit()
        except Exception as e:
            print(f'[Report] 周报保存失败: {e}')
        print(f'[Report] 周报生成完成: {week_start}~{week_end}')
        return True
    except Exception as e:
        print(f'[Report] 周报生成失败: {e}')
        return False

# 周报定时任务（每周一9:10生成，9:15发送邮件 - 错峰执行）
def _weekly_scheduler():
    last_week_key=None
    last_weekly_report_date=None
    while True:
        try:
            now=datetime.now()
            today_str = now.strftime('%Y-%m-%d')
            # 每周一9:10生成周报（错峰，避免与日报9:00冲突）
            if now.weekday()==0 and now.hour==9 and 10 <= now.minute < 15 and last_weekly_report_date != today_str:
                try:
                    _generate_weekly_report()
                    last_weekly_report_date = today_str
                    print('[Scheduler] 周报生成完成（周一9:10）')
                except Exception as e:
                    print(f'[Scheduler] 周报生成失败: {e}')
            # 每周一9:15发送周报邮件（错峰）
            if now.weekday()==0 and now.hour==9 and 15 <= now.minute < 20:
                week_key=now.strftime('%Y-W%W')
                if week_key!=last_week_key:
                    last_week_key=week_key
                    print('[Scheduler] 触发周报邮件发送（周一9:15）')
                    _send_weekly_email()
        except Exception as e:
            print('[Scheduler] 周报定时任务错误:', e)
        time.sleep(60)

@app.route('/api/report/special/export', methods=['POST'])
def api_special_report_export():
    data=request.get_json(silent=True) or {}
    report=data.get('report') or {}
    fmt=str(data.get('format','docx')).lower()
    if fmt not in ('docx','pdf','html'): return jsonify({'ok':False,'error':'format仅支持docx/pdf/html'}),400
    title=str(report.get('event_name') or report.get('title') or '广州太古汇舆情专报')
    safe=re.sub(r'[^0-9A-Za-z\u4e00-\u9fff_-]+','_',title)[:80]
    sections=[('一、事件概述',report.get('event_overview','')),('二、传播路径',report.get('spread_path','')),
              ('三、案例对标','\n'.join(f"{c.get('id')}｜{c.get('title')}：{c.get('taikoo_insight','')}" for c in report.get('matched_cases',[]))),
              ('四、toC影响',report.get('toc_detail','')),('五、toB影响',report.get('tob_detail','')),
              ('六、综合评级',report.get('comprehensive_level') or report.get('level','')),
              ('七、应对策略','\n'.join(map(str,report.get('strategies',[])))),
              ('八、风险预警','\n'.join(map(str,report.get('risk_warnings',[]))))]
    if fmt=='html':
        h='<html><head><meta charset="utf-8"><title>'+title+'</title></head><body><h1>'+title+'</h1>'
        for a,b in sections: h+=f'<h2>{a}</h2><div>{str(b).replace(chr(10),"<br>")}</div>'
        h+='</body></html>'
        path=Path(tempfile.gettempdir())/(safe+'.html'); path.write_text(h,encoding='utf-8')
        return send_file(path,as_attachment=True,download_name=path.name,mimetype='text/html')
    if fmt=='docx':
        try:
            from docx import Document
            doc=Document(); doc.add_heading(title,0)
            for a,b in sections:
                doc.add_heading(a,1)
                for line in str(b).splitlines() or ['—']: doc.add_paragraph(line)
            path=Path(tempfile.gettempdir())/(safe+'.docx'); doc.save(path)
            return send_file(path,as_attachment=True,download_name=path.name,mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        except Exception as exc: return jsonify({'ok':False,'error':'DOCX导出依赖未安装：'+str(exc)}),503
    try:
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        path=Path(tempfile.gettempdir())/(safe+'.pdf'); styles=getSampleStyleSheet()
        cn=ParagraphStyle('CN', parent=styles['Normal'], fontName='STSong-Light', fontSize=10, leading=16)
        h1=ParagraphStyle('CNH1', parent=styles['Heading1'], fontName='STSong-Light', fontSize=15, leading=20)
        story=[Paragraph(re.sub(r'([&<>])',lambda m:{'&':'&amp;','<':'&lt;','>':'&gt;'}[m.group(1)],title),ParagraphStyle('CNT',parent=styles['Title'],fontName='STSong-Light')),Spacer(1,12)]
        for a,b in sections:
            txt=str(b).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n','<br/>')
            story += [Paragraph(str(a),h1),Paragraph(txt or '—',cn),Spacer(1,8)]
        SimpleDocTemplate(str(path)).build(story)
        return send_file(path,as_attachment=True,download_name=path.name,mimetype='application/pdf')
    except Exception as exc: return jsonify({'ok':False,'error':'PDF导出依赖未安装：'+str(exc)}),503

@app.route('/api/special-report/check-trigger')
def api_check_special_report_trigger():
    """检查是否触发专报条件"""
    notes = db.get_high_risk_notes(20)
    negative_notes = [n for n in notes if n.get('sentiment') == 'negative']
    max_engagement = max([int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3 for n in notes], default=0)

    triggers = []
    if max_engagement >= 500:
        triggers.append(f'单条负面互动≥500（当前最高{max_engagement}）')
    if len(negative_notes) >= 3:
        triggers.append(f'负面帖≥3条集中爆发（当前{len(negative_notes)}条）')
    if any('安全' in (n.get('title','')+n.get('content','')) or '歧视' in (n.get('title','')+n.get('content','')) for n in notes):
        triggers.append('涉及安全·歧视·违法类话题')

    return jsonify({'ok': True, 'triggered': len(triggers) > 0, 'triggers': triggers, 'max_engagement': max_engagement, 'negative_count': len(negative_notes)})

def _next_half_hour(now=None):
    now=now or datetime.now()
    minute=30 if now.minute < 30 else 60
    candidate=now.replace(minute=minute % 60, second=0, microsecond=0)
    if minute == 60:
        candidate=now.replace(minute=0, second=0, microsecond=0)+timedelta(hours=1)
    return candidate

# v5.8.6 统一动态调度（影子模式）：固定时钟恢复为“唤醒检查点”，动态决策器先只做对照记录、
# 不门控生产；门控灰度经回归与确认后再切换。任何异常一律 fail-open，绝不阻断自动采集。
_shadow_schedule_planner = None
def _get_shadow_planner():
    global _shadow_schedule_planner
    if _shadow_schedule_planner is None:
        try:
            from platform_adapters.scheduling import get_planner
            _shadow_schedule_planner = get_planner()  # 包级进程单例，与采集结果回写共享状态
        except Exception as e:
            print(f'[ShadowPlanner] init fail (non-blocking): {e}')
            _shadow_schedule_planner = False
    return _shadow_schedule_planner or None


def scheduler_loop():
    """自动采集调度器：固定时间点作为唤醒检查点，叠加账号频率保护；
    v5.8.6 起由统一动态决策器做影子对照(动态间隔/状态驱动/next_run_at)，门控后续灰度。"""
    auto_collect_hours = [8, 10, 12, 14, 16, 18, 20, 22, 23]
    today_auto_hours = set()  # 今天已执行的自动采集小时
    last_report_date = ''
    last_email_date = ''
    last_date_check = ''
    last_midnight_report_date = ''  # 00:00日报生成记录
    last_morning_report_date = ''   # 09:00日报生成记录
    last_evening_report_date = ''   # 23:30日报生成记录
    _last_keepalive_min = -1        # 小红书双平台保活检查（每 30 分钟一次）
    
    import os as _os
    _os.environ.setdefault('ZBC_SCHED_GATE_MODE', 'enforce')
    print(f'[Scheduler] 自适应调度器启动，gate_mode={_os.environ.get("ZBC_SCHED_GATE_MODE")}（固定时间点仅作历史参考，实际由 ShadowPlanner 门控）')
    
    while True:
        try:
            now = datetime.now()
            today_str = now.strftime('%Y-%m-%d')
            
            # 跨天重置已执行小时记录
            if last_date_check != today_str:
                today_auto_hours = set()
                last_date_check = today_str
                print(f'[Scheduler] 新的一天 {today_str}，自动采集次数已重置')

            # ===== 小红书双平台登录保活定时检查（掉线自动再弹核心） =====
            # 每 30 分钟对 rednote_hk（9223）/ xhs_cn（9222）recheck：
            #   已登录 → 自动标记当日保活完成；掉线 → 重置当日标记 + need_relogin，
            #   前端轮询到 need_relogin=true 自动弹登录窗。仅审计/标记，不阻断采集。
            _kbucket = (now.hour * 60 + now.minute) // 30
            if _kbucket != _last_keepalive_min:
                _last_keepalive_min = _kbucket
                try:
                    import xhs_collection_optimizer as _xco
                    for _kpf in ('rednote_hk', 'xhs_cn'):
                        try:
                            _kd = _xco.recheck_keepalive(_kpf)
                            print(f'[Keepalive] {_kpf} -> {_kd.get("status")} need_relogin={_kd.get("need_relogin")} {_kd.get("message", "")}')
                        except Exception as _ke2:
                            print(f'[Keepalive] {_kpf} check fail: {_ke2}')
                except Exception as _ke1:
                    print(f'[Keepalive] 双平台保活检查失败: {_ke1}')
            
            # 自适应调度（GAP-05 门控，2026-09-02 用户签字）：不再用固定时间点，
            # 由 ShadowPlanner 根据状态（上次采集/成功率/熔断/频率）决定此刻是否采集；
            # gate 只收紧不放松，异常 fail-open 回退允许，绝不因新组件卡死既有调度。
            _should_run = True
            _gate_mode = 'no-planner'
            _sd = None
            _sp = _get_shadow_planner()
            if _sp is not None:
                try:
                    from platform_adapters.scheduling.gate import gate_should_run
                    _should_run, _sd, _gate_mode = gate_should_run(
                        _sp, 'xhs', now=now, hard_allow=True, persist=True)
                    if _sd is not None:
                        print(f'[Scheduler] gate={_gate_mode} should_run={_should_run} code={_sd.reason_code} next={_sd.next_run_at}')
                except Exception as _e:
                    _should_run, _gate_mode = True, 'fallback'
                    print(f'[Scheduler] gate eval fail-open: {_e}')

            if _should_run:
                # 账号频率保护（生产既有逻辑，保留）
                rate_ok, rate_msg = xhs_cookie_bridge.check_rate_limit('auto')
                if rate_ok:
                    try:
                        # 自适应参数：max_scroll 由 adaptive_engine 根据状态决定（回退6）
                        try:
                            import adaptive_engine as _ae
                            _max_scroll = int(_ae.adaptive_engine.get_current_params().get('max_scroll', 6))
                        except Exception:
                            _max_scroll = 6
                        # 使用xhs_cookie_bridge创建任务（自动接入次数限制和账号保护）
                        task_id = xhs_cookie_bridge.create_task(
                            keywords=xhs_cookie_bridge.DEFAULT_KEYWORDS,
                            max_scroll=_max_scroll,
                            run_type='auto'
                        )
                        print(f'[Scheduler] 自适应采集触发 gate={_gate_mode} max_scroll={_max_scroll} 任务ID: {task_id}')
                        # 不在触发瞬间乐观回写 SUCCESS：任务刚创建不代表成功。
                        # 真实六态由任务完成时 xhs_cookie_bridge._shadow_record_result 回写，
                        # 避免把“已创建任务”伪装成“采集成功/有数据”。
                    except Exception as e:
                        print(f'[Scheduler] 自适应采集创建任务失败: {e}')
                else:
                    print(f'[Scheduler] 自适应采集跳过（频率限制）: {rate_msg}')
            
            # 日报生成 - 三个时间点确保信息准确性
            # 1. 00:00 - 生成前一天的日报（总结前一天完整数据）
            if now.hour == 0 and now.minute < 5 and last_midnight_report_date != today_str:
                try:
                    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                    _generate_daily_report(yesterday)
                    last_midnight_report_date = today_str
                    print(f'[Scheduler] 00:00日报生成完成（{yesterday}）')
                except Exception as e:
                    print(f'[Scheduler] 00:00日报生成失败: {e}')
            
            # 2. 09:00 - 生成当天的日报（早间数据汇总）
            if now.hour == 9 and now.minute < 5 and last_morning_report_date != today_str:
                try:
                    _generate_daily_report(today_str)
                    last_morning_report_date = today_str
                    print(f'[Scheduler] 09:00日报生成完成（{today_str}）')
                except Exception as e:
                    print(f'[Scheduler] 09:00日报生成失败: {e}')
            
            # 3. 23:30 - 生成当天的日报（晚间完整数据，确保信息准确性）
            if now.hour == 23 and 30 <= now.minute < 35 and last_evening_report_date != today_str:
                try:
                    _generate_daily_report(today_str)
                    last_evening_report_date = today_str
                    print(f'[Scheduler] 23:30日报生成完成（{today_str}，晚间完整数据）')
                except Exception as e:
                    print(f'[Scheduler] 23:30日报生成失败: {e}')
            
            # 23:55生成所有周期报告（周/月/年）
            if now.hour == 23 and now.minute >= 55 and last_report_date != today_str:
                try:
                    _generate_all_reports()
                    last_report_date = today_str
                    print(f'[Scheduler] 周期报告生成完成 {today_str}')
                except Exception as e:
                    print(f'[Scheduler] 周期报告生成失败: {e}')
            
            # 每日9:05推送日报邮件（错峰，避免与9:00日报生成冲突）
            if now.hour == 9 and 5 <= now.minute < 10 and last_email_date != today_str:
                try:
                    print('[Email]', _send_daily_email())
                    last_email_date = today_str
                except Exception as e:
                    print(f'[Scheduler] 邮件推送失败: {e}')
                    
        except Exception as e:
            print('[Scheduler]', e)
        time.sleep(20)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='广州太古汇舆情监测系统')
    parser.add_argument('--host',default=APP_HOST,help='监听地址，默认0.0.0.0（支持本地/局域网/5G热点访问）')
    parser.add_argument('--port',type=int,default=APP_PORT)
    parser.add_argument('--no-scheduler',action='store_true',help='仅启动 Web，不启动自动采集调度器')
    args=parser.parse_args()
    if not args.no_scheduler:
        # v5.8.6 恢复主采集调度器：固定时钟唤醒 + 动态决策影子对照（周报线程另行评估后启用）
        threading.Thread(target=scheduler_loop, daemon=True, name='scheduler').start()
    # 双子星库 Contract: 小红书 P0 长期驻场心跳（Session 失效→扫码恢复→白名单采集）
    try:
        xhs_p0_orchestrator.start_resident()
        print('[XHS-P0] 小红书 P0 驻场心跳已启动')
    except Exception as _pe:
        print(f'[XHS-P0] 驻场心跳启动失败: {_pe}')
        # threading.Thread(target=_weekly_scheduler,daemon=True,name='weekly_scheduler').start()
        print('[Scheduler] 主采集调度器已启用（唤醒点+动态影子对照）')
    
    # 启动内存监控（防止OOM崩溃）——崩溃根因(重复endpoint)已修复，重新启用
    try:
        mem_opt = memory_optimizer.get_memory_optimizer()
        mem_opt.start_monitoring()
    except Exception as e:
        print(f'[Memory] 内存监控启动失败: {e}')

    # 启动进程级稳定性监控（watchdog+heartbeat，仅记录不强制退出）
    try:
        stab_mon = stability_monitor.get_stability_monitor()
        stab_mon.start_monitoring()
    except Exception as e:
        print(f'[Stability] 稳定性监控启动失败: {e}')
    
    auth_state='开启' if _auth_enabled() else '关闭（仅建议本机访问）'
    print(f'广州太古汇舆情监测系统 v{APP_VERSION} | {args.host}:{args.port} | 自动采集：{not args.no_scheduler} | HTTP认证：{auth_state}')

# ===== v5.8.0 新增API =====

# ===== 小红书 P0 生产编排 API（双子星库 Contract） =====
@app.route('/api/xhs/p0/status', methods=['GET'])
def api_xhs_p0_status():
    """前端轮询：小红书 P0 驻场/会话/恢复状态聚合"""
    try:
        return jsonify({'ok': True, **xhs_p0_orchestrator.get_status()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/p0/recovery/complete', methods=['POST'])
def api_xhs_p0_recovery_complete():
    """人工扫码后触发：关闭恢复任务，标记 Session 已恢复"""
    try:
        data = request.get_json(silent=True) or {}
        success = bool(data.get('success', True))
        return jsonify(xhs_p0_orchestrator.complete_scan_recovery(success=success))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/p0/collection', methods=['POST'])
def api_xhs_p0_collection():
    """手动触发采集：身份硬白名单门控后进入采集链"""
    try:
        data = request.get_json(silent=True) or {}
        account = data.get('account')
        keywords = data.get('keywords')
        max_scroll = int(data.get('max_scroll', 4))
        return jsonify(xhs_p0_orchestrator.trigger_collection(
            account_name=account, keywords=keywords, max_scroll=max_scroll))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== 稳定性监控API =====
@app.route('/api/stability/status', methods=['GET'])
def api_stability_status():
    """获取稳定性监控状态"""
    try:
        from stability_monitor import get_stability_monitor
        monitor = get_stability_monitor()
        status = monitor.get_status_report()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/stability/heartbeat', methods=['GET'])
def api_stability_heartbeat():
    """获取最近的心跳记录"""
    try:
        from stability_monitor import get_stability_monitor
        monitor = get_stability_monitor()
        log_file = monitor.heartbeat_log
        
        heartbeats = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-20:]  # 最近20条
                for line in lines:
                    try:
                        heartbeats.append(json.loads(line.strip()))
                    except Exception:
                        pass
        
        return jsonify({'ok': True, 'heartbeats': heartbeats, 'count': len(heartbeats)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/stability/crash-log', methods=['GET'])
def api_stability_crash_log():
    """获取崩溃日志"""
    try:
        from stability_monitor import get_stability_monitor
        monitor = get_stability_monitor()
        log_file = monitor.crash_log
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'ok': True, 'has_crash': True, 'content': content[-5000:]})  # 最后5000字符
        else:
            return jsonify({'ok': True, 'has_crash': False, 'message': '暂无崩溃记录'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== 合并仪表盘API（减少前端轮询请求数）=====
@app.route('/api/dashboard/all', methods=['GET'])
def api_dashboard_all():
    """
    合并仪表盘API：一次性返回所有前端需要的数据
    替代原来的8个独立API请求，减少并发请求，提高稳定性
    
    包含：overview, stats, alerts, events, risk-alerts, hot-topics, ai-status, status
    """
    conn = None
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        DB_PATH = db.DB_PATH
        # 使用WAL模式和超时配置，提高多线程稳定性
        conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        result = {'ok': True, 'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        total_notes = 0
        
        # 1. 概览统计
        try:
            cursor.execute("SELECT COUNT(*) as total FROM notes")
            total_notes = cursor.fetchone()['total']
            cursor.execute("SELECT COUNT(*) as verified FROM notes WHERE is_taikoo_verified=1")
            verified_notes = cursor.fetchone()['verified']
            cursor.execute("SELECT COUNT(*) as negative FROM notes WHERE sentiment='negative'")
            negative_notes = cursor.fetchone()['negative']
            cursor.execute("SELECT COUNT(*) as today FROM notes WHERE DATE(collected_at)=DATE('now')")
            today_notes = cursor.fetchone()['today']
            # 近14天趋势（与 /api/overview 同口径），补齐主轮询 renderTrend 所需，避免“暂无趋势数据”
            _now = datetime.now(); _start = (_now - timedelta(days=13)).strftime('%Y-%m-%d'); _end = _now.strftime('%Y-%m-%d')
            _cl, _sp = _subject_sql_and_values()
            _trows = cursor.execute(
                f"SELECT publish_date, COUNT(*) total, SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) negative, "
                f"SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) high FROM notes "
                f"WHERE is_taikoo_verified=1 AND {_cl} AND publish_date BETWEEN ? AND ? GROUP BY publish_date",
                tuple(_sp) + (_start, _end)).fetchall()
            _by = {r['publish_date']: {'total': r['total'] or 0, 'negative': r['negative'] or 0, 'high': r['high'] or 0} for r in _trows}
            _trend = []
            for _i in range(14):
                _dd = (_now - timedelta(days=13 - _i)).strftime('%Y-%m-%d')
                _xx = _by.get(_dd, {'total': 0, 'negative': 0, 'high': 0})
                _trend.append({'date': _dd, 'label': _dd[5:], 'total': _xx['total'], 'negative': _xx['negative'], 'high': _xx['high']})

            result['overview'] = {
                'total_notes': total_notes,
                'verified_notes': verified_notes,
                'negative_notes': negative_notes,
                'today_notes': today_notes,
                'unanalyzed': total_notes - verified_notes,
                'trend': _trend
            }
        except Exception as e:
            result['overview'] = {'error': str(e), 'total_notes': 0}
        
        # 2. 统计数据（补全前端需要的所有字段）
        try:
            cursor.execute("SELECT sentiment, COUNT(*) as count FROM notes GROUP BY sentiment")
            sentiment_stats = {row['sentiment']: row['count'] for row in cursor.fetchall()}
            cursor.execute("SELECT COUNT(*) FROM notes WHERE risk_level='high'")
            high_risk = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM notes WHERE risk_level='medium'")
            medium_risk = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM notes WHERE risk_level='low'")
            low_risk = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(likes+comments+shares+collects),0) FROM notes")
            total_eng = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(comments),0) FROM notes")
            total_comments = cursor.fetchone()[0]
            result['stats'] = {
                'sentiment': sentiment_stats,
                'total': total_notes,
                'positive': sentiment_stats.get('positive', 0),
                'neutral': sentiment_stats.get('neutral', 0),
                'negative': sentiment_stats.get('negative', 0),
                'high_risk': high_risk,
                'medium_risk': medium_risk,
                'low_risk': low_risk,
                'total_engagements': total_eng,
                'total_comments': total_comments,
                'categories': db.get_category_distribution()
            }
        except Exception as e:
            result['stats'] = {'error': str(e), 'total': total_notes}
        
        # 3. 未读告警
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
            if cursor.fetchone():
                cursor.execute("SELECT * FROM alerts WHERE is_read=0 ORDER BY rowid DESC LIMIT 20")
                result['alerts'] = [dict(row) for row in cursor.fetchall()]
            else:
                result['alerts'] = []
        except Exception as e:
            result['alerts'] = []
        
        # 4. 事件列表（质量分级：重点事件优先，泛化“相关讨论”折叠、占位备注隐藏，与事件中心同口径）
        try:
            _cur = db.get_events_curated(12)
            result['events'] = _cur['featured']
            result['events_meta'] = {'generic_count': _cur['generic_count'], 'noise_count': _cur['noise_count']}
        except Exception as e:
            result['events'] = []
        
        # 5. 风险告警（从notes表查询高/中风险笔记，risk_alerts表不存在）
        try:
            cursor.execute("""
                SELECT id, note_id, title, author_nickname, sentiment, risk_level, risk_score,
                       likes, comments, shares, collects, collected_at, publish_date, url,
                       category, summary, event_hint
                FROM notes 
                WHERE risk_level IN ('high','medium') 
                ORDER BY risk_score DESC, collected_at DESC 
                LIMIT 20
            """)
            result['risk_alerts'] = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            result['risk_alerts'] = []
        
        # 6. 热门话题（使用category字段分组）
        try:
            cursor.execute("""
                SELECT category as topic, COUNT(*) as count,
                       SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) as negative,
                       SUM(CASE WHEN sentiment='neutral' THEN 1 ELSE 0 END) as neutral
                FROM notes 
                WHERE category IS NOT NULL AND category != ''
                GROUP BY category 
                ORDER BY count DESC 
                LIMIT 14
            """)
            result['hot_topics'] = [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            result['hot_topics'] = []
        
        # 7. AI状态
        try:
            result['ai_status'] = intelligence.ai_status()
        except Exception as e:
            result['ai_status'] = {'enabled': False, 'error': str(e)}
        
        # 8. 系统状态
        try:
            result['system_status'] = {
                'version': APP_VERSION,
                'collector': 'Playwright/XHS search + rednote CDP',
                'auto_collect': True,
                'auth_enabled': _auth_enabled()
            }
        except Exception as e:
            result['system_status'] = {'error': str(e)}

        # 9. v5.9.0 合并字段：供前端统一轮询，避免多个独立30s请求
        try:
            cur2 = conn.cursor()
            # 待审核负面数（口径与 /api/negative/pending 一致）
            cur2.execute("SELECT COUNT(*) AS c FROM notes WHERE sentiment='negative' AND (negative_confirmed=0 OR negative_confirmed IS NULL)")
            result['pending_negative'] = cur2.fetchone()['c']
            # 未读预警数（口径与 /api/alerts?unread=1 一致；无 is_read 列时回退为 alerts 长度）
            try:
                cur2.execute("SELECT COUNT(*) AS c FROM alerts WHERE is_read=0")
                result['unread_alerts'] = cur2.fetchone()['c']
            except Exception:
                result['unread_alerts'] = len(result.get('alerts', []))
            # 数据变更摘要（口径与 /api/dashboard/changes 一致）
            result['changes'] = {
                'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': APP_VERSION,
                'stats': db.get_stats()
            }
        except Exception as e:
            result['poll_extras_error'] = str(e)

        return jsonify(result)
    
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        # 确保数据库连接总是被关闭
        if conn:
            try:
                conn.close()
            except:
                pass

# ===== 微博登录管理API =====
@app.route('/api/weibo/login-status', methods=['GET'])
def api_weibo_login_status():
    """获取微博登录状态"""
    try:
        from weibo_login_manager import get_weibo_manager
        manager = get_weibo_manager()
        status = manager.check_login_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/weibo/start-login', methods=['POST'])
def api_weibo_start_login():
    """启动微博扫码登录（异步）"""
    try:
        from weibo_login_manager import get_weibo_manager
        manager = get_weibo_manager()
        
        # 在后台线程中启动登录
        def login_thread():
            try:
                manager.login_with_qrcode(headless=False, timeout=300)
            except Exception as e:
                print(f'[WeiboLogin] 登录线程异常: {e}')
        
        threading.Thread(target=login_thread, daemon=True, name='weibo_login').start()
        
        return jsonify({'ok': True, 'message': '微博登录已启动，请在浏览器中扫码登录', 'timeout': 300})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/weibo/clear-login', methods=['POST'])
def api_weibo_clear_login():
    """清除微博登录数据"""
    try:
        from weibo_login_manager import get_weibo_manager
        manager = get_weibo_manager()
        success = manager.clear_login_data()
        return jsonify({'ok': success, 'message': '微博登录数据已清除' if success else '清除失败'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/weibo/cookies', methods=['GET'])
def api_weibo_cookies():
    """获取微博cookies（用于采集）"""
    try:
        from weibo_login_manager import get_weibo_manager
        manager = get_weibo_manager()
        cookies = manager.get_cookies()
        cookie_string = manager.get_cookie_string()
        return jsonify({
            'ok': True, 
            'cookie_count': len(cookies), 
            'cookie_string': cookie_string[:100] + '...' if len(cookie_string) > 100 else cookie_string
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== B站登录管理API =====
@app.route('/api/bilibili/login-status', methods=['GET'])
def api_bilibili_login_status():
    """获取B站登录状态"""
    try:
        from bilibili_login_manager import get_bilibili_manager
        manager = get_bilibili_manager()
        status = manager.check_login_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/bilibili/search', methods=['GET'])
def api_bilibili_search():
    """搜索B站视频"""
    try:
        from bilibili_login_manager import get_bilibili_manager
        manager = get_bilibili_manager()
        
        keyword = request.args.get('keyword', '广州太古汇')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        result = manager.search_videos(keyword, page, page_size)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/bilibili/clear-login', methods=['POST'])
def api_bilibili_clear_login():
    """清除B站登录数据"""
    try:
        from bilibili_login_manager import get_bilibili_manager
        manager = get_bilibili_manager()
        success = manager.clear_login_data()
        return jsonify({'ok': success, 'message': 'B站登录数据已清除' if success else '清除失败'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== 全网话题搜集API（微博+B站）=====
@app.route('/api/web/collect', methods=['POST'])
def api_web_collect():
    """触发全网话题搜集（微博+B站）"""
    try:
        data = request.get_json(silent=True) or {}
        keyword = data.get('keyword', '广州太古汇')
        platforms = data.get('platforms', ['weibo', 'bilibili'])
        
        results = {}
        
        # B站搜索
        if 'bilibili' in platforms:
            try:
                from bilibili_login_manager import get_bilibili_manager
                manager = get_bilibili_manager()
                bili_result = manager.search_videos(keyword, page=1, page_size=20)
                results['bilibili'] = bili_result
            except Exception as e:
                results['bilibili'] = {'ok': False, 'error': str(e)}
        
        # 微博搜索（使用cookie直接请求）
        if 'weibo' in platforms:
            try:
                from weibo_login_manager import get_weibo_manager
                weibo_manager = get_weibo_manager()
                cookie_string = weibo_manager.get_cookie_string()
                
                if cookie_string:
                    import requests
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Cookie': cookie_string,
                        'Referer': 'https://s.weibo.com/'
                    }
                    # 时间范围动态化：近30天，避免写死日期过期
                    _d_end = datetime.now(); _d_start = _d_end - timedelta(days=30)
                    from urllib.parse import quote as _q
                    url = f'https://s.weibo.com/weibo?q={_q(keyword)}&typeall=1&suball=1&timescope=custom:{_d_start:%Y-%m-%d}:{_d_end:%Y-%m-%d}&Refer=g'
                    response = requests.get(url, headers=headers, timeout=15)
                    
                    # 简单解析微博搜索结果
                    import re
                    import html as _html
                    content = response.text
                    # 提取微博内容（简化版）
                    cards = re.findall(r'<p class="txt"[^>]*>(.*?)</p>', content, re.DOTALL)
                    _cands = []
                    for card in cards[:40]:
                        t = re.sub(r'<[^>]+>', '', card)
                        t = _html.unescape(t)
                        t = re.sub(r'[\ue000-\uf8ff]', '', t)
                        t = re.sub(r'[\u200b-\u200f\ufeff\u2060]', '', t)
                        t = re.sub(r'\s+', ' ', t).strip()
                        t = re.sub(r'(展开全文c?|展开c|收起全文d?|收起d|全文)$', '', t).strip()
                        if t: _cands.append(t[:200])
                    # 前缀归并：同一条微博的列表截断版与全文版前40字相同，保留最完整版本
                    _best = {}
                    for t in _cands:
                        k = t[:40]
                        if k not in _best or len(t) > len(_best[k]): _best[k] = t
                    weibo_items = [{'content': t, 'platform': 'weibo', 'type': 'post'} for t in _best.values()]
                    results['weibo'] = {
                        'ok': True,
                        'keyword': keyword,
                        'total': len(weibo_items),
                        'items': weibo_items
                    }
                else:
                    results['weibo'] = {'ok': False, 'error': '微博未登录'}
            except Exception as e:
                results['weibo'] = {'ok': False, 'error': str(e)}
        
        # 保存到全网话题表（对齐 web_topics 真实结构：topic/source/sentiment/mention_count/first_seen/last_seen/tags/summary/created_at）
        try:
            conn = sqlite3.connect(db.DB_PATH, timeout=30)
            now_s = datetime.now().strftime('%Y-%m-%d %H:%M:%S'); today_s = datetime.now().strftime('%Y-%m-%d')
            def _save_topic(topic, source, mention, tags, summary):
                topic = (topic or '').strip()
                if not topic: return
                conn.execute("""INSERT INTO web_topics(topic,source,sentiment,relevance_score,mention_count,first_seen,last_seen,tags,summary,created_at)
                                SELECT ?,?,'pending',0,?,?,?,?,?,?
                                WHERE NOT EXISTS(SELECT 1 FROM web_topics WHERE topic=? AND source=?)""",
                             (topic[:200], source, mention or 0, today_s, today_s, tags or '', (summary or '')[:500], now_s, topic[:200], source))
            # B站视频
            if results.get('bilibili', {}).get('ok'):
                for video in results['bilibili'].get('videos', []):
                    _save_topic(video.get('title',''), 'bilibili', video.get('play',0), keyword,
                                json.dumps({'url':video.get('url',''),'author':video.get('author','')}, ensure_ascii=False))
            # 微博内容
            if results.get('weibo', {}).get('ok'):
                for item in results['weibo'].get('items', []):
                    _save_topic(item.get('content',''), 'weibo', 0, keyword, item.get('content',''))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f'[WebCollect] 保存到数据库失败: {e}')
        
        return jsonify({
            'ok': True,
            'keyword': keyword,
            'platforms': platforms,
            'results': {k: {'ok': v.get('ok'),
                            'count': len(v.get('videos', v.get('items', []))) if isinstance(v.get('videos', v.get('items')), list) else v.get('total', 0),
                            'total': v.get('total', 0)} for k, v in results.items()}
        })
    
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

def get_db():
    db_path = db.DB_PATH
    conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # 启用WAL模式，提高并发性能
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('PRAGMA synchronous=NORMAL')
    except Exception:
        pass
    return conn


@app.route('/api/web/topics', methods=['GET'])
def api_web_topics_v580():
    """获取全网话题列表"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = sqlite3.connect(db.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM web_topics 
        ORDER BY mention_count DESC, last_seen DESC
        LIMIT ?
    """, (limit,))
    topics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'ok': True, 'topics': topics, 'count': len(topics)})


@app.route('/api/web/topics/refresh', methods=['POST'])
def api_web_topics_refresh_v580():
    """刷新全网话题（从浏览器搜索，不占用小红书次数）"""
    # 这里可以集成浏览器搜索逻辑
    # 暂时返回模拟数据
    return jsonify({
        'ok': True,
        'message': '全网话题刷新中（不占用小红书检索次数）',
        'status': 'processing'
    })


@app.route('/api/web/events', methods=['GET'])
def api_web_events_v580():
    """获取全网事件列表"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = sqlite3.connect(db.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM web_events 
        ORDER BY discovered_at DESC
        LIMIT ?
    """, (limit,))
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'ok': True, 'events': events, 'count': len(events)})


@app.route('/api/web/brand-industry', methods=['GET'])
def api_web_brand_industry_v580():
    """品牌业态全网监测"""
    brand_id = request.args.get('brand_id')
    industry = request.args.get('industry')
    limit = request.args.get('limit', 50, type=int)
    
    conn = sqlite3.connect(db.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM brand_industry_monitor WHERE 1=1"
    params = []
    
    if brand_id:
        query += " AND brand_name LIKE ?"
        params.append(f"%{brand_id}%")
    if industry:
        query += " AND industry = ?"
        params.append(industry)
    
    query += " ORDER BY note_count DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    brands = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'ok': True, 'brands': brands, 'count': len(brands)})


@app.route('/api/ai/analyze', methods=['POST'])
def api_ai_analyze_v580():
    """AI分析舆情"""
    data = request.get_json(silent=True) or {}
    note_id = data.get('note_id')
    provider = data.get('provider', 'local')
    analysis_type = data.get('type', 'summary')  # summary/sentiment/risk/event
    
    # 这里可以集成实际的AI调用逻辑
    # 暂时返回模拟数据
    return jsonify({
        'ok': True,
        'provider': provider,
        'note_id': note_id,
        'analysis': {
            'summary': '这是AI分析的摘要内容',
            'sentiment': 'neutral',
            'risk_level': 'low',
            'event_type': 'general'
        }
    })


@app.route('/api/collection/counter', methods=['GET'])
def api_collection_counter_v580():
    """获取今日采集计数"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(db.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM collection_counters WHERE date = ?", (today,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("INSERT INTO collection_counters (date, daily_count, manual_count, auto_count) VALUES (?, 0, 0, 0)", (today,))
        conn.commit()
        cursor.execute("SELECT * FROM collection_counters WHERE date = ?", (today,))
        row = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'ok': True,
        'date': today,
        'daily_count': row['daily_count'],
        'manual_count': row['manual_count'],
        'auto_count': row['auto_count'],
        'daily_limit': 12,
        'manual_limit': 3,
        'auto_limit': 9,
        'last_collect_at': row['last_collect_at']
    })

# ===== v5.6.6 全网话题事件搜集（普通浏览器搜索，不占用小红书检索次数） =====
import urllib.request
import urllib.parse
import re
from html import unescape

def search_web_topics(keyword, max_results=10):
    """通过普通网页搜索获取话题事件，不占用小红书检索次数"""
    try:
        # 使用必应搜索（无需登录，普通浏览器可访问）
        query = urllib.parse.quote(f"{keyword} 舆情 话题 事件 2026")
        url = f"https://www.bing.com/search?q={query}&count={max_results}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        # 解析搜索结果
        results = []
        # 提取标题和摘要
        pattern = r'<li class="b_algo".*?<h2><a[^>]*href="([^"]*)"[^>]*>(.*?)</a></h2>.*?<p[^>]*>(.*?)</p>'
        matches = re.findall(pattern, html, re.DOTALL)
        for url, title, snippet in matches[:max_results]:
            clean_title = re.sub(r'<[^>]+>', '', unescape(title)).strip()
            clean_snippet = re.sub(r'<[^>]+>', '', unescape(snippet)).strip()
            if clean_title and len(clean_title) > 5:
                results.append({
                    'title': clean_title,
                    'url': url,
                    'snippet': clean_snippet[:200],
                    'source': 'web_search',
                    'collected_at': datetime.now().isoformat()
                })
        return results
    except Exception as e:
        print(f'[WebSearch] 搜索失败: {e}')
        return []

def get_trending_topics():
    """获取当前热门话题（从多个来源）"""
    topics = []
    # 1. 搜索广州太古汇相关话题
    topics.extend(search_web_topics('广州太古汇', 5))
    # 2. 搜索高端商场舆情话题
    topics.extend(search_web_topics('高端商场 舆情 投诉', 5))
    # 3. 搜索奢侈品服务话题
    topics.extend(search_web_topics('奢侈品专柜 服务 投诉', 5))
    # 去重
    seen = set()
    unique = []
    for t in topics:
        if t['title'] not in seen:
            seen.add(t['title'])
            unique.append(t)
    return unique[:15]

# 全网话题数据缓存
_web_topics_cache = {'data': [], 'updated_at': None}

def update_web_topics():
    """更新全网话题缓存（每6小时自动更新）"""
    global _web_topics_cache
    try:
        topics = get_trending_topics()
        _web_topics_cache = {'data': topics, 'updated_at': datetime.now().isoformat()}
        print(f'[WebTopics] 更新完成，共{len(topics)}条话题')
        return topics
    except Exception as e:
        print(f'[WebTopics] 更新失败: {e}')
        return []

def get_web_topics():
    """获取全网话题（优先缓存）"""
    global _web_topics_cache
    if _web_topics_cache['data'] and _web_topics_cache['updated_at']:
        updated = datetime.fromisoformat(_web_topics_cache['updated_at'])
        if (datetime.now() - updated).total_seconds() < 21600:  # 6小时缓存
            return _web_topics_cache['data']
    # 缓存过期，异步更新
    threading.Thread(target=update_web_topics, daemon=True).start()
    return _web_topics_cache['data']

@app.route('/api/web-topics')
def api_web_topics():
    """v5.9.0 优先读 web_topics 表真实数据并映射前端字段，为空回退内存缓存"""
    topics=[];updated_at=None
    try:
        _c=sqlite3.connect(db.DB_PATH,timeout=30);_c.row_factory=sqlite3.Row
        rows=_c.execute('SELECT * FROM web_topics ORDER BY mention_count DESC, last_seen DESC LIMIT 50').fetchall()
        _c.close()
        for r in rows:
            d=dict(r)
            d['title']=d.get('topic') or '无标题'
            d['snippet']=d.get('summary') or f"{d.get('source','web')} · 提及{d.get('mention_count',0)}次 · 情感{d.get('sentiment','-')}"
            topics.append(d)
        updated_at=rows[0]['created_at'] if rows else None
    except Exception as e:
        print(f'[WebTopics] 读库失败，回退缓存: {e}')
    if not topics:
        topics=get_web_topics();updated_at=_web_topics_cache.get('updated_at')
    return jsonify({'ok':True,'topics':topics,'count':len(topics),'updated_at':updated_at})
@app.route('/api/web-topics/refresh', methods=['POST'])
def api_web_topics_refresh():
    """手动刷新全网话题"""
    topics = update_web_topics()
    return jsonify({'ok': True, 'topics': topics, 'count': len(topics)})

# ===== v5.6.6 开发者工具 - 运行升级代码 =====
import tempfile
import importlib.util

@app.route('/api/dev/run-code', methods=['POST'])
def api_dev_run_code():
    """GAP-04 统一收口点③：开发者工具运行升级代码（调用 dev_exec_core 统一执行核心）。"""
    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()
    code_type = data.get('type', 'python')  # python / javascript
    if not code:
        return jsonify({'ok': False, 'error': '代码不能为空'}), 400
    resp, status = dev_exec_core.execute_dev_code_safe(
        code, code_type, backup=True, app=app, db=db, guard_func=_dev_exec_guard,
        endpoint='/api/dev/run-code'
    )
    # GAP-04 修复: guard 返回 (Flask Response, status) 时不可再 jsonify
    if hasattr(resp, 'get_data'):
        return resp, status
    return jsonify(resp), status


# ===== ZBIP Workspace 只读面板（文件树 / 只读终端）——Staging 旁路，纯只读、过滤敏感、防路径穿越 =====
import subprocess as _ws_sp
_WS_ROOT = Path(__file__).resolve().parent
_WS_HIDE_DIRS = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache',
                 '.skills-router', '.trae-cn', '.vscode', '.idea', 'data/cookies'}
_WS_HIDE_RE = re.compile(r'(^\.env)|cookie|token|secret|credential|passwd|password|\.(db|sqlite|sqlite3|pem|key|pfx)$|profile', re.I)

def _ws_hidden(name, is_dir):
    # 名称命中即隐藏，不依赖 is_dir：git linked-worktree 中 .git 是文件而非目录，
    # 若用 is_dir 门控会导致 worktree 内 .git 文件漏出。
    if name in _WS_HIDE_DIRS or name.startswith('edge-cdp') or name.startswith('chrome-cdp'):
        return True
    return bool(_WS_HIDE_RE.search(name))

@app.route('/api/workspace/file-tree')
def api_workspace_file_tree():
    """只读列目录：限定项目根、过滤敏感文件/目录、防路径穿越，返回真实文件数。"""
    try:
        rel = (request.args.get('path') or '').strip().replace('\\', '/').lstrip('/')
        target = (_WS_ROOT / rel).resolve() if rel else _WS_ROOT
        if target != _WS_ROOT and _WS_ROOT not in target.parents:
            return jsonify({'ok': False, 'error': '路径越界，已拒绝'}), 403
        if not target.exists() or not target.is_dir():
            return jsonify({'ok': False, 'error': '目录不存在'}), 404
        items, nd, nf = [], 0, 0
        for p in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                isd = p.is_dir()
            except OSError:
                continue
            if _ws_hidden(p.name, isd):
                continue
            if isd:
                nd += 1
            else:
                nf += 1
            items.append({'name': p.name, 'type': 'dir' if isd else 'file',
                          'rel': str(p.relative_to(_WS_ROOT)).replace('\\', '/'),
                          'size': None if isd else p.stat().st_size})
        return jsonify({'ok': True, 'root': _WS_ROOT.name, 'path': rel,
                        'items': items, 'counts': {'dirs': nd, 'files': nf, 'total': nd + nf}})
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500

_WS_TERM_ALLOW = {'ls', 'dir', 'pwd', 'whoami', 'help', 'clear', 'python', 'git'}
_WS_GIT_READONLY = {'status', 'log', 'diff', 'branch', 'rev-parse', 'show', 'remote', 'ls-files', 'count-objects'}

@app.route('/api/workspace/term', methods=['POST'])
def api_workspace_term():
    """只读 Web 终端：白名单命令、shell=False、cwd 锁定项目根、超时；拒绝一切写/管道/重定向。"""
    data = request.get_json(silent=True) or {}
    raw = (data.get('cmd') or '').strip()
    if not raw:
        return jsonify({'ok': False, 'error': '命令为空'}), 400
    if re.search(r'[;&|`$><]|\.\.', raw):
        return jsonify({'ok': False, 'blocked': True, 'error': '含管道/重定向/命令替换/上级路径，只读终端已拒绝。写操作请在本机终端执行。'}), 403
    parts = raw.split()
    head = parts[0].lower()
    if head not in _WS_TERM_ALLOW:
        return jsonify({'ok': False, 'blocked': True,
                        'error': 'Web 终端仅开放只读命令：ls / pwd / whoami / python --version / git 只读子命令 / help / clear。'}), 403
    try:
        if head in ('ls', 'dir'):
            lines = []
            for p in sorted(_WS_ROOT.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    isd = p.is_dir()
                except OSError:
                    continue
                if _ws_hidden(p.name, isd):
                    continue
                lines.append(('[D] ' if isd else '    ') + p.name)
            return jsonify({'ok': True, 'cmd': raw, 'cwd': str(_WS_ROOT), 'output': '\n'.join(lines)})
        if head == 'pwd':
            return jsonify({'ok': True, 'cmd': raw, 'cwd': str(_WS_ROOT), 'output': str(_WS_ROOT)})
        if head == 'help':
            return jsonify({'ok': True, 'cmd': raw, 'output':
                '只读 Web 终端可用命令：\n  ls                       列出项目根（自动过滤敏感项）\n  pwd                      项目根路径\n  whoami                   当前用户\n  python --version         Python 版本\n  git status|log|diff|branch|rev-parse|show|remote|ls-files   Git 只读查询\n  clear                    清屏\n写操作（commit/push/reset/安装/删除等）请在本机终端执行。'})
        if head == 'clear':
            return jsonify({'ok': True, 'clear': True})
        if head == 'python':
            if len(parts) < 2 or parts[1] != '--version':
                return jsonify({'ok': False, 'blocked': True, 'error': 'python 仅允许 --version'}), 403
            cmd = [sys.executable, '--version']
        elif head == 'whoami':
            cmd = ['whoami']
        else:  # git
            sub = parts[1].lower() if len(parts) > 1 else ''
            if sub not in _WS_GIT_READONLY:
                return jsonify({'ok': False, 'blocked': True, 'error': f'git {sub or "(无子命令)"} 不是只读子命令，已拒绝。'}), 403
            cmd = ['git', '-C', str(_WS_ROOT)] + parts[1:]
        r = _ws_sp.run(cmd, capture_output=True, text=True, timeout=15,
                       cwd=str(_WS_ROOT), encoding='utf-8', errors='replace')
        return jsonify({'ok': r.returncode == 0, 'cmd': raw, 'cwd': str(_WS_ROOT),
                        'output': (r.stdout or '') + (r.stderr or ''), 'code': r.returncode})
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500


@app.route('/api/workspace/file')
def api_workspace_file():
    """只读文件内容预览：限定项目根、过滤敏感、防路径穿越、限200KB、文本only、二进制拒绝预览。"""
    rel = (request.args.get('path') or '').strip().replace('\\', '/').lstrip('/')
    if not rel:
        return jsonify({'ok': False, 'error': 'path 为空'}), 400
    try:
        target = (_WS_ROOT / rel).resolve()
    except Exception:
        return jsonify({'ok': False, 'error': '路径非法'}), 400
    if target != _WS_ROOT and _WS_ROOT not in target.parents:
        return jsonify({'ok': False, 'error': '路径越界，已拒绝'}), 403
    if not target.exists() or not target.is_file():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    if _ws_hidden(target.name, False):
        return jsonify({'ok': False, 'error': '敏感文件，拒绝预览（.env/cookie/token/secret/db/profile 等）'}), 403
    size = target.stat().st_size
    MAX = 200 * 1024
    try:
        raw = target.read_bytes()[:MAX + 1]
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500
    if b'\x00' in raw[:8192]:
        return jsonify({'ok': True, 'path': rel, 'size': size, 'binary': True,
                        'content': '[二进制文件，不提供文本预览]'})
    text = raw.decode('utf-8', errors='replace')
    truncated = size > MAX
    return jsonify({'ok': True, 'path': rel, 'size': size,
                    'lines': text.count('\n') + 1, 'truncated': truncated,
                    'content': text[:MAX]})


# ===== 公关案例库 API（双模块联动体系） =====
@app.route('/api/pr/cases')
def api_pr_cases():
    """获取所有公关案例"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        scene = request.args.get('scene')
        level = request.args.get('level')
        keyword = request.args.get('keyword')
        cases = engine.search_cases(scene=scene, level=level, keyword=keyword)
        return jsonify({'ok': True, 'total': len(cases), 'cases': cases})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/cases/<case_id>')
def api_pr_case_detail(case_id):
    """获取单个公关案例详情"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        case = engine.get_case_by_id(case_id)
        if case:
            return jsonify({'ok': True, 'case': case})
        return jsonify({'ok': False, 'error': '案例不存在'}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/match', methods=['POST'])
def api_pr_match():
    """为笔记匹配同类案例（专报触发时调用）"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        data = request.get_json(silent=True) or {}
        note = data.get('note', {})
        top_n = data.get('top_n', 3)
        matched = engine.match_similar_cases(note, top_n=top_n)
        return jsonify({
            'ok': True,
            'matched': len(matched),
            'cases': matched,
            'case_ids': [c.get('id') for c in matched]
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/recommend', methods=['POST'])
def api_pr_recommend():
    """为笔记推荐公关话术"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        data = request.get_json(silent=True) or {}
        note = data.get('note', {})
        recommendation = engine.recommend_response(note)
        return jsonify({'ok': True, 'recommendation': recommendation})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/templates')
def api_pr_templates():
    """获取公关话术模板"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        scene = request.args.get('scene')
        if scene:
            template = engine.get_response_template(scene)
            return jsonify({'ok': True, 'template': template})
        return jsonify({'ok': True, 'templates': engine.templates, 'act_law': engine.response_templates.get('act_law', {})})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/statistics')
def api_pr_statistics():
    """获取案例库统计"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        return jsonify({'ok': True, 'statistics': engine.get_statistics()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/check-trigger', methods=['POST'])
def api_pr_check_trigger():
    """检查是否触发专报条件"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        data = request.get_json(silent=True) or {}
        notes = data.get('notes', [])
        note = data.get('note')
        result = engine.check_special_report_trigger(notes, note)
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ===== V4 升级模块旁路接入：独立 /v4 蓝图、独立认证与 v4_ 建表，不改写现网业务、不挂自动调度 =====
from v4_upgrade import create_v4_blueprint, init_v4_modules
init_v4_modules()
app.register_blueprint(create_v4_blueprint())

# GAP-10 report_center 旁路路由（Feature Gate: ZBC_REPORT_CENTER=1 启用，默认关闭）
from v4_upgrade.report_center.api import report_center_bp
app.register_blueprint(report_center_bp)

# AI Governance — 脱敏回传+额度控制+使用统计+输出标记（云端 zhipu 内置系统）
import ai_governance
import ai_resource_packs

# ===== 系统启动入口 =====


# ============ AI 资源包管理 API（智谱多资源包额度） ============
@app.route('/api/ai-resource-packs/status')
def api_ai_resource_packs_status():
    """所有资源包状态查询"""
    try:
        status = ai_resource_packs.get_all_packs_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-resource-packs/glm-4-5-air')
def api_ai_resource_packs_glm_status():
    """glm-4.5-air 实时状态（小 icon 用）"""
    try:
        status = ai_resource_packs.get_glm_4_5_air_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-resource-packs/pause', methods=['POST'])
def api_ai_resource_packs_pause():
    """暂停 AI 连接"""
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', '用户手动暂停')
        result = ai_resource_packs.pause_connection(reason)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-resource-packs/resume', methods=['POST'])
def api_ai_resource_packs_resume():
    """恢复 AI 连接"""
    try:
        result = ai_resource_packs.resume_connection()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-resource-packs/per-call-execute', methods=['POST'])
def api_ai_resource_packs_per_call_execute():
    """按次计费需求执行接口（用户输入需求，消耗1次按次额度）"""
    try:
        data = request.get_json(silent=True) or {}
        user_request = str(data.get('request') or data.get('prompt') or '').strip()
        if not user_request:
            return jsonify({'ok': False, 'error': '需求不能为空'}), 400
        model = data.get('model', 'glm-5.3')
        result = ai_resource_packs.execute_per_call_request(user_request, model)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500




# ============ API Key 管理（v4_workspace_keys 前端接入） ============
@app.route('/api/v4/api-keys')
def api_v4_api_keys_list():
    """API Key 列表"""
    try:
        import sqlite3
        db_path = os.environ.get('ZBC_DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db'))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""SELECT id, workspace, label, key_prefix, status, expires_at, last_used_at, created_at, created_by
                     FROM v4_workspace_keys ORDER BY created_at DESC LIMIT 200""")
        keys = [dict(row) for row in c.fetchall()]
        c.execute("SELECT status, COUNT(*) as cnt FROM v4_workspace_keys GROUP BY status")
        stats = {row['status']: row['cnt'] for row in c.fetchall()}
        conn.close()
        return jsonify({'ok': True, 'keys': keys, 'stats': stats, 'total': len(keys)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/v4/api-keys/generate', methods=['POST'])
def api_v4_api_keys_generate():
    """生成新 API Key"""
    try:
        import os, hashlib, secrets
        from datetime import datetime, timedelta
        data = request.get_json(silent=True) or {}
        label = str(data.get('label') or '').strip()
        workspace = str(data.get('workspace') or 'ZBMP').strip()
        expires_days = int(data.get('expires_days') or 0)  # 0=永不过期
        if not label:
            return jsonify({'ok': False, 'error': 'label 不能为空'}), 400

        # 生成密钥
        key_plain = 'zbmp_' + secrets.token_urlsafe(24)[:32]
        salt = os.urandom(16).hex()
        dk = hashlib.pbkdf2_hmac('sha256', key_plain.encode('utf-8'), bytes.fromhex(salt), 120000)
        key_hash = f"pbkdf2$120000${salt}${dk.hex()}"
        key_prefix = key_plain[:12] + '...'
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat() if expires_days > 0 else None

        import sqlite3
        db_path = os.environ.get('ZBC_DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""INSERT INTO v4_workspace_keys
                     (workspace, label, key_prefix, key_hash, created_by, status, expires_at, created_at)
                     VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
                  (workspace, label, key_prefix, key_hash, 'Zachary', expires_at, datetime.now().isoformat()))
        conn.commit()
        key_id = c.lastrowid
        conn.close()

        return jsonify({
            'ok': True,
            'key_id': key_id,
            'key_plain': key_plain,  # 只在生成时返回一次
            'key_prefix': key_prefix,
            'label': label,
            'workspace': workspace,
            'expires_at': expires_at,
            'message': '请立即保存此密钥，之后无法再次查看',
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/v4/api-keys/revoke', methods=['POST'])
def api_v4_api_keys_revoke():
    """撤销 API Key"""
    try:
        data = request.get_json(silent=True) or {}
        key_id = data.get('key_id')
        if not key_id:
            return jsonify({'ok': False, 'error': 'key_id 不能为空'}), 400
        import sqlite3
        from datetime import datetime
        db_path = os.environ.get('ZBC_DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("UPDATE v4_workspace_keys SET status='revoked' WHERE id=?", (key_id,))
        conn.commit()
        affected = c.rowcount
        conn.close()
        if affected == 0:
            return jsonify({'ok': False, 'error': '密钥不存在'}), 404
        return jsonify({'ok': True, 'key_id': key_id, 'status': 'revoked'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500




# ============ 小红书系统内二维码登录（Auth Recovery） ============
@app.route('/api/xhs/login/start', methods=['POST'])
def api_xhs_login_start():
    """启动小红书登录：通过CDP浏览器打开登录页，返回登录会话ID"""
    try:
        import json, time, uuid
        # 平台参数：xhs（国内 xiaohongshu.com / CDP 9222）| rednote（香港 rednote.com / CDP 9223）
        _body = request.get_json(silent=True) or {}
        _platform = (_body.get('platform') or 'xhs').strip().lower()
        if _platform == 'rednote':
            _cdp_url, _login_url, _label = 'http://127.0.0.1:9223', 'https://www.rednote.com/login', '小红书（香港 RedNote）'
        else:
            _cdp_url, _login_url, _label = 'http://127.0.0.1:9222', 'https://www.xiaohongshu.com', '小红书'
        session_id = 'xhs_login_' + uuid.uuid4().hex[:8]
        # 记录登录会话
        login_sessions = getattr(app, '_xhs_login_sessions', {})
        login_sessions[session_id] = {
            'status': 'pending',
            'created_at': time.time(),
            'platform': _platform,
        }
        app._xhs_login_sessions = login_sessions
        # 通过CDP浏览器打开登录页（异步，不阻塞）
        try:
            from playwright.sync_api import sync_playwright
            import threading
            def _open_login_page():
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.connect_over_cdp(_cdp_url, timeout=15000)
                        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                        page = ctx.new_page()
                        page.goto(_login_url, wait_until='domcontentloaded', timeout=30000)
                        login_sessions[session_id]['status'] = 'page_opened'
                        login_sessions[session_id]['url'] = page.url
                except Exception as e:
                    login_sessions[session_id]['status'] = 'error'
                    login_sessions[session_id]['error'] = str(e)
            threading.Thread(target=_open_login_page, daemon=True).start()
        except Exception as e:
            login_sessions[session_id]['status'] = 'browser_unavailable'
            login_sessions[session_id]['error'] = str(e)
        return jsonify({'ok': True, 'session_id': session_id, 'status': 'pending', 'message': '请在弹出的浏览器窗口中扫码登录' + _label})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/login/status')
def api_xhs_login_status():
    """检查小红书登录状态"""
    try:
        session_id = request.args.get('session_id', '')
        login_sessions = getattr(app, '_xhs_login_sessions', {})
        session = login_sessions.get(session_id, {'status': 'not_found'})
        # 尝试通过CDP检查是否已登录
        is_logged_in = False
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222', timeout=10000)
                ctx = browser.contexts[0] if browser.contexts else None
                if ctx:
                    cookies = ctx.cookies('https://www.xiaohongshu.com')
                    is_logged_in = any(c.get('name') == 'web_session' for c in cookies)
        except Exception:
            pass
        return jsonify({
            'ok': True,
            'session_id': session_id,
            'status': session.get('status', 'unknown'),
            'is_logged_in': is_logged_in,
            'message': '已登录' if is_logged_in else '等待扫码登录',
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/login/save', methods=['POST'])
def api_xhs_login_save():
    """保存小红书登录态（cookies）"""
    try:
        import json
        # 从CDP浏览器获取cookies并保存
        cookies_saved = False
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222', timeout=15000)
                ctx = browser.contexts[0] if browser.contexts else None
                if ctx:
                    cookies = ctx.cookies('https://www.xiaohongshu.com')
                    # 保存到文件
                    cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'xhs_cookies.json')
                    with open(cookie_path, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=2)
                    cookies_saved = True
        except Exception as e:
            return jsonify({'ok': False, 'error': f'保存cookies失败: {str(e)}'}), 500
        # 标记auth_recovery任务完成
        try:
            from auth_recovery_center import auth_recovery_center
            pending = auth_recovery_center.get_pending_tasks('xhs')
            for task in pending:
                auth_recovery_center.mark_completed(task.id, '系统内二维码登录成功')
        except Exception:
            pass
        return jsonify({'ok': True, 'cookies_saved': cookies_saved, 'message': '小红书登录态已保存'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500



# ============ Search-STD 搜索增强（案例库/知识库/RAG） ============
@app.route('/api/search/enhance', methods=['POST'])
def api_search_enhance():
    """搜索增强（智谱 search-std，100次额度）。用于案例库搜索增强、品牌知识库RAG、产品全局架构检索。"""
    try:
        data = request.get_json(silent=True) or {}
        query = str(data.get('query') or data.get('q') or '').strip()
        context = str(data.get('context') or '')
        max_results = int(data.get('max_results', 5))
        if not query:
            return jsonify({'ok': False, 'error': '查询不能为空'}), 400
        import intelligence
        result = intelligence.search_enhance(query, context, max_results)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500



# ============ 学习采集 + 小红书优化 API ============
@app.route('/api/learning/scan', methods=['POST'])
def api_learning_scan():
    """运行学习采集扫描（全量代码库学习，可选AI深度分析）"""
    try:
        data = request.get_json(silent=True) or {}
        use_ai = bool(data.get('use_ai', False))
        import learning_collector
        result = learning_collector.run_learning_scan(use_ai=use_ai)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/learning/history')
def api_learning_history():
    """获取学习历史"""
    try:
        import learning_collector
        result = learning_collector.get_learning_history()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/optimizer/config')
def api_xhs_optimizer_config():
    """获取小红书采集分类配置"""
    try:
        import xhs_collection_optimizer
        note_type = request.args.get('type', 'all')
        config = xhs_collection_optimizer.get_collection_config(note_type)
        return jsonify({'ok': True, 'note_type': note_type, 'config': config})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/optimizer/classify', methods=['POST'])
def api_xhs_optimizer_classify():
    """分类笔记（topic/opinion/event）"""
    try:
        data = request.get_json(silent=True) or {}
        title = str(data.get('title', ''))
        content = str(data.get('content', ''))
        keywords = data.get('keywords', [])
        import xhs_collection_optimizer
        note_type = xhs_collection_optimizer.classify_note(title, content, keywords)
        return jsonify({'ok': True, 'note_type': note_type, 'title': title[:50]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/rednote/keepalive')
def api_xhs_rednote_keepalive():
    """获取香港RedNote登录保活状态（支持 ?platform=rednote_hk|xhs_cn，默认 rednote_hk）"""
    try:
        import xhs_collection_optimizer
        platform = (request.args.get('platform') or 'rednote_hk').strip() or 'rednote_hk'
        status = xhs_collection_optimizer.get_keepalive_status(platform)
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/xhs/keepalive/mark', methods=['POST'])
def api_xhs_keepalive_mark():
    """标记当日保活完成（用户确认 / 登录成功回调）。body: {platform: rednote_hk|xhs_cn}"""
    try:
        import xhs_collection_optimizer
        platform = 'rednote_hk'
        if request.is_json:
            platform = (request.json.get('platform') or 'rednote_hk').strip() or 'rednote_hk'
        result = xhs_collection_optimizer.mark_keepalive_success(platform)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/xhs/keepalive/recheck', methods=['POST'])
def api_xhs_keepalive_recheck():
    """执行保活检查并给出决策（掉线自动再弹核心）。body: {platform, cdp_url?}
    返回 need_relogin=true 时前端应自动弹出登录弹窗。"""
    try:
        import xhs_collection_optimizer
        platform = 'rednote_hk'
        cdp_url = None
        if request.is_json:
            platform = (request.json.get('platform') or 'rednote_hk').strip() or 'rednote_hk'
            cdp_url = request.json.get('cdp_url')
        result = xhs_collection_optimizer.recheck_keepalive(platform, cdp_url)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/rednote/check-login', methods=['POST'])
def api_xhs_rednote_check_login():
    """检查香港RedNote登录状态（通过CDP 9223）"""
    try:
        import xhs_collection_optimizer
        cdp_url = request.json.get('cdp_url', 'http://127.0.0.1:9223') if request.is_json else 'http://127.0.0.1:9223'
        result = xhs_collection_optimizer.check_rednote_login(cdp_url)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ GAP-21 Cookie 导入 API（受 Basic Auth 保护，不接收/不返回 Cookie 明文）============
@app.route('/api/cookies/import', methods=['POST'])
def api_cookies_import():
    """触发从本地 data/ 源文件重新导入平台 Cookie（微博/B站/小红书）。

    安全约束：
      - 受全局 _basic_auth 保护（无凭证 401）
      - 不接收任何 Cookie 明文（请求体忽略）
      - 不返回 Cookie 值，只返回平台/数量/是否成功等元信息
      - 只写 data/（已被 .gitignore 整体忽略，凭证不入库）
      - 记录 Evidence（evidence_store）
    """
    import json as _json
    import os as _os
    from pathlib import Path as _Path
    _base = _Path(__file__).resolve().parent
    _data = _Path(_os.environ.get('ZBC_DATA_DIR', str(_base / 'data')))
    _data.mkdir(exist_ok=True)
    results = {}

    # --- 微博（.env: ZBC_WEIBO_COOKIE_JSON）---
    try:
        from dotenv import load_dotenv
        load_dotenv(_base / '.env')
    except Exception:
        pass
    import os as _os
    wb_raw = _os.environ.get('ZBC_WEIBO_COOKIE_JSON', '').strip()
    wb_n = 0
    if wb_raw:
        try:
            wb = _json.loads(wb_raw)
            if isinstance(wb, list):
                (_data / 'weibo_cookies.json').write_text(_json.dumps(wb, ensure_ascii=False, indent=2), encoding='utf-8')
                (_data / 'weibo_login_status.json').write_text(_json.dumps({
                    'logged_in': True,
                    'last_login': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'cookie_count': len(wb), 'login_method': 'cookie_import_api'}, ensure_ascii=False, indent=2), encoding='utf-8')
                wb_n = len(wb)
        except Exception as _e:
            results['weibo'] = {'ok': False, 'error': str(_e)}
    results.setdefault('weibo', {'ok': True, 'count': wb_n} if wb_n else {'ok': False, 'note': '未配置 ZBC_WEIBO_COOKIE_JSON'})

    # --- B站（.env: ZBC_BILI_COOKIE_JSON）---
    bl_raw = _os.environ.get('ZBC_BILI_COOKIE_JSON', '').strip()
    bl_n = 0
    if bl_raw:
        try:
            bl = _json.loads(bl_raw)
            if isinstance(bl, list):
                uid = next((str(c.get('value','')) for c in bl if c.get('name')=='DedeUserID'), '')
                (_data / 'bilibili_cookies.json').write_text(_json.dumps(bl, ensure_ascii=False, indent=2), encoding='utf-8')
                (_data / 'bilibili_login_status.json').write_text(_json.dumps({
                    'logged_in': True,
                    'last_login': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'cookie_count': len(bl), 'user_id': uid or 'unknown', 'login_method': 'cookie_import_api'}, ensure_ascii=False, indent=2), encoding='utf-8')
                bl_n = len(bl)
        except Exception as _e:
            results['bilibili'] = {'ok': False, 'error': str(_e)}
    results.setdefault('bilibili', {'ok': True, 'count': bl_n} if bl_n else {'ok': False, 'note': '未配置 ZBC_BILI_COOKIE_JSON'})

    # --- 小红书（本地源 data/xhs_cookies.source.json，凭证不入库）---
    xhs_src = _data / 'xhs_cookies.source.json'
    xhs_n = 0
    if xhs_src.exists():
        try:
            xhs = _json.loads(xhs_src.read_text(encoding='utf-8'))
            if isinstance(xhs, dict):
                xhs = xhs.get('cookies', [])
            if isinstance(xhs, list) and xhs:
                (_data / 'xhs_cookies.json').write_text(_json.dumps(xhs, ensure_ascii=False, indent=2), encoding='utf-8')
                parts = [f"{c.get('name','')}={c.get('value','')}" for c in xhs
                         if c.get('domain','').endswith('xiaohongshu.com') and c.get('name') and not c.get('name','').startswith('x-user-id-')]
                (_data / 'xhs_cookie_string.txt').write_text('; '.join(parts), encoding='utf-8')
                (_data / 'xhs_login_status.json').write_text(_json.dumps({
                    'logged_in': True,
                    'last_login': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'cookie_count': len(xhs), 'login_method': 'cookie_import_api', 'platform': 'xiaohongshu'}, ensure_ascii=False, indent=2), encoding='utf-8')
                xhs_n = len(xhs)
        except Exception as _e:
            results['xhs'] = {'ok': False, 'error': str(_e)}
    results.setdefault('xhs', {'ok': True, 'count': xhs_n} if xhs_n else {'ok': False, 'note': '未找到 data/xhs_cookies.source.json'})

    # Evidence 记录（不记录 Cookie 值，只记录元信息）
    try:
        from evidence_store import record_evidence
        record_evidence(source='zbc', project='ZBC', product='CTH', feature_id='GAP21_COOKIE_IMPORT',
                        env='prod', level='L4', test_name='cookie_import_api', result='PASS' if any(r.get('ok') for r in results.values()) else 'GAP',
                        outputs={'weibo': results.get('weibo',{}).get('count',0), 'bilibili': results.get('bilibili',{}).get('count',0), 'xhs': results.get('xhs',{}).get('count',0)},
                        actual=_json.dumps(results, ensure_ascii=False))
    except Exception:
        pass
    return jsonify({'ok': True, 'results': results})

@app.route('/api/cookies/import/status', methods=['GET'])
def api_cookies_import_status():
    """查看各平台 Cookie 导入状态（仅元信息，不返回 Cookie 值）。"""
    from pathlib import Path as _Path
    import os as _os, json as _json
    _base = _Path(__file__).resolve().parent
    _data = _base / 'data'
    def _stat(platform):
        p = _data / f'{platform}_login_status.json'
        if p.exists():
            try:
                d = _json.loads(p.read_text(encoding='utf-8'))
                return {'configured': True, 'logged_in': bool(d.get('logged_in')), 'cookie_count': d.get('cookie_count', 0), 'last_login': d.get('last_login','')}
            except Exception:
                return {'configured': True, 'error': 'parse_error'}
        return {'configured': False}
    return jsonify({'ok': True, 'status': {
        'weibo': _stat('weibo'),
        'bilibili': _stat('bilibili'),
        'xhs': _stat('xhs'),
        'xhs_source_exists': (_data / 'xhs_cookies.source.json').exists(),
    }})


@app.route('/api/cookies/import/raw', methods=['POST'])
def api_cookies_import_raw():
    """接收用户粘贴的平台 Cookie JSON，保存到本地 data/ 源文件并触发导入。

    安全约束：
      - 受全局 _basic_auth 保护（无凭证 401）
      - 仅接收 platform + cookies（JSON 数组），写入 data/（gitignore 不入库）
      - 不返回 Cookie 明文，只返回导入元信息
      - 记录 Evidence
    """
    import json as _json
    import os as _os
    from pathlib import Path as _Path
    _base = _Path(__file__).resolve().parent
    _data = _Path(_os.environ.get('ZBC_DATA_DIR', str(_base / 'data')))
    _data.mkdir(exist_ok=True)
    body = request.get_json(silent=True) or {}
    platform = (body.get('platform') or '').strip().lower()
    cookies = body.get('cookies')
    if platform not in ('weibo', 'bilibili', 'xhs', 'xiaohongshu'):
        return jsonify({'ok': False, 'error': 'platform 必须是 weibo/bilibili/xhs'}), 400
    if not isinstance(cookies, list) or not cookies:
        return jsonify({'ok': False, 'error': 'cookies 必须是非空 JSON 数组'}), 400
    # 规范化：仅保留合法 cookie 字段
    cleaned = []
    for c in cookies:
        if isinstance(c, dict) and c.get('name') and c.get('value') is not None:
            cleaned.append({
                'name': str(c.get('name', '')),
                'value': str(c.get('value', '')),
                'domain': str(c.get('domain', '')),
                'path': str(c.get('path', '/')),
                'httpOnly': bool(c.get('httpOnly', False)),
                'secure': bool(c.get('secure', False)),
                'expirationDate': c.get('expirationDate'),
            })
    if not cleaned:
        return jsonify({'ok': False, 'error': '无合法 cookie 条目（需含 name/value）'}), 400
    # 真实性校验：小红书必须包含非占位 web_session，防止测试/误操作污染生产 cookie
    if platform in ('xhs', 'xiaohongshu'):
        ws = [c.get('value', '') for c in cleaned if c.get('name') == 'web_session']
        if not ws:
            return jsonify({'ok': False, 'error': '小红书 Cookie 缺少 web_session（真实登录凭证），已拒绝导入'}), 400
        if len(ws[0]) < 6 or ws[0].lower() in ('x', 'test', 'placeholder', 's', 'token', '123456', 'true'):
            return jsonify({'ok': False, 'error': 'web_session 疑似测试/占位值，已拒绝导入（请提供真实登录 Cookie）'}), 400
    # 写入源文件
    if platform in ('weibo',):
        src_file = _data / 'weibo_cookies.json'
        status_file = _data / 'weibo_login_status.json'
        status = {'logged_in': True, 'cookie_count': len(cleaned), 'login_method': 'cookie_import_api_raw'}
    elif platform in ('bilibili',):
        src_file = _data / 'bilibili_cookies.json'
        status_file = _data / 'bilibili_login_status.json'
        status = {'logged_in': True, 'cookie_count': len(cleaned), 'login_method': 'cookie_import_api_raw'}
    else:  # xhs / xiaohongshu
        src_file = _data / 'xhs_cookies.source.json'
        status_file = _data / 'xhs_login_status.json'
        status = {'logged_in': True, 'cookie_count': len(cleaned), 'login_method': 'cookie_import_api_raw', 'platform': 'xiaohongshu'}
    src_file.write_text(_json.dumps(cleaned, ensure_ascii=False, indent=2), encoding='utf-8')
    # 仅当 apply=true 才同步生产 cookie 文件（防止测试污染；默认只写 source 待确认）
    apply = bool(body.get('apply', False))
    if apply and platform in ('xhs', 'xiaohongshu'):
        (_data / 'xhs_cookies.json').write_text(_json.dumps(cleaned, ensure_ascii=False, indent=2), encoding='utf-8')
        parts = [f"{c['name']}={c['value']}" for c in cleaned
                 if c.get('domain','').endswith('xiaohongshu.com') and not c['name'].startswith('x-user-id-')]
        (_data / 'xhs_cookie_string.txt').write_text('; '.join(parts), encoding='utf-8')
        status['applied'] = True
    status['last_login'] = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status_file.write_text(_json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    # Evidence（不记录 Cookie 值）
    try:
        from evidence_store import record_evidence
        record_evidence(source='zbc', project='ZBC', product='CTH', feature_id='GAP21_COOKIE_IMPORT_RAW',
                        env='prod', level='L4', test_name='cookie_import_api_raw', result='PASS',
                        outputs={'platform': platform, 'cookie_count': len(cleaned)},
                        actual=_json.dumps({'platform': platform, 'cookie_count': len(cleaned)}, ensure_ascii=False))
    except Exception:
        pass
    return jsonify({'ok': True, 'platform': platform, 'cookie_count': len(cleaned), 'applied': apply and platform in ('xhs', 'xiaohongshu')})

if __name__ == '__main__':
    import logging
    from logging.handlers import RotatingFileHandler
    
    # 配置详细日志
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 清除已有的日志处理器（避免重复）
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 文件日志（详细）
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'system.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # 控制台日志（简洁）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # 根日志器
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Flask日志器（不重复添加handler，继承root_logger）
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    # 不添加handler，避免重复记录
    
    # 命令行 --host/--port 优先于 .env（修复历史 bug：此前末尾 app.run 固定用 .env 的 APP_PORT，
    # 忽略 --port，导致旁路测试实例抢占现网端口）
    RUN_HOST = getattr(globals().get('args'), 'host', APP_HOST)
    RUN_PORT = getattr(globals().get('args'), 'port', APP_PORT)
    print("=" * 60)
    print(f"广州太古汇舆情监测系统 v{APP_VERSION}")
    print(f"启动地址: http://{RUN_HOST}:{RUN_PORT}")
    print(f"多线程模式: 开启")
    print(f"详细日志: {os.path.join(log_dir, 'system.log')}")
    print("=" * 60)
    
    # ===== ZBIP Runtime Integrity Preflight（统一启动闸门）=====
    # 默认只记录并写 Attestation、不阻断现网；ZBC_PREFLIGHT_ENFORCE=1 时存在 P0 即终止启动。
    try:
        _pf_report = runtime_preflight.run_preflight()
        print(runtime_preflight.format_summary(_pf_report))
    except SystemExit:
        raise
    except Exception as _pf_e:
        print(f"[Preflight] 预检异常，不阻断启动: {type(_pf_e).__name__}: {_pf_e}")

    # 自动检查并启动CDP浏览器（确保采集功能可用）
    # 注意：暂时禁用自动启动，避免Edge浏览器崩溃导致主进程退出
    # 采集时会按需启动CDP浏览器
    try:
        import cdp_helper
        cdp_status = cdp_helper.get_cdp_status()
        if cdp_status.get('available'):
            print(f"[CDP] 浏览器已就绪: 端口 {cdp_status.get('port')}")
        else:
            print(f"[CDP] 浏览器未启动，采集时将按需自动启动（避免启动时崩溃）")
    except Exception as e:
        print(f"[CDP] 检查失败: {e}")
    
    # 后台心跳线程（监控系统状态）
    def heartbeat_monitor():
        import time
        heartbeat_count = 0
        while True:
            try:
                heartbeat_count += 1
                # 每30秒记录一次心跳
                if heartbeat_count % 30 == 0:
                    logging.info(f"[Heartbeat] 系统运行正常，心跳次数: {heartbeat_count}")
                time.sleep(1)
            except Exception as e:
                logging.error(f"[Heartbeat] 心跳线程异常: {e}", exc_info=True)
                time.sleep(5)
    
    # 启动心跳线程（守护线程，主进程退出时自动结束）
    heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
    heartbeat_thread.start()
    logging.info("[System] 心跳监控线程已启动")
    
    # 全局异常捕获
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    # 线程异常捕获
    def thread_exception_handler(args):
        logging.critical(f"线程异常: {args.exc_type.__name__}: {args.exc_value}", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    
    threading.excepthook = thread_exception_handler

    # ===== P1-7 三 guardian 模块受控接入（守护 / 自动恢复 / 数据反馈闭环）=====
    # 全部 try/except 包裹，任一失败不阻断启动；ZBC_GUARDIAN_ENABLED=0 可整体关闭
    if os.environ.get('ZBC_GUARDIAN_ENABLED', '1') == '1':
        try:
            import auto_recovery as _ar
            _ar_eng = _ar.recovery_engine
            if not getattr(_ar_eng, '_p17_started', False):
                _ar_eng.start_background_monitor(60)
                _ar_eng._p17_started = True
                print('[Guardian] auto_recovery 自动恢复监控已启动(60s)')
        except Exception as _ge:
            print(f'[Guardian] auto_recovery 启动失败: {_ge}')
        try:
            import data_feedback_loop as _dfl
            _dfl_eng = _dfl.data_feedback_loop
            def _fb_loop():
                import time as _t
                while True:
                    try:
                        _dfl_eng.run_feedback_cycle()
                    except Exception as _fe:
                        print(f'[Guardian] 数据反馈闭环异常: {_fe}')
                    _t.sleep(21600)
            threading.Thread(target=_fb_loop, daemon=True, name='data-feedback-loop').start()
            print('[Guardian] data_feedback_loop 数据反馈闭环已启动(6h)')
        except Exception as _ge:
            print(f'[Guardian] data_feedback_loop 启动失败: {_ge}')
        try:
            import system_guardian as _sg
            _sg.health_check()
            print('[Guardian] system_guardian 健康状态已记录')
        except Exception as _ge:
            print(f'[Guardian] system_guardian 启动失败: {_ge}')
    
    try:
        # T-P1-1 waitress 可配置化：ZB_WSGI=waitress 时用生产级多线程 WSGI（waitress.serve），
        # 默认仍 Flask dev server（零影响）。先 Staging 验证再切生产；缺 waitress 自动回落 Flask。
        _wsgi = os.environ.get('ZB_WSGI', '').strip().lower()
        if _wsgi == 'waitress':
            try:
                from waitress import serve as _waitress_serve
                _threads = int(os.environ.get('ZB_WSGI_THREADS', '8') or '8')
                print(f'[System] 生产 WSGI: waitress.serve(host={RUN_HOST}, port={RUN_PORT}, threads={_threads})')
                _waitress_serve(app, host=RUN_HOST, port=RUN_PORT, threads=_threads)
            except ImportError:
                print('[System] waitress 未安装，回落 Flask dev server')
                app.run(host=RUN_HOST, port=RUN_PORT, debug=False, threaded=True)
        else:
            # 使用多线程模式，支持并发请求
            app.run(host=RUN_HOST, port=RUN_PORT, debug=False, threaded=True)
    except Exception as e:
        logging.critical(f"[System] 系统启动失败: {e}", exc_info=True)
        print(f"系统启动失败: {e}")
    finally:
        logging.info("[System] 系统已停止")
        print("系统已停止")

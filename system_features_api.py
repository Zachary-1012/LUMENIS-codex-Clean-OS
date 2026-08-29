"""
系统功能API路由 v1.0
包含：安全检查、评测体系、本地AI、采集器自动化
"""

import os
import sys
import json
from flask import Blueprint, jsonify, request

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入模块
from security_scanner import security_scanner
from evaluation_system import evaluation_system
from local_ai_client import local_ai
from collector_auto_start import collector_starter

system_features_bp = Blueprint('system_features', __name__)


# ============================================
# 安全检查 API
# ============================================

@system_features_bp.route('/api/security/scan')
def security_scan():
    """执行完整安全扫描"""
    try:
        result = security_scanner.full_scan()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/security/baseline', methods=['POST'])
def security_create_baseline():
    """创建文件完整性基线"""
    try:
        result = security_scanner.create_baseline()
        return jsonify({'ok': True, 'baseline_count': result.get('file_count', 0)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/security/integrity')
def security_check_integrity():
    """校验文件完整性"""
    try:
        result = security_scanner.verify_integrity()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/security/dangerous-code')
def security_dangerous_code():
    """扫描危险代码"""
    try:
        result = security_scanner.scan_dangerous_code()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/security/sensitive-info')
def security_sensitive_info():
    """扫描敏感信息"""
    try:
        result = security_scanner.scan_sensitive_info()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 评测体系 API
# ============================================

@system_features_bp.route('/api/evaluation/run')
def evaluation_run():
    """运行完整评测"""
    try:
        result = evaluation_system.run_full_evaluation()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/collection')
def evaluation_collection():
    """采集质量评测"""
    try:
        result = evaluation_system.evaluate_collection_quality()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/analysis')
def evaluation_analysis():
    """分析质量评测"""
    try:
        result = evaluation_system.evaluate_analysis_quality()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/stability')
def evaluation_stability():
    """系统稳定性评测"""
    try:
        result = evaluation_system.evaluate_system_stability()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/badcases')
def evaluation_badcases():
    """获取Badcase列表"""
    try:
        category = request.args.get('category')
        result = evaluation_system.get_badcases(category)
        return jsonify({'ok': True, 'badcases': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/golden-cases')
def evaluation_golden_cases():
    """获取Golden Case列表"""
    try:
        result = evaluation_system.get_golden_cases()
        return jsonify({'ok': True, 'golden_cases': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 本地AI API
# ============================================

@system_features_bp.route('/api/local-ai/status')
def local_ai_status():
    """获取本地AI状态"""
    try:
        result = local_ai.get_status()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/local-ai/analyze', methods=['POST'])
def local_ai_analyze():
    """本地AI分析"""
    try:
        data = request.get_json(silent=True) or {}
        text = data.get('text', '')
        analysis_type = data.get('type', 'sentiment')

        if not text:
            return jsonify({'ok': False, 'error': 'text不能为空'}), 400

        if analysis_type == 'sentiment':
            result = local_ai.analyze_sentiment(text)
        elif analysis_type == 'event':
            result = local_ai.analyze_event(text)
        elif analysis_type == 'risk':
            result = local_ai.analyze_risk(text)
        else:
            result = local_ai.generate(f"请分析以下内容：{text}")

        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/local-ai/chat', methods=['POST'])
def local_ai_chat():
    """本地AI聊天"""
    try:
        data = request.get_json(silent=True) or {}
        messages = data.get('messages', [])
        result = local_ai.chat(messages)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 采集器自动化 API
# ============================================

# 注意：/api/collector/status 已在 app.py 中实现，此处不再重复注册

@system_features_bp.route('/api/collector/start-cdp', methods=['POST'])
def collector_start_cdp():
    """启动CDP浏览器"""
    try:
        result = collector_starter.start_edge_with_cdp()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/collector/stop-cdp', methods=['POST'])
def collector_stop_cdp():
    """停止CDP浏览器"""
    try:
        result = collector_starter.stop_edge()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


print("[SystemFeaturesAPI] 系统功能API路由已加载", flush=True)

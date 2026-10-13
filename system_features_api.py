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

system_features_bp = Blueprint('system_features', __name__)


def _evaluation_runner():
    """Create the current Shared Evaluation runner at the point of use."""
    from lumenis.shared.evaluation.runner import EvaluationRunner

    return EvaluationRunner()


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
        result = _evaluation_runner().run_full_evaluation()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/collection')
def evaluation_collection():
    """采集质量评测"""
    try:
        result = _evaluation_runner().run_dimension_evaluation('collector')
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/analysis')
def evaluation_analysis():
    """分析质量评测"""
    try:
        result = _evaluation_runner().run_dimension_evaluation('ai')
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/stability')
def evaluation_stability():
    """系统稳定性评测"""
    try:
        result = _evaluation_runner().run_dimension_evaluation('runtime')
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/badcases')
def evaluation_badcases():
    """获取真实失败评估记录；不从合成种子或 AI 猜测生成 badcase。"""
    try:
        category = request.args.get('category')
        from lumenis.shared.evaluation.recorder import get_evaluation_records
        from lumenis.shared.evaluation.runner import VALID_DIMENSIONS

        dimension = {'collection': 'collector', 'analysis': 'ai', 'stability': 'runtime'}.get(
            category, category
        )
        if dimension and dimension not in VALID_DIMENSIONS:
            return jsonify({'ok': False, 'error': 'unknown evaluation category'}), 400
        result = get_evaluation_records(dimension=dimension, status='fail', limit=100)
        return jsonify({'ok': True, 'badcases': result, 'source': 'lumenis.shared.evaluation.recorder'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@system_features_bp.route('/api/evaluation/golden-cases')
def evaluation_golden_cases():
    """返回人工核验用例；当前 synthetic seed 不满足 golden 数据要求。"""
    try:
        return jsonify({
            'ok': True,
            'golden_cases': [],
            'state': 'NOT_AVAILABLE',
            'reason': 'The current benchmark registry contains synthetic seed data only; human ground truth is required.',
            'source': 'lumenis/shared/evaluation/benchmark_cases.json',
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 本地AI API
# ============================================

def _retired_local_ai_response():
    """Keep historical URLs while preventing provider discovery or inference."""
    return jsonify({
        'ok': False,
        'status': 'provider_disabled',
        'reason': 'RETIRED_LOCAL_AI_COMPATIBILITY_ONLY',
        'compatibility_adapter': True,
    }), 503

@system_features_bp.route('/api/local-ai/status')
def local_ai_status():
    """Retained endpoint: local model discovery is permanently unavailable."""
    return _retired_local_ai_response()


@system_features_bp.route('/api/local-ai/analyze', methods=['POST'])
def local_ai_analyze():
    """Retained endpoint: local model analysis is permanently unavailable."""
    return _retired_local_ai_response()


@system_features_bp.route('/api/local-ai/chat', methods=['POST'])
def local_ai_chat():
    """Retained endpoint: local model chat is permanently unavailable."""
    return _retired_local_ai_response()


# ============================================
# 采集器自动化 API
# ============================================

# 注意：/api/collector/status 已在 app.py 中实现，此处不再重复注册

print("[SystemFeaturesAPI] 系统功能API路由已加载", flush=True)

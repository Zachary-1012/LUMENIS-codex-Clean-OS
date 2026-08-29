"""
5层闭环架构 API v1.0
统一暴露5层架构引擎的API接口
- 自动调节引擎 (adaptive_engine)
- 自动修复引擎 (auto_recovery)
- 数据闭环引擎 (data_feedback_loop)
- 系统控制中心 (system_health_api - 已单独注册)
- 边界控制引擎 (safety_boundary)
"""

import os
import sys
import json
from datetime import datetime
from flask import Blueprint, jsonify, request

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入5层引擎
from adaptive_engine import adaptive_engine, StrategyLevel, RiskLevel
from auto_recovery import recovery_engine, FixStatus, AlertLevel
from data_feedback_loop import data_feedback_loop
from safety_boundary import boundary_control_engine, OperationType, SafetyLevel

architecture_bp = Blueprint('architecture', __name__)


# ============================================
# 第一层：自动调节引擎 API
# ============================================

@architecture_bp.route('/api/adaptive/status')
def adaptive_status():
    """获取自动调节引擎状态"""
    try:
        current_params = adaptive_engine.get_current_params()
        return jsonify({
            'ok': True,
            'status': adaptive_engine.get_status(),
            'current_params': current_params,
            'current_strategy': adaptive_engine.get_current_strategy(),
            'risk_level': adaptive_engine.get_risk_level(),
            'metrics': adaptive_engine.get_metrics(),
            'current_request_delay': current_params.get('request_delay', 55),  # 当前请求间隔（秒）
            'today_collections': adaptive_engine.get_metrics().get('today_collections', 0) if hasattr(adaptive_engine, 'get_metrics') else 0
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'current_request_delay': 55}), 500


@architecture_bp.route('/api/adaptive/can-collect')
def adaptive_can_collect():
    """判断是否可以采集"""
    try:
        can_collect, reason = adaptive_engine.can_collect_now()
        return jsonify({
            'ok': True,
            'can_collect': can_collect,
            'reason': reason
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/adaptive/report-result', methods=['POST'])
def adaptive_report_result():
    """报告采集结果，用于动态调整策略"""
    try:
        data = request.get_json(silent=True) or {}
        success = data.get('success', True)
        notes_count = data.get('notes_count', 0)
        duration = data.get('duration', 0)
        error = data.get('error', None)

        params = adaptive_engine.report_collection_result(
            success=success,
            notes_count=notes_count,
            duration=duration,
            error=error
        )

        return jsonify({
            'ok': True,
            'message': '采集结果已报告，策略已动态调整',
            'new_params': params,
            'current_strategy': adaptive_engine.get_current_strategy(),
            'risk_level': adaptive_engine.get_risk_level()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/adaptive/reset', methods=['POST'])
def adaptive_reset():
    """重置为正常策略（人工确认后使用）"""
    try:
        adaptive_engine.reset_to_normal()
        return jsonify({
            'ok': True,
            'message': '已重置为正常策略',
            'current_strategy': adaptive_engine.get_current_strategy(),
            'risk_level': adaptive_engine.get_risk_level()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 第二层：自动修复引擎 API
# ============================================

@architecture_bp.route('/api/recovery/health-check')
def recovery_health_check():
    """执行健康检查"""
    try:
        health = recovery_engine.health_check()
        return jsonify({
            'ok': True,
            'health': health
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/recovery/run-cycle', methods=['POST'])
def recovery_run_cycle():
    """运行一次完整的修复周期"""
    try:
        result = recovery_engine.run_recovery_cycle()
        return jsonify({
            'ok': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/recovery/stats')
def recovery_stats():
    """获取修复统计"""
    try:
        return jsonify({
            'ok': True,
            'stats': recovery_engine.get_stats()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/recovery/alerts')
def recovery_alerts():
    """获取活跃告警"""
    try:
        alerts = recovery_engine.get_active_alerts()
        return jsonify({
            'ok': True,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 第三层：数据闭环引擎 API
# ============================================

@architecture_bp.route('/api/feedback/analyze')
def feedback_analyze():
    """分析报告异常"""
    try:
        date_str = request.args.get('date')
        anomalies = data_feedback_loop.analyze_report_anomalies(date_str)
        return jsonify({
            'ok': True,
            'anomalies': anomalies,
            'count': len(anomalies)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/feedback/suggestions')
def feedback_suggestions():
    """获取策略建议"""
    try:
        date_str = request.args.get('date')
        anomalies = data_feedback_loop.analyze_report_anomalies(date_str)
        suggestions = data_feedback_loop.generate_strategy_suggestions(anomalies)
        return jsonify({
            'ok': True,
            'suggestions': suggestions,
            'count': len(suggestions)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/feedback/run-cycle', methods=['POST'])
def feedback_run_cycle():
    """运行一次完整的反馈周期"""
    try:
        data = request.get_json(silent=True) or {}
        date_str = data.get('date')
        result = data_feedback_loop.run_feedback_cycle(date_str)
        return jsonify({
            'ok': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/feedback/history')
def feedback_history():
    """获取反馈历史"""
    try:
        limit = int(request.args.get('limit', 20))
        history = data_feedback_loop.get_feedback_history(limit)
        return jsonify({
            'ok': True,
            'history': history,
            'count': len(history)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/feedback/pending')
def feedback_pending():
    """获取待处理反馈"""
    try:
        pending = data_feedback_loop.get_pending_feedback()
        return jsonify({
            'ok': True,
            'pending': pending,
            'count': len(pending)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/feedback/stats')
def feedback_stats():
    """获取反馈统计"""
    try:
        return jsonify({
            'ok': True,
            'stats': data_feedback_loop.get_stats()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 第五层：边界控制引擎 API
# ============================================

@architecture_bp.route('/api/boundary/safety-level/<operation_type>')
def boundary_safety_level(operation_type):
    """获取操作的安全级别"""
    try:
        safety = boundary_control_engine.get_safety_level(operation_type)
        can_auto, reason = boundary_control_engine.can_auto_execute(operation_type)
        return jsonify({
            'ok': True,
            'operation_type': operation_type,
            'safety_level': safety.value,
            'can_auto_execute': can_auto,
            'reason': reason
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/boundary/pending-confirmations')
def boundary_pending_confirmations():
    """获取待确认操作"""
    try:
        pending = boundary_control_engine.get_pending_confirmations()
        return jsonify({
            'ok': True,
            'pending': pending,
            'count': len(pending)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/boundary/approve/<int:confirmation_id>', methods=['POST'])
def boundary_approve(confirmation_id):
    """批准确认"""
    try:
        data = request.get_json(silent=True) or {}
        confirmed_by = data.get('confirmed_by', 'user')
        result = boundary_control_engine.approve_confirmation(confirmation_id, confirmed_by)
        return jsonify({
            'ok': result,
            'message': '批准成功' if result else '批准失败（确认不存在或已处理）'
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/boundary/reject/<int:confirmation_id>', methods=['POST'])
def boundary_reject(confirmation_id):
    """拒绝确认"""
    try:
        data = request.get_json(silent=True) or {}
        rejected_by = data.get('rejected_by', 'user')
        reason = data.get('reason', '')
        result = boundary_control_engine.reject_confirmation(confirmation_id, rejected_by, reason)
        return jsonify({
            'ok': result,
            'message': '拒绝成功' if result else '拒绝失败（确认不存在或已处理）'
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/boundary/file-integrity/check')
def boundary_file_integrity_check():
    """检查文件完整性"""
    try:
        result = boundary_control_engine.check_file_integrity()
        return jsonify({
            'ok': True,
            'result': result
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/boundary/file-integrity/baseline', methods=['POST'])
def boundary_file_integrity_baseline():
    """建立文件完整性基线"""
    try:
        data = request.get_json(silent=True) or {}
        files = data.get('files')
        baseline = boundary_control_engine.baseline_file_integrity(files)
        return jsonify({
            'ok': True,
            'message': '文件完整性基线已建立',
            'baseline_count': len(baseline)
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@architecture_bp.route('/api/boundary/stats')
def boundary_stats():
    """获取边界控制统计"""
    try:
        return jsonify({
            'ok': True,
            'stats': boundary_control_engine.get_stats()
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================
# 统一架构状态 API
# ============================================

@architecture_bp.route('/api/architecture/status')
def architecture_status():
    """获取5层架构整体状态"""
    try:
        return jsonify({
            'ok': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'layers': {
                'layer1_adaptive': {
                    'name': '自动调节引擎',
                    'status': 'running',
                    'current_strategy': adaptive_engine.get_current_strategy(),
                    'risk_level': adaptive_engine.get_risk_level()
                },
                'layer2_recovery': {
                    'name': '自动修复引擎',
                    'status': 'running',
                    'stats': recovery_engine.get_stats()
                },
                'layer3_feedback': {
                    'name': '数据闭环引擎',
                    'status': 'running',
                    'stats': data_feedback_loop.get_stats()
                },
                'layer4_health': {
                    'name': '系统控制中心',
                    'status': 'running',
                    'note': '详见 /api/system/health/detailed'
                },
                'layer5_boundary': {
                    'name': '边界控制引擎',
                    'status': 'running',
                    'stats': boundary_control_engine.get_stats()
                }
            },
            'overall_status': 'running'
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


print("[ArchitectureAPI] 5层闭环架构 API 已加载", flush=True)

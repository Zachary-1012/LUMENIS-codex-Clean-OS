"""
Auth Recovery Center API（V3.0 P0）
蓝图：提供恢复任务的查询、创建、更新接口，供前端弹窗提示和用户操作使用。
"""
from flask import Blueprint, request, jsonify
from auth_recovery_center import recovery_center, RecoveryStatus, AuthIssueType

auth_recovery_bp = Blueprint('auth_recovery', __name__, url_prefix='/api/auth-recovery')


@auth_recovery_bp.route('/summary', methods=['GET'])
def get_summary():
    """获取恢复中心摘要（前端轮询用，判断是否需要弹窗）"""
    summary = recovery_center.get_recovery_summary()
    return jsonify({
        'ok': True,
        'data': summary,
    })


@auth_recovery_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """获取恢复任务列表"""
    platform = request.args.get('platform')
    status = request.args.get('status', RecoveryStatus.PENDING.value)

    if status == RecoveryStatus.PENDING.value:
        tasks = recovery_center.get_pending_tasks(platform=platform)
    else:
        # 其他状态暂不支持查询，返回空
        tasks = []

    return jsonify({
        'ok': True,
        'tasks': [t.to_dict() for t in tasks],
        'count': len(tasks),
    })


@auth_recovery_bp.route('/tasks', methods=['POST'])
def create_task():
    """手动创建恢复任务（管理员用）"""
    data = request.get_json() or {}
    platform = data.get('platform', 'xhs')
    issue_type = data.get('issue_type', AuthIssueType.UNKNOWN.value)
    title = data.get('title', '认证异常')
    description = data.get('description', '')
    recovery_url = data.get('recovery_url', '')

    task = recovery_center.create_task(
        platform=platform,
        issue_type=issue_type,
        title=title,
        description=description,
        recovery_url=recovery_url,
    )

    return jsonify({
        'ok': True,
        'task': task.to_dict(),
    })


@auth_recovery_bp.route('/tasks/<int:task_id>/start', methods=['POST'])
def start_task(task_id: int):
    """标记任务为进行中（用户开始扫码/验证）"""
    success = recovery_center.mark_in_progress(task_id)
    return jsonify({
        'ok': success,
        'message': '任务已标记为进行中' if success else '任务不存在',
    })


@auth_recovery_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id: int):
    """标记任务为已完成（用户验证成功）

    注意：标记完成后，系统会自动触发健康探活，确认完全健康才解除熔断。
    健康探活由 topic_campaign.topic_recover 执行。
    """
    data = request.get_json() or {}
    error_message = data.get('error_message', '')

    success = recovery_center.mark_completed(task_id, error_message=error_message)

    # 触发健康探活和恢复（异步，不阻塞响应）
    if success:
        try:
            from topic_campaign import topic_recover
            # 在后台线程执行恢复
            import threading
            def _recover():
                try:
                    topic_recover(reason='auth_recovery_task_completed')
                except Exception as e:
                    print(f"[AuthRecovery] 后台恢复失败: {e}")
            threading.Thread(target=_recover, daemon=True).start()
        except Exception as e:
            print(f"[AuthRecovery] 触发恢复失败: {e}")

    return jsonify({
        'ok': success,
        'message': '任务已完成，正在执行健康探活...' if success else '任务不存在',
    })


@auth_recovery_bp.route('/tasks/<int:task_id>/fail', methods=['POST'])
def fail_task(task_id: int):
    """标记任务为失败"""
    data = request.get_json() or {}
    error_message = data.get('error_message', '验证失败')

    success = recovery_center.mark_failed(task_id, error_message=error_message)
    return jsonify({
        'ok': success,
        'message': '任务已标记为失败' if success else '任务不存在',
    })


@auth_recovery_bp.route('/health', methods=['GET'])
def health():
    """恢复中心健康检查"""
    return jsonify({
        'ok': True,
        'module': 'auth_recovery_center',
        'version': 'v3.0-p0',
        'pending_tasks': recovery_center.get_recovery_summary()['pending_count'],
    })

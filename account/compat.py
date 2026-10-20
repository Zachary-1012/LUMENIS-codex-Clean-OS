"""
account/compat.py — 旧路由兼容层（deprecated）

现有 /api/v4/api-keys/*、/api/auth/* 加兼容层，内部转发到新API。
标 deprecated，不立即删。
"""
import warnings
from flask import Blueprint, request, jsonify

from .service import require_admin_or_owner, require_owner

compat_bp = Blueprint("account_compat", __name__)

# Deprecated 标记
DEPRECATED_HEADER = {"X-Deprecated": "true", "X-Successor": "/api/system/account/*"}


@compat_bp.route("/api/v4/api-keys", methods=["GET"])
@require_admin_or_owner
def compat_api_keys_list():
    """[DEPRECATED] 转发到 /api/system/account/workspace-keys"""
    from .workspace_keys import list_workspace_keys, get_rotation_required_count
    keys = list_workspace_keys()
    rotation = get_rotation_required_count()
    resp = jsonify({"ok": True, "keys": keys, "stats": {"active": rotation["total_active"]},
                    "deprecated": True, "successor": "/api/system/account/workspace-keys"})
    resp.headers.update(DEPRECATED_HEADER)
    return resp


@compat_bp.route("/api/v4/api-keys/generate", methods=["POST"])
@require_owner
def compat_api_keys_generate():
    """[DEPRECATED] 转发到 /api/system/account/workspace-keys (POST)"""
    from .workspace_keys import create_workspace_key
    data = request.get_json(silent=True) or {}
    # 旧接口允许 expires_days=0 永不过期，新接口强制过期，这里默认30天
    expires_days = int(data.get("expires_days", 0))
    if expires_days <= 0:
        expires_days = 30  # 强制过期
    result = create_workspace_key(
        workspace=data.get("workspace", "ZBMP"),
        label=data.get("label", "deprecated-legacy"),
        expires_days=expires_days,
    )
    resp = jsonify({**result, "deprecated": True,
                    "successor": "/api/system/account/workspace-keys",
                    "note": "旧永不过期选项已移除，强制30天过期"})
    resp.headers.update(DEPRECATED_HEADER)
    return resp, 201 if result["success"] else 400


@compat_bp.route("/api/v4/api-keys/revoke", methods=["POST"])
@require_owner
def compat_api_keys_revoke():
    """[DEPRECATED] 转发到 /api/system/account/workspace-keys/<id> (DELETE)"""
    from .workspace_keys import revoke_workspace_key
    data = request.get_json(silent=True) or {}
    key_id = data.get("key_id")
    if not key_id:
        return jsonify({"ok": False, "error": "key_id 不能为空"}), 400
    result = revoke_workspace_key(int(key_id))
    resp = jsonify({**result, "deprecated": True,
                    "successor": "DELETE /api/system/account/workspace-keys/<id>"})
    resp.headers.update(DEPRECATED_HEADER)
    return resp

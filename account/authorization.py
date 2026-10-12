"""
account/authorization.py — 双域授权矩阵

成员授权必须带 product_id(ZBMP/CTH/SYSTEM) + module + action(read/write)。
与 permission_gate 打通：ZBMP Analyst 不天然拥有 CTH 权限。
AI 不参与授权判定，完全由规则+DB状态决定。
"""
from .models import get_db

VALID_PRODUCTS = ("ZBMP", "CTH", "SYSTEM", "SHARED")
VALID_ACTIONS = ("read", "write")


def get_member_authorizations(user_id: int, *, connection=None) -> list:
    """获取成员的双域授权矩阵"""
    if connection is None:
        conn = get_db()
    else:
        from lumenis.system.security.permission import _require_canonical_scope_connection
        conn = _require_canonical_scope_connection(connection)
    try:
        cur = conn.execute("""
            SELECT id, user_id, product_id, module, action, data_scope, time_range,
                   granted_by, created_at, updated_at
            FROM v4_member_authorizations WHERE user_id=? ORDER BY product_id, module, action
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        if connection is None:
            conn.close()


def set_member_authorizations(user_id: int, authorizations: list, granted_by: int = None) -> dict:
    """
    设置成员授权矩阵（全量替换）。
    authorizations: [{product_id, module, action, data_scope, time_range}, ...]
    """
    conn = get_db()
    try:
        # 校验用户存在且不是 owner
        cur = conn.execute("SELECT role, username FROM v4_users WHERE id=?", (user_id,))
        user = cur.fetchone()
        if not user:
            return {"success": False, "error": "用户不存在"}
        if user["role"] == "owner":
            return {"success": False, "error": "主账号拥有全部权限，无需设置授权"}

        # 校验每条授权
        for auth in authorizations:
            product = (auth.get("product_id") or "").upper()
            if product not in VALID_PRODUCTS:
                return {"success": False, "error": f"无效产品域：{product}，必须是 {VALID_PRODUCTS}"}
            action = (auth.get("action") or "read").lower()
            if action not in VALID_ACTIONS:
                return {"success": False, "error": f"无效动作：{action}，必须是 read/write"}

        # 全量替换：先删后插
        conn.execute("DELETE FROM v4_member_authorizations WHERE user_id=?", (user_id,))
        for auth in authorizations:
            product = auth["product_id"].upper()
            module = auth.get("module", "*")
            action = auth.get("action", "read").lower()
            data_scope = auth.get("data_scope")
            time_range = auth.get("time_range")
            conn.execute(
                """INSERT OR REPLACE INTO v4_member_authorizations
                   (user_id, product_id, module, action, data_scope, time_range, granted_by)
                   VALUES (?,?,?,?,?,?,?)""",
                (user_id, product, module, action, data_scope, time_range, granted_by)
            )
        conn.commit()

        from .audit import log_audit
        log_audit("authorization_set", "member", str(user_id),
                  f"设置授权 {len(authorizations)} 条: {user['username']}")

        return {"success": True, "authorizations": get_member_authorizations(user_id)}
    finally:
        conn.close()


def check_dual_domain_permission(user_id: int, product_id: str, module: str = "*",
                                 action: str = "read", *, connection=None) -> bool:
    """
    双域权限校验。
    owner/admin 拥有全部权限；member(user) 按授权矩阵校验。
    ZBMP 权限 ≠ CTH 权限。
    """
    product_id = (product_id or "").upper()
    action = (action or "read").lower()
    if connection is None:
        conn = get_db()
    else:
        from lumenis.system.security.permission import _require_canonical_scope_connection
        conn = _require_canonical_scope_connection(connection)
    try:
        cur = conn.execute("SELECT role FROM v4_users WHERE id=? AND status='active'", (user_id,))
        user = cur.fetchone()
        if not user:
            return False
        # owner/admin 全部放行
        if user["role"] in ("owner", "admin"):
            return True
        # member 按授权矩阵
        cur = conn.execute(
            """SELECT 1 FROM v4_member_authorizations
               WHERE user_id=? AND product_id=? AND action=?
               AND (module='*' OR module=?)
               LIMIT 1""",
            (user_id, product_id, action, module)
        )
        return cur.fetchone() is not None
    finally:
        if connection is None:
            conn.close()


def get_authorization_matrix_summary() -> dict:
    """获取全部成员的授权矩阵摘要（用于设置页展示）"""
    conn = get_db()
    try:
        cur = conn.execute("""
            SELECT u.id, u.username, u.role, u.display_name,
                   a.product_id, a.module, a.action
            FROM v4_users u
            LEFT JOIN v4_member_authorizations a ON a.user_id = u.id
            WHERE u.role != 'owner'
            ORDER BY u.role, u.id, a.product_id
        """)
        rows = cur.fetchall()
        matrix = {}
        for r in rows:
            uid = r["id"]
            if uid not in matrix:
                matrix[uid] = {
                    "user_id": uid, "username": r["username"],
                    "role": r["role"], "display_name": r["display_name"],
                    "auths": [],
                }
            if r["product_id"]:
                matrix[uid]["auths"].append({
                    "product_id": r["product_id"],
                    "module": r["module"],
                    "action": r["action"],
                })
        return {"members": list(matrix.values())}
    finally:
        conn.close()

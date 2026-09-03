# -*- coding: utf-8 -*-
"""
sync_v4_owner_password.py
把 v4 独立用户体系的 owner 主账号密码，安全对齐到 .env 的 Basic Auth 凭证
（TAIKOO_AUTH_USER / TAIKOO_AUTH_PASSWORD），并清除失败计数 / 锁定。

背景：Basic Auth(.env) 与 v4_users 是两套独立凭证，改了 .env 不会自动同步 v4 owner，
会出现“现网密码已改、v4 设置页仍登不上 / 差一次就锁”的旧残留。本脚本做一次性收敛，
也可在每次改 Basic 密码后复跑保持单一来源。

安全约束：
- 只 UPDATE v4_users 中 role='owner' 的这一行认证字段，绝不触碰任何业务表 / 舆情数据；
- 写入前用 sqlite 在线 backup API 一致性备份整个库到 data/backups/；
- 默认 dry-run 只打印不写；加 --apply 才真正写入；
- 密码不硬编码，一律从 .env 读取；
- 写入后用 verify_password 在本地校验，并走一次 service.login 完整验证（不经过 HTTP、不消耗外部尝试）。

用法：
  .venv\\Scripts\\python.exe scripts/sync_v4_owner_password.py            # 预演
  .venv\\Scripts\\python.exe scripts/sync_v4_owner_password.py --apply    # 真正执行
"""
import os
import sys
import time
import sqlite3
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def load_env_basic():
    """从 .env 读取 TAIKOO_AUTH_USER / TAIKOO_AUTH_PASSWORD（不依赖第三方库）。"""
    user = os.getenv("TAIKOO_AUTH_USER", "")
    pw = os.getenv("TAIKOO_AUTH_PASSWORD", "")
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k == "TAIKOO_AUTH_USER" and not user:
                    user = v
                if k == "TAIKOO_AUTH_PASSWORD" and not pw:
                    pw = v
    return user, pw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写入；缺省仅预演")
    args = ap.parse_args()

    from v4_upgrade.config import DB_PATH
    from v4_upgrade.auth.security import hash_password, verify_password

    target_user, target_pw = load_env_basic()
    if not target_user or not target_pw:
        print("[FATAL] .env 缺少 TAIKOO_AUTH_USER / TAIKOO_AUTH_PASSWORD，终止（不猜默认值）。")
        sys.exit(2)
    print(f"[INFO] 目标 owner：username={target_user!r}（密码取自 .env，不回显）")

    # 写入前一致性备份（在线 backup API，WAL 安全）
    backup_path = None
    if args.apply:
        bdir = os.path.join(ROOT, "data", "backups")
        os.makedirs(bdir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(bdir, f"pre_v4ownersync_{ts}.db")
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(backup_path)
        with dst:
            src.backup(dst)
        dst.close(); src.close()
        print(f"[BACKUP] 已一致性备份 -> {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id,username,role,status,failed_attempts,locked_until,password_hash "
            "FROM v4_users WHERE role='owner' ORDER BY id LIMIT 1"
        ).fetchone()
        if not row:
            print("[FATAL] 不存在 role=owner 账号，终止（不擅自创建）。")
            sys.exit(3)
        print(f"[BEFORE] id={row['id']} username={row['username']!r} status={row['status']} "
              f"failed={row['failed_attempts']} locked={row['locked_until']} "
              f"pw_match_now={verify_password(target_pw, row['password_hash'])}")

        new_hash = hash_password(target_pw)
        if not args.apply:
            print("[DRY-RUN] 将把 owner 对齐为 .env 凭证并清零 failed_attempts/locked_until；加 --apply 执行。")
            print("[DRY-RUN] 新哈希本地校验:", verify_password(target_pw, new_hash))
            return

        with conn:  # 事务
            conn.execute(
                "UPDATE v4_users SET username=?, password_hash=?, status='active', "
                "failed_attempts=0, locked_until=NULL, must_change_password=0, "
                "updated_at=datetime('now','localtime') WHERE id=? AND role='owner'",
                (target_user, new_hash, row["id"]),
            )
        after = conn.execute(
            "SELECT username,status,failed_attempts,locked_until,password_hash "
            "FROM v4_users WHERE id=?", (row["id"],)
        ).fetchone()
        ok_hash = verify_password(target_pw, after["password_hash"])
        print(f"[AFTER] username={after['username']!r} status={after['status']} "
              f"failed={after['failed_attempts']} locked={after['locked_until']} pw_verify={ok_hash}")
        if not ok_hash:
            print("[FATAL] 写入后本地校验失败，请用备份恢复：", backup_path)
            sys.exit(4)
    finally:
        conn.close()

    # 走完整 service.login 验证（内存内，成功会清计数并发 token；不经过 HTTP）
    from v4_upgrade.auth import service
    res = service.login(target_user, target_pw, ip="127.0.0.1", user_agent="ownersync-script")
    print("[LOGIN-CHECK] success=", res.get("success"),
          "role=", (res.get("user") or {}).get("role"),
          "token=", bool(res.get("token")), "err=", res.get("error"))
    if not res.get("success"):
        print("[FATAL] service.login 验证失败，请用备份恢复：", backup_path)
        sys.exit(5)
    print("[DONE] v4 owner 已与 .env Basic 凭证对齐，锁定计数已清零。")


if __name__ == "__main__":
    main()

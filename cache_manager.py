# -*- coding: utf-8 -*-
"""
广州太古汇舆情系统：本地缓存降级模块

功能：
1. 每次成功采集后保存数据快照到 data/cache/
2. 网络不可用时，前端展示缓存数据 + "最后更新时间"
3. 管理缓存版本和过期时间
4. 提供缓存状态API
5. 不显示空白页面
"""
from __future__ import annotations
import json, os, shutil, time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / "data" / "cache"
CACHE_META = CACHE_DIR / "cache_meta.json"
MAX_CACHE_AGE_HOURS = 72  # 缓存最大保留时间（小时）
MAX_SNAPSHOTS = 5  # 保留最近5个快照

def _ensure_dirs():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _load_meta() -> Dict:
    _ensure_dirs()
    if CACHE_META.exists():
        try:
            return json.loads(CACHE_META.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"snapshots": [], "current": None}

def _save_meta(meta: Dict):
    _ensure_dirs()
    CACHE_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

def create_snapshot(db_path: str = None) -> Dict:
    """
    创建当前数据库的缓存快照
    
    Args:
        db_path: 数据库路径，默认使用 data/monitor.db
    
    Returns:
        快照信息字典
    """
    _ensure_dirs()
    
    if db_path is None:
        db_path = str(BASE / "data" / "monitor.db")
    
    if not os.path.exists(db_path):
        return {"success": False, "error": "数据库不存在"}
    
    # 生成快照ID
    snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = CACHE_DIR / snapshot_id
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    # 复制数据库
    db_dest = snapshot_dir / "monitor.db"
    try:
        shutil.copy2(db_path, str(db_dest))
    except Exception as e:
        return {"success": False, "error": f"复制数据库失败: {str(e)}"}
    
    # 生成快照摘要（用于快速展示）
    summary = _generate_db_summary(db_path)
    
    # 保存快照信息
    snapshot_info = {
        "id": snapshot_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "created_ts": time.time(),
        "db_size": os.path.getsize(db_dest),
        "summary": summary,
        "path": str(snapshot_dir)
    }
    
    # 保存摘要到快照目录
    (snapshot_dir / "summary.json").write_text(
        json.dumps(snapshot_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    # 更新元数据
    meta = _load_meta()
    meta["snapshots"].append(snapshot_info)
    meta["current"] = snapshot_id
    # 只保留最近MAX_SNAPSHOTS个
    if len(meta["snapshots"]) > MAX_SNAPSHOTS:
        old_snapshots = meta["snapshots"][:-MAX_SNAPSHOTS]
        meta["snapshots"] = meta["snapshots"][-MAX_SNAPSHOTS:]
        # 删除旧快照目录
        for old in old_snapshots:
            old_path = CACHE_DIR / old["id"]
            if old_path.exists():
                shutil.rmtree(str(old_path), ignore_errors=True)
    
    _save_meta(meta)
    
    # 清理过期缓存
    _cleanup_expired()
    
    return {"success": True, "snapshot": snapshot_info}

def _generate_db_summary(db_path: str) -> Dict:
    """生成数据库摘要（统计信息）"""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        summary = {"tables": {}}
        
        # 统计各表记录数
        tables = ["notes", "events", "alerts", "daily_reports", "note_comments"]
        for table in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                summary["tables"][table] = count
            except Exception:
                summary["tables"][table] = 0
        
        # 统计情感分布
        try:
            sentiment = conn.execute("""
                SELECT sentiment, COUNT(*) as cnt 
                FROM notes 
                WHERE sentiment IS NOT NULL AND sentiment != ''
                GROUP BY sentiment
            """).fetchall()
            summary["sentiment"] = {row[0]: row[1] for row in sentiment}
        except Exception:
            summary["sentiment"] = {}
        
        # 最近更新时间
        try:
            latest = conn.execute("SELECT MAX(created_at) FROM notes").fetchone()[0]
            summary["latest_note_time"] = latest
        except Exception:
            summary["latest_note_time"] = None
        
        conn.close()
        return summary
    except Exception as e:
        return {"error": str(e)}

def get_latest_cache() -> Optional[Dict]:
    """获取最新的缓存快照信息"""
    meta = _load_meta()
    if not meta["snapshots"]:
        return None
    return meta["snapshots"][-1]

def get_cache_status() -> Dict:
    """获取缓存状态（供API调用）"""
    meta = _load_meta()
    latest = get_latest_cache()
    
    is_expired = False
    age_hours = None
    if latest:
        age_hours = (time.time() - latest["created_ts"]) / 3600
        is_expired = age_hours > MAX_CACHE_AGE_HOURS
    
    return {
        "has_cache": latest is not None,
        "cache_count": len(meta["snapshots"]),
        "latest_snapshot": latest,
        "latest_age_hours": round(age_hours, 1) if age_hours else None,
        "is_expired": is_expired,
        "max_age_hours": MAX_CACHE_AGE_HOURS,
        "should_use_cache": latest is not None and not is_expired
    }

def get_cached_data(query_type: str = "stats", limit: int = 50) -> Dict:
    """
    从缓存中获取数据（供前端降级展示）
    
    Args:
        query_type: 查询类型 - stats/notes/events/alerts
        limit: 返回条数限制
    
    Returns:
        缓存数据 + 元信息
    """
    latest = get_latest_cache()
    if not latest:
        return {"has_cache": False, "data": None, "message": "无可用缓存"}
    
    cache_db = Path(latest["path"]) / "monitor.db"
    if not cache_db.exists():
        return {"has_cache": False, "data": None, "message": "缓存数据库不存在"}
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(cache_db))
        conn.row_factory = sqlite3.Row
        
        result = {
            "has_cache": True,
            "cache_time": latest["created_at"],
            "cache_age_minutes": round((time.time() - latest["created_ts"]) / 60, 1),
            "is_cached_data": True,
            "warning": "当前为缓存数据，网络恢复后将自动更新"
        }
        
        if query_type == "stats":
            # 统计信息
            total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            negative = conn.execute("SELECT COUNT(*) FROM notes WHERE sentiment='negative'").fetchone()[0]
            positive = conn.execute("SELECT COUNT(*) FROM notes WHERE sentiment='positive'").fetchone()[0]
            high_risk = conn.execute("SELECT COUNT(*) FROM alerts WHERE level='high'").fetchone()[0]
            total_engagements = conn.execute("SELECT COALESCE(SUM(likes+comments+collects+shares),0) FROM notes").fetchone()[0]
            
            result["data"] = {
                "total": total,
                "negative": negative,
                "positive": positive,
                "neutral": total - negative - positive,
                "high_risk": high_risk,
                "total_engagements": total_engagements
            }
        
        elif query_type == "notes":
            rows = conn.execute("""
                SELECT id, title, author, likes, collects, comments, sentiment, 
                       risk_level, created_at, url 
                FROM notes 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            result["data"] = [dict(row) for row in rows]
        
        elif query_type == "events":
            rows = conn.execute("""
                SELECT * FROM events 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            result["data"] = [dict(row) for row in rows]
        
        elif query_type == "alerts":
            rows = conn.execute("""
                SELECT * FROM alerts 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            result["data"] = [dict(row) for row in rows]
        
        conn.close()
        return result
    
    except Exception as e:
        return {"has_cache": True, "data": None, "error": str(e)}

def _cleanup_expired():
    """清理过期的缓存快照"""
    meta = _load_meta()
    now = time.time()
    expired = []
    valid = []
    
    for snap in meta["snapshots"]:
        age_hours = (now - snap["created_ts"]) / 3600
        if age_hours > MAX_CACHE_AGE_HOURS:
            expired.append(snap)
        else:
            valid.append(snap)
    
    # 删除过期快照
    for old in expired:
        old_path = CACHE_DIR / old["id"]
        if old_path.exists():
            shutil.rmtree(str(old_path), ignore_errors=True)
    
    meta["snapshots"] = valid
    if meta["current"] not in [s["id"] for s in valid]:
        meta["current"] = valid[-1]["id"] if valid else None
    
    _save_meta(meta)

def list_snapshots() -> List[Dict]:
    """列出所有缓存快照"""
    meta = _load_meta()
    return meta["snapshots"]

def delete_snapshot(snapshot_id: str) -> Dict:
    """删除指定快照"""
    meta = _load_meta()
    snap_path = CACHE_DIR / snapshot_id
    
    if snap_path.exists():
        shutil.rmtree(str(snap_path), ignore_errors=True)
    
    meta["snapshots"] = [s for s in meta["snapshots"] if s["id"] != snapshot_id]
    if meta["current"] == snapshot_id:
        meta["current"] = meta["snapshots"][-1]["id"] if meta["snapshots"] else None
    
    _save_meta(meta)
    return {"success": True, "deleted": snapshot_id}

"""
人工复核完整闭环
- 负面舆情二次确认
- 工单流转
- 样本回流（用于AI模型迭代）
- 复核统计
"""
import os
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from lumenis.shared.database import DatabaseRepository, main_db_path


class ReviewStatus(Enum):
    """复核状态"""
    PENDING = "pending"           # 待复核
    CONFIRMED = "confirmed"       # 已确认（确认为负面）
    REJECTED = "rejected"         # 已驳回（非负面）
    ESCALATED = "escalated"       # 已升级（需要上级复核）


class ReviewPriority(Enum):
    """复核优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ReviewWorkflow:
    """人工复核工作流"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = main_db_path()
        self.db_path = db_path
        self._ensure_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        return DatabaseRepository(self.db_path).connect()
    
    def _ensure_tables(self):
        """确保复核相关表存在"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 复核工单表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE,
                note_id TEXT,
                review_type TEXT DEFAULT 'negative',
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                reason TEXT,
                reviewer TEXT,
                review_comment TEXT,
                review_time TEXT,
                created_at TEXT,
                updated_at TEXT,
                escalated_to TEXT,
                sample_label TEXT,
                model_version TEXT
            )
        """)
        
        # 复核操作日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT,
                note_id TEXT,
                action TEXT,
                operator TEXT,
                comment TEXT,
                old_status TEXT,
                new_status TEXT,
                created_at TEXT
            )
        """)
        
        # 样本回流表（用于AI模型迭代）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT UNIQUE,
                title TEXT,
                content TEXT,
                original_sentiment TEXT,
                reviewed_sentiment TEXT,
                original_risk TEXT,
                reviewed_risk TEXT,
                is_negative_confirmed INTEGER DEFAULT 0,
                reviewer TEXT,
                review_time TEXT,
                model_trained INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_ticket(self, note_id: str, review_type: str = "negative",
                      priority: str = "medium", reason: str = "") -> str:
        """创建复核工单"""
        ticket_id = f"REV{datetime.now().strftime('%Y%m%d%H%M%S')}{note_id[-4:]}"
        now = datetime.now().isoformat()
        
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR IGNORE INTO review_tickets 
                (ticket_id, note_id, review_type, status, priority, reason, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticket_id, note_id, review_type, "pending", priority, reason, now, now))
            
            # 记录日志
            conn.execute("""
                INSERT INTO review_logs 
                (ticket_id, note_id, action, operator, old_status, new_status, created_at)
                VALUES (?, ?, 'create', 'system', '', 'pending', ?)
            """, (ticket_id, note_id, now))
            
            conn.commit()
            return ticket_id
        except Exception as e:
            print(f"[ReviewWorkflow] 创建工单失败: {e}")
            return ""
        finally:
            conn.close()
    
    def confirm_negative(self, note_id: str, reviewer: str = "",
                         comment: str = "") -> bool:
        """确认负面舆情"""
        now = datetime.now().isoformat()
        conn = self._get_connection()
        try:
            # 更新工单状态
            conn.execute("""
                UPDATE review_tickets 
                SET status = 'confirmed', reviewer = ?, review_comment = ?, 
                    review_time = ?, updated_at = ?
                WHERE note_id = ? AND status = 'pending'
            """, (reviewer, comment, now, now, note_id))
            
            # 更新笔记的negative_confirmed字段
            conn.execute("""
                UPDATE notes 
                SET negative_confirmed = 1, negative_confirmed_at = ?, 
                    negative_confirmed_by = ?
                WHERE note_id = ?
            """, (now, reviewer, note_id))
            
            # 记录日志
            ticket = conn.execute(
                "SELECT ticket_id FROM review_tickets WHERE note_id = ? ORDER BY id DESC LIMIT 1",
                (note_id,)
            ).fetchone()
            ticket_id = ticket['ticket_id'] if ticket else ""
            
            conn.execute("""
                INSERT INTO review_logs 
                (ticket_id, note_id, action, operator, comment, old_status, new_status, created_at)
                VALUES (?, ?, 'confirm', ?, ?, 'pending', 'confirmed', ?)
            """, (ticket_id, note_id, reviewer, comment, now))
            
            # 样本回流
            self._add_sample(conn, note_id, is_negative_confirmed=1, reviewer=reviewer)
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[ReviewWorkflow] 确认负面失败: {e}")
            return False
        finally:
            conn.close()
    
    def reject_negative(self, note_id: str, reviewer: str = "",
                        comment: str = "") -> bool:
        """驳回负面舆情（非负面）"""
        now = datetime.now().isoformat()
        conn = self._get_connection()
        try:
            # 更新工单状态
            conn.execute("""
                UPDATE review_tickets 
                SET status = 'rejected', reviewer = ?, review_comment = ?, 
                    review_time = ?, updated_at = ?
                WHERE note_id = ? AND status = 'pending'
            """, (reviewer, comment, now, now, note_id))
            
            # 更新笔记的negative_confirmed字段
            conn.execute("""
                UPDATE notes 
                SET negative_confirmed = 2, negative_confirmed_at = ?, 
                    negative_confirmed_by = ?
                WHERE note_id = ?
            """, (now, reviewer, note_id))
            
            # 记录日志
            ticket = conn.execute(
                "SELECT ticket_id FROM review_tickets WHERE note_id = ? ORDER BY id DESC LIMIT 1",
                (note_id,)
            ).fetchone()
            ticket_id = ticket['ticket_id'] if ticket else ""
            
            conn.execute("""
                INSERT INTO review_logs 
                (ticket_id, note_id, action, operator, comment, old_status, new_status, created_at)
                VALUES (?, ?, 'reject', ?, ?, 'pending', 'rejected', ?)
            """, (ticket_id, note_id, reviewer, comment, now))
            
            # 样本回流
            self._add_sample(conn, note_id, is_negative_confirmed=0, reviewer=reviewer)
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[ReviewWorkflow] 驳回负面失败: {e}")
            return False
        finally:
            conn.close()
    
    def _add_sample(self, conn: sqlite3.Connection, note_id: str,
                    is_negative_confirmed: int, reviewer: str):
        """添加样本到回流表（用于AI模型迭代）"""
        now = datetime.now().isoformat()
        try:
            note = conn.execute(
                "SELECT title, content, sentiment, risk_level FROM notes WHERE note_id = ?",
                (note_id,)
            ).fetchone()
            
            if note:
                conn.execute("""
                    INSERT OR REPLACE INTO review_samples 
                    (note_id, title, content, original_sentiment, reviewed_sentiment,
                     original_risk, reviewed_risk, is_negative_confirmed, reviewer, 
                     review_time, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    note_id, note['title'], note['content'],
                    note['sentiment'], note['sentiment'],  # 复核后标签待更新
                    note['risk_level'], note['risk_level'],
                    is_negative_confirmed, reviewer, now, now
                ))
        except Exception as e:
            print(f"[ReviewWorkflow] 样本回流失败: {e}")
    
    def get_pending_list(self, page: int = 1, per_page: int = 20) -> Dict:
        """获取待复核列表"""
        conn = self._get_connection()
        try:
            offset = (page - 1) * per_page
            
            # 关联notes表获取笔记详情
            cursor = conn.execute("""
                SELECT rt.*, n.title, n.content, n.author_nickname, n.publish_date,
                       n.likes, n.comments, n.sentiment, n.risk_level, n.url
                FROM review_tickets rt
                LEFT JOIN notes n ON rt.note_id = n.note_id
                WHERE rt.status = 'pending'
                ORDER BY rt.priority DESC, rt.created_at DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            
            tickets = [dict(row) for row in cursor.fetchall()]
            
            # 总数
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM review_tickets WHERE status = 'pending'"
            ).fetchone()['cnt']
            
            return {
                'tickets': tickets,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        finally:
            conn.close()
    
    def get_stats(self) -> Dict:
        """获取复核统计"""
        conn = self._get_connection()
        try:
            stats = {}
            
            # 按状态统计
            cursor = conn.execute("""
                SELECT status, COUNT(*) as cnt FROM review_tickets GROUP BY status
            """)
            for row in cursor.fetchall():
                stats[row['status']] = row['cnt']
            
            # 今日复核数
            today = datetime.now().strftime('%Y-%m-%d')
            today_count = conn.execute("""
                SELECT COUNT(*) as cnt FROM review_tickets 
                WHERE review_time LIKE ?
            """, (f"{today}%",)).fetchone()['cnt']
            stats['today_reviewed'] = today_count
            
            # 样本回流数
            sample_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM review_samples"
            ).fetchone()['cnt']
            stats['sample_count'] = sample_count
            
            # 已训练样本数
            trained_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM review_samples WHERE model_trained = 1"
            ).fetchone()['cnt']
            stats['trained_sample_count'] = trained_count
            
            return stats
        finally:
            conn.close()
    
    def get_samples_for_training(self, limit: int = 100) -> List[Dict]:
        """获取用于模型训练的样本"""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM review_samples 
                WHERE model_trained = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def mark_samples_trained(self, sample_ids: List[int]):
        """标记样本已用于训练"""
        conn = self._get_connection()
        try:
            for sid in sample_ids:
                conn.execute(
                    "UPDATE review_samples SET model_trained = 1 WHERE id = ?",
                    (sid,)
                )
            conn.commit()
        finally:
            conn.close()

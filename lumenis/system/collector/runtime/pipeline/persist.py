"""
数据持久化
将处理后的笔记写入数据库
去重（note_id唯一）、更新已有笔记
"""
import os
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime


class NotePersister:
    """笔记持久化器"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "monitor.db"
            )
        self.db_path = db_path
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保数据库目录存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def note_exists(self, note_id: str) -> bool:
        """检查笔记是否已存在"""
        if not note_id:
            return False
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as cnt FROM notes WHERE note_id = ?",
                (note_id,)
            )
            return cursor.fetchone()['cnt'] > 0
        except:
            return False
        finally:
            conn.close()
    
    def insert_note(self, note: Dict) -> bool:
        """
        插入或更新笔记
        返回: True=新插入, False=更新
        """
        note_id = note.get('note_id', '')
        if not note_id:
            return False
        
        conn = self._get_connection()
        try:
            # 检查是否已存在
            exists = self.note_exists(note_id)
            
            if exists:
                # 更新已有笔记
                self._update_note(conn, note)
                return False
            else:
                # 插入新笔记
                self._insert_note(conn, note)
                return True
        except Exception as e:
            print(f"[NotePersister] 保存笔记失败: {e}")
            return False
        finally:
            conn.close()
    
    def _insert_note(self, conn: sqlite3.Connection, note: Dict):
        """插入新笔记"""
        now = datetime.now().isoformat()
        
        # 基础字段
        fields = {
            'note_id': note.get('note_id', ''),
            'title': note.get('title', ''),
            'content': note.get('content', ''),
            'author_id': note.get('author_id', ''),
            'author_nickname': note.get('author_nickname', ''),
            'likes': note.get('likes', 0),
            'comments': note.get('comments', 0),
            'collects': note.get('collects', 0),
            'shares': note.get('shares', 0),
            'publish_date': note.get('publish_date', ''),
            'url': note.get('url', ''),
            'xsec_token': note.get('xsec_token', ''),
            'source_platform': note.get('source_platform', 'xhs'),
            'sentiment': note.get('sentiment', 'neutral'),
            'risk_level': note.get('risk_level', 'low'),
            'keywords': note.get('keywords', ''),
            'industry': note.get('industry', ''),
            'event_id': note.get('event_id', ''),
            'negative_confirmed': note.get('negative_confirmed', 0),
            'subject_verified': note.get('_subject_verified', 0),
            'subject_confidence': note.get('_subject_confidence', 0),
            'collected_at': now,
            'created_at': now,
            'updated_at': now,
        }
        
        # 动态构建INSERT
        columns = ', '.join(fields.keys())
        placeholders = ', '.join(['?' for _ in fields])
        values = list(fields.values())
        
        conn.execute(
            f"INSERT OR IGNORE INTO notes ({columns}) VALUES ({placeholders})",
            values
        )
        conn.commit()
    
    def _update_note(self, conn: sqlite3.Connection, note: Dict):
        """更新已有笔记（只更新互动量等可变字段）"""
        now = datetime.now().isoformat()
        
        update_fields = {
            'likes': note.get('likes', 0),
            'comments': note.get('comments', 0),
            'collects': note.get('collects', 0),
            'shares': note.get('shares', 0),
            'updated_at': now,
        }
        
        # 如果正文之前为空，现在有内容，更新正文
        if note.get('content'):
            update_fields['content'] = note['content']
        
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [note.get('note_id', '')]
        
        conn.execute(
            f"UPDATE notes SET {set_clause} WHERE note_id = ?",
            values
        )
        conn.commit()
    
    def batch_persist(self, notes: List[Dict]) -> Dict:
        """
        批量持久化
        返回: {'inserted': 新插入数, 'updated': 更新数, 'failed': 失败数}
        """
        result = {'inserted': 0, 'updated': 0, 'failed': 0}
        
        for note in notes:
            try:
                is_new = self.insert_note(note)
                if is_new:
                    result['inserted'] += 1
                else:
                    result['updated'] += 1
            except Exception as e:
                print(f"[NotePersister] 批量保存失败: {e}")
                result['failed'] += 1
        
        return result
    
    def save_comments(self, comments: List[Dict]) -> int:
        """保存评论到 note_comments 表（生产表名，非 comments）"""
        if not comments:
            return 0
        
        conn = self._get_connection()
        saved = 0
        now = datetime.now().isoformat()
        try:
            for comment in comments:
                try:
                    import json as _json
                    raw_json = _json.dumps(comment.get('raw_data', {}), ensure_ascii=False)
                    conn.execute("""
                        INSERT OR IGNORE INTO note_comments 
                        (comment_id, note_id, content, author_id, author_nickname, 
                         likes, publish_time, parent_id, raw_json, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        comment.get('comment_id', ''),
                        comment.get('note_id', ''),
                        comment.get('content', ''),
                        comment.get('author_id', ''),
                        comment.get('author_nickname', ''),
                        comment.get('likes', 0),
                        comment.get('publish_time', ''),
                        comment.get('parent_comment_id', comment.get('parent_id', '')),
                        raw_json,
                        now,
                    ))
                    saved += 1
                except Exception as ce:
                    print(f"[NotePersister] 单条评论保存失败: {ce}")
            conn.commit()
        except Exception as e:
            print(f"[NotePersister] 保存评论失败: {e}")
        finally:
            conn.close()
        
        return saved

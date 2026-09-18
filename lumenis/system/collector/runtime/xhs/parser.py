"""
XHSParser - 小红书响应解析器

职责：
- 将 API 原始响应解析为数据模型
- 将 HTML 页面解析为数据模型
- 不做主体过滤、不做情感分析（这些是后续 pipeline 的职责）
"""
import re
from typing import List, Optional, Dict, Any
from .models import XHSNote, XHSComment


class XHSParser:
    """小红书响应解析器"""

    @staticmethod
    def parse_search_response(data: Dict[str, Any]) -> List[XHSNote]:
        """
        解析搜索接口响应
        :param data: API 原始 JSON
        :return: 笔记列表
        """
        notes = []
        if not data:
            return notes
        try:
            items = data.get('data', {}).get('items', []) or []
            for item in items:
                note = XHSParser._parse_note_item(item)
                if note:
                    notes.append(note)
        except Exception as e:
            print(f'[XHSParser] 解析搜索响应失败: {e}')
        return notes

    @staticmethod
    def _parse_note_item(item: Dict[str, Any]) -> Optional[XHSNote]:
        """解析单个笔记项"""
        try:
            note_data = item.get('note_card', {}) or item
            note_id = note_data.get('note_id') or note_data.get('id') or ''
            if not note_id:
                return None

            title = note_data.get('display_title', '') or note_data.get('title', '')
            desc = note_data.get('desc', '') or note_data.get('content', '')
            cover = ''
            images = note_data.get('images_list', []) or []
            if images:
                cover = images[0].get('url_default', '') or images[0].get('url', '')
            elif note_data.get('cover'):
                cover = note_data['cover'].get('url_default', '') or note_data['cover'].get('url', '')

            user = note_data.get('user', {}) or {}
            author_id = user.get('user_id', '') or user.get('nickname', '')
            author_nickname = user.get('nickname', '') or user.get('user_id', '')
            author_avatar = user.get('avatar', '') or ''

            interact_info = note_data.get('interact_info', {}) or {}
            likes = int(interact_info.get('liked_count', 0) or interact_info.get('like_count', 0) or 0)
            comments = int(interact_info.get('comment_count', 0) or 0)
            collects = int(interact_info.get('collected_count', 0) or 0)
            shares = int(interact_info.get('share_count', 0) or 0)

            note_type = note_data.get('type', 'normal') or 'normal'
            xsec_token = note_data.get('xsec_token', '') or item.get('xsec_token', '')
            url = f'https://www.xiaohongshu.com/explore/{note_id}'
            if xsec_token:
                url += f'?xsec_token={xsec_token}'

            time_info = note_data.get('time', '') or note_data.get('last_update_time', '')
            publish_date = XHSParser._format_time(time_info)

            tag_list = []
            for tag in note_data.get('tag_list', []) or []:
                if isinstance(tag, dict):
                    tag_list.append(tag.get('name', ''))
                elif isinstance(tag, str):
                    tag_list.append(tag)

            return XHSNote(
                note_id=note_id,
                title=title,
                content=desc,
                url=url,
                cover=cover,
                author_id=author_id,
                author_nickname=author_nickname,
                author_avatar=author_avatar,
                likes=likes,
                comments=comments,
                collects=collects,
                shares=shares,
                note_type=note_type,
                xsec_token=xsec_token,
                publish_date=publish_date,
                image_list=[img.get('url_default', '') for img in images if isinstance(img, dict)],
                tag_list=tag_list,
                raw_data=item,
            )
        except Exception as e:
            print(f'[XHSParser] 解析笔记项失败: {e}')
            return None

    @staticmethod
    def parse_detail_response(data: Dict[str, Any]) -> Optional[XHSNote]:
        """解析笔记详情响应"""
        if not data:
            return None
        try:
            items = data.get('data', {}).get('items', []) or []
            if items:
                return XHSParser._parse_note_item(items[0])
        except Exception as e:
            print(f'[XHSParser] 解析详情响应失败: {e}')
        return None

    @staticmethod
    def parse_comments_response(data: Dict[str, Any]) -> tuple:
        """
        解析评论响应
        :return: (评论列表, 下一页游标, 是否有更多)
        """
        comments = []
        cursor = ''
        has_more = False
        if not data:
            return comments, cursor, has_more
        try:
            comment_data = data.get('data', {}) or {}
            cursor = comment_data.get('cursor', '') or ''
            has_more = bool(comment_data.get('has_more', False))
            for item in comment_data.get('comments', []) or []:
                comment = XHSParser._parse_comment_item(item)
                if comment:
                    comments.append(comment)
        except Exception as e:
            print(f'[XHSParser] 解析评论响应失败: {e}')
        return comments, cursor, has_more

    @staticmethod
    def _parse_comment_item(item: Dict[str, Any]) -> Optional[XHSComment]:
        """解析单个评论项"""
        try:
            comment_id = item.get('id', '') or item.get('comment_id', '')
            if not comment_id:
                return None
            user_info = item.get('user_info', {}) or {}
            return XHSComment(
                comment_id=comment_id,
                note_id=item.get('note_id', ''),
                content=item.get('content', '') or '',
                author_id=user_info.get('user_id', '') or '',
                author_nickname=user_info.get('nickname', '') or '',
                likes=int(item.get('like_count', 0) or 0),
                publish_time=XHSParser._format_time(item.get('create_time', '')),
                ip_location=item.get('ip_location', '') or '',
                raw_data=item,
            )
        except Exception:
            return None

    @staticmethod
    def _format_time(time_str: str) -> str:
        """格式化时间字符串为 YYYY-MM-DD"""
        if not time_str:
            return ''
        # 时间戳（毫秒）
        if str(time_str).isdigit() and len(str(time_str)) >= 10:
            try:
                from datetime import datetime
                ts = int(time_str)
                if ts > 1e12:
                    ts = ts // 1000
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            except Exception:
                pass
        # 字符串日期
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', str(time_str))
        if match:
            return f'{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}'
        return str(time_str)[:10]

    @staticmethod
    def parse_html_search(page_html: str) -> List[XHSNote]:
        """
        从 HTML 页面解析搜索结果（备用方案，API 不可用时使用）
        :param page_html: 页面 HTML
        :return: 笔记列表
        """
        notes = []
        # 实际实现使用 BeautifulSoup 或正则
        # 这里是架构骨架
        try:
            # 从 __INITIAL_STATE__ 中提取数据
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', page_html, re.DOTALL)
            if match:
                import json
                data = json.loads(match.group(1))
                # 解析数据...
                pass
        except Exception as e:
            print(f'[XHSParser] 解析 HTML 失败: {e}')
        return notes

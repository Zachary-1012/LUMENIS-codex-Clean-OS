"""
数据标准化
繁简归一、时间纠错、空值过滤、字段标准化
"""
import re
from typing import Dict, List, Optional
from datetime import datetime


class NoteNormalizer:
    """笔记数据标准化器"""
    
    def __init__(self):
        # 繁体到简体的常用字映射（简化版）
        self.traditional_to_simplified = {
            '廣': '广', '州': '州', '太': '太', '古': '古', '匯': '汇',
            '購': '购', '買': '买', '賣': '卖', '車': '车', '門': '门',
            '開': '开', '關': '关', '時間': '时间', '時候': '时候',
            '裡': '里', '後': '后', '為': '为', '與': '与', '對': '对',
            '從': '从', '過': '过', '還': '还', '來': '来', '個': '个',
            '們': '们', '這': '这', '那': '那', '裡': '里', '麼': '么',
            '會': '会', '能': '能', '要': '要', '說': '说', '話': '话',
            '點': '点', '樣': '样', '覺': '觉', '實': '实', '現': '现',
        }
    
    def normalize_text(self, text: str) -> str:
        """文本标准化：繁简归一、去除多余空白"""
        if not text:
            return ""
        
        # 繁简归一
        for traditional, simplified in self.traditional_to_simplified.items():
            text = text.replace(traditional, simplified)
        
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 去除特殊字符
        text = text.replace('\u200b', '').replace('\ufeff', '')
        
        return text
    
    def normalize_date(self, date_str: str) -> str:
        """日期标准化：统一为 YYYY-MM-DD HH:MM:SS 格式"""
        if not date_str:
            return ""
        
        date_str = str(date_str).strip()
        
        # 已经是标准格式
        if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', date_str):
            return date_str
        
        # 时间戳（毫秒）
        if date_str.isdigit() and len(date_str) >= 10:
            try:
                ts = int(date_str)
                if ts > 1e12:  # 毫秒
                    ts /= 1000
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # 常见格式转换
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
            '%Y/%m/%d',
            '%Y年%m月%d日 %H:%M:%S',
            '%Y年%m月%d日 %H:%M',
            '%Y年%m月%d日',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                continue
        
        # 相对时间（如"3小时前"、"2天前"）
        now = datetime.now()
        if '小时前' in date_str:
            try:
                hours = int(re.search(r'(\d+)', date_str).group())
                return (now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        elif '天前' in date_str:
            try:
                days = int(re.search(r'(\d+)', date_str).group())
                return (now - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        elif '分钟前' in date_str or '刚刚' in date_str:
            return now.strftime('%Y-%m-%d %H:%M:%S')
        
        return date_str
    
    def normalize_number(self, value) -> int:
        """数字标准化：处理"1.2万"、"3.5k"等格式"""
        if value is None:
            return 0
        
        if isinstance(value, (int, float)):
            return int(value)
        
        value = str(value).strip().lower()
        
        if not value:
            return 0
        
        # 纯数字
        if value.isdigit():
            return int(value)
        
        # 带单位
        multiplier = 1
        if '万' in value or 'w' in value:
            multiplier = 10000
            value = value.replace('万', '').replace('w', '')
        elif '千' in value or 'k' in value:
            multiplier = 1000
            value = value.replace('千', '').replace('k', '')
        
        try:
            num = float(re.sub(r'[^\d.]', '', value))
            return int(num * multiplier)
        except:
            return 0
    
    def normalize_note(self, note: Dict) -> Dict:
        """标准化单条笔记"""
        normalized = note.copy()
        
        # 文本标准化
        normalized['title'] = self.normalize_text(note.get('title', ''))
        normalized['content'] = self.normalize_text(note.get('content', ''))
        normalized['author_nickname'] = self.normalize_text(note.get('author_nickname', ''))
        
        # 日期标准化
        normalized['publish_date'] = self.normalize_date(note.get('publish_date', ''))
        
        # 数字标准化
        normalized['likes'] = self.normalize_number(note.get('likes', 0))
        normalized['comments'] = self.normalize_number(note.get('comments', 0))
        normalized['collects'] = self.normalize_number(note.get('collects', 0))
        normalized['shares'] = self.normalize_number(note.get('shares', 0))
        
        # 计算互动总量
        normalized['total_engagement'] = (
            normalized['likes'] + 
            normalized['comments'] * 3 + 
            normalized['collects'] * 2 + 
            normalized['shares']
        )
        
        # 确保note_id存在
        if not normalized.get('note_id'):
            normalized['note_id'] = ''
        
        # 确保source_platform存在
        if not normalized.get('source_platform'):
            normalized['source_platform'] = 'xhs'
        
        return normalized
    
    def normalize_notes(self, notes: List[Dict]) -> List[Dict]:
        """批量标准化笔记"""
        return [self.normalize_note(note) for note in notes]
    
    def is_valid_note(self, note: Dict) -> bool:
        """检查笔记是否有效（非空、有内容）"""
        title = (note.get('title') or '').strip()
        content = (note.get('content') or '').strip()
        note_id = (note.get('note_id') or '').strip()
        
        # 必须有note_id
        if not note_id:
            return False
        
        # 标题和正文不能都为空
        if not title and not content:
            return False
        
        # 异常时间检查（未来时间、超远期历史时间）
        publish_date = note.get('publish_date', '')
        if publish_date:
            try:
                dt = datetime.strptime(publish_date[:19], '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                if dt > now:  # 未来时间
                    return False
                if dt.year < 2010:  # 超远期历史
                    return False
            except:
                pass
        
        return True
    
    def filter_valid(self, notes: List[Dict]) -> List[Dict]:
        """过滤无效笔记"""
        return [note for note in notes if self.is_valid_note(note)]


# 导入timedelta（放在文件末尾避免循环导入问题）
from datetime import timedelta



def normalize_note(note) -> dict:
    """模块级适配函数：兼容 live_engine 调用契约，委托 NoteNormalizer。"""
    return NoteNormalizer().normalize_note(note)

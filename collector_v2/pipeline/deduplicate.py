"""
SimHash语义去重
解决转载、洗稿、重复内容问题
双重去重：URL去重 + SimHash语义去重
"""
import hashlib
import re
from typing import List, Set, Optional, Dict
from collections import defaultdict


class SimHashDeduplicator:
    """SimHash语义去重器"""
    
    def __init__(self, hash_bits: int = 64, threshold: int = 6):
        """
        hash_bits: SimHash位数
        threshold: 汉明距离阈值，小于此值认为重复
                   短文本建议5-8，长文本建议3-5
        """
        self.hash_bits = hash_bits
        self.threshold = threshold
        self._hashes: Set[int] = set()
        self._hash_to_note: Dict[int, str] = {}
    
    def _tokenize(self, text: str) -> List[str]:
        """分词（简单按字/词切分）"""
        if not text:
            return []
        # 移除标点和空白
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        # 中文按字切分，英文按词切分
        tokens = []
        current_word = ""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                if current_word:
                    tokens.append(current_word.lower())
                    current_word = ""
                tokens.append(char)
            else:
                current_word += char
        if current_word:
            tokens.append(current_word.lower())
        return tokens
    
    def _hash_token(self, token: str) -> int:
        """对单个token哈希"""
        return int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
    
    def compute(self, text: str) -> int:
        """计算文本的SimHash值"""
        tokens = self._tokenize(text)
        if not tokens:
            return 0
        
        # 初始化向量
        v = [0] * self.hash_bits
        
        for token in tokens:
            h = self._hash_token(token)
            for i in range(self.hash_bits):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        
        # 生成SimHash
        simhash = 0
        for i in range(self.hash_bits):
            if v[i] > 0:
                simhash |= (1 << i)
        
        return simhash
    
    def hamming_distance(self, h1: int, h2: int) -> int:
        """计算汉明距离"""
        x = h1 ^ h2
        count = 0
        while x:
            count += 1
            x &= x - 1
        return count
    
    def is_duplicate(self, text: str, note_id: str = "") -> tuple:
        """
        判断文本是否重复
        返回: (is_duplicate, similar_note_id, min_distance)
        min_distance: 与已有文本的最小汉明距离（用于调试）
        """
        simhash = self.compute(text)
        
        # 检查是否有相似的，记录最小距离
        min_distance = float('inf')
        similar_note_id = ""
        
        for existing_hash, existing_note_id in self._hash_to_note.items():
            distance = self.hamming_distance(simhash, existing_hash)
            if distance < min_distance:
                min_distance = distance
                similar_note_id = existing_note_id
            if distance <= self.threshold:
                return True, existing_note_id, distance
        
        # 不重复，添加到集合
        self._hashes.add(simhash)
        if note_id:
            self._hash_to_note[simhash] = note_id
        
        actual_min = min_distance if min_distance != float('inf') else -1
        return False, "", actual_min
    
    def add(self, text: str, note_id: str):
        """添加文本到去重集合"""
        simhash = self.compute(text)
        self._hashes.add(simhash)
        self._hash_to_note[simhash] = note_id
    
    def batch_deduplicate(self, notes: List[Dict]) -> List[Dict]:
        """
        批量去重
        notes: 包含note_id和title/content的字典列表
        返回: 去重后的笔记列表
        """
        unique_notes = []
        duplicate_count = 0
        
        for note in notes:
            note_id = note.get("note_id", "")
            title = note.get("title", "")
            content = note.get("content", "")
            text = f"{title} {content}"
            
            is_dup, similar_id, distance = self.is_duplicate(text, note_id)
            
            if is_dup:
                duplicate_count += 1
                note["_duplicate"] = True
                note["_similar_note_id"] = similar_id
                note["_hamming_distance"] = distance
            else:
                note["_duplicate"] = False
                unique_notes.append(note)
        
        return unique_notes
    
    def clear(self):
        """清空去重集合"""
        self._hashes.clear()
        self._hash_to_note.clear()
    
    @property
    def size(self) -> int:
        return len(self._hashes)
    
    def debug_distance(self, text1: str, text2: str) -> Dict:
        """
        调试方法：计算两个文本的SimHash和汉明距离
        返回: {'hash1': int, 'hash2': int, 'distance': int, 'tokens1': list, 'tokens2': list}
        """
        h1 = self.compute(text1)
        h2 = self.compute(text2)
        distance = self.hamming_distance(h1, h2)
        return {
            'hash1': h1,
            'hash2': h2,
            'distance': distance,
            'tokens1': self._tokenize(text1),
            'tokens2': self._tokenize(text2),
            'threshold': self.threshold,
            'is_duplicate': distance <= self.threshold
        }

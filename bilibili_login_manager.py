"""
B站登录管理模块
功能：
1. Cookie导入和管理
2. 登录态检测
3. B站搜索采集（视频、评论、弹幕）
4. 与系统全网话题搜集集成
"""
import os
import json
import time
from pathlib import Path
from datetime import datetime


class BilibiliLoginManager:
    """B站登录管理器"""
    
    def __init__(self):
        base_dir = Path(__file__).resolve().parent
        self.cookie_file = str(base_dir / 'data' / 'bilibili_cookies.json')
        self.status_file = str(base_dir / 'data' / 'bilibili_login_status.json')
        self._browser = None
    
    def check_login_status(self):
        """检测登录状态"""
        result = {
            'logged_in': False,
            'has_cookies': False,
            'cookie_count': 0,
            'user_id': None,
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'message': ''
        }
        
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                result['has_cookies'] = True
                result['cookie_count'] = len(cookies)
                
                # 查找SESSDATA和DedeUserID
                for cookie in cookies:
                    if cookie.get('name') == 'DedeUserID':
                        result['user_id'] = cookie.get('value')
                    if cookie.get('name') == 'SESSDATA':
                        result['logged_in'] = True
            except Exception:
                pass
        
        if result['logged_in']:
            result['message'] = f'B站已登录，用户ID: {result.get("user_id", "未知")}'
        else:
            result['message'] = 'B站未登录或Cookie无效'
        
        return result
    
    def get_cookies(self):
        """获取cookies列表"""
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def get_cookie_string(self):
        """获取cookie字符串（用于HTTP请求）"""
        cookies = self.get_cookies()
        if not cookies:
            return ''
        
        cookie_parts = []
        for cookie in cookies:
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            if name and value:
                cookie_parts.append(f'{name}={value}')
        
        return '; '.join(cookie_parts)
    
    def get_headers(self):
        """获取B站请求头"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com/',
            'Cookie': self.get_cookie_string()
        }
    
    def search_videos(self, keyword, page=1, page_size=20):
        """
        搜索B站视频
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
        
        Returns:
            dict: 搜索结果
        """
        try:
            import requests
            
            url = 'https://api.bilibili.com/x/web-interface/search/type'
            params = {
                'search_type': 'video',
                'keyword': keyword,
                'page': page,
                'page_size': page_size
            }
            
            response = requests.get(url, headers=self.get_headers(), params=params, timeout=15)
            data = response.json()
            
            if data.get('code') == 0:
                result = data.get('data', {})
                videos = []
                for result_item in result.get('result', []):
                    videos.append({
                        'id': result_item.get('aid'),
                        'bvid': result_item.get('bvid'),
                        'title': result_item.get('title', '').replace('<em class="keyword">', '').replace('</em>', ''),
                        'author': result_item.get('author'),
                        'play': result_item.get('play'),
                        'video_review': result_item.get('video_review'),
                        'favorites': result_item.get('favorites'),
                        'pubdate': result_item.get('pubdate'),
                        'duration': result_item.get('duration'),
                        'description': result_item.get('description', ''),
                        'url': f'https://www.bilibili.com/video/{result_item.get("bvid", "")}',
                        'platform': 'bilibili',
                        'type': 'video'
                    })
                
                return {
                    'ok': True,
                    'keyword': keyword,
                    'total': result.get('numResults', 0),
                    'page': page,
                    'page_size': page_size,
                    'videos': videos
                }
            else:
                return {'ok': False, 'error': data.get('message', '搜索失败'), 'code': data.get('code')}
        
        except Exception as e:
            return {'ok': False, 'error': str(e)}
    
    def clear_login_data(self):
        """清除登录数据"""
        try:
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
            if os.path.exists(self.status_file):
                os.remove(self.status_file)
            return True
        except Exception as e:
            print(f'[BilibiliLogin] 清除登录数据失败: {e}')
            return False


# 全局单例
_bilibili_manager = None

def get_bilibili_manager():
    """获取全局B站登录管理器单例"""
    global _bilibili_manager
    if _bilibili_manager is None:
        _bilibili_manager = BilibiliLoginManager()
    return _bilibili_manager


if __name__ == '__main__':
    manager = BilibiliLoginManager()
    
    print('=== B站登录状态 ===')
    status = manager.check_login_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    
    if status['logged_in']:
        print()
        print('=== 测试搜索"广州太古汇" ===')
        result = manager.search_videos('广州太古汇')
        if result['ok']:
            print(f'找到 {result["total"]} 个视频')
            for i, video in enumerate(result['videos'][:5]):
                print(f'{i+1}. {video["title"]} - {video["author"]} - 播放:{video["play"]}')
        else:
            print(f'搜索失败: {result.get("error")}')

"""
微博登录管理模块
功能：
1. 扫码登录微博，保存登录态
2. 登录态检测和自动恢复
3. 持久化浏览器配置（user_data_dir）
4. 与系统集成，提供全网话题搜集数据源

使用方法：
    from weibo_login_manager import WeiboLoginManager
    manager = WeiboLoginManager()
    manager.login_with_qrcode()  # 扫码登录
    manager.check_login_status()  # 检测登录状态
"""
import os
import json
import time
from pathlib import Path
from datetime import datetime


class WeiboLoginManager:
    """微博登录管理器"""

    @classmethod
    def read_saved_session_metadata(cls):
        """Read cached state without loading Cookies or creating a profile.

        A saved login receipt is historical metadata, never current session
        verification. Missing/invalid values retain an explicit unknown state.
        """
        result = {'state': 'UNVERIFIED', 'saved_logged_in': None,
                  'cookie_count': None, 'last_login': None}
        status_file = Path(__file__).resolve().parent / 'data' / 'weibo_login_status.json'
        if not status_file.is_file():
            return {**result, 'state': 'NOT_AVAILABLE'}
        try:
            if status_file.stat().st_size > 65536:
                raise ValueError('session metadata is too large')
            status = json.loads(status_file.read_text(encoding='utf-8'))
            if type(status) is not dict:
                raise ValueError('session metadata must be an object')
            if type(status.get('logged_in')) is bool:
                result['saved_logged_in'] = status['logged_in']
            count = status.get('cookie_count')
            if type(count) is int and count >= 0:
                result['cookie_count'] = count
            timestamp = status.get('last_login')
            if type(timestamp) is str:
                datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                result['last_login'] = timestamp
            return result
        except (OSError, ValueError, TypeError):
            return {**result, 'state': 'ERROR'}
    
    def __init__(self, user_data_dir=None):
        """
        初始化微博登录管理器
        
        Args:
            user_data_dir: 浏览器用户数据目录，用于保存登录态
        """
        base_dir = Path(__file__).resolve().parent
        self.user_data_dir = user_data_dir or str(base_dir / 'data' / 'weibo_profile')
        self.cookie_file = str(base_dir / 'data' / 'weibo_cookies.json')
        self.status_file = str(base_dir / 'data' / 'weibo_login_status.json')
        
        # 确保目录存在
        os.makedirs(self.user_data_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        
        self._browser = None
        self._context = None
        self._page = None
        
        print(f'[WeiboLogin] 初始化完成，登录态保存目录: {self.user_data_dir}')
    
    def login_with_qrcode(self, headless=False, timeout=300):
        """
        扫码登录微博
        
        Args:
            headless: 是否无头模式（False会显示浏览器窗口）
            timeout: 登录超时时间（秒），默认5分钟
        
        Returns:
            bool: 是否登录成功
        """
        try:
            from playwright.sync_api import sync_playwright
            
            print('[WeiboLogin] 启动浏览器，打开微博登录页...')
            
            with sync_playwright() as p:
                # 使用持久化上下文，保存登录态
                context = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=headless,
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = context.new_page()
                
                # 打开微博登录页
                page.goto('https://passport.weibo.com/sso/signin', wait_until='domcontentloaded', timeout=30000)
                time.sleep(2)
                
                print('[WeiboLogin] ========================================')
                print('[WeiboLogin] 请在浏览器中使用微博APP扫码登录')
                print('[WeiboLogin] 登录成功后请回到这里按回车键继续')
                print('[WeiboLogin] ========================================')
                
                # 等待用户登录
                start_time = time.time()
                logged_in = False
                
                while time.time() - start_time < timeout:
                    # 检测是否登录成功（跳转到微博首页或搜索页）
                    current_url = page.url
                    if 'weibo.com' in current_url and 'passport' not in current_url and 'signin' not in current_url:
                        logged_in = True
                        print(f'[WeiboLogin] 检测到登录成功！当前URL: {current_url}')
                        break
                    
                    # 检测页面内容是否包含用户信息
                    try:
                        content = page.content()
                        if '我的首页' in content or '微博首页' in content or '退出' in content:
                            logged_in = True
                            print('[WeiboLogin] 检测到登录成功！页面包含用户信息')
                            break
                    except Exception:
                        pass
                    
                    time.sleep(2)
                
                if not logged_in:
                    print(f'[WeiboLogin] ⚠️ 登录超时（{timeout}秒），请重新运行登录')
                    context.close()
                    return False
                
                # 保存cookies
                cookies = context.cookies()
                self._save_cookies(cookies)
                
                # 保存登录状态
                self._save_login_status(True, cookies)
                
                print('[WeiboLogin] ✅ 登录成功！登录态已保存')
                print(f'[WeiboLogin] Cookies数量: {len(cookies)}')
                print(f'[WeiboLogin] 登录态保存目录: {self.user_data_dir}')
                
                # 测试搜索功能
                print('[WeiboLogin] 测试微博搜索功能...')
                try:
                    page.goto('https://s.weibo.com/weibo?q=广州太古汇', wait_until='domcontentloaded', timeout=30000)
                    time.sleep(3)
                    content = page.content()
                    if '登录' not in content or 'weibo.com/login' not in content:
                        print('[WeiboLogin] ✅ 搜索功能正常，可以采集微博数据')
                    else:
                        print('[WeiboLogin] ⚠️ 搜索页需要重新登录')
                except Exception as e:
                    print(f'[WeiboLogin] 搜索测试失败: {e}')
                
                context.close()
                return True
                
        except ImportError:
            print('[WeiboLogin] ❌ playwright未安装，请运行: pip install playwright && playwright install chromium')
            return False
        except Exception as e:
            print(f'[WeiboLogin] ❌ 登录异常: {e}')
            return False
    
    def check_login_status(self):
        """
        检测登录状态
        
        Returns:
            dict: 登录状态信息
        """
        result = {
            'logged_in': False,
            'has_cookies': False,
            'has_profile': False,
            'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'message': ''
        }
        
        # 检查是否有cookies文件
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                result['has_cookies'] = True
                result['cookie_count'] = len(cookies)
            except Exception:
                pass
        
        # 检查是否有浏览器配置目录
        if os.path.exists(self.user_data_dir):
            profile_files = os.listdir(self.user_data_dir)
            if len(profile_files) > 0:
                result['has_profile'] = True
                result['profile_files'] = len(profile_files)
        
        # 读取保存的登录状态
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                result['saved_status'] = status.get('logged_in', False)
                result['last_login'] = status.get('last_login', '未知')
            except Exception:
                pass
        
        # 如果有cookies或profile，认为可能已登录
        if result['has_cookies'] or result['has_profile']:
            result['logged_in'] = True
            result['message'] = '检测到登录态，可尝试采集'
        else:
            result['message'] = '未检测到登录态，请先扫码登录'
        
        return result
    
    def get_cookies(self):
        """
        获取保存的cookies
        
        Returns:
            list: cookies列表
        """
        if os.path.exists(self.cookie_file):
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def get_cookie_string(self):
        """
        获取cookie字符串（用于HTTP请求）
        
        Returns:
            str: cookie字符串
        """
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
    
    def _save_cookies(self, cookies):
        """保存cookies到文件"""
        try:
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[WeiboLogin] 保存cookies失败: {e}')
    
    def _save_login_status(self, logged_in, cookies=None):
        """保存登录状态"""
        status = {
            'logged_in': logged_in,
            'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'cookie_count': len(cookies) if cookies else 0
        }
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[WeiboLogin] 保存登录状态失败: {e}')
    
    def clear_login_data(self):
        """清除登录数据"""
        try:
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
            if os.path.exists(self.status_file):
                os.remove(self.status_file)
            # 清除浏览器配置目录
            if os.path.exists(self.user_data_dir):
                import shutil
                shutil.rmtree(self.user_data_dir, ignore_errors=True)
            print('[WeiboLogin] ✅ 登录数据已清除')
            return True
        except Exception as e:
            print(f'[WeiboLogin] 清除登录数据失败: {e}')
            return False


# 全局单例
_weibo_manager = None

def get_weibo_manager():
    """获取全局微博登录管理器单例"""
    global _weibo_manager
    if _weibo_manager is None:
        _weibo_manager = WeiboLoginManager()
    return _weibo_manager


if __name__ == '__main__':
    # 测试
    manager = WeiboLoginManager()
    
    print('=== 微博登录管理器测试 ===')
    print()
    
    # 检测登录状态
    status = manager.check_login_status()
    print('当前登录状态:')
    print(json.dumps(status, ensure_ascii=False, indent=2))
    print()
    
    # 询问是否登录
    choice = input('是否现在扫码登录微博？(y/n): ')
    if choice.lower() == 'y':
        success = manager.login_with_qrcode(headless=False)
        if success:
            print('登录成功！')
        else:
            print('登录失败，请重试')

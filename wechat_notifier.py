"""
广州太古汇舆情监测系统 - 微信通知中心
支持多渠道微信推送，消息去重，失败自动重试，推送日志

推送渠道：
1. 企业微信群机器人（Webhook，最稳定）
2. Server酱（方糖）
3. PushPlus
4. WxPusher

不替代邮件，作为独立通知渠道。
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'monitor.db')


# ============================================================
# 通知级别
# ============================================================
class NotificationLevel(Enum):
    """通知级别"""
    INFO = 'info'           # 普通信息
    WARNING = 'warning'     # 警告
    HIGH_RISK = 'high_risk' # 高风险（立即推送）
    CRITICAL = 'critical'   # 严重风险（立即推送）
    ERROR = 'error'         # 系统异常
    DAILY = 'daily'         # 日报
    WEEKLY = 'weekly'       # 周报


# ============================================================
# 通知类型
# ============================================================
class NotificationType(Enum):
    """通知类型"""
    HIGH_RISK_ALERT = 'high_risk_alert'       # 高风险舆情
    CRITICAL_ALERT = 'critical_alert'         # 严重风险
    SYSTEM_ERROR = 'system_error'             # 系统异常
    COLLECTION_FAILED = 'collection_failed'   # 采集失败
    LOGIN_EXPIRED = 'login_expired'           # 登录态失效
    DAILY_REPORT = 'daily_report'             # 日报推送
    WEEKLY_REPORT = 'weekly_report'           # 周报推送
    GENERAL = 'general'                       # 通用通知


# ============================================================
# 推送渠道基类
# ============================================================
class NotificationChannel:
    """通知渠道基类"""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
    
    def send(self, title: str, content: str, level: NotificationLevel = NotificationLevel.INFO) -> bool:
        """发送通知"""
        raise NotImplementedError
    
    def test(self) -> bool:
        """测试渠道连通性"""
        raise NotImplementedError


# ============================================================
# 企业微信群机器人
# ============================================================
class WeComBotChannel(NotificationChannel):
    """企业微信群机器人（Webhook，最稳定）"""
    
    def __init__(self, webhook_url: str, enabled: bool = True):
        super().__init__('企业微信群机器人', enabled)
        self.webhook_url = webhook_url
    
    def send(self, title: str, content: str, level: NotificationLevel = NotificationLevel.INFO) -> bool:
        """发送企业微信消息"""
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            # 级别图标
            level_icons = {
                NotificationLevel.INFO: 'ℹ️',
                NotificationLevel.WARNING: '⚠️',
                NotificationLevel.HIGH_RISK: '🔴',
                NotificationLevel.CRITICAL: '🚨',
                NotificationLevel.ERROR: '❌',
                NotificationLevel.DAILY: '📊',
                NotificationLevel.WEEKLY: '📈',
            }
            icon = level_icons.get(level, '📢')
            
            # 构造markdown消息
            markdown_content = f"## {icon} {title}\n\n{content}\n\n---\n*广州太古汇舆情监测系统 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
            
            payload = {
                'msgtype': 'markdown',
                'markdown': {
                    'content': markdown_content
                }
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('errcode', -1) == 0
                
        except Exception as e:
            print(f"[企业微信] 发送失败: {e}")
            return False
    
    def test(self) -> bool:
        """测试连通性"""
        return self.send('测试消息', '这是一条测试消息，微信通知中心工作正常。', NotificationLevel.INFO)


# ============================================================
# Server酱（方糖）
# ============================================================
class ServerChanChannel(NotificationChannel):
    """Server酱（方糖）微信推送"""
    
    def __init__(self, send_key: str, enabled: bool = True):
        super().__init__('Server酱', enabled)
        self.send_key = send_key
    
    def send(self, title: str, content: str, level: NotificationLevel = NotificationLevel.INFO) -> bool:
        """发送Server酱消息"""
        if not self.enabled or not self.send_key:
            return False
        
        try:
            url = f'https://sctapi.ftqq.com/{self.send_key}.send'
            
            payload = urllib.parse.urlencode({
                'title': title,
                'desp': content
            }).encode('utf-8')
            
            req = urllib.request.Request(
                url,
                data=payload,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('code', -1) == 0
                
        except Exception as e:
            print(f"[Server酱] 发送失败: {e}")
            return False
    
    def test(self) -> bool:
        """测试连通性"""
        return self.send('测试消息', '这是一条测试消息，微信通知中心工作正常。', NotificationLevel.INFO)


# ============================================================
# PushPlus
# ============================================================
class PushPlusChannel(NotificationChannel):
    """PushPlus微信推送"""
    
    def __init__(self, token: str, enabled: bool = True):
        super().__init__('PushPlus', enabled)
        self.token = token
    
    def send(self, title: str, content: str, level: NotificationLevel = NotificationLevel.INFO) -> bool:
        """发送PushPlus消息"""
        if not self.enabled or not self.token:
            return False
        
        try:
            url = 'http://www.pushplus.plus/send'
            
            payload = json.dumps({
                'token': self.token,
                'title': title,
                'content': content,
                'template': 'html'
            }).encode('utf-8')
            
            req = urllib.request.Request(
                url,
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('code', -1) == 200
                
        except Exception as e:
            print(f"[PushPlus] 发送失败: {e}")
            return False
    
    def test(self) -> bool:
        """测试连通性"""
        return self.send('测试消息', '这是一条测试消息，微信通知中心工作正常。', NotificationLevel.INFO)


# ============================================================
# 自定义微信公众号（模板消息推送）
# ============================================================
class WeChatOfficialAccountChannel(NotificationChannel):
    """
    自定义微信公众号模板消息推送
    使用自己的公众号，通过模板消息推送给关注用户
    需要：AppID、AppSecret、模板ID、接收者openid列表
    """
    
    def __init__(self, app_id: str, app_secret: str, template_id: str,
                 receiver_openids: List[str], enabled: bool = True):
        super().__init__('微信公众号', enabled)
        self.app_id = app_id
        self.app_secret = app_secret
        self.template_id = template_id
        self.receiver_openids = receiver_openids
        self._access_token = None
        self._token_expires_at = 0
    
    def _get_access_token(self) -> Optional[str]:
        """获取access_token（自动缓存2小时）"""
        now = time.time()
        
        # 如果token未过期，直接返回
        if self._access_token and now < self._token_expires_at:
            return self._access_token
        
        try:
            url = (
                f'https://api.weixin.qq.com/cgi-bin/token'
                f'?grant_type=client_credential'
                f'&appid={self.app_id}'
                f'&secret={self.app_secret}'
            )
            
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'access_token' in result:
                    self._access_token = result['access_token']
                    # 提前5分钟过期，避免边界问题
                    self._token_expires_at = now + result.get('expires_in', 7200) - 300
                    return self._access_token
                else:
                    print(f"[微信公众号] 获取access_token失败: {result}")
                    return None
                    
        except Exception as e:
            print(f"[微信公众号] 获取access_token异常: {e}")
            return None
    
    def _format_template_data(self, title: str, content: str, 
                               level: NotificationLevel) -> Dict[str, Any]:
        """
        格式化模板消息数据
        模板字段约定：
        {{first.DATA}} - 标题/级别
        {{keyword1.DATA}} - 通知类型
        {{keyword2.DATA}} - 内容摘要
        {{keyword3.DATA}} - 时间
        {{remark.DATA}} - 备注/详情
        """
        level_names = {
            NotificationLevel.INFO: '普通通知',
            NotificationLevel.WARNING: '警告通知',
            NotificationLevel.HIGH_RISK: '高风险告警',
            NotificationLevel.CRITICAL: '严重风险告警',
            NotificationLevel.ERROR: '系统异常',
            NotificationLevel.DAILY: '每日日报',
            NotificationLevel.WEEKLY: '每周周报',
        }
        level_name = level_names.get(level, '通知')
        
        # 内容摘要（限制长度）
        content_summary = content.replace('\n', ' ')[:100]
        if len(content) > 100:
            content_summary += '...'
        
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            'first': {
                'value': f'{level_name}：{title}',
                'color': '#FF0000' if level in [NotificationLevel.HIGH_RISK, NotificationLevel.CRITICAL, NotificationLevel.ERROR] 
                         else '#FF9900' if level == NotificationLevel.WARNING 
                         else '#173177'
            },
            'keyword1': {
                'value': level_name,
                'color': '#173177'
            },
            'keyword2': {
                'value': content_summary,
                'color': '#173177'
            },
            'keyword3': {
                'value': now_str,
                'color': '#173177'
            },
            'remark': {
                'value': '\n广州太古汇舆情监测系统',
                'color': '#888888'
            }
        }
    
    def send(self, title: str, content: str, 
             level: NotificationLevel = NotificationLevel.INFO) -> bool:
        """发送微信公众号模板消息"""
        if not self.enabled or not self.app_id or not self.app_secret:
            return False
        
        if not self.receiver_openids:
            print("[微信公众号] 没有配置接收者openid")
            return False
        
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        url = f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}'
        
        template_data = self._format_template_data(title, content, level)
        
        all_success = True
        for openid in self.receiver_openids:
            try:
                payload = json.dumps({
                    'touser': openid,
                    'template_id': self.template_id,
                    'data': template_data
                }, ensure_ascii=False).encode('utf-8')
                
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    if result.get('errcode', 0) != 0:
                        print(f"[微信公众号] 发送给 {openid} 失败: {result}")
                        all_success = False
                        
            except Exception as e:
                print(f"[微信公众号] 发送给 {openid} 异常: {e}")
                all_success = False
        
        return all_success
    
    def test(self) -> bool:
        """测试连通性（先测试获取access_token）"""
        token = self._get_access_token()
        if token:
            # token获取成功，再尝试发送测试消息
            return self.send(
                '微信公众号测试', 
                '这是一条测试消息，微信公众号通知中心工作正常。',
                NotificationLevel.INFO
            )
        return False


# ============================================================
# 通知模板
# ============================================================
class NotificationTemplates:
    """通知模板"""
    
    @staticmethod
    def high_risk_alert(note_title: str, note_url: str, risk_reason: str, likes: int = 0) -> tuple:
        """高风险舆情告警模板"""
        title = '🔴 高风险舆情告警'
        content = f"""
**笔记标题**：{note_title}
**风险原因**：{risk_reason}
**互动数据**：{likes} 赞
**笔记链接**：[点击查看]({note_url})

> 请及时关注并处理此高风险舆情。
"""
        return title, content.strip()
    
    @staticmethod
    def critical_alert(event_title: str, impact: str, note_count: int) -> tuple:
        """严重风险告警模板"""
        title = '🚨 严重风险告警'
        content = f"""
**事件标题**：{event_title}
**影响范围**：{impact}
**关联笔记**：{note_count} 条

> ⚠️ 严重风险事件，请立即处理！
"""
        return title, content.strip()
    
    @staticmethod
    def system_error(error_msg: str, module: str = '未知') -> tuple:
        """系统异常模板"""
        title = '❌ 系统异常告警'
        content = f"""
**异常模块**：{module}
**异常信息**：{error_msg}
**发生时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

> 请检查系统运行状态。
"""
        return title, content.strip()
    
    @staticmethod
    def collection_failed(reason: str, keyword: str = '') -> tuple:
        """采集失败模板"""
        title = '⚠️ 采集失败告警'
        content = f"""
**采集关键词**：{keyword or '全部'}
**失败原因**：{reason}
**失败时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

> 请检查小红书登录态和网络连接。
"""
        return title, content.strip()
    
    @staticmethod
    def login_expired(platform: str = '小红书') -> tuple:
        """登录态失效模板"""
        title = '🔐 登录态失效告警'
        content = f"""
**平台**：{platform}
**状态**：登录态已失效
**时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

> 请重新登录{platform}，否则采集将无法正常进行。
"""
        return title, content.strip()
    
    @staticmethod
    def daily_report(date: str, total_notes: int, negative_count: int, high_risk_count: int, report_url: str = '') -> tuple:
        """日报推送模板"""
        title = f'📊 舆情日报 - {date}'
        content = f"""
**统计日期**：{date}
**笔记总数**：{total_notes} 条
**负面笔记**：{negative_count} 条
**高风险**：{high_risk_count} 条

{('**完整报告**：[点击查看](' + report_url + ')') if report_url else ''}

> 详细数据请登录系统查看。
"""
        return title, content.strip()
    
    @staticmethod
    def weekly_report(week_range: str, total_notes: int, negative_count: int, event_count: int, report_url: str = '') -> tuple:
        """周报推送模板"""
        title = f'📈 舆情周报 - {week_range}'
        content = f"""
**统计周期**：{week_range}
**笔记总数**：{total_notes} 条
**负面笔记**：{negative_count} 条
**舆情事件**：{event_count} 个

{('**完整报告**：[点击查看](' + report_url + ')') if report_url else ''}

> 详细数据请登录系统查看。
"""
        return title, content.strip()


# ============================================================
# 微信通知中心
# ============================================================
class WeChatNotifier:
    """微信通知中心"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化微信通知中心
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path or DB_PATH
        self.channels: List[NotificationChannel] = []
        self.dedup_cache: Dict[str, datetime] = {}
        self.dedup_ttl = 300  # 去重时间窗口（秒），5分钟内相同消息不重复推送
        
        self._init_database()
        self._load_channels()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 推送日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_type TEXT,
                level TEXT,
                title TEXT,
                content TEXT,
                channel TEXT,
                status TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                message_hash TEXT,
                created_at TEXT,
                sent_at TEXT
            )
        """)
        
        # 通知配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT,
                channel_type TEXT,
                config_json TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_channels(self):
        """从配置加载推送渠道"""
        # 从环境变量加载
        env = self._load_env()
        
        # 企业微信群机器人
        wecom_webhook = env.get('WECOM_WEBHOOK_URL', '')
        if wecom_webhook:
            self.channels.append(WeComBotChannel(wecom_webhook, enabled=True))
        
        # Server酱
        serverchan_key = env.get('SERVERCHAN_SEND_KEY', '')
        if serverchan_key:
            self.channels.append(ServerChanChannel(serverchan_key, enabled=True))
        
        # PushPlus
        pushplus_token = env.get('PUSHPLUS_TOKEN', '')
        if pushplus_token:
            self.channels.append(PushPlusChannel(pushplus_token, enabled=True))
        
        # 自定义微信公众号（模板消息推送）
        wechat_app_id = env.get('WECHAT_APP_ID', '')
        wechat_app_secret = env.get('WECHAT_APP_SECRET', '')
        wechat_template_id = env.get('WECHAT_TEMPLATE_ID', '')
        wechat_receiver_openids = env.get('WECHAT_RECEIVER_OPENIDS', '')
        
        if wechat_app_id and wechat_app_secret and wechat_template_id and wechat_receiver_openids:
            # 支持多个openid，用逗号分隔
            openids = [oid.strip() for oid in wechat_receiver_openids.split(',') if oid.strip()]
            self.channels.append(WeChatOfficialAccountChannel(
                app_id=wechat_app_id,
                app_secret=wechat_app_secret,
                template_id=wechat_template_id,
                receiver_openids=openids,
                enabled=True
            ))
        
        # 从数据库加载
        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT * FROM notification_config WHERE enabled = 1")
            for row in cursor.fetchall():
                config = json.loads(row['config_json'])
                channel_type = row['channel_type']
                
                if channel_type == 'wecom':
                    self.channels.append(WeComBotChannel(
                        config.get('webhook_url', ''),
                        enabled=row['enabled'] == 1
                    ))
                elif channel_type == 'serverchan':
                    self.channels.append(ServerChanChannel(
                        config.get('send_key', ''),
                        enabled=row['enabled'] == 1
                    ))
                elif channel_type == 'pushplus':
                    self.channels.append(PushPlusChannel(
                        config.get('token', ''),
                        enabled=row['enabled'] == 1
                    ))
                elif channel_type == 'wechat_official':
                    openids = config.get('receiver_openids', [])
                    if isinstance(openids, str):
                        openids = [oid.strip() for oid in openids.split(',') if oid.strip()]
                    self.channels.append(WeChatOfficialAccountChannel(
                        app_id=config.get('app_id', ''),
                        app_secret=config.get('app_secret', ''),
                        template_id=config.get('template_id', ''),
                        receiver_openids=openids,
                        enabled=row['enabled'] == 1
                    ))
            conn.close()
        except Exception as e:
            print(f"[通知中心] 加载数据库配置失败: {e}")
    
    def _load_env(self) -> Dict[str, str]:
        """加载.env文件"""
        env = {}
        env_path = os.path.join(BASE_DIR, '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env[key.strip()] = value.strip().strip('"').strip("'")
        return env
    
    def _generate_hash(self, notification_type: str, title: str, content: str) -> str:
        """生成消息哈希（用于去重）"""
        raw = f"{notification_type}:{title}:{content[:200]}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()
    
    def _is_duplicate(self, message_hash: str) -> bool:
        """检查是否重复消息"""
        now = datetime.now()
        
        # 清理过期缓存
        expired = [k for k, v in self.dedup_cache.items() 
                   if (now - v).total_seconds() > self.dedup_ttl]
        for k in expired:
            del self.dedup_cache[k]
        
        if message_hash in self.dedup_cache:
            return True
        
        self.dedup_cache[message_hash] = now
        return False
    
    def _log_notification(self, notification_type: str, level: NotificationLevel, 
                          title: str, content: str, channel: str, 
                          status: str, error_message: str = '', 
                          retry_count: int = 0, message_hash: str = ''):
        """记录推送日志"""
        try:
            conn = self._get_connection()
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT INTO notification_logs 
                (notification_type, level, title, content, channel, status, 
                 error_message, retry_count, message_hash, created_at, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notification_type, level.value, title, content, channel,
                status, error_message, retry_count, message_hash, now,
                now if status == 'success' else None
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[通知中心] 记录日志失败: {e}")
    
    def send(self, notification_type: NotificationType, title: str, content: str,
             level: NotificationLevel = NotificationLevel.INFO, 
             max_retries: int = 3, dedup: bool = True) -> Dict[str, Any]:
        """
        发送通知（多渠道，自动重试）
        
        Args:
            notification_type: 通知类型
            title: 标题
            content: 内容
            level: 级别
            max_retries: 最大重试次数
            dedup: 是否去重
        
        Returns:
            发送结果
        """
        result = {
            'success': False,
            'channels': [],
            'failed_channels': [],
            'message_hash': '',
            'duplicate': False
        }
        
        # 消息去重
        message_hash = self._generate_hash(notification_type.value, title, content)
        result['message_hash'] = message_hash
        
        if dedup and self._is_duplicate(message_hash):
            result['duplicate'] = True
            self._log_notification(
                notification_type.value, level, title, content,
                'all', 'skipped', '重复消息，跳过推送', 0, message_hash
            )
            return result
        
        # 检查是否有可用渠道
        enabled_channels = [c for c in self.channels if c.enabled]
        if not enabled_channels:
            self._log_notification(
                notification_type.value, level, title, content,
                'all', 'failed', '没有可用的推送渠道', 0, message_hash
            )
            return result
        
        # 多渠道发送
        for channel in enabled_channels:
            success = False
            last_error = ''
            
            for retry in range(max_retries):
                try:
                    success = channel.send(title, content, level)
                    if success:
                        break
                except Exception as e:
                    last_error = str(e)
                
                if retry < max_retries - 1:
                    time.sleep(2 ** retry)  # 指数退避
            
            if success:
                result['channels'].append(channel.name)
                self._log_notification(
                    notification_type.value, level, title, content,
                    channel.name, 'success', '', 0, message_hash
                )
            else:
                result['failed_channels'].append({
                    'channel': channel.name,
                    'error': last_error or '发送失败'
                })
                self._log_notification(
                    notification_type.value, level, title, content,
                    channel.name, 'failed', last_error, max_retries, message_hash
                )
        
        result['success'] = len(result['channels']) > 0
        return result
    
    def send_high_risk_alert(self, note_title: str, note_url: str, 
                              risk_reason: str, likes: int = 0) -> Dict[str, Any]:
        """发送高风险舆情告警（立即推送）"""
        title, content = NotificationTemplates.high_risk_alert(
            note_title, note_url, risk_reason, likes
        )
        return self.send(
            NotificationType.HIGH_RISK_ALERT, title, content,
            level=NotificationLevel.HIGH_RISK, dedup=True
        )
    
    def send_critical_alert(self, event_title: str, impact: str, 
                             note_count: int) -> Dict[str, Any]:
        """发送严重风险告警（立即推送）"""
        title, content = NotificationTemplates.critical_alert(
            event_title, impact, note_count
        )
        return self.send(
            NotificationType.CRITICAL_ALERT, title, content,
            level=NotificationLevel.CRITICAL, dedup=True
        )
    
    def send_system_error(self, error_msg: str, module: str = '未知') -> Dict[str, Any]:
        """发送系统异常告警"""
        title, content = NotificationTemplates.system_error(error_msg, module)
        return self.send(
            NotificationType.SYSTEM_ERROR, title, content,
            level=NotificationLevel.ERROR, dedup=False
        )
    
    def send_collection_failed(self, reason: str, keyword: str = '') -> Dict[str, Any]:
        """发送采集失败告警"""
        title, content = NotificationTemplates.collection_failed(reason, keyword)
        return self.send(
            NotificationType.COLLECTION_FAILED, title, content,
            level=NotificationLevel.WARNING, dedup=True
        )
    
    def send_login_expired(self, platform: str = '小红书') -> Dict[str, Any]:
        """发送登录态失效告警"""
        title, content = NotificationTemplates.login_expired(platform)
        return self.send(
            NotificationType.LOGIN_EXPIRED, title, content,
            level=NotificationLevel.WARNING, dedup=True
        )
    
    def send_daily_report(self, date: str, total_notes: int, 
                           negative_count: int, high_risk_count: int,
                           report_url: str = '') -> Dict[str, Any]:
        """发送日报推送"""
        title, content = NotificationTemplates.daily_report(
            date, total_notes, negative_count, high_risk_count, report_url
        )
        return self.send(
            NotificationType.DAILY_REPORT, title, content,
            level=NotificationLevel.DAILY, dedup=False
        )
    
    def send_weekly_report(self, week_range: str, total_notes: int,
                            negative_count: int, event_count: int,
                            report_url: str = '') -> Dict[str, Any]:
        """发送周报推送"""
        title, content = NotificationTemplates.weekly_report(
            week_range, total_notes, negative_count, event_count, report_url
        )
        return self.send(
            NotificationType.WEEKLY_REPORT, title, content,
            level=NotificationLevel.WEEKLY, dedup=False
        )
    
    def test_all_channels(self) -> List[Dict[str, Any]]:
        """测试所有渠道连通性"""
        results = []
        for channel in self.channels:
            if channel.enabled:
                success = channel.test()
                results.append({
                    'channel': channel.name,
                    'success': success
                })
        return results
    
    def get_notification_logs(self, limit: int = 50, 
                               status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取推送日志"""
        conn = self._get_connection()
        query = "SELECT * FROM notification_logs"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs
    
    def get_channel_status(self) -> List[Dict[str, Any]]:
        """获取渠道状态"""
        return [
            {
                'name': channel.name,
                'enabled': channel.enabled,
                'type': type(channel).__name__
            }
            for channel in self.channels
        ]
    
    def add_channel(self, channel_type: str, config: Dict[str, Any], 
                    enabled: bool = True) -> bool:
        """添加推送渠道"""
        try:
            conn = self._get_connection()
            now = datetime.now().isoformat()
            
            conn.execute("""
                INSERT INTO notification_config 
                (channel_name, channel_type, config_json, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                config.get('name', channel_type),
                channel_type,
                json.dumps(config, ensure_ascii=False),
                1 if enabled else 0,
                now, now
            ))
            conn.commit()
            conn.close()
            
            # 重新加载渠道
            self.channels = []
            self._load_channels()
            
            return True
        except Exception as e:
            print(f"[通知中心] 添加渠道失败: {e}")
            return False


# ============================================================
# 全局单例
# ============================================================
_global_notifier: Optional[WeChatNotifier] = None


def get_notifier() -> WeChatNotifier:
    """获取全局微信通知中心实例"""
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = WeChatNotifier()
    return _global_notifier


# ============================================================
# 命令行测试
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("📱 微信通知中心 - 测试")
    print("=" * 60)
    
    notifier = WeChatNotifier()
    
    # 渠道状态
    print(f"\n📡 推送渠道:")
    channels = notifier.get_channel_status()
    if channels:
        for ch in channels:
            status = '✅ 已启用' if ch['enabled'] else '❌ 已禁用'
            print(f"  {status} {ch['name']} ({ch['type']})")
    else:
        print("  ⚠️  没有配置推送渠道")
        print("  请在.env文件中添加以下任一配置:")
        print("    WECOM_WEBHOOK_URL=你的企业微信机器人Webhook")
        print("    SERVERCHAN_SEND_KEY=你的Server酱SendKey")
        print("    PUSHPLUS_TOKEN=你的PushPlus Token")
    
    # 推送日志
    print(f"\n📋 最近推送日志:")
    logs = notifier.get_notification_logs(limit=5)
    if logs:
        for log in logs:
            status_icon = '✅' if log['status'] == 'success' else '❌'
            print(f"  {status_icon} [{log['created_at']}] {log['title']} - {log['channel']}")
    else:
        print("  暂无推送记录")
    
    # 测试发送（如果有渠道）
    if channels:
        print(f"\n🧪 发送测试消息...")
        result = notifier.send(
            NotificationType.GENERAL,
            '微信通知中心测试',
            '这是一条测试消息，微信通知中心工作正常。\n\n支持：高风险告警、系统异常、采集失败、日报周报推送等。',
            level=NotificationLevel.INFO,
            dedup=False
        )
        print(f"  发送结果: {'✅ 成功' if result['success'] else '❌ 失败'}")
        print(f"  成功渠道: {result['channels']}")
        print(f"  失败渠道: {result['failed_channels']}")
    
    print(f"\n{'=' * 60}")
    print("✅ 微信通知中心测试完成")
    print(f"{'=' * 60}")

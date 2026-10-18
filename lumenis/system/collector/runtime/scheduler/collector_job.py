"""
采集调度器
- 每日12次采集机会，合理分配
- 一键实时更新保留3次机会
- 剩下9次自动采集，确保7*24h每天都有舆情日报
- 新账号前3次极轻量模式
- 冷却15分钟
"""
import os
import json
import asyncio
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum


class CollectMode(Enum):
    """采集模式"""
    LIGHT = "light"           # 极轻量（新账号前3次）
    NORMAL = "normal"         # 正常
    MANUAL = "manual"         # 手动一键更新
    SCHEDULED = "scheduled"   # 定时自动


class CollectorJob:
    """采集任务"""
    
    def __init__(self, job_id: str, keywords: List[str], 
                 mode: CollectMode = CollectMode.NORMAL,
                 max_scroll: int = 3, max_details: int = 20):
        self.job_id = job_id
        self.keywords = keywords
        self.mode = mode
        self.max_scroll = max_scroll
        self.max_details = max_details
        self.created_at = datetime.now()
        self.started_at = None
        self.finished_at = None
        self.status = "pending"  # pending/running/success/failed
        self.result = {}
        self.error = ""
    
    def to_dict(self) -> Dict:
        return {
            'job_id': self.job_id,
            'keywords': self.keywords,
            'mode': self.mode.value,
            'max_scroll': self.max_scroll,
            'max_details': self.max_details,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'status': self.status,
            'result': self.result,
            'error': self.error,
        }


class Scheduler:
    """采集调度器"""
    
    # 冷却时间（分钟）
    COOLDOWN_MINUTES = 15
    # 新账号前N次极轻量
    NEW_ACCOUNT_LIGHT_COUNT = 3
    # 自动采集时间点（24小时制，确保覆盖全天）
    AUTO_COLLECT_HOURS = [8, 10, 12, 14, 16, 18, 20, 22, 23]
    
    def __init__(self, state_file: Optional[str] = None):
        if state_file is None:
            state_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "collector_state.json"
            )
        self.state_file = state_file
        self.state = self._load_state()
        self.jobs: Dict[str, CollectorJob] = {}
        self._collect_callback: Optional[Callable] = None
    
    def tick_upstream_review(self, queue, *, actor, scope, now=None):
        """Explicit existing-runtime tick; no schedule exists/enables by default."""
        from .upstream_math_review import tick
        return tick(queue, actor=actor, scope=scope, now=now)

    def upstream_review_processor(self, queue, *, actor_provider):
        from .upstream_math_review import processor
        return processor(queue, actor_provider=actor_provider)

    def _load_state(self) -> Dict:
        """加载调度状态（持久化，重启不丢失）"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # 默认状态
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'today': today,
            'total_count': 0,           # 今日总采集次数
            'manual_count': 0,          # 今日手动采集次数
            'auto_count': 0,            # 今日自动采集次数
            'total_collect_count': 0,   # 累计总采集次数（用于新账号判断）
            'last_collect_time': None,  # 上次采集时间
            'last_auto_hour': -1,       # 上次自动采集小时
        }
    
    def _save_state(self):
        """保存调度状态"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def _check_new_day(self):
        """检查是否新的一天，重置计数"""
        today = datetime.now().strftime('%Y-%m-%d')
        if self.state.get('today') != today:
            self.state['today'] = today
            self.state['total_count'] = 0
            self.state['manual_count'] = 0
            self.state['auto_count'] = 0
            self.state['last_auto_hour'] = -1
            self._save_state()
            print(f"[Scheduler] 新的一天 {today}，采集次数已重置")
    
    def is_new_account(self) -> bool:
        """是否是新账号（前N次极轻量）"""
        return self.state.get('total_collect_count', 0) < self.NEW_ACCOUNT_LIGHT_COUNT
    
    def can_collect(self, mode: CollectMode = CollectMode.NORMAL) -> tuple:
        """
        检查是否可以采集
        返回: (can_collect, reason, wait_minutes)
        """
        self._check_new_day()
        
        # Keep the safety cooldown; historical daily/manual product quotas no
        # longer determine whether an authorized collection may run.
        last_time = self.state.get('last_collect_time')
        if last_time:
            try:
                last_dt = datetime.fromisoformat(last_time)
                elapsed = (datetime.now() - last_dt).total_seconds() / 60
                if elapsed < self.COOLDOWN_MINUTES:
                    wait = self.COOLDOWN_MINUTES - elapsed
                    return False, f"冷却中，请等待{int(wait)}分钟", int(wait)
            except:
                pass
        
        return True, "可以采集", 0
    
    def get_mode(self) -> CollectMode:
        """获取当前应使用的采集模式"""
        if self.is_new_account():
            return CollectMode.LIGHT
        return CollectMode.NORMAL
    
    def get_max_scroll(self, mode: CollectMode) -> int:
        """根据模式获取最大滚动次数"""
        if mode == CollectMode.LIGHT:
            return 2
        return 3
    
    def record_collect(self, mode: CollectMode, job_id: str = ""):
        """记录一次采集"""
        self._check_new_day()
        self.state['total_count'] += 1
        self.state['total_collect_count'] += 1
        self.state['last_collect_time'] = datetime.now().isoformat()
        
        if mode == CollectMode.MANUAL:
            self.state['manual_count'] += 1
        elif mode == CollectMode.SCHEDULED:
            self.state['auto_count'] += 1
        
        self._save_state()
        print(f"[Scheduler] 采集记录: 今日{self.state['total_count']}次, "
              f"手动{self.state['manual_count']}次, "
              f"自动{self.state['auto_count']}次, "
              f"累计{self.state['total_collect_count']}次")
    
    def should_auto_collect_now(self) -> bool:
        """检查现在是否应该自动采集"""
        now = datetime.now()
        current_hour = now.hour
        
        # 检查是否在自动采集时间点
        if current_hour not in self.AUTO_COLLECT_HOURS:
            return False
        
        # 检查这个小时是否已经采集过
        if self.state.get('last_auto_hour') == current_hour:
            return False
        
        # 检查是否可以采集
        can, _, _ = self.can_collect(CollectMode.SCHEDULED)
        return can
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        self._check_new_day()
        return {
            'today': self.state['today'],
            'daily_limit': None,
            'total_count': self.state['total_count'],
            'remaining': None,
            'manual_count': self.state['manual_count'],
            'manual_limit': None,
            'manual_remaining': None,
            'auto_count': self.state['auto_count'],
            'total_collect_count': self.state['total_collect_count'],
            'is_new_account': self.is_new_account(),
            'current_mode': self.get_mode().value,
            'last_collect_time': self.state.get('last_collect_time'),
            'auto_collect_hours': self.AUTO_COLLECT_HOURS,
            'cooldown_minutes': self.COOLDOWN_MINUTES,
        }
    
    def set_collect_callback(self, callback: Callable):
        """设置采集回调函数"""
        self._collect_callback = callback
    
    async def run_auto_collect(self):
        """运行自动采集（调度循环）"""
        while True:
            try:
                if self.should_auto_collect_now():
                    print(f"[Scheduler] 触发自动采集: {datetime.now().strftime('%H:%M')}")
                    if self._collect_callback:
                        mode = CollectMode.SCHEDULED
                        job_id = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        await self._collect_callback(job_id, mode)
                        self.record_collect(mode, job_id)
                        self.state['last_auto_hour'] = datetime.now().hour
                        self._save_state()
            except Exception as e:
                print(f"[Scheduler] 自动采集异常: {e}")
            
            # 每分钟检查一次
            await asyncio.sleep(60)

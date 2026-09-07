"""
ZBC 双账号不规则轮换采集管理器 v1.0
- 两个小红书账号（大陆主号xhs_cn + 香港rednote_hk）不规则交替使用
- 根据最近成功率、风控状态、冷却时间、连续使用次数动态选择
- KOS采集专用香港账号
- 话题采集支持APP端adapter
- 安全保险：任一账号风控/冷却/失败时自动切换，双账号都不可用时安全停止
"""
import os
import json
import time
import random
from datetime import datetime, timedelta

try:
    from xhs_cookie_bridge import (
        select_account, get_account_status, is_user_paused,
        XHS_CN_PRIMARY_NAME, XHS_RETINAUT_NAME,
        ACCOUNT_PROFILES, ACCOUNT_CDP_PORTS
    )
except ImportError:
    XHS_CN_PRIMARY_NAME = 'XHS_CN_PRIMARY'
    XHS_RETINAUT_NAME = 'XHS_RETINAUT'
    ACCOUNT_PROFILES = {XHS_CN_PRIMARY_NAME: None, XHS_RETINAUT_NAME: None}
    ACCOUNT_CDP_PORTS = {XHS_CN_PRIMARY_NAME: 9222, XHS_RETINAUT_NAME: 9223}
    def select_account(name): return True, 'stub'
    def get_account_status(): return {}
    def is_user_paused(): return None

# 账号状态文件
STATE_FILE = os.path.join('data', 'private', 'dual_account_rotation_state.json')

# 轮换参数
MAX_CONSECUTIVE_USES = 3  # 同一账号连续使用最大次数（防止固定节奏）
MIN_SWITCH_INTERVAL_SEC = 30  # 最小切换间隔（秒）
RISK_PENALTY_WEIGHT = 0.4  # 风控惩罚权重
FAILURE_PENALTY_WEIGHT = 0.3  # 失败惩罚权重
COOLDOWN_PENALTY_WEIGHT = 0.5  # 冷却惩罚权重
JITTER_RANGE = (0.7, 1.3)  # 不规则浮动范围


class DualAccountRotation:
    """双账号不规则轮换管理器。"""

    def __init__(self):
        self.state = self._load_state()
        self.accounts = [XHS_CN_PRIMARY_NAME, XHS_RETINAUT_NAME]

    def _load_state(self):
        """加载账号轮换状态。"""
        default = {
            'current_account': None,
            'consecutive_uses': 0,
            'last_switch_at': 0,
            'account_stats': {
                XHS_CN_PRIMARY_NAME: {'success': 0, 'failure': 0, 'last_use': 0, 'risk_count': 0, 'cooldown_until': 0},
                XHS_RETINAUT_NAME: {'success': 0, 'failure': 0, 'last_use': 0, 'risk_count': 0, 'cooldown_until': 0}
            },
            'rotation_history': []
        }
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    # 合并默认值（防止新字段缺失）
                    for k, v in default.items():
                        if k not in saved:
                            saved[k] = v
                    for acc in self.accounts if hasattr(self, 'accounts') else [XHS_CN_PRIMARY_NAME, XHS_RETINAUT_NAME]:
                        if acc not in saved['account_stats']:
                            saved['account_stats'][acc] = default['account_stats'].get(acc, default['account_stats'][XHS_CN_PRIMARY_NAME])
                    return saved
            except:
                pass
        return default

    def _save_state(self):
        """保存账号轮换状态。"""
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _account_score(self, account):
        """计算账号综合得分（越高越优先）。"""
        stats = self.state['account_stats'].get(account, {})
        now = time.time()

        # 基础分
        score = 1.0

        # 成功率
        total = stats.get('success', 0) + stats.get('failure', 0)
        if total > 0:
            success_rate = stats.get('success', 0) / total
            score += success_rate * 0.5

        # 风控惩罚
        risk_count = stats.get('risk_count', 0)
        score -= risk_count * RISK_PENALTY_WEIGHT

        # 近期失败惩罚
        if stats.get('last_use', 0) > now - 3600:  # 最近1小时内
            failure_recent = stats.get('failure', 0)
            score -= failure_recent * FAILURE_PENALTY_WEIGHT

        # 冷却惩罚
        cooldown_until = stats.get('cooldown_until', 0)
        if cooldown_until > now:
            score -= COOLDOWN_PENALTY_WEIGHT * 10  # 冷却中大幅降分

        # 连续使用惩罚（鼓励切换）
        if self.state.get('current_account') == account:
            consecutive = self.state.get('consecutive_uses', 0)
            score -= consecutive * 0.2

        # 不规则抖动
        jitter = random.uniform(*JITTER_RANGE)
        score *= jitter

        return score

    def select_next_account(self, force_account=None, kos_mode=False):
        """
        选择下一个采集账号。

        Args:
            force_account: 强制使用指定账号（如KOS专用香港号）
            kos_mode: KOS采集模式，强制使用香港账号

        Returns:
            (account_name, reason)
        """
        # KOS模式强制香港账号
        if kos_mode or force_account == XHS_RETINAUT_NAME:
            account = XHS_RETINAUT_NAME
            reason = 'KOS专用香港账号'
        elif force_account:
            account = force_account
            reason = f'强制指定账号: {force_account}'
        else:
            # 检查最小切换间隔
            now = time.time()
            time_since_switch = now - self.state.get('last_switch_at', 0)

            # 如果当前账号连续使用未达上限且切换间隔不足，继续使用当前账号
            current = self.state.get('current_account')
            if (current and time_since_switch < MIN_SWITCH_INTERVAL_SEC
                    and self.state.get('consecutive_uses', 0) < MAX_CONSECUTIVE_USES):
                account = current
                reason = f'继续使用当前账号（连续{self.state["consecutive_uses"]}次，切换间隔不足）'
            else:
                # 计算两个账号得分，选择得分高的
                scores = {acc: self._account_score(acc) for acc in self.accounts}
                account = max(scores, key=scores.get)
                reason = f'动态选择: {account}(score={scores[account]:.2f}) vs {[a for a in self.accounts if a != account][0]}(score={scores[[a for a in self.accounts if a != account][0]]:.2f})'

        # 切换账号
        if account != self.state.get('current_account'):
            ok, msg = select_account(account)
            if not ok:
                # 切换失败，尝试另一个账号
                other = [a for a in self.accounts if a != account][0]
                ok2, msg2 = select_account(other)
                if ok2:
                    account = other
                    reason += f' | 首选切换失败({msg})，回退到{other}'
                else:
                    return None, f'双账号切换均失败: {msg} / {msg2}'
            self.state['current_account'] = account
            self.state['consecutive_uses'] = 1
            self.state['last_switch_at'] = time.time()
        else:
            self.state['consecutive_uses'] = self.state.get('consecutive_uses', 0) + 1

        # 更新使用记录
        self.state['account_stats'][account]['last_use'] = time.time()
        self.state['rotation_history'].append({
            'account': account,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        # 只保留最近100条历史
        if len(self.state['rotation_history']) > 100:
            self.state['rotation_history'] = self.state['rotation_history'][-100:]

        self._save_state()
        return account, reason

    def record_result(self, account, success, risk=False, cooldown_minutes=0):
        """记录采集结果。"""
        stats = self.state['account_stats'].get(account, {})
        if success:
            stats['success'] = stats.get('success', 0) + 1
        else:
            stats['failure'] = stats.get('failure', 0) + 1
        if risk:
            stats['risk_count'] = stats.get('risk_count', 0) + 1
        if cooldown_minutes > 0:
            stats['cooldown_until'] = time.time() + cooldown_minutes * 60
        self.state['account_stats'][account] = stats
        self._save_state()

    def get_status(self):
        """获取轮换状态。"""
        return {
            'current_account': self.state.get('current_account'),
            'consecutive_uses': self.state.get('consecutive_uses', 0),
            'last_switch_at': datetime.fromtimestamp(self.state.get('last_switch_at', 0)).isoformat() if self.state.get('last_switch_at') else None,
            'account_stats': self.state.get('account_stats', {}),
            'recent_rotations': self.state.get('rotation_history', [])[-10:],
            'ports': ACCOUNT_CDP_PORTS
        }


# 全局单例
_rotation = None

def get_rotation():
    global _rotation
    if _rotation is None:
        _rotation = DualAccountRotation()
    return _rotation


def select_account_for_collection(kos_mode=False, force_account=None):
    """采集入口：选择下一个账号。"""
    rot = get_rotation()
    return rot.select_next_account(force_account=force_account, kos_mode=kos_mode)


def record_collection_result(account, success, risk=False, cooldown_minutes=0):
    """记录采集结果。"""
    rot = get_rotation()
    rot.record_result(account, success, risk, cooldown_minutes)


def get_rotation_status():
    """获取轮换状态。"""
    rot = get_rotation()
    return rot.get_status()

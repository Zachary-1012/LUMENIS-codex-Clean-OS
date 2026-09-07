# -*- coding: utf-8 -*-
"""
ZBC Module Registry — 模组注册与用户自定义管理
设计原则：功能不删除，用户可启用/禁用/排序/自定义布局
"""
import json, os, threading
from datetime import datetime

# 内置模组注册表（所有可用功能模组）
BUILTIN_MODULES = {
    # CTH 域
    "cth_overview": {"name": "CTH 概览", "domain": "cth", "category": "dashboard", "icon": "📊", "default": True, "description": "太古汇实时概览KPI"},
    "cth_realtime": {"name": "实时舆情", "domain": "cth", "category": "monitor", "icon": "📡", "default": True, "description": "小红书笔记实时流"},
    "cth_events": {"name": "事件", "domain": "cth", "category": "monitor", "icon": "⚡", "default": True, "description": "传播/营销/舆情事件"},
    "cth_risk": {"name": "风险预警", "domain": "cth", "category": "monitor", "icon": "⚠️", "default": True, "description": "负面风险与预警"},
    "cth_negative": {"name": "负面确认", "domain": "cth", "category": "monitor", "icon": "🔴", "default": True, "description": "负面内容人工复核"},
    "cth_topics": {"name": "话题监测", "domain": "cth", "category": "monitor", "icon": "#️⃣", "default": True, "description": "话题端监测与APP采集"},
    "cth_brands": {"name": "品牌业态", "domain": "cth", "category": "analysis", "icon": "🏢", "default": True, "description": "199品牌9大业态"},
    "cth_official": {"name": "官方动态", "domain": "cth", "category": "analysis", "icon": "🏛️", "default": True, "description": "太古汇官方账号动态"},
    "cth_data_center": {"name": "数据", "domain": "cth", "category": "data", "icon": "🗄️", "default": True, "description": "全平台数据真源验证"},
    "cth_reports": {"name": "报告", "domain": "cth", "category": "report", "icon": "📋", "default": True, "description": "日/周/月报与专报"},
    "cth_calendar": {"name": "舆情日历", "domain": "cth", "category": "analysis", "icon": "📅", "default": False, "description": "舆情时间线日历视图"},
    "cth_case_library": {"name": "营销案例库", "domain": "cth", "category": "library", "icon": "📚", "default": False, "description": "品牌营销案例研究"},
    # ZBMP 域
    "zbmp_overview": {"name": "品牌市场概览", "domain": "zbmp", "category": "dashboard", "icon": "📈", "default": True, "description": "品牌智能总览"},
    "zbmp_brand": {"name": "品牌监测", "domain": "zbmp", "category": "monitor", "icon": "🎯", "default": True, "description": "品牌声量与表现"},
    "zbmp_kos": {"name": "KOS 运营", "domain": "zbmp", "category": "monitor", "icon": "👑", "default": True, "description": "KOS/KOL/KOC管理"},
    "zbmp_content": {"name": "内容制作", "domain": "zbmp", "category": "creation", "icon": "✍️", "default": True, "description": "AI内容生成与案例库"},
    "zbmp_podcast": {"name": "播客", "domain": "zbmp", "category": "creation", "icon": "🎙️", "default": True, "description": "播客选题与故事节点"},
    "zbmp_competition": {"name": "竞品分析", "domain": "zbmp", "category": "analysis", "icon": "⚔️", "default": False, "description": "竞争品牌对标"},
    "zbmp_reports": {"name": "品牌报告", "domain": "zbmp", "category": "report", "icon": "📊", "default": True, "description": "品牌表现/竞争/增长报告"},
    # System 域
    "system_ai": {"name": "AI 助手", "domain": "system", "category": "intelligence", "icon": "🤖", "default": True, "description": "GPT风格AI轻量助手"},
    "system_browser": {"name": "AI 浏览器", "domain": "system", "category": "tool", "icon": "🌐", "default": True, "description": "内置AI浏览器Runtime"},
    "system_runtime": {"name": "运行时", "domain": "system", "category": "infra", "icon": "⚙️", "default": True, "description": "Worker/Guardian/DLQ监控"},
    "system_collector": {"name": "采集器", "domain": "system", "category": "infra", "icon": "📥", "default": True, "description": "采集调度与双账号轮换"},
    "system_database": {"name": "数据库", "domain": "system", "category": "infra", "icon": "💾", "default": True, "description": "129表生命周期管理"},
    "system_security": {"name": "安全", "domain": "system", "category": "infra", "icon": "🔒", "default": True, "description": "权限/审计/凭证扫描"},
    "system_settings": {"name": "系统设置", "domain": "system", "category": "config", "icon": "🛠️", "default": True, "description": "平台开关/模组管理/品牌配置"},
    "system_evaluation": {"name": "验收评估", "domain": "system", "category": "config", "icon": "✅", "default": False, "description": "Feature Completion Matrix"},
}

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "private", "module_user_config.json")
_lock = threading.Lock()

def _load_user_config():
    """加载用户自定义模组配置"""
    try:
        if os.path.exists(_STATE_FILE):
            with open(_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {"enabled": {}, "order": {}, "layout": {}}

def _save_user_config(cfg):
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    with open(_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get_all_modules(domain=None):
    """获取所有模组（含用户启用状态和排序）"""
    cfg = _load_user_config()
    result = []
    for mid, m in BUILTIN_MODULES.items():
        if domain and m["domain"] != domain:
            continue
        user_enabled = cfg["enabled"].get(mid)
        is_enabled = user_enabled if user_enabled is not None else m["default"]
        order = cfg["order"].get(mid, 999)
        result.append({
            "module_id": mid,
            **m,
            "enabled": is_enabled,
            "user_override": user_enabled is not None,
            "order": order,
            "layout": cfg["layout"].get(mid, {}),
        })
    result.sort(key=lambda x: (x["order"], x["module_id"]))
    return result

def get_enabled_modules(domain=None):
    """获取已启用的模组"""
    return [m for m in get_all_modules(domain) if m["enabled"]]

def toggle_module(module_id, enabled):
    """启用/禁用模组（不删除，仅切换可见性）"""
    if module_id not in BUILTIN_MODULES:
        return False, "module not found"
    with _lock:
        cfg = _load_user_config()
        cfg["enabled"][module_id] = bool(enabled)
        _save_user_config(cfg)
    return True, "ok"

def reorder_modules(domain, ordered_ids):
    """重新排序模组"""
    with _lock:
        cfg = _load_user_config()
        for i, mid in enumerate(ordered_ids):
            if mid in BUILTIN_MODULES:
                cfg["order"][mid] = i
        _save_user_config(cfg)
    return True, "ok"

def update_module_layout(module_id, layout):
    """更新模组布局配置（位置/大小/可见性）"""
    if module_id not in BUILTIN_MODULES:
        return False, "module not found"
    with _lock:
        cfg = _load_user_config()
        cfg["layout"][module_id] = layout
        _save_user_config(cfg)
    return True, "ok"

def reset_to_default():
    """重置为默认配置（不删除模组，仅恢复默认启用状态和排序）"""
    with _lock:
        _save_user_config({"enabled": {}, "order": {}, "layout": {}})
    return True, "reset to default"

def register_module_api(app):
    """注册模组管理API"""
    from flask import request, jsonify

    @app.route('/api/modules', methods=['GET'])
    def api_modules_list():
        domain = request.args.get('domain')
        return jsonify({"ok": True, "modules": get_all_modules(domain), "total": len(BUILTIN_MODULES)})

    @app.route('/api/modules/<module_id>/toggle', methods=['POST'])
    def api_module_toggle(module_id):
        data = request.get_json(silent=True) or {}
        enabled = data.get('enabled', True)
        ok, msg = toggle_module(module_id, enabled)
        return jsonify({"ok": ok, "message": msg, "module_id": module_id, "enabled": enabled})

    @app.route('/api/modules/reorder', methods=['POST'])
    def api_modules_reorder():
        data = request.get_json(silent=True) or {}
        domain = data.get('domain', 'cth')
        ordered_ids = data.get('order', [])
        ok, msg = reorder_modules(domain, ordered_ids)
        return jsonify({"ok": ok, "message": msg})

    @app.route('/api/modules/<module_id>/layout', methods=['POST'])
    def api_module_layout(module_id):
        data = request.get_json(silent=True) or {}
        ok, msg = update_module_layout(module_id, data)
        return jsonify({"ok": ok, "message": msg})

    @app.route('/api/modules/reset', methods=['POST'])
    def api_modules_reset():
        ok, msg = reset_to_default()
        return jsonify({"ok": ok, "message": msg})

    print("[module_registry] API registered: /api/modules/*")

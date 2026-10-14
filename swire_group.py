# -*- coding: utf-8 -*-
"""
品牌营销案例库（Brand Marketing Case Library）  v5.8.5
=====================================================================
定位：以「品牌主体」为一级维度的营销事件 / 笔记案例库，舆情系统的外延知识底座。
  - 一级：品牌主体（太古汇/太古里/颐堤港各项目及场内品牌，可自行增删）。
    二级：点击品牌下钻事件库（营销/展览/联名/周年/调整/服务/公益/风险全类型）。
  - 软删除：删除仅前端隐藏(is_active=0)，数据保留，重加同名品牌自动激活更新。
  - 添加品牌后异步触发关键词采集补齐（环境受限降级为“待补齐”，不阻塞）。
  - 兼容：内部代号/接口前缀沿用 swire，对外统一展示“品牌营销案例库”。
说明：表内“种子事件”均为公开、可查证的事实框架，仅作冷启动，source 标注
为公开资料，后续由采集与人工持续补全，不据此下主观负面结论。
"""
import sqlite3
import threading
import datetime as _dt
from flask import request, jsonify

# 统一 Node 解析（移除写死的旧沙箱hash路径，改走 canonical 解析器）
try:
    from runtime_bin import resolve_node as _resolve_node
except Exception:
    def _resolve_node(): return 'node'

from lumenis.shared.database import get_repository, main_db_path

DB_PATH = main_db_path()

_init_lock = threading.Lock()
_inited = False

# ============ 太古系项目字典（公开事实） ============
# key, 名称, 城市, 产品线, 开业年, 简介
PROJECTS = [
    ('guangzhou_thh', '广州太古汇', '广州', '太古汇', '2011', '天河路商圈高端购物中心，华南标杆，方所文化、艺术展陈与奢侈品牌矩阵'),
    ('chengdu_tkl', '成都太古里', '成都', '太古里', '2015', '毗邻大慈寺的开放式低密度街区商业，历史片区与现代商业融合，裸眼3D大屏城市地标'),
    ('sanlitun_tkl', '三里屯太古里', '北京', '太古里', '2008', '京城潮流地标，分南/北/西区，品牌快闪与首发首店密集'),
    ('xingye_thh', '兴业太古汇', '上海', '太古汇', '2017', '静安南京西路，中国首家星巴克臻选烘焙工坊曾入驻'),
    ('qiantan_tkl', '前滩太古里', '上海', '太古里', '2021', '浦东前滩，Wellbeing 用心好生活理念，天空跑道与开放式里巷'),
    ('indigo', '颐堤港', '北京', '颐堤港', '2012', '酒仙桥，购物中心+写字楼+酒店综合体，冬季花园与节庆市集'),
    ('xian_tkl', '西安太古里', '西安', '太古里', '2025', '小雁塔历史文化片区，新旧交融的开放式商业（新开业项目）'),
    ('group_brand', '集团/跨项目品牌', '全国', '品牌', '-', '太古地产及场内品牌跨项目、全国性营销与品牌事件'),
]

# 事件类型（全类型，不止舆情）
EVENT_TYPES = ['营销活动', '展览艺术', '联名快闪', '开业周年', '品牌调整', '服务体验', '公益可持续', '舆情风险']

# ============ 公开事实种子事件（冷启动，持续补全） ============
# (project_key, brand, event_type, title, summary, event_date, sentiment, source)
SEED_EVENTS = [
    ('guangzhou_thh', '', '开业周年', '广州太古汇开业，奠定华南高端商业标杆',
     '2011 年开业，位于广州天河路商圈，形成奢侈品、美妆、文化艺术与餐饮复合业态。', '2011-09-01', 'positive', '公开资料·种子待补全'),
    ('guangzhou_thh', '方所', '品牌调整', '方所书店入驻广州太古汇，成为文化地标',
     '方所将书店、美学、咖啡、服饰与展览结合，强化项目文化标签。', '2011-09-01', 'positive', '公开资料·种子待补全'),
    ('guangzhou_thh', '', '开业周年', '广州太古汇十五周年系列（一方五境/拾光五境/那年汇相遇）',
     '2026-08-28 至 2026-10-07 开展十五周年长效主题营销与传播追踪，系统专题监测同步运行。', '2026-08-28', 'positive', '系统专题·种子待补全'),
    ('chengdu_tkl', '', '开业周年', '成都太古里开业，大慈寺片区古今交融',
     '2015 年开业，开放式、低密度街区商业与千年古刹大慈寺共生，成为城市更新样本。', '2015-04-24', 'positive', '公开资料·种子待补全'),
    ('chengdu_tkl', '', '营销活动', '成都太古里裸眼3D曲面大屏成城市地标',
     '面向红星路的巨型曲面屏以裸眼 3D 内容多次出圈，成为社交媒体打卡与品牌发布阵地。', '2020-10-01', 'positive', '公开资料·种子待补全'),
    ('sanlitun_tkl', '', '开业周年', '三里屯太古里开业，定义京城潮流地标',
     '2008 年开业，分南区、北区、西区，首店首发与潮流快闪密集，是品牌年轻化试验场。', '2008-07-19', 'positive', '公开资料·种子待补全'),
    ('xingye_thh', '星巴克', '联名快闪', '中国首家星巴克臻选烘焙工坊落户兴业太古汇',
     '2017 年随兴业太古汇开业亮相，超大沉浸式烘焙工坊一度成为南京西路目的地级业态。', '2017-11-01', 'positive', '公开资料·种子待补全'),
    ('qiantan_tkl', '', '开业周年', '前滩太古里开业，主打 Wellbeing 用心好生活',
     '2021 年开业，开放式里巷、天空跑道与健康生活方式业态组合，服务浦东前滩国际商务区。', '2021-09-30', 'positive', '公开资料·种子待补全'),
    ('indigo', '', '营销活动', '颐堤港冬季花园与节庆市集',
     '2012 年开业，以室内冬季花园、季节性主题展与圣诞市集形成家庭客群心智。', '2012-09-20', 'neutral', '公开资料·种子待补全'),
    ('xian_tkl', '', '开业周年', '西安太古里开业，小雁塔片区更新',
     '依托小雁塔历史文化片区打造开放式商业，延续太古里“古今交融”产品线。', '2025-09-01', 'neutral', '公开资料·种子待补全'),
]


def _conn():
    return get_repository().connect(timeout=30)


def init_swire():
    """建表 + 写入项目字典与种子事件（幂等）。"""
    global _inited
    with _init_lock:
        if _inited:
            return
        c = _conn()
        try:
            c.execute("""CREATE TABLE IF NOT EXISTS swire_projects(
                project_key TEXT PRIMARY KEY, name TEXT, city TEXT, line TEXT,
                opened TEXT, intro TEXT, sort INTEGER DEFAULT 0,
                kind TEXT DEFAULT 'project', keywords TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1, collect_status TEXT DEFAULT 'idle',
                created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '')""")
            _exist_cols = {r[1] for r in c.execute('PRAGMA table_info(swire_projects)').fetchall()}
            for _col, _ddl in [
                ('kind', "ALTER TABLE swire_projects ADD COLUMN kind TEXT DEFAULT 'project'"),
                ('keywords', "ALTER TABLE swire_projects ADD COLUMN keywords TEXT DEFAULT ''"),
                ('is_active', "ALTER TABLE swire_projects ADD COLUMN is_active INTEGER DEFAULT 1"),
                ('collect_status', "ALTER TABLE swire_projects ADD COLUMN collect_status TEXT DEFAULT 'idle'"),
                ('created_at', "ALTER TABLE swire_projects ADD COLUMN created_at TEXT DEFAULT ''"),
                ('updated_at', "ALTER TABLE swire_projects ADD COLUMN updated_at TEXT DEFAULT ''"),
            ]:
                if _col not in _exist_cols:
                    c.execute(_ddl)
            # 全网营销/品牌事件（全类型、全情感）
            c.execute("""CREATE TABLE IF NOT EXISTS swire_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_key TEXT, brand TEXT DEFAULT '', event_type TEXT,
                title TEXT, summary TEXT, source TEXT DEFAULT '', url TEXT DEFAULT '',
                event_date TEXT, sentiment TEXT DEFAULT 'neutral',
                tags TEXT DEFAULT '', created_at TEXT,
                UNIQUE(project_key,title,event_date))""")
            # 非广州项目的小红书笔记库（广州项目复用主 notes 表）
            c.execute("""CREATE TABLE IF NOT EXISTS swire_notes(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_key TEXT, brand TEXT DEFAULT '', note_id TEXT,
                title TEXT, author TEXT DEFAULT '', likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0, collects INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0, sentiment TEXT DEFAULT 'neutral',
                note_url TEXT DEFAULT '', publish_date TEXT DEFAULT '',
                collected_at TEXT, UNIQUE(project_key,note_id))""")
            c.execute('CREATE INDEX IF NOT EXISTS idx_swe_proj ON swire_events(project_key,event_date DESC)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_swn_proj ON swire_notes(project_key)')
            now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for i, (key, name, city, line, opened, intro) in enumerate(PROJECTS):
                c.execute("""INSERT INTO swire_projects(project_key,name,city,line,opened,intro,sort,kind,is_active,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,'project',1,?,?) ON CONFLICT(project_key) DO UPDATE SET
                    name=excluded.name,city=excluded.city,line=excluded.line,
                    opened=excluded.opened,intro=excluded.intro,updated_at=excluded.updated_at""",
                          (key, name, city, line, opened, intro, i, now, now))
            for (pk, brand, et, title, summary, ed, sent, src) in SEED_EVENTS:
                c.execute("""INSERT INTO swire_events(project_key,brand,event_type,title,summary,source,event_date,sentiment,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(project_key,title,event_date) DO NOTHING""",
                          (pk, brand, et, title, summary, src, ed, sent, now))
            c.commit()
            _inited = True
        finally:
            c.close()


def _project_map(c):
    return {r['project_key']: dict(r) for r in c.execute('SELECT * FROM swire_projects ORDER BY sort').fetchall()}


def _upsert_brand_notes(key, brand_name, notes):
    """采集到的品牌笔记幂等写入 swire_notes，返回 (新增数, 更新数)。"""
    now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ins = upd = 0
    c = _conn()
    try:
        for n in notes or []:
            nid = str(n.get('note_id') or n.get('id') or '').strip()
            if not nid:
                continue
            exists = c.execute('SELECT 1 FROM swire_notes WHERE project_key=? AND note_id=?', (key, nid)).fetchone()
            vals = (key, n.get('brand') or brand_name, nid, n.get('title') or '',
                    n.get('author') or n.get('author_nickname') or '', int(n.get('likes') or 0),
                    int(n.get('comments') or 0), int(n.get('collects') or 0), int(n.get('shares') or 0),
                    n.get('sentiment') or 'neutral', n.get('url') or n.get('note_url') or '',
                    (n.get('publish_date') or '')[:10], now)
            if exists:
                c.execute("""UPDATE swire_notes SET brand=?,title=?,author=?,likes=?,comments=?,collects=?,shares=?,
                    sentiment=?,note_url=?,publish_date=?,collected_at=? WHERE project_key=? AND note_id=?""", vals[1:])
                upd += 1
            else:
                c.execute("""INSERT INTO swire_notes(project_key,brand,note_id,title,author,likes,comments,collects,
                    shares,sentiment,note_url,publish_date,collected_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", vals)
                ins += 1
        c.commit()
    finally:
        c.close()
    return ins, upd


def _set_brand_status(key, status):
    now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c = _conn()
    try:
        c.execute('UPDATE swire_projects SET collect_status=?,updated_at=? WHERE project_key=?', (status, now, key)); c.commit()
    finally:
        c.close()


def _brand_collect_job(key, brand_name, keywords):
    """Return a truthful block until a real SYSTEM task/actor/scope is bound.

    This legacy library has no authorized task context and is not an independent
    Collector. Do not spawn a browser, write collection state, or mutate notes.
    """
    return {
        'ok': False,
        'status': 'UNAVAILABLE',
        'code': 'COLLECTION_TASK_CONTEXT_REQUIRED',
        'message': '请从已授权的序境采集任务提交此来源；当前品牌库没有绑定任务身份。',
    }


def _kickoff_brand_collect(key, brand_name, keywords):
    return _brand_collect_job(key, brand_name, keywords)


def register_swire_group(app):
    """注册品牌营销案例库模块路由（对外展示名：品牌营销案例库）。"""
    init_swire()

    @app.route('/api/swire/overview')
    def swire_overview():
        c = _conn(); c.row_factory = sqlite3.Row
        try:
            projects = [dict(r) for r in c.execute('SELECT * FROM swire_projects WHERE COALESCE(is_active,1)=1 ORDER BY sort, project_key').fetchall()]
            removed_total = c.execute('SELECT COUNT(*) n FROM swire_projects WHERE COALESCE(is_active,1)=0').fetchone()['n']
            ev_total = c.execute('SELECT COUNT(*) n FROM swire_events').fetchone()['n']
            # 广州太古汇笔记数取自主库 notes
            gz_notes = c.execute("SELECT COUNT(*) n FROM notes WHERE is_taikoo_verified=1").fetchone()['n']
            other_notes = c.execute('SELECT COUNT(*) n FROM swire_notes').fetchone()['n']
            by_type = [dict(r) for r in c.execute(
                'SELECT event_type,COUNT(*) n FROM swire_events GROUP BY event_type ORDER BY n DESC').fetchall()]
            by_sent = [dict(r) for r in c.execute(
                'SELECT sentiment,COUNT(*) n FROM swire_events GROUP BY sentiment').fetchall()]
            for p in projects:
                pk = p['project_key']
                p['event_count'] = c.execute(
                    'SELECT COUNT(*) n FROM swire_events WHERE project_key=?', (pk,)).fetchone()['n']
                if pk == 'guangzhou_thh':
                    p['note_count'] = gz_notes
                else:
                    p['note_count'] = c.execute(
                        'SELECT COUNT(*) n FROM swire_notes WHERE project_key=?', (pk,)).fetchone()['n']
            return {
                'ok': True,
                'projects': projects,
                'event_total': ev_total,
                'note_total': gz_notes + other_notes,
                'removed_total': removed_total,
                'library_name': '品牌营销案例库',
                'by_type': by_type,
                'by_sentiment': by_sent,
                'event_types': EVENT_TYPES,
            }
        finally:
            c.close()

    @app.route('/api/swire/events')
    def swire_events():
        project = (request.args.get('project') or '').strip()
        etype = (request.args.get('type') or '').strip()
        kw = (request.args.get('kw') or '').strip()
        limit = min(500, max(10, request.args.get('limit', 200, type=int)))
        q = 'SELECT * FROM swire_events WHERE 1=1'
        p = []
        if project:
            q += ' AND project_key=?'; p.append(project)
        if etype:
            q += ' AND event_type=?'; p.append(etype)
        if kw:
            q += ' AND (title LIKE ? OR summary LIKE ? OR brand LIKE ?)'
            p += [f'%{kw}%'] * 3
        q += ' ORDER BY event_date DESC, id DESC LIMIT ?'; p.append(limit)
        c = _conn(); c.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in c.execute(q, p).fetchall()]
            pmap = _project_map(c)
            for r in rows:
                pr = pmap.get(r['project_key']) or {}
                r['project_name'] = pr.get('name', r['project_key'])
                r['city'] = pr.get('city', '')
                r['line'] = pr.get('line', '')
            return {'ok': True, 'events': rows, 'count': len(rows)}
        finally:
            c.close()

    @app.route('/api/swire/notes')
    def swire_notes():
        project = (request.args.get('project') or 'guangzhou_thh').strip()
        kw = (request.args.get('kw') or '').strip()
        limit = min(200, max(10, request.args.get('limit', 60, type=int)))
        c = _conn(); c.row_factory = sqlite3.Row
        try:
            if project == 'guangzhou_thh':
                # 广州太古汇：直接复用主库 notes（主体已核验优先）
                q = """SELECT note_id,title,author_nickname AS author,likes,comments,collects,shares,
                              sentiment,risk_level,url AS note_url,publish_date,source_keyword
                       FROM notes WHERE 1=1"""
                p = []
                if kw:
                    q += ' AND (title LIKE ? OR author_nickname LIKE ?)'; p += [f'%{kw}%'] * 2
                q += ' ORDER BY publish_date DESC, id DESC LIMIT ?'; p.append(limit)
                rows = [dict(r) for r in c.execute(q, p).fetchall()]
                src = '主库 notes（广州太古汇）'
            else:
                q = 'SELECT * FROM swire_notes WHERE project_key=?'
                p = [project]
                if kw:
                    q += ' AND (title LIKE ? OR author LIKE ?)'; p += [f'%{kw}%'] * 2
                q += ' ORDER BY publish_date DESC, id DESC LIMIT ?'; p.append(limit)
                rows = [dict(r) for r in c.execute(q, p).fetchall()]
                src = 'swire_notes（外延项目，采集补全）'
            return {'ok': True, 'notes': rows, 'count': len(rows), 'source': src}
        finally:
            c.close()

    @app.route('/api/swire/event', methods=['POST'])
    def swire_event_add():
        """人工/采集补充一条营销或品牌事件。"""
        d = request.get_json(silent=True) or {}
        title = (d.get('title') or '').strip()
        pk = (d.get('project_key') or 'group_brand').strip()
        if not title:
            return jsonify({'ok': False, 'error': '标题不能为空'}), 400
        now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c = _conn()
        try:
            c.execute("""INSERT INTO swire_events(project_key,brand,event_type,title,summary,source,url,event_date,sentiment,tags,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(project_key,title,event_date) DO NOTHING""",
                      (pk, d.get('brand', ''), d.get('event_type', '营销活动'), title,
                       d.get('summary', ''), d.get('source', '人工录入'), d.get('url', ''),
                       d.get('event_date') or now[:10], d.get('sentiment', 'neutral'),
                       d.get('tags', ''), now))
            c.commit()
            return {'ok': True}
        finally:
            c.close()

    @app.route('/api/swire/brand-detail')
    def swire_brand_detail():
        """二级下钻：单个品牌主体的事件库 + 笔记库 + 统计（与品牌/太古舆情同逻辑）。"""
        key = (request.args.get('key') or '').strip()
        if not key:
            return jsonify({'ok': False, 'error': '缺少品牌 key'}), 400
        c = _conn(); c.row_factory = sqlite3.Row
        try:
            brow = c.execute('SELECT * FROM swire_projects WHERE project_key=?', (key,)).fetchone()
            if not brow:
                return jsonify({'ok': False, 'error': '品牌不存在或已删除'}), 404
            brand = dict(brow)
            events = [dict(r) for r in c.execute(
                'SELECT * FROM swire_events WHERE project_key=? ORDER BY event_date DESC,id DESC LIMIT 300', (key,)).fetchall()]
            if key == 'guangzhou_thh':
                notes = [dict(r) for r in c.execute("""SELECT note_id,title,author_nickname AS author,likes,comments,
                    collects,shares,sentiment,risk_level,url AS note_url,publish_date FROM notes
                    WHERE is_taikoo_verified=1 ORDER BY publish_date DESC,id DESC LIMIT 200""").fetchall()]
                note_src = '主库 notes（广州太古汇）'
            else:
                notes = [dict(r) for r in c.execute(
                    'SELECT * FROM swire_notes WHERE project_key=? ORDER BY publish_date DESC,id DESC LIMIT 200', (key,)).fetchall()]
                note_src = 'swire_notes（采集补全）'
            eng = sum((n.get('likes') or 0) + (n.get('comments') or 0) + (n.get('collects') or 0) + (n.get('shares') or 0) for n in notes)
            stat = {'events': len(events), 'notes': len(notes),
                    'pos': sum(1 for e in events if e['sentiment'] == 'positive'),
                    'neu': sum(1 for e in events if e['sentiment'] == 'neutral'),
                    'neg': sum(1 for e in events if e['sentiment'] == 'negative'), 'engagements': eng}
            by_type = [dict(r) for r in c.execute(
                'SELECT event_type,COUNT(*) n FROM swire_events WHERE project_key=? GROUP BY event_type ORDER BY n DESC',
                (key,)).fetchall()]
            return {'ok': True, 'brand': brand, 'events': events, 'notes': notes,
                    'stat': stat, 'by_type': by_type, 'event_types': EVENT_TYPES, 'note_src': note_src}
        finally:
            c.close()

    @app.route('/api/swire/brand-remove', methods=['POST'])
    def swire_brand_remove():
        """软删除品牌：仅置 is_active=0 前端隐藏，事件/笔记数据完整保留，重新添加即恢复。"""
        d = request.get_json(silent=True) or {}
        key = (d.get('project_key') or d.get('key') or '').strip()
        if not key:
            return jsonify({'ok': False, 'error': '缺少品牌 key'}), 400
        now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c = _conn()
        try:
            row = c.execute('SELECT 1 FROM swire_projects WHERE project_key=?', (key,)).fetchone()
            if not row:
                return jsonify({'ok': False, 'error': '品牌不存在'}), 404
            c.execute('UPDATE swire_projects SET is_active=0,updated_at=? WHERE project_key=?', (now, key))
            c.commit()
            return {'ok': True, 'soft_deleted': True, 'kept_tables': ['swire_events', 'swire_notes']}
        finally:
            c.close()

    @app.route('/api/swire/brand-save', methods=['POST'])
    def swire_brand_save():
        """Save a brand; collection requires an authorized SYSTEM task context."""
        import hashlib, re
        d = request.get_json(silent=True) or {}
        name = (d.get('name') or '').strip()
        if not name:
            return jsonify({'ok': False, 'error': '品牌名称不能为空'}), 400
        city = (d.get('city') or '').strip(); line = (d.get('line') or '品牌').strip()
        intro = (d.get('intro') or '').strip(); kws = (d.get('keywords') or '').strip()
        kind = (d.get('kind') or 'brand').strip(); opened = (d.get('opened') or '').strip()
        now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c = _conn(); c.row_factory = sqlite3.Row
        try:
            row = c.execute('SELECT * FROM swire_projects WHERE name=?', (name,)).fetchone()
            if row:
                key = row['project_key']
                c.execute("""UPDATE swire_projects SET is_active=1,city=?,line=?,intro=?,keywords=?,
                    kind=?,opened=?,updated_at=? WHERE project_key=?""",
                          (city, line, intro, kws, kind, opened, now, key))
                action = 'reactivated'
            else:
                ascii_kw = re.sub(r'[^a-zA-Z0-9]', '', name)
                base = ('b_' + ascii_kw[:12]) if ascii_kw else ('brand_' + hashlib.md5(name.encode('utf-8')).hexdigest()[:10])
                key = base; i = 1
                while c.execute('SELECT 1 FROM swire_projects WHERE project_key=?', (key,)).fetchone():
                    i += 1; key = f'{base}_{i}'
                mx = c.execute('SELECT COALESCE(MAX(sort),0) m FROM swire_projects').fetchone()['m']
                c.execute("""INSERT INTO swire_projects(project_key,name,city,line,opened,intro,sort,kind,keywords,
                    is_active,collect_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,1,'unavailable',?,?)""",
                          (key, name, city, line, opened, intro, (mx or 0) + 10, kind, kws, now, now))
                action = 'created'
            c.commit()
            brand = dict(c.execute('SELECT * FROM swire_projects WHERE project_key=?', (key,)).fetchone())
        finally:
            c.close()
        collection = _kickoff_brand_collect(key, name, kws)
        return {'ok': True, 'action': action, 'brand': brand,
                'collection': collection}

    @app.route('/api/swire/brand-collect', methods=['POST'])
    def swire_brand_collect():
        """对已存在品牌手动再触发一次采集补齐。"""
        d = request.get_json(silent=True) or {}
        key = (d.get('project_key') or d.get('key') or '').strip()
        if not key:
            return jsonify({'ok': False, 'error': '缺少品牌 key'}), 400
        c = _conn(); c.row_factory = sqlite3.Row
        try:
            b = c.execute('SELECT * FROM swire_projects WHERE project_key=?', (key,)).fetchone()
            if not b:
                return jsonify({'ok': False, 'error': '品牌不存在'}), 404
            b = dict(b)
        finally:
            c.close()
        collection = _kickoff_brand_collect(key, b['name'], b.get('keywords') or '')
        return jsonify(collection), 409

    print('[SwireGroup] 品牌营销案例库模块已注册')

# -*- coding: utf-8 -*-
"""话题监测端口：多任务管理后端 E2E（建任务/列表/按 key 查询/启停/清理）。"""
import sys, os, sqlite3, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask
import topic_campaign as tc
import database as dbmod

app = Flask(__name__)
tc.register_topic_campaign(app)
c = app.test_client()
TKEY = None
TNAME = '【单测】话题任务A'

def cleanup():
    conn = sqlite3.connect(dbmod.DB_PATH)
    for t in ['topic_campaigns', 'topic_campaign_topics', 'topic_campaign_snapshots', 'topic_campaign_notes']:
        conn.execute(f"DELETE FROM {t} WHERE campaign_key=?", (TKEY,)) if TKEY else None
    conn.commit(); conn.close()

# 1) 任务列表（含内置十五周年）
r = c.get('/api/topic-campaign/campaigns'); d = r.get_json()
keys = [x['campaign_key'] for x in d['campaigns']]
print('[列表]', r.status_code, '任务数=', len(d['campaigns']), '含十五周年=', 'taikoo_15th' in keys)

# 2) 新建任务（话题用字符串，测试分隔解析）
r = c.post('/api/topic-campaign/campaign-save', json={
    'name': TNAME, 'start_date': '2026-08-01', 'end_date': '2026-12-31',
    'interval_minutes': 120, 'topics': '#测试话题X;#测试话题Y\n#测试话题Z'})
assert r.status_code == 200 and r.json['ok'], r.data
TKEY = r.json['campaign_key']
print('[新建]', r.json['action'], 'key=', TKEY, '话题数=', r.json['topic_count'])

# 3) 列表能看到且统计正确
r = c.get('/api/topic-campaign/campaigns')
me = next(x for x in r.json['campaigns'] if x['campaign_key'] == TKEY)
print('[列表核对] 话题数=', me['topic_count'], '在窗口内=', me['in_window'], '时间段=', me['start_date'], '~', me['end_date'])
assert me['topic_count'] == 3 and me['in_window'] is True

# 4) 按 key 取话题
r = c.get(f'/api/topic-campaign/topics?campaign_key={TKEY}')
print('[按key话题]', [t['topic'] for t in r.json['topics']])
assert len(r.json['topics']) == 3

# 5) timeline / notes 按 key 不报错（空）
print('[timeline]', c.get(f'/api/topic-campaign/timeline?campaign_key={TKEY}').json)
print('[notes]', c.get(f'/api/topic-campaign/notes?campaign_key={TKEY}').json)

# 6) 暂停后窗口判断为 False、run 返回 400。
# 本测试只验证 campaign 管理语义；生产 Collector 身份/端点门另有独立测试。
# 新的 fail-closed Collector gate 会在窗口检查之前返回 423/503，因此这里显式
# 隔离它，避免旧管理测试把“采集运行时不可用”误判成“暂停语义回归”。
tc._legacy_campaign_route_status = lambda auto_trigger=False: {'ok': True}
c.post('/api/topic-campaign/campaign-toggle', json={'campaign_key': TKEY, 'status': 'paused'})
r = c.get('/api/topic-campaign/campaigns')
me = next(x for x in r.json['campaigns'] if x['campaign_key'] == TKEY)
print('[暂停] 在窗口内=', me['in_window'], '(应为False)')
r = c.post('/api/topic-campaign/run', json={'campaign_key': TKEY})
print('[暂停时run] HTTP', r.status_code, '(应400)')
assert r.status_code == 400
# 恢复
c.post('/api/topic-campaign/campaign-toggle', json={'campaign_key': TKEY, 'status': 'active'})

# 7) 更新同名任务（campaign_key 已存在 -> updated，话题重建）
r = c.post('/api/topic-campaign/campaign-save', json={
    'campaign_key': TKEY, 'name': TNAME, 'start_date': '2026-08-01', 'end_date': '2026-12-31',
    'topics': ['#只留一个话题']})
print('[更新]', r.json['action'], '话题数=', r.json['topic_count'], 'key复用=', r.json['campaign_key'] == TKEY)
assert r.json['action'] == 'updated' and r.json['topic_count'] == 1

# 清理
time.sleep(0.3); cleanup()
conn = sqlite3.connect(dbmod.DB_PATH)
left = conn.execute("SELECT COUNT(*) FROM topic_campaigns WHERE campaign_key=?", (TKEY,)).fetchone()[0]; conn.close()
print('[清理] 残留=', left)
print('ALL_TOPIC_PORT_TESTS_DONE')

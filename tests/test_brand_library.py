# -*- coding: utf-8 -*-
"""品牌营销案例库后端接口端到端单测：增 / 下钻 / 软删 / 重激活 / 数据保留。"""
import sys, os, time, sqlite3
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask
import swire_group as sg

app = Flask(__name__)
sg.register_swire_group(app)
c = app.test_client()
TEST_NAME = '【单测】测试品牌ZZ'

# 0) 清理可能残留
_con = sqlite3.connect(sg.DB_PATH); _con.execute("DELETE FROM swire_projects WHERE name=?", (TEST_NAME,)); _con.commit(); _con.close()

# 1) 迁移列核对
_con = sqlite3.connect(sg.DB_PATH)
cols = [r[1] for r in _con.execute('PRAGMA table_info(swire_projects)')]; _con.close()
need = ['kind', 'keywords', 'is_active', 'collect_status', 'created_at', 'updated_at']
print('[迁移] 新字段齐全 =', all(x in cols for x in need), '| 列=', cols)

# 2) overview
r = c.get('/api/swire/overview'); d = r.get_json()
print('[overview]', r.status_code, '| 在库品牌=', len(d['projects']), '| 已软删=', d.get('removed_total'), '| 库名=', d.get('library_name'))

# 3) 添加品牌
r = c.post('/api/swire/brand-save', json={'name': TEST_NAME, 'city': '广州', 'line': '美妆', 'intro': '单元测试', 'keywords': TEST_NAME})
assert r.status_code == 200 and r.json['ok'], r.data
key = r.json['brand']['project_key']
print('[添加]', r.json['action'], '| key=', key, '| is_active=', r.json['brand']['is_active'], '| status=', r.json['brand']['collect_status'])

# 4) 下钻
r = c.get(f'/api/swire/brand-detail?key={key}'); dd = r.get_json()
print('[下钻]', r.status_code, '| 品牌=', dd['brand']['name'], '| stat=', dd['stat'], '| 事件类型数=', len(dd['by_type']))

# 5) 手动采集触发（环境受限应优雅返回 collecting，不报错）
r = c.post('/api/swire/brand-collect', json={'project_key': key})
print('[手动采集]', r.status_code, r.json)

# 6) 软删除
r = c.post('/api/swire/brand-remove', json={'project_key': key})
print('[软删]', r.status_code, r.json)
r = c.get('/api/swire/overview')
print('[软删后] 列表仍含该品牌 =', any(p['name'] == TEST_NAME for p in r.json['projects']), '| removed_total=', r.json['removed_total'])
# 下钻已软删品牌：仍可查到（数据保留），这里返回200（管理员可追溯）
r = c.get(f'/api/swire/brand-detail?key={key}')
print('[软删后下钻] HTTP', r.status_code, '(200=数据仍保留可追溯)')

# 7) 同名重加 -> reactivated
time.sleep(0.3)
r = c.post('/api/swire/brand-save', json={'name': TEST_NAME, 'city': '深圳', 'line': '护肤'})
print('[重加同名]', r.json.get('action'), '| 复用key=', r.json['brand']['project_key'] == key,
      '| is_active=', r.json['brand']['is_active'], '| 城市已更新=', r.json['brand']['city'] == '深圳')

# 8) 清理（物理删除测试品牌，保持库干净）
time.sleep(0.3)
_con = sqlite3.connect(sg.DB_PATH)
_con.execute("DELETE FROM swire_projects WHERE name=?", (TEST_NAME,)); _con.commit()
left = _con.execute("SELECT COUNT(*) FROM swire_projects WHERE name=?", (TEST_NAME,)).fetchone()[0]; _con.close()
print('[清理] 测试品牌残留 =', left)
print('ALL_BRAND_LIB_TESTS_DONE')

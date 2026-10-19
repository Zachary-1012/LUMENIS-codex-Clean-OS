# -*- coding: utf-8 -*-
"""营销节点日历模块测试。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.marketing_calendar import (suggest_hotspot, nodes_for_month, node_on,
                                        _NODES)


def test_month_nodes_complete():
    for m in range(1, 13):
        assert len(nodes_for_month(m)) >= 2, "月%d 节点不足" % m


def test_hotspot_hits_midautumn():
    r = suggest_hotspot("2026-09-25", "商业地产")
    assert any(n["name"] == "中秋节" for n in r["nodes"]), r["nodes"]
    assert r["themes"]


def test_hotspot_double11():
    r = suggest_hotspot("2026-11-11", "美妆")
    assert any("双11" in n["name"] for n in r["nodes"]), r["nodes"]


def test_hotspot_valentine():
    r = suggest_hotspot("2026-02-14")
    assert any("情人节" in n["name"] for n in r["nodes"]), r["nodes"]


def test_node_on_today():
    import datetime
    today = datetime.date.today().strftime("%m-%d")
    hits = node_on(datetime.date.today().strftime("%Y-%m-%d"))
    # 今天可能是也可能不是节点，但口径必须与 MM-DD 版一致
    assert hits == node_on(today)


def test_all_nodes_have_required_fields():
    for nodes in _NODES.values():
        for n in nodes:
            assert {"name", "date", "kind", "theme", "cats"} <= set(n), n
            assert len(n["date"]) == 5


def test_vertical_industry_nodes():
    from scripts.marketing_calendar import industry_nodes, _V_NODES
    assert len(_V_NODES) >= 6, "垂直行业覆盖不足"
    moms = industry_nodes("母婴")
    assert moms and all(n["industry"] == "母婴" for n in moms), moms
    june = industry_nodes("美妆", month=3)
    assert any("美妆节" == n["name"] for n in june), june
    coffee = industry_nodes("咖啡")
    assert any("咖啡" in n["name"] for n in coffee), coffee


def test_year_market_and_date_type_boundaries():
    from scripts.marketing_calendar import calendar_context, cross_industry_season
    assert suggest_hotspot('2027-02-17')['state'] == 'year_not_covered'
    assert node_on('2027-02-17') == []
    assert suggest_hotspot('2026-02-17', market='HK')['state'] == 'market_not_covered'
    for value in ('2026-02-29', '2026-12-21T16:00:00Z', 'bad-date'):
        assert suggest_hotspot(value)['state'] == 'invalid_input'
    assert suggest_hotspot('')['state'] == 'date_required'
    assert calendar_context('02-17')['year_explicit'] is False
    assert not cross_industry_season('美妆', '2027-02')['season_nodes']
    assert not any(n['name'] == '冬至' for n in nodes_for_month(12))
    assert calendar_context('2026-12-22')['excluded_disputed_nodes'] == ['冬至']
    assert all(n['holiday_status'] == 'NOT_ESTABLISHED' for n in node_on('2026-02-17'))


def test_category_suggestion_is_not_same_day_fact():
    r = suggest_hotspot('2026-02-01', '美妆')
    assert all(n['match_reason'] == 'category_month_suggestion' for n in r['nodes'])
    assert r['calendar_reference']['canonical'] is False


# Register exact existing app routes without application startup or live services.
def calendar_http():
    import ast
    from pathlib import Path
    from flask import Flask, request, jsonify, Response
    app = Flask('calendar-isolated-existing-route')
    tree = ast.parse(Path('app.py').read_text(encoding='utf-8-sig'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'marketing_overview')
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<current-calendar-route>', 'exec'),
         dict(app=app, request=request, jsonify=jsonify, Response=Response))
    return app.test_client()


def test_registered_calendar_csv_and_invalid_year():
    import csv, io
    client = calendar_http()
    response = client.get('/api/v2/marketing/overview?year=2027&date=2027-02-17&month=02&export=csv')
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.data.decode())))
    assert len(rows) == 2 and rows[1][9] == 'year_not_covered'
    current = client.get('/api/v2/marketing/overview?year=2026&date=2026-02-17&month=02').json
    assert current['hotspot']['date'] == '2026-02-17'
    assert current['calendar_reference']['source_admission'] == 'NOT_ADMITTED'
    assert client.get('/api/v2/marketing/overview?year=oops').status_code == 400
    assert client.get('/api/v2/marketing/overview?date=2026-02-29').status_code == 400


from tests.test_saved_document_workflow import workspace
from tests.test_pitch_caller_routes import route


def test_actual_pitch_http_transmits_calendar_context(route):
    app, _, _ = route
    client = app.test_client()
    base = {'text': '独立书店，预算500元，安静读者交流活动', 'target_date': '2026-04-23', 'market': 'CN'}
    result = client.post('/api/creative/pitch-analyze', json=base)
    assert result.status_code == 200
    assert result.json['data']['ideas']['meta']['bound_hotspot'] == '世界读书日'
    for bad in ('2026-02-29', '2026-04-23T00:00:00+08:00', {}, 20260423):
        assert client.post('/api/creative/pitch-analyze', json={**base, 'target_date': bad}).status_code == 400
    unknown = client.post('/api/creative/pitch-analyze', json={**base, 'market': 'unknown'}).json
    assert unknown['data']['marketing']['state'] == 'market_not_covered'
    default = client.post('/api/creative/pitch-analyze', json={'text': base['text']}).json
    assert default['data']['marketing']['state'] == 'date_required'


def test_original_brief_csv_saved_reopened_and_revised(workspace):
    from scripts.pitch_parser import analyze_pitch
    from lumenis.shared.reporting import saved_work
    ws = workspace
    body = '读者可以带一页自己写的阅读便笺。参加或独自阅读都可以，不要求消费。'
    brief = analyze_pitch('独立书店，预算500元，安静读者交流', target_date='2026-04-23')
    csv = calendar_http().get('/api/v2/marketing/overview?year=2026&date=2026-04-23&month=04&export=csv').data
    saved = saved_work.save_work(title='阅读日活动草稿', markdown=body, kind='report',
        payload={'calendar_reference': brief['marketing']['calendar_reference'],
                 'planned_date': '2026-04-23', 'original_manuscript': body,
                 'business_outcome': 'NOT_OBSERVED'}, citations=[], request_id='calendar-original-01',
        actor=ws['actor'], scope=ws['scope'],
        attachments=[{'name': 'calendar.csv', 'media_type': 'text/csv', 'content': csv}])
    artifact = saved['artifact']['artifact_id']
    reopened = saved_work.reopen_work(artifact, actor=ws['actor'], scope=ws['scope'])
    assert reopened['document']['markdown'] == body
    downloaded = saved_work.download_attachment(artifact, name='calendar.csv', actor=ws['actor'], scope=ws['scope'])
    assert downloaded['content'] == csv
    import subprocess, sys, json
    from tests.test_saved_document_workflow import _PROCESS
    cold_code = _PROCESS.replace('print(json.dumps(item["receipt"]))',
        'print(json.dumps({"document": item["document"], "sha256": item["artifact"]["sha256"]}))')
    cold = subprocess.run([sys.executable, '-c', cold_code, 'read', artifact],
                          capture_output=True, text=True, timeout=30)
    assert cold.returncode == 0, cold.stderr
    cold_result = json.loads(cold.stdout.strip().splitlines()[-1])
    assert cold_result['document']['markdown'] == body
    assert cold_result['sha256'] == saved['artifact']['sha256']
    revised = saved_work.revise_work(artifact, actor=ws['actor'], scope=ws['scope'], request_id='calendar-revise-01',
        expected_sha256=saved['artifact']['sha256'], reason='用户调整活动排期；保留参考日期与手稿。',
        edits=[{'pointer': '/payload/planned_date', 'expected': '2026-04-23', 'value': '2026-04-24'}])
    assert revised['document']['markdown'] == body
    assert revised['document']['payload']['calendar_reference']['date'] == '2026-04-23'
    assert saved_work.reopen_work(artifact, actor=ws['actor'], scope=ws['scope'])['document']['payload']['planned_date'] == '2026-04-23'


def test_ic_registered_scope_and_invalid_year():
    from flask import Flask
    from ic_routes import ic_bp
    app = Flask('calendar-ic-existing')
    app.register_blueprint(ic_bp)
    client = app.test_client()
    assert client.get('/api/ic/marketing/calendar?year=nope').status_code == 400
    value = client.get('/api/ic/marketing/calendar?date=2027-02-17&month=2').json
    assert value['calendar_reference']['state'] == 'year_not_covered' and value['nodes'] == []
    value = calendar_http().get('/api/v2/marketing/overview?year=2027&month=2').json
    assert value['calendar_reference']['state'] == 'year_not_covered'


def test_legacy_month_cross_reference_preserved_without_brief_clock_binding():
    from scripts.marketing_calendar import cross_global, cross_industry_season
    global_june = cross_global(month=6)
    assert global_june['month'] == 6 and global_june['season_nodes']
    assert global_june['calendar_reference']['year'] == 2026
    assert global_june['calendar_reference']['date_origin'] == 'legacy_month_reference_not_brief_date'
    legacy = cross_industry_season('美妆')
    assert legacy['calendar_reference']['state'] == 'reference_only_not_live_verified'
    assert legacy['calendar_reference']['date_origin'] == 'legacy_month_reference_not_brief_date'
    assert cross_global(month=6, market='HK')['calendar_reference']['state'] == 'market_not_covered'
    assert cross_global(month=13)['calendar_reference']['state'] == 'invalid_input'
    assert not cross_global(date_str='2027-06')['season_nodes']


def test_cross_helpers_reject_nonstring_date_without_clock_fallback():
    from scripts.marketing_calendar import cross_global, cross_industry_season
    for invalid in (None, 20260423, False, [], {}, ['2026-04-23']):
        for value in (cross_global(month=6, date_str=invalid),
                      cross_industry_season('餐饮', date_str=invalid)):
            assert value['calendar_reference']['state'] == 'invalid_input'
            assert value['month'] is None
            assert not value['season_nodes'] and not value['advice']
    assert cross_global(month=6)['season_nodes']
    assert cross_global(date_str='2026-06-21')['season_nodes']
    assert cross_industry_season('餐饮', date_str='2026-06-21')['season_nodes']

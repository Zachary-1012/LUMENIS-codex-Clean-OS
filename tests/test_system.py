"""本地回归测试：不访问网络，不启动浏览器。"""
import pytest
from tests.test_event_aggregation_authority import signed_scoped_event_sources
from subject_context import brand_scope

import database as db
import ai_analyzer
from subject_rules import SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit, subject_sql_and_values

@pytest.fixture(autouse=True)
def explicit_reference_subject():
    # Legacy reference-subject APIs require an explicit focus, never a global default.
    with brand_scope('guangzhou_taikoo_hui', product_id='CTH'):
        yield


def test_system_contract(signed_scoped_event_sources):
    """Run the legacy system contract against an OS-temporary database.

    The signed source fixture binds ``ZBC_DB_PATH`` to an OS-temporary DB.
    Its real Evidence/Canonical sources also exercise the scoped event writer;
    no module-collection writes or implicit default subject are required.
    """
    with db.get_db() as c:
        cols={r[1] for r in c.execute('pragma table_info(notes)')}
    required={'status','last_seen_at','is_taikoo_verified','verify_reason','source_platform','relevance_status','verification_status','verification_confidence','fact_basis','ai_reason','event_hint','translations','relevance_score','content_quality','duplicate_of','ai_model','last_reviewed_at','body','source_keyword','matched_keywords'}
    assert required <= cols, cols
    ok,reason=ai_analyzer.verify_taikoo_location('上海太古汇今天怎么样','我在上海')
    assert not ok and '上海' in reason
    ok,reason=ai_analyzer.verify_taikoo_location('广州太古汇停车体验','停车很方便')
    assert ok
    assert subject_hit(title='广州太古汇停车体验')
    assert not subject_hit(title='上海太古汇停车体验')
    assert not subject_hit(title='成都远洋太古汇活动')
    assert len(SUBJECT_WORDS)==17 and len(SUBJECT_EXCLUDE_WORDS)==18
    clause, params = subject_sql_and_values('n')
    assert 'NOT' in clause and len(params)==(17+18)*5
    rid,new=db.insert_note({'note_id':'n1','source_platform':'xiaohongshu','title':'广州太古汇停车体验','content':'停车很方便','publish_date':'2026-08-24','is_taikoo_verified':1,'source_keyword':'广州太古汇','matched_keywords':'广州太古汇'})
    assert new and rid
    db.insert_note({'note_id':'bad1','source_platform':'xiaohongshu','title':'上海太古汇停车体验','content':'上海静安','publish_date':'2026-08-24','is_taikoo_verified':1})
    db.update_note_analysis('n1',ai_analyzer.analyze_note({'note_id':'n1','title':'广州太古汇停车体验','content':'停车很方便','likes':10,'comments':2,'author_nickname':'用户'}))
    rows=db.get_notes({'verified':True},10,0)
    assert len(rows)==1 and rows[0]['note_id']=='n1'
    row=rows[0]
    assert row['status']=='active' and row['source_platform']=='xiaohongshu'
    assert db.insert_web_mention({'source_id':'web1','source_platform':'google_news','title':'广州太古汇活动','content':'公开网页测试','url':'https://example.com/web1'})
    db.update_web_analysis('web1', {'relevance':'relevant','verification':'review','confidence':0.8,'sentiment':'positive','risk_level':'low','summary':'网页测试','topics':['品牌活动'],'provider':'rule'})
    assert len(db.get_web_mentions()) == 1
    db.log_web_source('test','测试来源','test',True,item_count=1)
    db.log_web_run('test','广州太古汇','2026-08-25 00:00:00','2026-08-25 00:00:01',1,1,0,'')
    with pytest.raises(ValueError, match='SCOPE_REQUIRED'):
        db.upsert_event({'event_key': 'test-event', 'title': 'unscoped must fail'})
    scope = {'domain_id': 'cth', 'subject_id': 'SUBJECT-A',
             'brand_focus_id': None, 'global_scope': False}
    exact = db._normalize_event_scope(scope, allow_global=False)
    event_key = db._event_scope_token(exact) + '.test-event'
    eid = db.upsert_event({'event_key': event_key, 'title': '广州太古汇停车事件',
                          'summary': '测试', 'first_seen': '2026-08-24',
                          'last_seen': '2026-08-24', 'event_date': '2026-08-24'},
                         scope=scope, mentions=[{'source_type': 'note', 'source_id': 'scope-note-a'}])
    event = db.get_scoped_events(1, scope=scope, include_sources=True)['events'][0]
    assert event['id'] == eid and event['event_key'] == event_key
    assert event['mention_count'] == 1 and len(event['sources']) == 1
    db.upsert_feedback_keyword('停车',1.2,'web')
    assert db.get_feedback_keywords(1)[0]['keyword']=='停车'
    print('ALL TESTS PASSED')

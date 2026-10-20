import pytest
from lumenis.system.collector.adapters.wechat import WechatPublicAdapter, parse_public_article, parse_sogou_discovery
from lumenis.system.collector.adapters.public_source import PublicResponse
from lumenis.system.collector.adapters.base import CollectionStatus


def response(body, url='https://mp.weixin.qq.com/s/native-share-path'):
    return PublicResponse(url=url, content=body.encode(), content_type='text/html', status_code=200)


def test_original_body_native_timestamp_and_missing_metrics_are_distinct():
    r=response('<h1 id="activity-name">2026停车服务</h1><a id="js_name">发布者原文</a>'
               '<em id="publish_time">昨天</em><div id="js_content">正文<img data-src="https://mmbiz.qpic.cn/example.jpg"></div>'
               '<script>var ct = "1788105600";</script>')
    item=parse_public_article(r)
    assert item['content']=='正文' and item['publish_datetime'].startswith('2026-08-30')
    assert item['raw']['publish_time_literal']=='昨天' and item['raw']['ct']=='1788105600'
    assert all(item[k] is None for k in ['likes','comments','collects','shares','views'])
    assert item['raw']['images'][0]['url']=='https://mmbiz.qpic.cn/example.jpg'


def test_index_date_and_shell_never_become_article_publication_or_body():
    r=response('<li id="sogou_vr_1"><div class="txt-box"><h3><a href="/link?url=public">文章标题</a></h3>'
               '<p class="txt-info">索引摘要</p><div class="s-p">2026-10-04</div></div></li>',
               'https://weixin.sogou.com/weixin?type=2&query=停车')
    candidates,_=parse_sogou_discovery(r)
    assert len(candidates)==1 and candidates[0]['native_publication'] is None
    assert candidates[0]['index_date_not_article_publication'] is True
    assert parse_public_article(r) is None


def test_missing_year_relative_day_and_edit_literal_stay_uninterpreted():
    item=parse_public_article(response('<h1 id="activity-name">题目</h1><em id="publish_time">9月20日 编辑于</em>'
                                      '<div id="js_content">完整可回查正文</div>'))
    assert item['publish_datetime'] is None and item['raw']['publish_time_literal']=='9月20日 编辑于'


def test_challenge_stops_original_follows_without_cookie_or_repeat():
    seen=[]
    index=response('<li id="sogou_vr_1"><h3><a href="https://mp.weixin.qq.com/s/one">A</a></h3></li>'
                   '<li id="sogou_vr_2"><h3><a href="https://mp.weixin.qq.com/s/two">B</a></h3></li>',
                   'https://weixin.sogou.com/weixin?type=2')
    def fetch(url):
        seen.append(url)
        return index if len(seen)==1 else response('<div>请完成安全验证</div>')
    result=WechatPublicAdapter(fetcher=fetch).search('广州太古汇 停车')
    assert result.status is CollectionStatus.NEED_VERIFY and len(seen)==2
    assert result.items==[] and result.metadata['original_body_available'] is False
    assert result.metadata['reason']=='SOURCE_VERIFICATION_REQUIRED'
    assert result.metadata['provider']=='public_sogou_discovery_original_fetch'
    assert result.metadata['request_final_status']=='NEED_VERIFY'
    assert result.metadata['http_status']==200
    assert result.metadata['accepted_count']==0
    assert result.metadata['challenge_body_included'] is False


def test_fix_106_search_challenge_reports_bounded_diagnostic_without_challenge_body():
    challenge_text = '请完成安全验证 PRIVATE_CHALLENGE_TEXT'
    challenge = response(f'<div>{challenge_text}</div>',
                         'https://weixin.sogou.com/weixin?type=2&query=synthetic')
    result = WechatPublicAdapter(fetcher=lambda _url: challenge).search('synthetic keyword')
    assert result.status is CollectionStatus.NEED_VERIFY
    assert result.message == 'Source verification required'
    assert result.metadata == {
        'reason': 'SOURCE_VERIFICATION_REQUIRED',
        'provider': 'public_sogou_discovery_original_fetch',
        'request_final_status': 'NEED_VERIFY',
        'http_status': 200,
        'accepted_count': 0,
        'original_body_available': False,
        'challenge_body_included': False,
        'index_only': True,
    }
    assert 'PRIVATE_CHALLENGE_TEXT' not in repr(result.metadata)


def test_fix_106_original_article_challenge_keeps_need_verify_and_final_status():
    challenge_text = '请完成安全验证 PRIVATE_CHALLENGE_TEXT'
    challenge = response(f'<div>{challenge_text}</div>')
    result = WechatPublicAdapter(fetcher=lambda _url: challenge).detail(
        'https://mp.weixin.qq.com/s/exact-article')
    assert result.status is CollectionStatus.NEED_VERIFY
    assert result.metadata['provider'] == 'public_original_article_fetch'
    assert result.metadata['request_final_status'] == 'NEED_VERIFY'
    assert result.metadata['accepted_count'] == 0
    assert result.metadata['http_status'] == 200
    assert result.metadata['challenge_body_included'] is False
    assert 'PRIVATE_CHALLENGE_TEXT' not in result.message
    assert 'PRIVATE_CHALLENGE_TEXT' not in repr(result.metadata)


def test_native_query_tuple_does_not_change_with_referral_parameters():
    html='<div id="js_content">正文</div>'
    a=parse_public_article(response(html,'https://mp.weixin.qq.com/s?__biz=b&mid=42&idx=1&sn=content&scene=1'))
    b=parse_public_article(response(html,'https://mp.weixin.qq.com/s?__biz=b&mid=42&idx=1&sn=content&scene=99'))
    assert a['platform_content_id']==b['platform_content_id']=='b|42|1|content'
    assert a['raw']['native_article_identity']==b['raw']['native_article_identity']


@pytest.mark.parametrize('url', [
    'https://example.com/not-wechat',
    'https://mp.weixin.qq.com.example.com/s/article',
    'https://mp.weixin.qq.com@evil.example/s/article',
    'https://user:password@mp.weixin.qq.com/s/article',
    'https://mp.weixin.qq.com:444/s/article',
    'http://mp.weixin.qq.com/s/article',
    'https://mp.weixin.qq.com/not-an-article',
    'https://[malformed/s/article',
])
def test_detail_rejects_foreign_host_before_transport(url):
    adapter=WechatPublicAdapter(fetcher=lambda _: pytest.fail('foreign target reached transport'))
    result=adapter.detail(url)
    assert result.status is CollectionStatus.NOT_SUPPORTED
    assert result.items == [] and result.ok is False
    assert result.metadata['reason'] == 'SOURCE_URL_NOT_SUPPORTED'
    assert result.metadata['original_body_available'] is False
    assert result.metadata['network_attempted'] is False
    assert result.metadata['persistence_attempted'] is False
    assert result.metadata['requires_auth'] is False
    assert result.metadata['cookies_used'] is False


def test_foreign_url_search_does_not_fall_through_to_discovery():
    adapter=WechatPublicAdapter(fetcher=lambda _: pytest.fail('foreign URL reached transport'))
    result=adapter.search('https://example.com/not-wechat')
    assert result.status is CollectionStatus.NOT_SUPPORTED
    assert result.items == [] and result.metadata['network_attempted'] is False


def test_supported_original_url_still_reaches_original_body():
    calls=[]
    def fetch(url):
        calls.append(url)
        return response('<div id="js_content">原生完整正文</div>', url)
    url='https://mp.weixin.qq.com/s/native-share-path'
    result=WechatPublicAdapter(fetcher=fetch).detail(url)
    assert calls == [url] and result.status is CollectionStatus.SUCCESS
    assert result.items[0]['content'] == '原生完整正文'

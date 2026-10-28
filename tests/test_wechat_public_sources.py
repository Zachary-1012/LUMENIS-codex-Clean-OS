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
        'pagination': {
            'request_cursor': None, 'next_cursor': None, 'exhausted': None,
            'page_complete': False, 'coverage_scope': 'PUBLIC_INDEX_VERIFICATION_REQUIRED',
            'continuation_blocked': True, 'blocked_status': 'NEED_VERIFY',
        },
    }
    assert result.raw_count is None
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


@pytest.mark.parametrize('prompt', [
    '此验证码用于确认这些请求是您的正常行为而不是自动程序发出的，需要您协助验证。',
    '此验证码用于确认这些请求是您的正常行为\n而不是自动程序发出的， 需要您协助验证。',
])
def test_sogou_http200_verification_explanation_is_not_a_discovery_page(prompt):
    challenge = response('<title>搜狗搜索</title><main>' + prompt + '<input name="c"></main>'
        '<li id="sogou_vr_1"><h3><a href="https://mp.weixin.qq.com/s/stale">旧链接</a></h3></li>',
        'https://weixin.sogou.com/antispider/')
    assert parse_sogou_discovery(challenge) == ([], None)
    calls = []
    def fetch(url):
        calls.append(url)
        return challenge
    result = WechatPublicAdapter(fetcher=fetch).search('query fixture')
    assert result.status is CollectionStatus.NEED_VERIFY and len(calls) == 1
    assert result.raw_count is None and result.items == []
    assert result.metadata['pagination']['next_cursor'] is None
    assert result.metadata['pagination']['continuation_blocked'] is True
    assert result.metadata['http_status'] == 200


def test_sogou_verification_preserves_original_and_stops_remaining_candidates_and_pages():
    first = 'https://mp.weixin.qq.com/s/first-permitted'
    third = 'https://mp.weixin.qq.com/s/independent-permitted'
    blocked = 'https://weixin.sogou.com/link?url=fixture-blocked'
    index = response(
        f'<li id="sogou_vr_1"><h3><a href="{first}">第一篇</a></h3></li>'
        f'<li id="sogou_vr_2"><h3><a href="{blocked}">第二篇</a></h3></li>'
        f'<li id="sogou_vr_3"><h3><a href="{third}">第三篇</a></h3></li>'
        '<a id="sogou_next" href="/weixin?type=2&amp;query=query%20fixture&amp;page=2">下一页</a>',
        'https://weixin.sogou.com/weixin?type=2&query=query%20fixture&page=1')
    challenge = response('<main>此验证码用于确认这些请求是您的正常行为而不是自动程序发出的，需要您协助验证。</main>'
        '<script>window.location="https://mp.weixin.qq.com/s/must-not-follow";</script>',
        'https://weixin.sogou.com/antispider/')
    calls = []
    def fetch(url):
        calls.append(url)
        if len(calls) == 1:
            return index
        if url == first:
            return response('<div id="js_content">已取得的合规原文</div>', first)
        if url == blocked:
            return challenge
        if url == third:
            return response('<div id="js_content">独立可访问原文</div>', third)
        pytest.fail('verification caused an extra transport attempt')
    adapter = WechatPublicAdapter(fetcher=fetch)
    result = adapter.search('query fixture')
    assert result.status is CollectionStatus.NEED_VERIFY
    assert calls == ['https://weixin.sogou.com/weixin?type=2&query=query%20fixture&page=1', first, blocked]
    assert len(result.metadata['discovery_candidates']) == 3 and result.raw_count == 3
    assert len(result.items) == 1 and result.items[0]['content'] == '已取得的合规原文'
    assert result.metadata['accepted_count'] == 1 and result.metadata['original_body_available'] is True
    assert result.metadata['per_request_original_attempt_count'] == 2
    assert result.metadata['per_request_deferred_source_count'] == 1
    assert result.metadata['original_outcomes'][-1]['reason'] == 'DISCOVERY_REDIRECT_VERIFICATION_REQUIRED'
    assert result.metadata['next_search_url'] is None
    pagination = result.metadata['pagination']
    assert pagination['next_cursor'] is None and pagination['observed_next_cursor'] == {'page': 2}
    assert pagination['continuation_blocked'] is True and pagination['page_complete'] is False
    assert pagination['exhausted'] is None
    # The challenge pauses this discovery invocation, not an independent,
    # explicitly requested and permitted original-source read.
    independent = adapter.detail(third)
    assert independent.status is CollectionStatus.SUCCESS
    assert independent.items[0]['content'] == '独立可访问原文'


def test_original_article_can_quote_verification_explanation_without_becoming_a_challenge():
    text = '此验证码用于确认这些请求是您的正常行为而不是自动程序发出的，需要您协助验证。'
    original = response('<h1 id="activity-name">验证说明介绍</h1><div id="js_content">' + text + '</div>')
    result = WechatPublicAdapter(fetcher=lambda _url: original).detail('https://mp.weixin.qq.com/s/normal-article')
    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]['content'] == text


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


def test_public_article_preserves_native_media_hints_without_fetching_media():
    from lumenis.system.collector.adapters.platform_naming import map_raw_to_normalized

    html = (
        '<div id="js_content">实际正文'
        '<mpvideo data-vid="wx-video-1" data-src="https://media.example.test/one.mp4" '
        'data-title="原生视频标题"></mpvideo>'
        '<mpvoice voice_encode_fileid="wx-audio-1"></mpvoice>'
        '<video poster="https://media.example.test/cover.jpg">'
        '<source src="/two.mp4" type="video/mp4">'
        '<source data-src="/lazy.mp4" type="video/webm">'
        '</video>'
        '<iframe src="https://mp.weixin.qq.com/embed/video"></iframe>'
        '<iframe data-mpvid="wx-video-2" src="https://mp.weixin.qq.com/embed/native-video"></iframe>'
        '<mp-common-videosnap data-id="finder-1" '
        'data-url="https://media.example.test/thumbnail.jpg"></mp-common-videosnap>'
        '<img data-src="https://media.example.test/article-image.jpg" alt="文章图片">'
        '</div>'
    )
    article_url = 'https://mp.weixin.qq.com/s/native-share-path'
    fetch_calls = []

    def fetch(url):
        fetch_calls.append(url)
        return response(html, article_url)

    result = WechatPublicAdapter(fetcher=fetch).detail(article_url)
    assert result.status is CollectionStatus.SUCCESS
    assert fetch_calls == [article_url]
    item = result.items[0]

    assert item is not None
    hints = item['raw']['media_hints']
    assert [hint['native_tag'] for hint in hints] == [
        'mpvideo', 'mpvoice', 'video', 'source', 'source',
        'iframe', 'iframe', 'mp-common-videosnap',
    ]
    assert hints[0]['media_id'] == 'wx-video-1'
    assert hints[0]['url'] == 'https://media.example.test/one.mp4'
    assert hints[0]['native_attributes']['data-title'] == '原生视频标题'
    assert hints[1]['media_type'] == 'audio' and hints[1]['url'] is None
    assert hints[2]['cover_url'] == 'https://media.example.test/cover.jpg'
    assert hints[3]['url'] == 'https://mp.weixin.qq.com/two.mp4'
    assert hints[3]['native_locator']['source_element_index'] == 0
    assert hints[4]['url'] == 'https://mp.weixin.qq.com/lazy.mp4'
    assert hints[5]['url_role'] == 'EMBED_PAGE' and hints[5]['media_type'] == 'embed'
    assert hints[6]['media_id'] == 'wx-video-2' and hints[6]['media_type'] == 'video'
    assert hints[7]['observed_data_url_role'] == 'UNKNOWN'
    assert item['raw']['images'] == [{
        'url': 'https://media.example.test/article-image.jpg',
        'alt': '文章图片',
    }]

    normalized = map_raw_to_normalized(item['raw'], 'wechat')
    assert normalized['raw_data']['media_hints'] == hints
    assert normalized['media_list'][0] == item['raw']['images'][0]
    assert len(normalized['media_list']) == len(item['raw']['images']) + len(hints)
    assert [observation['native_tag'] for observation in normalized['media_list'][1:]] == [
        hint['native_tag'] for hint in hints
    ]
    for projected, hint in zip(normalized['media_list'][1:], hints):
        expected = dict(hint)
        url = expected.get('url')
        if not isinstance(url, str) or not url.strip():
            url = expected.get('display_uri')
        expected['url'] = url if isinstance(url, str) and url.strip() else None
        assert projected == expected

    repeated_observation = dict(item['raw'], media_hints=[*hints, item['raw']['images'][0]])
    deduplicated = map_raw_to_normalized(repeated_observation, 'wechat')
    assert deduplicated['media_list'] == normalized['media_list']
    assert deduplicated['raw_data'] is repeated_observation


@pytest.mark.parametrize('src', [
    'javascript:alert(1)',
    'data:video/mp4;base64,AAAA',
    'blob:https://mp.weixin.qq.com/id',
    'https://user:password@media.example.test/one.mp4',
    'https://media.example.test/one.mp4?auth_key=private',
    'https://media.example.test/one.mp4?access_token=private',
    'https://[malformed/one.mp4',
])
def test_media_hint_rejects_executable_or_credential_urls(src):
    item = parse_public_article(response(
        f'<div id="js_content">正文<mpvideo data-vid="public-video-id" data-src="{src}"></mpvideo></div>'
    ))

    assert item is not None
    hint = item['raw']['media_hints'][0]
    assert hint['media_id'] == 'public-video-id' and hint['url'] is None
    assert src not in str(hint)


def test_media_hints_ignore_fallback_markup_and_strip_fragments():
    item = parse_public_article(response(
        '<div id="js_content">正文'
        '<form><video src="https://media.example.test/form.mp4"></video></form>'
        '<noscript><audio src="https://media.example.test/fallback.mp3"></audio></noscript>'
        '<audio src="https://media.example.test/actual.mp3#private-fragment"></audio>'
        '</div>'
    ))

    assert item is not None
    hints = item['raw']['media_hints']
    assert len(hints) == 1
    assert hints[0]['url'] == 'https://media.example.test/actual.mp3'


def test_public_literal_navigation_fragments_are_not_confused_with_executable_redirects():
    parse = WechatPublicAdapter._literal_article_navigation
    source = "var url = ''; url += 'http://mp.weixin.qq.com/s/'; url += 'native-fixture'; window.location.replace(url);"
    assert parse(source) == 'https://mp.weixin.qq.com/s/native-fixture'
    assert parse("var url='https://mp.weixin.qq.com/s/fixture'; url=computeToken(); window.location.replace(url);") is None
    assert parse("var url='https://mp.weixin.qq.com/s/fixture'; url += readSecret(); window.location.replace(url);") is None
    assert parse("var url='https://mp.weixin.qq.com/s/fixture';") is None

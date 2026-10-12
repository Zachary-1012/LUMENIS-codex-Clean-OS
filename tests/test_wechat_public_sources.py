import pytest

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.public_source import (
    PublicResponse,
    PublicSourceError,
)
from lumenis.system.collector.adapters.wechat import (
    WechatPublicAdapter,
    parse_public_article,
    parse_sogou_discovery,
)


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


def test_original_media_cues_retain_ids_sources_and_raw_attributes_without_fetching():
    html = ('<div id="js_content">实际正文'
            '<mpvideo data-vid="wxv-1" data-title="原生标题" data-src="//mpvideo.qpic.cn/one.mp4"></mpvideo>'
            '<mpvoice voice_encode_fileid="voice-1" name="原生音频"></mpvoice>'
            '<video poster="https://mmbiz.qpic.cn/cover.jpg"><source src="/media/two.mp4" type="video/mp4">'
            '<source data-src="/media/lazy.mp4" type="video/mp4"></video>'
            '<audio src="https://mmbiz.qpic.cn/three.mp3" duration="123"></audio>'
            '<iframe data-mpvid="wxv-2" data-src="//v.qq.com/iframe/preview.html?vid=wxv-2"></iframe>'
            '<iframe src="https://example.test/embed"></iframe></div>'
            '<video src="https://example.test/outside.mp4"></video>')
    calls = []

    def fetch(url):
        calls.append(url)
        return response(html, url)

    url = 'https://mp.weixin.qq.com/s/article-media'
    result = WechatPublicAdapter(fetcher=fetch).detail(url)
    assert calls == [url] and result.status is CollectionStatus.SUCCESS
    item = result.items[0]
    assert item['content'] == '实际正文' and item['publish_datetime'] is None
    hints = item['raw']['media_hints']
    assert [hint['native_tag'] for hint in hints] == [
        'mpvideo', 'mpvoice', 'video', 'source', 'source', 'audio', 'iframe', 'iframe']
    assert hints[0]['media_id'] == 'wxv-1'
    assert hints[0]['url'] == 'https://mpvideo.qpic.cn/one.mp4'
    assert hints[0]['native_attributes']['data-title'] == '原生标题'
    assert hints[1]['media_id'] == 'voice-1' and hints[1]['url'] is None
    assert hints[2]['url'] is None and hints[2]['cover_url'] == 'https://mmbiz.qpic.cn/cover.jpg'
    assert hints[3]['url'] == 'https://mp.weixin.qq.com/media/two.mp4'
    assert hints[3]['native_locator']['source_element_index'] == 0
    assert hints[4]['url'] == 'https://mp.weixin.qq.com/media/lazy.mp4'
    assert hints[4]['native_locator']['source_element_index'] == 1
    assert hints[5]['native_attributes']['duration'] == '123'
    assert hints[6]['url_role'] == 'EMBED_PAGE' and hints[6]['media_type'] == 'video'
    assert hints[7]['media_type'] == 'embed'
    assert all(item[key] is None for key in ('likes', 'comments', 'collects', 'shares', 'views'))


def test_channels_data_url_remains_untyped_hint_without_claiming_playable_video():
    item = parse_public_article(response(
        '<div id="js_content">视频号说明<mp-common-videosnap data-id="finder-1" '
        'data-url="https://mmbiz.qpic.cn/thumbnail.jpg" data-desc="发布者描述">'
        '</mp-common-videosnap></div>'))
    hint = item['raw']['media_hints'][0]
    assert hint['media_id'] == 'finder-1' and hint['url'] is None
    assert hint['observed_data_url'] == 'https://mmbiz.qpic.cn/thumbnail.jpg'
    assert hint['observed_data_url_role'] == 'UNKNOWN'
    assert hint['native_attributes']['data-desc'] == '发布者描述'


@pytest.mark.parametrize('src', [
    'javascript:alert(1)', 'data:video/mp4;base64,AAAA', 'blob:https://mp.weixin.qq.com/id',
    'https://user:password@media.example.test/one.mp4',
    'https://media.example.test/one.mp4?auth_key=private',
    'https://media.example.test/one.mp4?access_token=private',
    'https://[malformed/one.mp4',
])
def test_media_hint_does_not_export_executable_or_credential_url(src):
    item = parse_public_article(response(
        f'<div id="js_content">正文<mpvideo data-vid="public-video-id" data-src="{src}"></mpvideo></div>'))
    hint = item['raw']['media_hints'][0]
    assert hint['media_id'] == 'public-video-id' and hint['url'] is None
    assert src not in str(hint)


def test_media_hint_excludes_form_noscript_and_strips_url_fragment():
    item = parse_public_article(response(
        '<div id="js_content">正文<form><video src="https://example.test/form.mp4"></video></form>'
        '<noscript><audio src="https://example.test/fallback.mp3"></audio></noscript>'
        '<audio src="https://example.test/actual.mp3#token=private"></audio></div>'))
    hints = item['raw']['media_hints']
    assert len(hints) == 1 and hints[0]['url'] == 'https://example.test/actual.mp3'


@pytest.mark.parametrize('src', ['javascript:alert(1)', 'https://example.test/image.jpg?auth_key=private'])
def test_original_image_observation_does_not_export_unsafe_resource(src):
    from lumenis.system.collector.adapters.platform_naming import map_raw_to_normalized

    item = parse_public_article(response(
        f'<div id="js_content">正文<img data-src="{src}" alt="发布者图示"></div>'))
    image = item['raw']['images'][0]
    assert image == {'url': None, 'alt': '发布者图示', 'media_type': 'image'}
    assert map_raw_to_normalized(item['raw'], 'wechat')['media_list'] == [image]
    assert src not in str(item['raw'])


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


def test_sogou_index_challenge_records_safe_diagnostic_without_following_original():
    calls = []
    challenge_html = '<div>请完成安全验证</div>'

    def fetch(url):
        calls.append(url)
        return response(challenge_html, url)

    result = WechatPublicAdapter(fetcher=fetch).search('停车')

    assert calls == ['https://weixin.sogou.com/weixin?type=2&query=%E5%81%9C%E8%BD%A6&page=1']
    assert result.status is CollectionStatus.NEED_VERIFY and result.ok is False
    assert result.items == [] and result.raw_count == 0
    assert result.metadata['provider'] == 'public_sogou_discovery_original_fetch'
    assert result.metadata['reason'] == 'SEARCH_INDEX_VERIFICATION_REQUIRED'
    assert result.metadata['index_only'] is True
    assert result.metadata['original_body_available'] is False
    detail = result.metadata['detail']
    assert detail['state'] == CollectionStatus.NEED_VERIFY.value
    assert detail['reason'] == 'SEARCH_INDEX_VERIFICATION_REQUIRED'
    assert detail['requested_source_url'] == 'https://weixin.sogou.com/weixin'
    assert detail['final_source_url'] == 'https://weixin.sogou.com/weixin'
    assert detail['source_access_mode'] == 'public_read_only'
    assert detail['accepted_native_article_count'] == 0
    assert challenge_html not in repr(result.metadata)


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


def test_discovery_candidates_are_not_counted_as_collected_articles():
    index = response(''.join(
        f'<li id="sogou_vr_{number}"><h3><a href="https://mp.weixin.qq.com/s/article{number}">候选</a></h3></li>'
        for number in range(10)), 'https://weixin.sogou.com/weixin?type=2')

    def fetch(url):
        return index if 'weixin.sogou.com' in url else response('<div>原文不可用</div>', url)

    result = WechatPublicAdapter(fetcher=fetch).search('罗湖万象城 活动')
    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.items == [] and result.raw_count == 0
    detail = result.metadata['detail']
    assert detail['discovery_candidate_count'] == detail['attempted_original_count'] == 10
    assert detail['accepted_native_article_count'] == 0
    assert all(item['reason'] == 'ORIGINAL_ARTICLE_BODY_NOT_OBSERVED'
               for item in detail['original_outcomes'])
    assert detail['original_outcomes'][0]['final_source_url'] == 'https://mp.weixin.qq.com/s/article0'
    assert all(len(item['discovery_locator_sha256']) == 64 for item in detail['original_outcomes'])


def test_partial_discovery_counts_only_observed_original_body():
    index = response(''.join(
        f'<li id="sogou_vr_{number}"><h3><a href="https://mp.weixin.qq.com/s/article{number}">候选</a></h3></li>'
        for number in range(2)), 'https://weixin.sogou.com/weixin?type=2')

    def fetch(url):
        if 'weixin.sogou.com' in url:
            return index
        body = '<div id="js_content">实际原文</div>' if url.endswith('article0') else '<div>不可用</div>'
        return response(body, url)

    result = WechatPublicAdapter(fetcher=fetch).search('广州太古汇 服务')
    assert result.status is CollectionStatus.SUCCESS and result.raw_count == 1
    assert len(result.items) == 1 and result.items[0]['content'] == '实际原文'
    assert result.metadata['discovery_candidate_count'] == 2
    assert result.metadata['detail']['accepted_native_article_count'] == 1


def test_partial_original_body_survives_later_challenge_without_success_promotion():
    calls = []
    index = response(''.join(
        f'<li id="sogou_vr_{number}"><h3><a href="https://mp.weixin.qq.com/s/article{number}">候选</a></h3></li>'
        for number in range(3)), 'https://weixin.sogou.com/weixin?type=2')

    def fetch(url):
        calls.append(url)
        if 'weixin.sogou.com' in url:
            return index
        if url.endswith('article0'):
            return response('<div id="js_content">验证发生前取得的原文</div>', url)
        return response('<div>请完成安全验证</div>', url)

    result = WechatPublicAdapter(fetcher=fetch).search('广州太古汇 服务')
    assert result.status is CollectionStatus.NEED_VERIFY and result.ok is False
    assert len(calls) == 3 and result.raw_count == len(result.items) == 1
    assert result.items[0]['content'] == '验证发生前取得的原文'
    assert result.metadata['partial'] is True
    assert result.metadata['detail']['attempted_original_count'] == 2
    assert result.metadata['per_request_deferred_source_count'] == 1
    assert result.metadata['detail']['original_outcomes'][1]['reason'] == 'ORIGINAL_VERIFICATION_REQUIRED'


@pytest.mark.parametrize('final_url', [
    'http://mp.weixin.qq.com/s/article',
    'https://mp.weixin.qq.com:444/s/article',
    'https://mp.weixin.qq.com/not-an-article',
    'https://mp.weixin.qq.com/s?mid=42',
    'https://user:password@mp.weixin.qq.com/s/article',
    'https://example.com/s/article',
])
def test_original_body_requires_valid_final_article_url(final_url):
    fetched = response('<div id="js_content">不可误采的正文</div>', final_url)
    assert parse_public_article(fetched) is None
    result = WechatPublicAdapter(fetcher=lambda _: fetched).detail('https://mp.weixin.qq.com/s/requested')
    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.items == [] and result.raw_count == 0
    assert result.metadata['detail']['reason'] == 'ORIGINAL_ARTICLE_URL_NOT_SUPPORTED'


@pytest.mark.parametrize('http_status,reason', [
    (429, 'PUBLIC_HTTP_RATE_LIMITED'),
    (403, 'PUBLIC_HTTP_ACCESS_RESTRICTED'),
    (401, 'PUBLIC_HTTP_ACCESS_RESTRICTED'),
])
def test_public_http_restriction_stops_following_and_records_safe_category(http_status, reason):
    calls = []
    index = response(''.join(
        f'<li id="sogou_vr_{number}"><h3><a href="https://mp.weixin.qq.com/s/article{number}">候选</a></h3></li>'
        for number in range(2)), 'https://weixin.sogou.com/weixin?type=2')

    def fetch(url):
        calls.append(url)
        if len(calls) == 1:
            return index
        raise PublicSourceError(f'public source returned HTTP {http_status}')

    result = WechatPublicAdapter(fetcher=fetch).search('Nike 城市活动')
    assert result.status is CollectionStatus.BLOCKED and len(calls) == 2
    assert result.items == [] and result.raw_count == 0
    detail = result.metadata['detail']
    assert detail['attempted_original_count'] == 1
    assert detail['original_outcomes'][0]['reason'] == reason
    assert detail['original_outcomes'][0]['http_status'] == http_status
    assert result.metadata['per_request_deferred_source_count'] == 1


def test_transport_diagnostic_never_copies_arbitrary_exception_or_url_query():
    secret_text = 'credential-value-must-not-be-recorded'

    def fail(_):
        raise PublicSourceError(f'private transport detail {secret_text}')

    result = WechatPublicAdapter(fetcher=fail).detail('https://mp.weixin.qq.com/s/article')
    assert secret_text not in repr(result.metadata)
    assert result.metadata['detail']['reason'] == 'PUBLIC_TRANSPORT_UNAVAILABLE'
    fetched = response('<div id="js_content">原文</div>',
                       'https://mp.weixin.qq.com/s/article?token=' + secret_text)
    result = WechatPublicAdapter(fetcher=lambda _: fetched).detail('https://mp.weixin.qq.com/s/article')
    assert result.status is CollectionStatus.SUCCESS
    assert secret_text not in repr(result.metadata['detail'])
    assert result.metadata['detail']['final_source_url'] == 'https://mp.weixin.qq.com/s/article'

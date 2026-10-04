import json
import pytest
from lumenis.system.collector.adapters.instagram import InstagramAdapter, parse_public_instagram_document
from lumenis.system.collector.adapters.public_source import PublicResponse


def document(code='NativePost', pk='3950357121996910485', caption='原始文案 #城市限定'):
    media={'pk':pk,'code':code,'if_not_gated_logged_out':{
        'pk':pk,'code':code,'taken_at':1785146450,
        'caption':{'text':caption,'created_at':1785146453}, 'caption_is_edited':False,
        'like_count':0, 'comment_count':None, 'organic_tracking_token':'never export',
        'user':{'pk':'123','username':'issuer','private_viewer_context':'never export'},
    },'comments_connection':{'edges':[], 'page_info':{'has_next_page':True}}}
    html='<script type="application/json">'+json.dumps({'data':media},ensure_ascii=False)+'</script>'
    return PublicResponse(url='https://www.instagram.com/reel/NativePost/',content=html.encode(),content_type='text/html',status_code=200)


def test_matching_native_id_complete_caption_and_distinct_native_times():
    item=parse_public_instagram_document(document(),'NativePost')
    assert item['platform_content_id']=='3950357121996910485'
    assert item['content']=='原始文案 #城市限定'
    assert item['raw']['taken_at']==1785146450 and item['raw']['caption_created_at']==1785146453
    assert item['publish_datetime']=='2026-07-27T10:00:50+00:00'
    assert item['likes']==0 and item['comments'] is None and item['views'] is None
    assert 'organic_tracking_token' not in item['raw']
    assert 'private_viewer_context' not in item['raw']['author']
    assert item['raw']['comment_page_info']['has_next_page'] is True


def test_wrong_post_and_meta_only_page_are_not_original_bodies():
    assert parse_public_instagram_document(document(code='AnotherPost'),'NativePost') is None
    shell=PublicResponse(url='https://www.instagram.com/reel/NativePost/',content=b'<meta name="description" content="index snippet">',content_type='text/html',status_code=200)
    assert parse_public_instagram_document(shell,'NativePost') is None


def test_public_exact_post_path_does_not_touch_credential_engine():
    adapter=InstagramAdapter(public_fetcher=lambda _:document())
    adapter._get_engine=lambda:pytest.fail('public post should not read session or Cookie')
    result=adapter.search('https://www.instagram.com/reel/NativePost/')
    assert result.ok and result.items[0]['content']=='原始文案 #城市限定'
    assert result.metadata['original_body_available'] is True


def test_foreign_host_is_rejected_before_any_request():
    adapter=InstagramAdapter(public_fetcher=lambda _:pytest.fail('unexpected source fetch'))
    with pytest.raises(ValueError):adapter.search('https://example.com/reel/NativePost/')


def test_public_comment_user_fields_never_export_viewer_or_private_tracking():
    original=document()
    decoded=json.loads(original.content.decode().split("<script type=\"application/json\">")[1].split("</script>")[0])
    decoded["data"]["comments_connection"]["edges"]=[{"node":{"pk":"comment-1","text":"公开评论","like_count":0,"user":{"pk":"u-1","username":"public-user","is_verified":False,"viewer_session":"private-context","password":"never"},"viewer_tracking":"never"}}]
    body=("<script>"+json.dumps(decoded,ensure_ascii=False)+"</script>").encode()
    response=PublicResponse(url=original.url,content=body,content_type="text/html",status_code=200)
    item=parse_public_instagram_document(response,"NativePost")
    assert item["raw"]["public_comments"]==[{"pk":"comment-1","text":"公开评论","like_count":0,"user":{"pk":"u-1","username":"public-user","is_verified":False}}]

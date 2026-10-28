"""Daum Cafe/Tistory native public pages using the original safe HTTP owner."""
from __future__ import annotations

import re
from urllib.parse import quote

from .naver import KoreanSourceError, _https_parts, _KoreanPublicPageAdapter
from .registry import register_adapter


class DaumAdapter(_KoreanPublicPageAdapter):
    platform = 'daum'
    enabled = False
    monitor_priority = 'secondary'
    body_selectors = ('#user_contents', '.article_view', '.contents_style', '.tt_article_useless_p_margin', '.entry-content', '.article_cont')
    search_host, search_path, search_parameter = 'search.daum.net', '/search', 'q'

    @classmethod
    def identity(cls, value):
        if isinstance(value, str) and not value.startswith('https://'):
            match = re.fullmatch(r'tistory:([A-Za-z0-9-]{1,63}):([0-9]{1,20})', value)
            cafe = re.fullmatch(r'cafe:([A-Za-z0-9_-]{1,100}):([A-Za-z0-9_-]{1,100}):([0-9]{1,20})', value)
            if match:
                value = f'https://{match[1]}.tistory.com/{match[2]}'
            elif cafe:
                value = f'https://cafe.daum.net/{cafe[1]}/{cafe[2]}/{cafe[3]}'
        parts = _https_parts(value)
        host = parts.hostname or ''
        segments = [segment for segment in parts.path.split('/') if segment]
        if host.endswith('.tistory.com') and re.fullmatch(r'[A-Za-z0-9-]{1,63}', host[:-12]):
            owner = host[:-12]
            if len(segments) == 2 and segments[0] == 'm':
                segments = segments[1:]
            if len(segments) != 1 or not segments[0].isdigit() or len(segments[0]) > 20:
                raise KoreanSourceError('SOURCE_URL_INVALID')
            post = segments[0]
            canonical = f'https://{owner}.tistory.com/{post}'
            return {'kind': 'tistory', 'native_content_id': f'tistory:{owner}:{post}',
                    'blog_id': owner, 'post_id': post, 'author_id': owner,
                    'url': canonical, 'read_url': canonical}
        if host in {'cafe.daum.net', 'm.cafe.daum.net'} and len(segments) == 3:
            owner, board, post = segments
            if not all(re.fullmatch(r'[A-Za-z0-9_-]{1,100}', v) for v in (owner, board)) or not re.fullmatch(r'[0-9]{1,20}', post):
                raise KoreanSourceError('SOURCE_URL_INVALID')
            canonical = f'https://cafe.daum.net/{owner}/{board}/{post}'
            return {'kind': 'cafe', 'native_content_id': f'cafe:{owner}:{board}:{post}',
                    'cafe_id': owner, 'board_id': board, 'article_id': post,
                    'author_id': None, 'url': canonical, 'read_url': canonical}
        raise KoreanSourceError('SOURCE_URL_INVALID')

    def creator(self, creator_id, **kwargs):
        owner = str(creator_id).removeprefix('tistory:')
        if not re.fullmatch(r'[A-Za-z0-9-]{1,63}', owner):
            return self._failure(KoreanSourceError('AUTHOR_ID_INVALID'), capability='author')
        return self._public_profile(owner, url=f'https://{owner}.tistory.com/', kind='tistory')

    def search(self, keyword, **kwargs):
        if isinstance(keyword, str) and keyword.startswith('https://'):
            try:
                parts = _https_parts(keyword)
                host = parts.hostname or ''
                if host.endswith('.tistory.com') and parts.path.rstrip('/') == '/rss':
                    owner = host[:-12]
                    if not re.fullmatch(r'[A-Za-z0-9-]{1,63}', owner) or parts.query:
                        raise KoreanSourceError('SOURCE_URL_INVALID')
                    return self._feed(keyword, owner=owner, kind='tistory', max_results=kwargs.get('max_results', 20), cursor=kwargs.get('cursor'))
            except KoreanSourceError as exc:
                return self._failure(exc, capability='search')
        return super().search(keyword, **kwargs)

    def author_posts(self, author_id, **kwargs):
        owner = str(author_id).removeprefix('tistory:')
        if not re.fullmatch(r'[A-Za-z0-9-]{1,63}', owner):
            return self._failure(KoreanSourceError('AUTHOR_ID_INVALID'), capability='author_posts')
        return self._listing(owner, mode='author_posts', base_url=f'https://{quote(owner)}.tistory.com/',
                             max_results=kwargs.get('max_results', 20), cursor=kwargs.get('cursor'))


register_adapter('daum', DaumAdapter)

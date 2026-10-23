"""Bounded, deterministic extraction from an already authorized browser page.

No navigation, HTTP client, credentials, model calls or SourceUse admission live here.
The Browser owner supplies the page capture; its existing Evidence owner records it.
"""
from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import re
import time
from urllib.parse import urlsplit, urlunsplit

MAX_CAPTURE_CHARS = 32768
MAX_BLOCKS = 256
MAX_RESULT_BYTES = 512 * 1024
FORMATS = frozenset({'text', 'markdown', 'html'})


class BrowserExtractionError(ValueError):
    def __init__(self, code: str, **details):
        self.code = code
        self.details = details
        super().__init__(code)


def validate_extract_request(data):
    if type(data) is not dict or set(data) - {
        'url', 'formats', 'timeout_ms', 'question', 'page_revision', 'target_id'
    }:
        raise BrowserExtractionError('BROWSER_EXTRACTION_OPTIONS_INVALID')
    url = data.get('url')
    if url is not None or 'question' not in data:
        if not isinstance(url, str) or not 1 <= len(url) <= 4096 or url != url.strip():
            raise BrowserExtractionError('BROWSER_EXTRACTION_URL_INVALID')
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or '').lower()
            if (parsed.scheme not in {'http', 'https'} or not host or parsed.username is not None
                    or parsed.password is not None or any(ord(c) < 32 for c in url)
                    or host == 'localhost' or host.endswith(('.localhost', '.local', '.internal'))):
                raise ValueError
            _ = parsed.port
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                if '.' not in host:
                    raise ValueError
            else:
                if not address.is_global:
                    raise ValueError
        except ValueError:
            raise BrowserExtractionError('BROWSER_EXTRACTION_URL_INVALID') from None
    formats = data.get('formats')
    if (type(formats) is not dict or not formats or set(formats) - FORMATS
            or any(type(v) is not bool for v in formats.values()) or not any(formats.values())):
        raise BrowserExtractionError('BROWSER_EXTRACTION_FORMATS_INVALID')
    timeout = data.get('timeout_ms', 10000)
    if type(timeout) is not int or not 100 <= timeout <= 30000:
        raise BrowserExtractionError('BROWSER_EXTRACTION_TIMEOUT_INVALID')
    result = {'url': url, 'formats': {k: True for k in sorted(formats) if formats[k]}, 'timeout_ms': timeout}
    if any(key in data for key in ('question', 'page_revision', 'target_id')):
        question = data.get('question')
        revision, target = data.get('page_revision'), data.get('target_id')
        if (not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000
                or any(ord(c) < 32 and c not in '\n\t' for c in question)
                or type(revision) is not int or revision < 0
                or not isinstance(target, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}', target)):
            raise BrowserExtractionError('BROWSER_CONTEXT_REQUEST_INVALID')
        result.update(question=question.strip(), page_revision=revision, target_id=target)
    return result


def select_page_context(structure, question):
    from lumenis.shared.reporting.operational_brief import _analysis_window

    body = '\n\n'.join(block['text'] for block in structure['blocks'])
    excerpt, selection = _analysis_window(body, question)
    return {
        'question': question,
        'excerpt': excerpt,
        'selection': selection,
        'captured_characters': len(body),
        'coverage': structure['coverage'],
        'answer_state': 'NOT_GENERATED',
        'content_kind': 'SOURCE_EXCERPT',
        'semantic_relevance': 'NOT_EVALUATED',
    }


def same_document_url(left, right):
    """Normalize only browser-equivalent origin spelling and an empty '/' path.

    Query and fragment stay exact; redirects never silently broaden the target.
    """
    def key(value):
        parsed = urlsplit(value)
        host = (parsed.hostname or '').encode('idna').decode('ascii').lower()
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        return parsed.scheme.lower(), host, port, parsed.path or '/', parsed.query, parsed.fragment
    try:
        return key(left) == key(right)
    except (ValueError, UnicodeError, AttributeError):
        return False


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise BrowserExtractionError('BROWSER_EXTRACTION_TIMEOUT')


# Fixed source only. Never evaluate user code, read inputs, cookies or storage.
# Return text blocks, not page-controlled HTML/attributes/URLs or executable markup.
CAPTURE_SCRIPT = r"""(() => {
 const started = performance.now(), blocks = [], maxChars = 32768, maxNodes = 4096;
 let scanned = 0, chars = 0, truncated = false, last = null;
 const excluded = 'script,style,noscript,template,input,textarea,select,option,button,form,[contenteditable],iframe,object,embed,svg,canvas';
 const root = document.body;
 if (document.querySelector('input[type=password],iframe[src*=recaptcha],iframe[src*=hcaptcha],[data-sitekey]') || /^(access denied|verify you are human|just a moment)/i.test(document.title.trim())) return {interaction_required:true};
 if (!root) return {blocks: [], title: document.title.slice(0,300), url: location.href, truncated:false};
 const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
 while (walker.nextNode()) {
  if (++scanned > maxNodes || chars >= maxChars || blocks.length >= 256 || performance.now()-started > 2000) { truncated=true; break; }
  const node=walker.currentNode, parent=node.parentElement;
  if (!parent || parent.closest(excluded)) continue;
  let visible=true;
  for (let el=parent; el; el=el.parentElement) {
   const style=getComputedStyle(el);
   if (el.hidden || el.getAttribute('aria-hidden')==='true' || style.display==='none' || style.visibility==='hidden' || style.visibility==='collapse' || style.opacity==='0' || style.contentVisibility==='hidden') {visible=false;break;}
  }
  if (!visible || !parent.getClientRects().length) continue;
  const raw=(node.nodeValue || '').replace(/\s+/g,' ').trim();
  if (!raw) continue;
  const owner=parent.closest('h1,h2,h3,h4,h5,h6,p,li,pre,blockquote,td,th') || parent;
  const tag=/^(H[1-6]|P|LI|PRE|BLOCKQUOTE|TD|TH)$/.test(owner.tagName) ? owner.tagName.toLowerCase() : 'p';
  const merge=last===owner && blocks.length, separator=merge ? 1 : 0;
  if (maxChars-chars <= separator) {truncated=true;break;}
  const text=raw.slice(0,maxChars-chars-separator); chars+=text.length+separator;
  if (text.length<raw.length) truncated=true;
  if (merge) blocks[blocks.length-1].text+=' '+text;
  else { blocks.push({tag,text}); last=owner; }
 }
 const resources=[];
 for (const el of root.querySelectorAll('a[href],img[src],video, audio, source[src]')) {
  if (resources.length>=128 || performance.now()-started>2000) {truncated=true;break;}
  if (el.closest('form,[contenteditable]')) continue;
  let visible=!!el.getClientRects().length;
  for(let parent=el;parent;parent=parent.parentElement){
   const style=getComputedStyle(parent);
   if(parent.hidden || parent.getAttribute('aria-hidden')==='true' || style.display==='none' || style.visibility==='hidden' || style.opacity==='0') {visible=false;break;}
  }
  if(!visible) continue;
  const kind=el.tagName==='A'?'link':el.tagName==='IMG'?'image':el.tagName==='AUDIO'?'audio':el.tagName==='SOURCE'?'source':'video';
  const url=kind==='link'?el.href:(el.currentSrc||el.src||'');
  resources.push({kind,url:String(url).slice(0,4096),label:String(kind==='link'?el.innerText:(el.alt||'')).slice(0,300)});
 }
 return {blocks,resources,title:document.title.slice(0,300),url:location.href,truncated};
})()"""


def format_capture(capture, requested, sanitize):
    if (type(capture) is not dict or type(capture.get('blocks')) is not list
            or len(capture['blocks']) > MAX_BLOCKS):
        raise BrowserExtractionError('BROWSER_EXTRACTION_CAPTURE_INVALID')
    blocks = []
    size = 0
    for block in capture['blocks']:
        if type(block) is not dict or set(block) != {'tag', 'text'} or not isinstance(block['text'], str):
            raise BrowserExtractionError('BROWSER_EXTRACTION_CAPTURE_INVALID')
        tag = block['tag']
        if tag not in {'h1','h2','h3','h4','h5','h6','p','li','pre','blockquote','td','th'}:
            raise BrowserExtractionError('BROWSER_EXTRACTION_CAPTURE_INVALID')
        size += len(block['text'])
        if size > MAX_CAPTURE_CHARS + MAX_BLOCKS:
            raise BrowserExtractionError('BROWSER_EXTRACTION_TOO_LARGE')
        blocks.append((tag, sanitize(block['text'])))
    text = '\n\n'.join(value for _, value in blocks)
    # Escape markdown syntax; no remote images, links or embedded HTML survive.
    def escaped(value):
        return re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', html.escape(value, quote=False))
    markdown = '\n\n'.join((('#' * int(tag[1]) + ' ') if tag.startswith('h') else '- ' if tag == 'li' else '> ' if tag == 'blockquote' else '') + escaped(value) for tag, value in blocks)
    rendered = '\n'.join('<{0}>{1}</{0}>'.format('p' if tag in {'li','td','th'} else tag, html.escape(value)) for tag,value in blocks)
    values = {'text': text, 'markdown': markdown, 'html': rendered}
    result = {key: {'success': True, 'data': values[key], 'content_sha256': hashlib.sha256(values[key].encode()).hexdigest()} for key in requested}
    if len(json.dumps(result, ensure_ascii=False).encode()) > MAX_RESULT_BYTES:
        raise BrowserExtractionError('BROWSER_EXTRACTION_TOO_LARGE')
    return result


CAPTURE_TTL_SECONDS = 300
MAX_RESOURCES = 128


def capture_structure(capture, sanitize):
    """Project untrusted DOM values; never fetch resources or claim SourceUse."""
    # Reuse exactly the existing bounded block validator before projection.
    format_capture(capture, {'text': True}, sanitize)
    blocks = [{'block_id': f'b{i}', 'tag': b['tag'], 'text': sanitize(b['text'])}
              for i, b in enumerate(capture['blocks'])]
    raw_resources = capture.get('resources', [])
    if type(raw_resources) is not list or len(raw_resources) > MAX_RESOURCES:
        raise BrowserExtractionError('BROWSER_EXTRACTION_CAPTURE_INVALID')
    resources = []
    for i, item in enumerate(raw_resources):
        if (type(item) is not dict or set(item) != {'kind', 'url', 'label'}
                or not isinstance(item['kind'], str) or item['kind'] not in {'link', 'image', 'audio', 'video', 'source'}
                or type(item['url']) is not str or len(item['url']) > 4096
                or type(item['label']) is not str or len(item['label']) > 300):
            raise BrowserExtractionError('BROWSER_EXTRACTION_CAPTURE_INVALID')
        value, state, reason = None, 'UNAVAILABLE', 'INVALID_OR_NON_PUBLIC_URL'
        try:
            parsed = urlsplit(item['url'])
            host = (parsed.hostname or '').lower()
            valid = (parsed.scheme == 'https' and host and '.' in host
                     and parsed.username is None and parsed.password is None
                     and not host.endswith(('.localhost', '.local', '.internal'))
                     and not any(ord(c) < 32 for c in item['url']) and '\\' not in item['url'])
            try:
                valid = valid and __import__('ipaddress').ip_address(host).is_global
            except ValueError:
                pass
            _ = parsed.port
            if valid:
                if parsed.query or parsed.fragment:
                    state, reason = 'REQUIRES_SESSION_REF', 'QUERY_OR_FRAGMENT_NOT_EXPORTED'
                else:
                    clean = sanitize(urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', '')))
                    if clean == item['url']:
                        value, state, reason = clean, 'OBSERVED', None
        except ValueError:
            pass
        resources.append({'resource_id': f'r{i}', 'kind': item['kind'],
                          'url': value, 'state': state, 'reason': reason,
                          'label': sanitize(item['label']), 'rights_state': 'UNKNOWN',
                          'original_sha256': None, 'download_state': 'NOT_REQUESTED',
                          'content_state': 'METADATA_ONLY'})
    result = {'blocks': blocks, 'resources': resources,
            'dimensions': {'native_id': {'value': None, 'state': 'NOT_EXTRACTED'},
                           'published_at': {'value': None, 'state': 'NOT_EXTRACTED'},
                           'author': {'value': None, 'state': 'NOT_EXTRACTED'},
                           'metrics': {'value': None, 'state': 'NOT_EXTRACTED'},
                           'comments': {'value': None, 'state': 'NOT_EXTRACTED'}},
            'coverage': 'PARTIAL' if capture.get('truncated') else 'BOUNDED_DOM_ONLY'}
    if len(json.dumps(result, ensure_ascii=False).encode()) > MAX_RESULT_BYTES:
        raise BrowserExtractionError('BROWSER_EXTRACTION_TOO_LARGE')
    return result


def validate_capture_command(data):
    if type(data) is not dict:
        raise BrowserExtractionError('BROWSER_CAPTURE_COMMAND_INVALID')
    command = data.get('command')
    fields = {'capabilities': {'command'},
              'preview': {'command', 'request_id', 'url', 'formats', 'timeout_ms'},
              'select': {'command', 'capture_id', 'block_id', 'start', 'end'},
              'discard': {'command', 'capture_id'}}
    if not isinstance(command, str) or command not in fields or set(data) - fields[command]:
        raise BrowserExtractionError('BROWSER_CAPTURE_COMMAND_INVALID')
    if command == 'preview':
        rid = data.get('request_id')
        if not isinstance(rid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', rid):
            raise BrowserExtractionError('BROWSER_CAPTURE_REQUEST_INVALID')
        validate_extract_request({k:v for k,v in data.items() if k not in {'command','request_id'}})
    elif command in {'select', 'discard'}:
        if not isinstance(data.get('capture_id'), str) or not re.fullmatch(r'cap_[a-f0-9]{32}', data['capture_id']):
            raise BrowserExtractionError('BROWSER_CAPTURE_ID_INVALID')
        if command == 'select' and (not isinstance(data.get('block_id'), str)
                or not re.fullmatch(r'b[0-9]{1,3}', data['block_id'])
                or type(data.get('start')) is not int or type(data.get('end')) is not int):
            raise BrowserExtractionError('BROWSER_CAPTURE_SELECTION_INVALID')
    return data


def select_capture(capture, data):
    block = next((b for b in capture['structure']['blocks'] if b['block_id'] == data['block_id']), None)
    if block is None or not 0 <= data['start'] < data['end'] <= len(block['text']):
        raise BrowserExtractionError('BROWSER_CAPTURE_SELECTION_INVALID')
    text = block['text'][data['start']:data['end']]
    markdown = format_capture({'blocks': [{'tag': 'p', 'text': text}]}, {'markdown': True}, str)['markdown']['data']
    return {'text': text, 'markdown': markdown, 'locator': {'block_id': block['block_id'],
            'start': data['start'], 'end': data['end'], 'offset_unit': 'unicode_code_point',
            'exact': text, 'prefix': block['text'][max(0,data['start']-32):data['start']],
            'suffix': block['text'][data['end']:data['end']+32]},
            'content_sha256': hashlib.sha256(text.encode()).hexdigest()}


BROWSER_SOURCE_VERSION = 'collected-browser-snapshot:v1'


def snapshot_bytes(value):
    """Canonical retained *sanitized snapshot* bytes, never original web bytes."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if not 0 < len(raw) <= 2 * MAX_RESULT_BYTES:
        raise BrowserExtractionError('BROWSER_SOURCE_TOO_LARGE')
    return raw


def snapshot_body(structure):
    blocks = structure.get('blocks') if isinstance(structure, dict) else None
    if not isinstance(blocks, list) or not 0 < len(blocks) <= MAX_BLOCKS:
        raise BrowserExtractionError('BROWSER_SOURCE_SNAPSHOT_INVALID')
    parts, mapping, seen, offset = [], [], set(), 0
    for block in blocks:
        if (not isinstance(block, dict) or not isinstance(block.get('text'), str)
                or not isinstance(block.get('block_id'), str) or block['block_id'] in seen):
            raise BrowserExtractionError('BROWSER_SOURCE_SNAPSHOT_INVALID')
        seen.add(block['block_id'])
        text = block['text']
        if parts: offset += 1
        mapping.append({'block_id': block['block_id'], 'start': offset, 'end': offset+len(text),
                        'unit': 'sanitized-browser-text', 'offset_unit': 'unicode-codepoint'})
        parts.append(text)
        offset += len(text)
    body = '\n'.join(parts)
    if not body.strip():
        raise BrowserExtractionError('BROWSER_SOURCE_SNAPSHOT_INVALID')
    return body, mapping


def make_source_snapshot(capture, *, target_id, page_revision):
    body, mapping = snapshot_body(capture['structure'])
    # Match the original Browser Evidence's serialization, not the artifact hash.
    capture_hash = hashlib.sha256(json.dumps(
        {'formats': capture['formats'], 'structure': capture['structure']},
        sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    binding = {'schema': 'lumenis.browser-snapshot/v1', 'capture_sha256': capture_hash,
               'body_sha256': hashlib.sha256(body.encode()).hexdigest(),
               'session_id': capture['session_id'], 'operation_id': capture['operation_id'],
               'browser_evidence_id': capture['evidence_id'], 'target_id': target_id,
               'page_revision': page_revision}
    snapshot = {'schema': binding['schema'], 'binding': binding,
                'formats': capture['formats'], 'structure': capture['structure'],
                'metadata': capture['metadata'], 'body': body, 'block_map': mapping,
                'partial': bool(capture['partial']), 'original_resource_sha256': None}
    return json.loads(snapshot_bytes(snapshot))


def validate_source_snapshot(snapshot):
    if (not isinstance(snapshot, dict) or set(snapshot) != {'schema','binding','formats','structure',
            'metadata','body','block_map','partial','original_resource_sha256'}
            or snapshot['schema'] != 'lumenis.browser-snapshot/v1'
            or snapshot['original_resource_sha256'] is not None or type(snapshot['partial']) is not bool):
        raise BrowserExtractionError('BROWSER_SOURCE_SNAPSHOT_INVALID')
    binding = snapshot['binding']
    if (not isinstance(binding, dict) or set(binding) != {'schema','capture_sha256','body_sha256',
            'session_id','operation_id','browser_evidence_id','target_id','page_revision'}
            or binding['schema'] != snapshot['schema']
            or any(not isinstance(binding[k], str) or not binding[k] for k in ('session_id','operation_id','target_id'))
            or type(binding['browser_evidence_id']) is not int or binding['browser_evidence_id'] <= 0
            or type(binding['page_revision']) is not int or binding['page_revision'] < 0):
        raise BrowserExtractionError('BROWSER_SOURCE_SNAPSHOT_INVALID')
    body, mapping = snapshot_body(snapshot['structure'])
    digest = hashlib.sha256(json.dumps({'formats': snapshot['formats'], 'structure': snapshot['structure']},
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if (body != snapshot['body'] or mapping != snapshot['block_map']
            or binding['body_sha256'] != hashlib.sha256(body.encode()).hexdigest()
            or binding['capture_sha256'] != digest or not isinstance(snapshot['metadata'], dict)
            or snapshot['metadata'].get('page_revision') != binding['page_revision']):
        raise BrowserExtractionError('BROWSER_SOURCE_SNAPSHOT_INVALID')
    snapshot_bytes(snapshot)
    return snapshot

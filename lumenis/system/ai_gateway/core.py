import threading, time

# V1.0: 线程安全的最后一次 AI 调用元信息（用于 token 记录，不破坏 _chat 2-tuple 接口）
_last_call_meta_lock = threading.Lock()
_last_call_meta = {"provider": "", "model": "", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "timestamp": ""}


def _set_call_meta(provider="", model="", prompt_tokens=0, completion_tokens=0, total_tokens=0):
    """记录最后一次 AI 调用的元信息（线程安全）。"""
    with _last_call_meta_lock:
        _last_call_meta.update({
            "provider": provider or "",
            "model": model or "",
            "prompt_tokens": int(prompt_tokens or 0),
            "completion_tokens": int(completion_tokens or 0),
            "total_tokens": int(total_tokens or 0),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })


def _get_call_meta():
    """获取最后一次 AI 调用的元信息（线程安全，返回副本）。"""
    with _last_call_meta_lock:
        return dict(_last_call_meta)

"""LUMENIS SYSTEM AI Gateway compatibility module.

Retired identities remain only in denial and historical evidence metadata.
Product-owned inference is the sole AI-task route and stays explicitly
unavailable until an approved runtime is bound.
"""
import json, os, re, urllib.request

# ZBC Phase 7: module status markers
MODULE_STATUS = 'ACTIVE_PRIMARY'
AI_ROLE = 'CENTRAL_GATEWAY'  # Product AI uses the owned Gateway; retired routes fail closed
PROVIDER_POLICY = 'owned-only; legacy signatures inert; no discovery, transport or fallback'

_CACHE = {'ts': 0, 'provider': None, 'model': None, 'base': None}

def _env(name, default=''):
    return os.getenv(name, default).strip()


def _selected_provider_disabled(requested=None):
    """Legacy provider selection cannot authorize any model transport."""
    return True


def _provider_disabled_meta(level='medium', model=None):
    _set_call_meta(provider='provider_disabled', model=model or '')
    return {
        'cache': False, 'level': level, 'model': model, 'provider': 'provider_disabled',
        'token_usage': 0, 'prompt_tokens': 0, 'completion_tokens': 0, 'call_id': None,
    }


def bind_owned_service(binding):
    """Explicitly bind one admitted, server-held production executor."""
    from .owned_service import bind_owned_service as bind

    return bind(binding)


def clear_owned_service(domain_id, expected_binding_sha256):
    """Safety-stop one domain binding without retrying or replaying work."""
    from .owned_service import clear_owned_service as clear

    return clear(domain_id, expected_binding_sha256)


def revoke_owned_service(admission_verifier):
    """Revoke exactly the active binding named by a fresh canonical decision."""
    from .owned_service import revoke_owned_service as revoke

    return revoke(admission_verifier)


def run_owned_request(request, *, is_cancelled=None, expected_binding_sha256=None):
    """Run a complete typed, source-authorized request through the one Gateway."""
    from .owned_service import run_owned_request as run

    return run(request, is_cancelled=is_cancelled, expected_binding_sha256=expected_binding_sha256)


def owned_inference_status(domain_id=None):
    """Read a scoped service slot, or the legacy non-production candidate status."""
    if domain_id is not None:
        from .owned_service import owned_service_status

        return owned_service_status(domain_id)
    from . import owned_inference

    return owned_inference.owned_inference_status()


def owned_service_observation(domain_id=None):
    """Secret-safe scoped production status; never consult an evaluation candidate."""
    def code(value, fallback):
        return value if (isinstance(value, str) and 0 < len(value) <= 128
                         and value.isascii() and value.replace('_', '').isalnum()) else fallback

    def scoped(domain):
        try:
            raw = owned_inference_status(domain)
            if not isinstance(raw, dict):
                raise TypeError('status is not an object')
        except Exception:
            raw = {'reason': 'OWNED_RUNTIME_STATUS_UNAVAILABLE'}
        binding = code(raw.get('service_binding'), 'NOT_VERIFIED')
        available = raw.get('available') is True and binding == 'BOUND'
        model = raw.get('model_id')
        if not available or not isinstance(model, str) or len(model) > 128:
            model = None
        return {'provider': 'owned', 'available': available, 'service_binding': binding,
                'state': code(raw.get('state'), 'UNKNOWN'),
                'reason': code(raw.get('reason'), 'OWNED_RUNTIME_UNAVAILABLE'),
                'model_id': model, 'fallback_allowed': False}

    if domain_id is not None:
        if domain_id not in {'cth', 'bmp', 'shared'}:
            return {'provider': 'owned', 'available': False, 'service_binding': 'BLOCKED',
                    'state': 'BLOCKED', 'reason': 'OWNED_SERVICE_DOMAIN_INVALID',
                    'model_id': None, 'fallback_allowed': False}
        return scoped(domain_id)
    domains = {domain: scoped(domain) for domain in ('cth', 'bmp', 'shared')}
    first = next(iter(domains.values()))
    if all(value == first for value in domains.values()):
        return {**first, 'domains': domains}
    ready = sum(item['available'] for item in domains.values())
    return {'provider': 'owned', 'available': ready == len(domains),
            'service_binding': 'BOUND' if ready == len(domains) else 'PARTIALLY_BOUND' if ready else 'NOT_BOUND',
            'state': 'SERVICE_BOUND' if ready == len(domains) else 'PARTIAL' if ready else 'UNAVAILABLE',
            'reason': 'OWNED_SERVICE_SCOPED_STATUS', 'model_id': None,
            'fallback_allowed': False, 'domains': domains}


def owned_retrieval_status():
    """Report actual serving capabilities, without probing/loading any model.

    The currently admitted OwnedProductionRuntime is a text generator with a
    tokenizer measurement API. It has no typed embedding or cross-encoder
    executor. A text-model binding cannot stand in for either capability; new
    retrieval weights and runtime admission remain separate requirements.
    """
    return {
        'embedding': {'available': False, 'state': 'BLOCKED_MODEL_NOT_ADMITTED',
                      'code': 'OWNED_EMBEDDING_EXECUTOR_NOT_BOUND', 'model_id': None},
        'cross_encoder': {'available': False, 'state': 'BLOCKED_MODEL_NOT_ADMITTED',
                          'code': 'OWNED_RERANKER_EXECUTOR_NOT_BOUND', 'model_id': None},
        'model_execution': 'NOT_RUN', 'fallback_allowed': False,
    }


def run_owned_analysis(*, text=None, analysis_type=None, note_id=None, request=None,
                       is_cancelled=None, context_sections=None):
    """Route analysis through the owned-runtime boundary without provider fallback.

    The current offline candidate loader is evaluation-only. Until a promoted
    runtime is explicitly service-bound, this method must return unavailable
    instead of treating an evaluation candidate or another provider as product
    inference.
    """
    if request is not None:
        if context_sections is not None:
            from lumenis.ai_hub.context_pack import run_budgeted_owned_request
            result = run_budgeted_owned_request(request, optional_sections=context_sections,
                                                is_cancelled=is_cancelled)
        else:
            result = run_owned_request(request, is_cancelled=is_cancelled)
        if note_id is not None:
            result.setdefault("note_id", note_id)
        return result

    if not isinstance(text, str) or not text.strip():
        return {
            "ok": False, "status": "INVALID_INPUT", "code": "ANALYSIS_TEXT_REQUIRED",
            "provider": "owned", "note_id": note_id, "analysis": None,
        }

    runtime = owned_inference_status()
    if runtime.get("available") is not True or runtime.get("service_binding") != "BOUND":
        return {
            "ok": False, "status": "UNAVAILABLE",
            "code": runtime.get("reason") or "OWNED_RUNTIME_NOT_BOUND",
            "provider": "owned", "note_id": note_id, "analysis": None,
            "runtime": runtime,
        }

    # No promoted service invocation contract is currently bound to the Gateway.
    # Keep this explicit even if a candidate-status implementation changes.
    return {
        "ok": False, "status": "UNAVAILABLE", "code": "OWNED_SERVICE_EXECUTOR_NOT_BOUND",
        "provider": "owned", "note_id": note_id, "analysis": None,
        "runtime": runtime,
    }


def run_owned_multimodal_analysis(*, image_bytes, media_type, text, analysis_type,
                                  response_schema, note_id=None):
    """Fail closed at the owned multimodal boundary until its service is bound.

    This entry never probes or falls back to retired local/external vision
    providers. An offline text candidate is not an image-capable product
    executor. A promoted multimodal service must implement this same contract.
    """
    image_valid = False
    if type(image_bytes) is bytes and 0 < len(image_bytes) <= 8 * 1024 * 1024:
        image_valid = (
            media_type == "image/png" and image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
            or media_type == "image/jpeg" and image_bytes.startswith(b"\xff\xd8\xff")
            and image_bytes.endswith(b"\xff\xd9")
            or media_type == "image/webp" and len(image_bytes) >= 12
            and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP"
            and int.from_bytes(image_bytes[4:8], "little") + 8 == len(image_bytes)
        )
    if (not image_valid
            or not isinstance(text, str) or not text.strip() or len(text) > 5000
            or not isinstance(analysis_type, str) or not analysis_type.strip()
            or not isinstance(response_schema, dict)):
        return {
            "ok": False, "status": "INVALID_INPUT", "code": "OWNED_MULTIMODAL_INPUT_INVALID",
            "provider": "owned", "model": None, "note_id": note_id,
            "execution_ref": None, "analysis": None,
        }

    runtime = owned_inference_status()
    if runtime.get("available") is not True or runtime.get("service_binding") != "BOUND":
        return {
            "ok": False, "status": "UNAVAILABLE",
            "code": runtime.get("reason") or "OWNED_RUNTIME_NOT_BOUND",
            "provider": "owned", "model": runtime.get("model_id"), "note_id": note_id,
            "execution_ref": None, "analysis": None, "runtime": runtime,
        }

    return {
        "ok": False, "status": "UNAVAILABLE", "code": "OWNED_MULTIMODAL_EXECUTOR_NOT_BOUND",
        "provider": "owned", "model": runtime.get("model_id"), "note_id": note_id,
        "execution_ref": None, "analysis": None, "runtime": runtime,
    }

def _get_json(url, timeout=1.5):
    """Retained private signature; retired discovery never performs HTTP."""
    raise RuntimeError("RETIRED_PROVIDER_TRANSPORT_DISABLED")

def _installed_hints():
    """Historical discovery interface; no process, filesystem or network probe."""
    return []

def _detect_local():
    """Historical discovery interface; no provider autodiscovery."""
    return None

def _provider_config():
    """Historical provider selection is inert; env/config cannot reactivate it."""
    return None

def ai_status():
    """Describe only the canonical owned route without probing another provider."""
    runtime = owned_inference_status()
    available = runtime.get('available') is True and runtime.get('service_binding') == 'BOUND'
    return {'enabled': available, 'provider': 'owned' if available else 'provider_disabled',
            'model': runtime.get('model_id') or '', 'base_url': '',
            'detail': runtime.get('reason') or runtime.get('state') or 'UNAVAILABLE',
            'runtime': 'owned' if available else 'unavailable', 'installed': available,
            'running': available, 'hints': [], 'owned_status': runtime}

def ai_enabled():
    """Compatibility status follows the canonical owned binding only."""
    return ai_status()["enabled"]


# ============================================================
# Capability metadata for the single owned Gateway route.
# ============================================================
_CAPABILITY_MODEL_MAP = {
    'vision': {
        'provider': 'owned', 'model': None, 'fallback_chain': [],
        'description': 'Owned Gateway multimodal capability; unavailable until a vision executor is bound',
    },
    'web_search': {
        'provider': 'owned', 'model': None, 'fallback_chain': [],
        'description': 'Owned Gateway analysis; verified retrieval Evidence is required',
    },
    'strong_reasoning': {
        'provider': 'owned', 'model': None, 'fallback_chain': [],
        'description': 'Owned Gateway reasoning; unavailable until a promoted runtime is bound',
    },
    'daily': {
        'provider': 'owned', 'model': None, 'fallback_chain': [],
        'description': 'Owned Gateway analysis; unavailable until a promoted runtime is bound',
    },
    'offline_fallback': {
        'provider': 'owned', 'model': None, 'fallback_chain': [],
        'description': 'Legacy capability alias; retired local providers are not called',
    },
}


def select_model_by_capability(capability='daily'):
    """Describe an owned Gateway capability without selecting a fallback provider."""
    cap = (capability or 'daily').lower().strip()
    if cap not in _CAPABILITY_MODEL_MAP:
        cap = 'daily'  # 未知 capability 安全降级到 daily
    entry = dict(_CAPABILITY_MODEL_MAP[cap])
    entry['capability'] = cap
    runtime = owned_inference_status()
    entry['primary_available'] = (
        runtime.get('available') is True and runtime.get('service_binding') == 'BOUND'
    )
    entry['primary_status'] = runtime.get('reason') or runtime.get('state') or 'UNAVAILABLE'
    entry['model'] = runtime.get('model_id')
    entry['fallback_chain'] = []
    return entry


# ============================================================
# 外接云端 AI 发送前脱敏（最高原则：敏感信息不出内网）
# 外部调用仅限用户明确选择的已授权接口；本段不授予模型或网络调用权限。
# 硬脱敏：凭证/令牌/手机号/身份证/邮箱/内网主机/内部端口/本地路径。
# 品牌/客户名默认保留（品牌分析需要真实业务语义），可用 AI_CLOUD_REDACT_BRAND=true
# 配合 AI_REDACT_NAMES=名称1,名称2 做软脱敏。
# ============================================================
_REDACT_PATTERNS = [
    (re.compile(r'(?i)(api[_-]?key|access[_-]?key|secret|password|passwd|pwd|cookie|authorization|bearer|session[_-]?id)\s*[:=]\s*(?:Bearer\s+)?[^\s,;"\']+'), r'\1=[REDACTED]'),
    (re.compile(r'(?i)(xsec_token|access_token|refresh_token|web_session|web_session_v2|sig|sign|ticket)=[A-Za-z0-9%._\-]+'), r'\1=[REDACTED]'),
    (re.compile(r'Bearer\s+[A-Za-z0-9._\-]{8,}'), 'Bearer [REDACTED]'),
    (re.compile(r'(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)'), '[身份证]'),
    (re.compile(r'(?<!\d)\d{16,19}(?!\d)'), '[银行卡号]'),
    (re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)'), '[手机号]'),
    (re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}'), '[邮箱]'),
    (re.compile(r'\b(?:127\.0\.0\.1|localhost|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b'), '[内网主机]'),
    (re.compile(r':(?:8200|8201|8300|8301|9222|11434|10808)\b'), ':[内部端口]'),
    (re.compile(r'[A-Za-z]:\\[^\s"\'<>]+'), '[本地路径]'),
]

def redact_for_cloud(text):
    """对外接云端模型的文本做脱敏；返回脱敏后文本。"""
    if not text:
        return text
    out = str(text)
    for pat, rep in _REDACT_PATTERNS:
        try:
            out = pat.sub(rep, out)
        except Exception:
            continue
    if _env('AI_CLOUD_REDACT_BRAND', '').lower() in ('1', 'true', 'yes', 'on', 'y'):
        for name in [x.strip() for x in _env('AI_REDACT_NAMES', '').split(',') if x.strip()]:
            out = out.replace(name, '[客户]')
    return out


def _call_local_chat(provider, model, base, system, user, temperature, max_tokens, timeout):
    """Preserved tuple contract; no local transport remains executable."""
    _set_call_meta(provider="provider_disabled", model=model or "")
    return None, "provider_disabled"

def _chat(system,user,temperature=0.1,max_tokens=1200,model=None,timeout=None):
    """Legacy callers have no per-call external input contract; remain inert."""
    _set_call_meta(provider="provider_disabled", model=model or "")
    return None, "provider_disabled"

def _ollama_local_chat(system, user_text, image_base64, model, temperature, max_tokens,
                       response_schema=None, *, required_capability='vision', timeout_seconds=None):
    """Compatibility only: never read credentials, discover, load or call a provider."""
    return None, 'provider_disabled', {
        'provider': 'provider_disabled', 'model': None, 'requested_model': model,
        'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': None,
        'status': 'provider_disabled', 'execution': 'NOT_RUN',
        'reason': 'RETIRED_PROVIDER_TRANSPORT_DISABLED',
    }


def _ollama_vision_chat(system, user_text, image_base64, model, temperature, max_tokens, response_schema=None):
    content, status, _meta = _ollama_local_chat(
        system, user_text, image_base64, model, temperature, max_tokens, response_schema,
        required_capability='vision',
    )
    return content, status


def local_structured_chat(system, user, *, response_schema, model=None, max_tokens=2000, timeout_seconds=None):
    """Preserved schema/text interface; owned callers supply the canonical request."""
    return _ollama_local_chat(system, user, None, model, 0, max_tokens,
                              response_schema, required_capability='completion',
                              timeout_seconds=timeout_seconds)


def local_embeddings(texts, *, model=None, timeout_seconds=60):
    """Preserve unavailable embedding tuple without reading provider settings."""
    return None, 'provider_disabled', {
        'provider': 'provider_disabled', 'model': None, 'requested_model': model,
        'prompt_tokens': None, 'duration_ns': None, 'status': 'provider_disabled',
        'execution': 'NOT_RUN', 'reason': 'RETIRED_PROVIDER_TRANSPORT_DISABLED',
    }


def vision_chat(system, user_text, image_base64, model=None, temperature=0.2, max_tokens=2000,
                level='medium', *, local_only=False, response_schema=None):
    """Legacy vision compatibility interface; retired provider routes stay inert.

    New product callers use ``run_owned_multimodal_analysis``. This preserved
    signature never discovers, probes, calls or falls back to a retired local
    or external provider.
    """
    _set_call_meta(provider='provider_disabled', model=model or '')
    return None, 'provider_disabled'

def _json_from_text(text):
    if not text:return None
    text=text.strip()
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text,flags=re.I|re.S).strip()
    try:return json.loads(text)
    except Exception:
        m=re.search(r'\{.*\}',text,re.S)
        if m:
            try:return json.loads(m.group(0))
            except Exception:return None
    return None

def _review_note_scope(rule_analysis):
    """Validate the shape of the caller's server-resolved scope, not authority.

    The source owner must check Canonical membership, Evidence and Permission
    before passing this projection. A model cannot establish subject identity.
    """
    from lumenis.shared.database.scope import normalize_product_domain

    scope = rule_analysis.get('verified_scope')
    if not isinstance(scope, dict) or scope.get('global_scope') is not False:
        return None
    try:
        product, domain = normalize_product_domain(scope.get('product_id'), scope.get('domain_id'))
    except ValueError:
        return None
    key = 'subject_id' if domain == 'cth' else 'brand_focus_id'
    other = 'brand_focus_id' if domain == 'cth' else 'subject_id'
    identity = scope.get(key)
    name = scope.get('display_name')
    aliases = scope.get('aliases', [])
    if (not isinstance(identity, str) or not identity.strip() or identity != identity.strip()
            or scope.get(other) is not None or not isinstance(name, str) or not name.strip()
            or not isinstance(aliases, list) or any(not isinstance(item, str) for item in aliases)):
        return None
    return {'domain_id': domain, 'product_id': product, key: identity,
            'display_name': name, 'aliases': aliases}


def review_note(note, rule_analysis):
    if not rule_analysis.get('verified'):
        return {'relevance':'irrelevant','verification':'rejected','confidence':1.0,'reason':rule_analysis.get('verify_reason','主体不匹配'),'provider':'rule'}
    scope = _review_note_scope(rule_analysis)
    if scope is None:
        return {'relevance': 'relevant', 'verification': 'review', 'confidence': 0.55,
                'fact_basis': 'text', 'summary': rule_analysis.get('summary', ''),
                'risk_reason': rule_analysis.get('summary', '规则引擎结果，待核验'),
                'event_hint': '', 'topics': rule_analysis.get('topics', []), 'provider': 'rule',
                'enhancement_state': 'VERIFIED_SCOPE_REQUIRED'}
    title=note.get('title','') or ''; content=note.get('content','') or ''
    system='''你是当前已核验业务范围的舆情分析员，不得自行假定或替换主体。只根据文本判断，不补造事实。输出严格JSON：{"relevance":"relevant|noise|suspicious","verification":"verified|review|suspicious_fake","sentiment":"positive|neutral|negative","confidence":0-1,"fact_basis":"text|mixed|none","summary":"不超过45字","risk_reason":"不超过60字","event_hint":"不超过30字","topics":["最多5个"]}。positive=明确正向体验/认可；negative=明确投诉/争议/负面体验；neutral=事实、攻略、普通分享；noise=虽然出现主体词但主题与当前已核验范围无关；suspicious=营销、搬运、讽刺、信息不足。单一用户指控必须保持未证实。'''
    user=f'服务端核验主体：{json.dumps(scope,ensure_ascii=False)}\n标题：{title}\n正文：{content[:6000]}\n规则初判：{json.dumps(rule_analysis,ensure_ascii=False)}'
    raw,provider,_=chat(system,user,level='medium',use_cache=True,temperature=0.0,max_tokens=700,pack_id='glm_4_5_air')
    data=_json_from_text(raw)
    if not data:
        return {'relevance':'relevant','verification':'review','confidence':0.55,'fact_basis':'text','summary':rule_analysis.get('summary',''),'risk_reason':rule_analysis.get('summary','规则引擎结果，待核验'),'event_hint':'','topics':rule_analysis.get('topics',[]),'provider':'rule'}
    try:data['confidence']=max(0,min(1,float(data.get('confidence',.5))))
    except:data['confidence']=.5
    data['provider']=provider
    if data.get('relevance')=='irrelevant':data['verification']='rejected'
    return data

def summarize_event(event,notes):
    sample=[{'title':n.get('title',''),'summary':n.get('summary',''),'sentiment':n.get('sentiment','neutral'),'risk':n.get('risk_level','low'),'platform':n.get('source_platform','xiaohongshu')} for n in notes[:15]]
    system='''你是品牌舆情事件分析员。把同一事件的多平台提及凝练成管理层摘要。只输出JSON：{"title":"不超过24字","summary":"不超过90字","fact_status":"confirmed|partially_confirmed|unconfirmed","impact":"positive|neutral|negative","risk_reason":"不超过60字","recommended_action":"不超过70字"}。单一用户指控不得写成已证实事实；没有独立来源必须unconfirmed。'''
    raw,provider,_=chat(system,json.dumps({'event':event,'mentions':sample},ensure_ascii=False),level='medium',use_cache=True,temperature=0.0,max_tokens=700,pack_id='glm_4_5_air')
    data=_json_from_text(raw)
    if data:data['provider']=provider;return data
    from canonical_metrics import sentiment_count as _scf, risk_count as _rcf
    _sci=_scf(notes); _rci=_rcf(notes); neg=_sci['negative']; high=_rci['high']  # Canonical; high不含critical
    return {'title':event.get('title','事件')[:24],'summary':f'相关提及{len(notes)}条，负面{neg}条，高风险{high}条；目前仅能确认存在相关讨论，事实仍需核验。','fact_status':'unconfirmed','impact':'negative' if neg else 'neutral','risk_reason':'存在负面讨论' if neg else '暂未发现明显风险','recommended_action':'核查原始来源并持续观察传播变化。','provider':'rule'}

def _owned_analysis_text(result):
    analysis = result.get('analysis') if isinstance(result, dict) else None
    if isinstance(analysis, str) and analysis.strip():
        return analysis.strip()
    if isinstance(analysis, dict):
        for key in ('reply', 'summary', 'text', 'content', 'translation'):
            value = analysis.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _owned_analysis_complete(result):
    return (
        isinstance(result, dict) and result.get('ok') is True
        and result.get('status') == 'COMPLETED' and result.get('provider') == 'owned'
        and _owned_analysis_text(result) is not None
    )


def test_connection(text):
    result = run_owned_analysis(text=text, analysis_type='connection_test')
    if _owned_analysis_complete(result):
        return {
            'ok': True, 'enabled': True, 'status': 'COMPLETED',
            'provider': 'owned', 'message': 'Owned Gateway analysis completed.',
            'reply': _owned_analysis_text(result),
        }
    result = result if isinstance(result, dict) else {}
    _set_call_meta(provider='owned_unavailable', model='')
    return {
        'ok': False, 'enabled': False,
        'status': result.get('status') if result.get('status') != 'COMPLETED' else 'ERROR',
        'code': result.get('code') or 'OWNED_RUNTIME_NOT_BOUND',
        'provider': 'owned', 'message': 'Owned Gateway is unavailable.', 'reply': None,
    }

def translate_text(text,target='en'):
    if not isinstance(text, str) or not text.strip():
        return ''
    target = target.lower().strip() if isinstance(target, str) else ''
    if target == 'zh':
        return text
    labels = {'en': 'English', 'ko': 'Korean'}
    if target not in labels:
        return ''
    prompt = (
        f'Translate the supplied text into {labels[target]}. Preserve personal, '
        'brand, venue and product names. Return only the translated text.\n\n'
        + text[:3000]
    )
    result = run_owned_analysis(text=prompt, analysis_type='translation')
    if not (isinstance(result, dict) and result.get('ok') is True
            and result.get('status') == 'COMPLETED' and result.get('provider') == 'owned'):
        _set_call_meta(provider='owned_unavailable', model='')
        return ''
    analysis = result.get('analysis')
    if isinstance(analysis, str) and analysis.strip():
        return analysis.strip()
    if isinstance(analysis, dict):
        translated = analysis.get('translation') or analysis.get('text')
        if isinstance(translated, str) and translated.strip():
            return translated.strip()
    _set_call_meta(provider='owned_result_invalid', model='')
    return ''


# ============================================================
# Owned Gateway business helpers; unknown/unavailable results remain explicit.
# 返回结构与旧 ark_llm.sentiment_analyse/generate_summary/extract_keywords 兼容。
# ============================================================

def analyze_sentiment(text, max_len=2000):
    """Return owned sentiment output or explicit unavailable fields; never infer neutral."""
    try:
        max_len = max(1, min(2000, int(max_len)))
    except (TypeError, ValueError, OverflowError):
        max_len = 2000
    if not isinstance(text, str) or not text.strip():
        return {'ok': False, 'status': 'INVALID_INPUT', 'code': 'ANALYSIS_TEXT_REQUIRED',
                'sentiment': None, 'label': None, 'summary': None, 'keywords': None, 'provider': 'owned'}
    result = run_owned_analysis(text=text[:6000], analysis_type='sentiment')
    analysis = result.get('analysis') if isinstance(result, dict) else None
    valid = (
        _owned_analysis_complete(result) and isinstance(analysis, dict)
        and type(analysis.get('sentiment')) is int and analysis.get('sentiment') in (-1, 0, 1)
        and analysis.get('label') in {'positive', 'neutral', 'negative'}
        and isinstance(analysis.get('summary'), str)
        and isinstance(analysis.get('keywords'), list)
        and all(isinstance(item, str) for item in analysis['keywords'])
    )
    if not valid:
        result = result if isinstance(result, dict) else {}
        _set_call_meta(provider='owned_unavailable', model='')
        return {
            'ok': False,
            'status': result.get('status') if result.get('status') != 'COMPLETED' else 'ERROR',
            'code': result.get('code') or 'OWNED_SENTIMENT_RESULT_INVALID',
            'sentiment': None, 'label': None, 'summary': None, 'keywords': None,
            'provider': 'owned',
        }
    _set_call_meta(provider='owned', model=result.get('model'))
    return {
        'ok': True, 'status': 'COMPLETED', 'sentiment': analysis['sentiment'],
        'label': analysis['label'], 'summary': analysis['summary'][:max_len],
        'keywords': analysis['keywords'], 'provider': 'owned',
    }


def generate_summary(text, max_length=200):
    """Return an owned summary or an empty compatibility value on failure."""
    try:
        max_length = max(1, min(2000, int(max_length)))
    except (TypeError, ValueError, OverflowError):
        max_length = 200
    if not isinstance(text, str) or not text.strip():
        return ''
    result = run_owned_analysis(
        text=f'Create a faithful summary with at most {max_length} characters.\n\n{text[:6000]}',
        analysis_type='summary',
    )
    out = _owned_analysis_text(result) if _owned_analysis_complete(result) else None
    if not out:
        _set_call_meta(provider='owned_unavailable', model='')
        return ''
    _set_call_meta(provider='owned', model=result.get('model'))
    return out[:max_length]


def extract_keywords(text, num_keywords=10):
    """Return owned keywords or an empty compatibility value on failure."""
    try:
        num_keywords = max(1, min(30, int(num_keywords)))
    except (TypeError, ValueError, OverflowError):
        num_keywords = 10
    if not isinstance(text, str) or not text.strip():
        return []
    result = run_owned_analysis(
        text=f'Extract up to {num_keywords} source-grounded keywords.\n\n{text[:6000]}',
        analysis_type='keywords',
    )
    analysis = result.get('analysis') if isinstance(result, dict) else None
    keywords = analysis.get('keywords') if isinstance(analysis, dict) else None
    if (not _owned_analysis_complete(result) or not isinstance(keywords, list)
            or any(not isinstance(item, str) or not item.strip() for item in keywords)):
        _set_call_meta(provider='owned_unavailable', model='')
        return []
    _set_call_meta(provider='owned', model=result.get('model'))
    return [item[:30] for item in keywords[:num_keywords]]


def search_enhance(query, context='', max_results=5, model=None, level='medium'):
    """Preserved search interface; acquisition stays with Collector/Source owners."""
    if not str(query or '').strip():
        return {'ok': False, 'error': '查询不能为空', 'results': []}
    return {'ok': False, 'error': 'provider_disabled', 'status': 'provider_disabled',
            'provider': 'provider_disabled', 'results': [], 'execution': 'NOT_RUN',
            'reason': 'RETIRED_PROVIDER_TRANSPORT_DISABLED'}


def generate_report(title, data, report_type="daily"):
    """舆情报告生成（智谱驱动）。返回 markdown 报告字符串；失败回退规则拼装。"""
    system = (f'你是品牌舆情报告撰写助手，根据数据生成{report_type}报告正文（markdown），'
              f'标题围绕「{title}」，结论可追溯到数据，不编造事实。只输出报告正文。')
    raw, provider, _ = chat(system, json.dumps(data, ensure_ascii=False)[:8000], level='high', use_cache=False, temperature=0.4, max_tokens=1500, pack_id='glm_4_5_air')
    out = (raw or '').strip()
    if out:
        return out
    # 规则回退：列出关键数据点
    lines = [f'# {title}', '']
    if isinstance(data, dict):
        for k, v in list(data.items())[:20]:
            lines.append(f'- {k}: {v}')
    return '\n'.join(lines)


# ============================================================
# 高效智谱使用层（2026-09-04）——五层优化：并发 / 缓存 / 模型分层 / 任务分级 / 预算护栏。
# 全部为新增独立入口，现有 _chat / vision_chat / 业务函数零改动（_chat 仅新增可选 timeout 参数）。
# ============================================================
import threading, hashlib

# 任务复杂度分级：LOW 简单快 / MEDIUM 常规 / HIGH 深度 / CRITICAL 最重要
_LEVEL_CONFIG = {
    'low':      {'timeout': 30,  'max_tokens': 200,  'temperature': 0.0},
    'medium':   {'timeout': 60,  'max_tokens': 800,  'temperature': 0.1},
    'high':     {'timeout': 90,  'max_tokens': 2000, 'temperature': 0.2},
    'critical': {'timeout': 120, 'max_tokens': 4000, 'temperature': 0.2},
}
# 强模型分层：HIGH/CRITICAL 用 ZHIPU_STRONG_MODEL（如 glm-4.7）；未配置则沿用默认模型（不强求）
def _strong_model():
    """No legacy environment setting can select a product model."""
    return None

_CACHE_LOCK = threading.Lock()
_CHAT_CACHE = {}          # md5 -> (output, provider)
_CHAT_CACHE_MAX = 512     # 内存缓存上限，防无限增长


def _level_params(level, temperature=None, max_tokens=None, model=None):
    """按任务复杂度解析分级参数（timeout/max_tokens/temperature/model）。"""
    cfg = _LEVEL_CONFIG.get((level or 'medium').lower(), _LEVEL_CONFIG['medium'])
    return {
        'temperature': cfg['temperature'] if temperature is None else temperature,
        'max_tokens': cfg['max_tokens'] if max_tokens is None else max_tokens,
        'model': model or (_strong_model() if (level or '').lower() in ('high', 'critical') else None),
        'timeout': cfg['timeout'],
    }


def _cache_key(system, user, temperature, max_tokens, model):
    h = hashlib.md5()
    h.update((str(system) + '\x00' + str(user) + '\x00' + repr(temperature) + '\x00' + str(max_tokens) + '\x00' + str(model)).encode('utf-8'))
    return h.hexdigest()


def _chat_cache_get(key):
    with _CACHE_LOCK:
        return _CHAT_CACHE.get(key)


def _chat_cache_set(key, out, provider):
    if out is None:
        return
    with _CACHE_LOCK:
        if len(_CHAT_CACHE) >= _CHAT_CACHE_MAX:
            _CHAT_CACHE.clear()
        _CHAT_CACHE[key] = (out, provider)


def _budget_check(pack_id='glm_4_5_air', amount=1):
    """预算护栏：超额返回 False（调用方降级到规则，不硬崩）。配额系统不可用时放行。"""
    try:
        import ai_resource_packs
        q = ai_resource_packs.check_quota(pack_id, amount)
        return bool(q.get('allowed'))
    except Exception:
        return True


def _budget_record(pack_id='glm_4_5_air', amount=1, endpoint='', detail=''):
    try:
        import ai_resource_packs
        ai_resource_packs.record_usage(pack_id, amount, endpoint=endpoint, detail=detail)
    except Exception:
        pass


def chat(system, user, level='medium', use_cache=False, temperature=None, max_tokens=None, model=None, pack_id='glm_4_5_air', track=True, capability='daily', *, external_user_input=False, external_approval=None):
    """Preserved three-tuple signature; no provider fallback or hidden billing.

    Generic prompts lack the canonical actor/domain/source-use request and cannot
    be silently promoted to owned execution. Use run_owned_request explicitly.
    The admitted external API is used only when selected by the current user and the caller identifies direct
    user conversation, never retrieved business/source data. The final adapter
    rechecks the server identity and exact request in Shared Permission; this
    internal input-classification flag is not an authorization grant.
    Existing source-bearing callers require their typed SourceUse contract and
    cannot acquire external transmission permission from global configuration.
    """
    from lumenis.system.ai_gateway import user_api_adapter as _user_api
    if external_user_input is True:
        content, provider, usage = _user_api.chat(
            system, user, temperature=0.2 if temperature is None else temperature,
            max_tokens=1200 if max_tokens is None else max_tokens,
            external_user_input=True, external_approval=external_approval,
        )
        preview = usage.get('approval_request') if isinstance(usage, dict) else None
        audit_id = usage.get('audit_id') if isinstance(usage, dict) else None
        if type(audit_id) is not str or re.fullmatch(r'aud_[0-9a-f]{16}', audit_id) is None:
            audit_id = None
        return content, provider, {
            'provider': provider, 'model': _user_api.config().get('model'),
            'usage': None if preview or audit_id else usage, 'approval_request': preview,
            'audit_id': audit_id,
        }
    return None, 'provider_disabled', _provider_disabled_meta(level, model)


def chat_batch(items, level='medium', max_workers=4, use_cache=False, pack_id='glm_4_5_air'):
    """Preserved batch shape; no executor, retry, quota write or transport."""
    return [{'index': i, 'ok': False, 'output': None,
             'provider': 'provider_disabled', 'error': 'provider_disabled',
             'elapsed_ms': None, 'cache': False} for i, _item in enumerate(items or [])]

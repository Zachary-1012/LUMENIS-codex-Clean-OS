import threading, time
from provider_registry import is_provider_available, provider_status

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

"""广州太古汇本地智能层。

设计目标：无预算也能工作；如果电脑本地已经运行 Ollama / LM Studio / llama.cpp，自动发现并调用本地模型；
否则自动退回可审计的本地规则智能引擎。外部 API Key 永远不是必需项。
"""
import json, os, re, urllib.request, urllib.error, time, shutil, platform
import ai_channel  # [StableChannel] 云端多层稳固通道（熔断+重试+心跳保活）

# ZBC Phase 7: module status markers
MODULE_STATUS = 'ACTIVE_PRIMARY'
AI_ROLE = 'CENTRAL_GATEWAY'  # all AI calls route through _chat/chat; local-first, rule final fallback
PROVIDER_POLICY = 'ollama local primary when configured; cloud providers explicit-only; rule final fallback'

_CACHE = {'ts': 0, 'provider': None, 'model': None, 'base': None}

def _env(name, default=''):
    return os.getenv(name, default).strip()

def _get_json(url, timeout=1.5):
    req=urllib.request.Request(url, headers={'User-Agent':'TaikooMonitor/5.1 local-ai-discovery'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8','replace'))

def _installed_hints():
    """返回本机已发现的本地 AI 运行时线索；不自动启动任何程序。"""
    hints=[]
    if shutil.which('ollama'):
        hints.append({'provider':'ollama','installed':True,'running':False,'detail':'检测到 ollama 命令，可启动 Ollama 服务后自动接入'})
    if platform.system().lower() == 'windows':
        paths=[os.path.expandvars(r'%LOCALAPPDATA%\\LM Studio\\LM Studio.exe'), os.path.expandvars(r'%PROGRAMFILES%\\LM Studio\\LM Studio.exe')]
        if any(os.path.exists(x) for x in paths):
            hints.append({'provider':'lmstudio','installed':True,'running':False,'detail':'检测到 LM Studio，可启动本地 Server 后自动接入'})
    if shutil.which('llama-server') or shutil.which('llama-cpp-server'):
        hints.append({'provider':'llama_cpp','installed':True,'running':False,'detail':'检测到 llama.cpp server，可启动本地接口后自动接入'})
    return hints

def _detect_local():
    """自动探测本机 AI：Ollama > LM Studio > llama.cpp。"""
    preferred=_env('LOCAL_AI_PREFERRED','').lower()
    checks=[]
    if preferred in ('ollama','lmstudio','llama_cpp'):
        checks.append(preferred)
    checks += [x for x in ('ollama','lmstudio','llama_cpp') if x not in checks]
    for p in checks:
        try:
            if p=='ollama':
                base=_env('OLLAMA_BASE_URL','http://127.0.0.1:11434').rstrip('/')
                data=_get_json(base+'/api/tags')
                models=data.get('models') or []
                if models:
                    wanted=_env('OLLAMA_MODEL','qwen2.5-coder:7b-agent')
                    model=wanted or models[0].get('name')
                    if model: return ('ollama',model,base)
            elif p=='lmstudio':
                base=_env('LMSTUDIO_BASE_URL','http://127.0.0.1:1234').rstrip('/')
                data=_get_json(base+'/v1/models')
                models=data.get('data') or []
                if models: return ('lmstudio',_env('LMSTUDIO_MODEL','') or models[0].get('id'),base)
            elif p=='llama_cpp':
                base=_env('LLAMA_CPP_BASE_URL','http://127.0.0.1:8080').rstrip('/')
                data=_get_json(base+'/v1/models')
                models=data.get('data') or []
                if models: return ('llama_cpp',_env('LLAMA_CPP_MODEL','') or models[0].get('id','local'),base)
        except Exception:
            continue
    return None

def _provider_config():
    now=time.time()
    if now-_CACHE['ts']<30:
        detected=(_CACHE['provider'],_CACHE['model'],_CACHE['base']) if _CACHE['provider'] else None
    else:
        requested=_env('AI_PROVIDER','auto').lower()
        detected=None
        if requested in ('ollama','lmstudio','llama_cpp'):
            os.environ['LOCAL_AI_PREFERRED']=requested
            detected=_detect_local()
        elif requested in ('qwen','openai','deepseek','ark','doubao','zhipu','glm'):
            configs={
                'qwen':(_env('DASHSCOPE_API_KEY'),_env('DASHSCOPE_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1'),_env('QWEN_MODEL','qwen-plus')),
                'zhipu':(_env('ZHIPU_API_KEY'),_env('ZHIPU_BASE_URL','https://open.bigmodel.cn/api/paas/v4'),_env('ZHIPU_MODEL','glm-4.5-air')),
                'openai':(_env('OPENAI_API_KEY'),_env('OPENAI_BASE_URL','https://api.openai.com/v1'),_env('OPENAI_MODEL','gpt-4.1-mini')),
                'deepseek':(_env('DEEPSEEK_API_KEY'),_env('DEEPSEEK_BASE_URL','https://api.deepseek.com/v1'),_env('DEEPSEEK_MODEL','deepseek-chat')),
                'ark':(_env('ARK_API_KEY'),_env('ARK_BASE_URL','https://ark.cn-beijing.volces.com/api/v3'),_env('ARK_MODEL','doubao-seed-evolving-latest-version')),
                'doubao':(_env('ARK_API_KEY'),_env('ARK_BASE_URL','https://ark.cn-beijing.volces.com/api/v3'),_env('ARK_MODEL','doubao-seed-evolving-latest-version')),
            }
            provider_name = 'zhipu' if requested == 'glm' else ('ark' if requested in ('ark','doubao') else requested)
            # 'glm' 是 zhipu 的别名（provider_name 已映射），但 configs 无 'glm' 键；
            # 若直接用 requested 取 configs 会 KeyError 且发生在 _chat 的 try 块外导致崩溃（智谱评审 P0B-2）。
            lookup_key = requested if requested in configs else 'zhipu'
            # V2 P0-5: DISABLED provider 显式请求时返回 None，不伪造成功
            if not is_provider_available(lookup_key):
                detected = None
            else:
                key, base, model = configs[lookup_key]
                detected=(provider_name,model,base.rstrip('/')) if key else None
        else:
            # 正式架构 Ollama-only：auto 只自动发现本机模型；本机没有即回退本地规则引擎（离线可跑、
            # 绝不因云端网络挂起而把批量复核卡死）。云端为 Legacy/Optional，默认不自动启用：
            # 确需云端请显式 AI_PROVIDER=<provider>，或置 ALLOW_CLOUD_AI=true 让 auto 纳入已配 Key 的云端。
            detected=_detect_local()
            if not detected and _env('ALLOW_CLOUD_AI','').lower() in ('1','true','yes','on','y'):
                for p,key,base,model in [
                    ('zhipu',_env('ZHIPU_API_KEY'),_env('ZHIPU_BASE_URL','https://open.bigmodel.cn/api/paas/v4'),_env('ZHIPU_MODEL','glm-4.5-air')),
                    ('ark',_env('ARK_API_KEY'),_env('ARK_BASE_URL','https://ark.cn-beijing.volces.com/api/v3'),_env('ARK_MODEL','doubao-pro-32k')),
                ]:
                    if key and is_provider_available(p): detected=(p,model,base.rstrip('/')); break
        _CACHE.update(ts=now,provider=(detected[0] if detected else None),model=(detected[1] if detected else None),base=(detected[2] if detected else None))
    return detected

def ai_status():
    d=_provider_config()
    hints=_installed_hints()
    if d:
        provider,model,base=d
        return {'enabled':True,'provider':provider,'model':model,'base_url':base,'detail':'本机模型自动接入' if provider in ('ollama','lmstudio','llama_cpp') else '云端 Key 已配置','runtime':'local' if provider in ('ollama','lmstudio','llama_cpp') else 'cloud','installed':True,'running':True,'hints':hints}
    return {'enabled':False,'provider':'local_rule','model':'Taikoo Local Intelligence','base_url':'','detail':'未发现可调用的本地模型，当前使用内置本地智能引擎','runtime':'rule','installed':bool(hints),'running':False,'hints':hints}

def ai_enabled(): return bool(_provider_config())


# ============================================================
# P1-5: AI Capability-Based Routing
# 按任务能力自动选择模型，保持 provider-agnostic，主 provider 不可用时自动降级
# ============================================================
_CAPABILITY_MODEL_MAP = {
    'vision': {
        'provider': 'zhipu',
        'model': 'glm-4.6v',
        'fallback_chain': ['zhipu:glm-4.5-air', 'ark', 'ollama'],
        'description': '视觉理解（图片分析/OCR/多模态）',
    },
    'web_search': {
        'provider': 'zhipu',
        'model': 'web-search-pro',
        'fallback_chain': ['zhipu:glm-4.5-air', 'ark', 'ollama'],
        'description': '联网搜索（实时信息/事实核查）',
    },
    'strong_reasoning': {
        'provider': 'zhipu',
        'model': 'glm-5.3',
        'fallback_chain': ['zhipu:glm-4.5-air', 'ark', 'ollama'],
        'description': '强推理（复杂分析/逻辑链/深度研判）',
    },
    'daily': {
        'provider': 'ark',
        'model': 'doubao-lite-4k',
        'fallback_chain': ['zhipu:glm-4.5-air', 'ollama'],
        'description': '日常最小输出（摘要/分类/情绪/轻量对话，豆包 lite 省额度，失败自动降智谱）',
        'thinking_disabled': True,
    },
    'offline_fallback': {
        'provider': 'ollama',
        'model': 'local-model',
        'fallback_chain': ['lmstudio', 'llama_cpp', 'rule'],
        'description': '离线兜底（本地模型/确定性规则）',
    },
}


def select_model_by_capability(capability='daily'):
    """按任务能力选择 AI 模型，返回 {provider, model, fallback_chain, ...}。

    capability 可选值:
      - 'vision'           -> glm-4.6v（智谱视觉）
      - 'web_search'       -> web-search-pro（智谱联网）
      - 'strong_reasoning' -> glm-5.3（智谱强推理）
      - 'daily'            -> glm-4.5-air（智谱日常，关思考）
      - 'offline_fallback' -> ollama 本地模型

    返回 dict 包含 provider, model, fallback_chain, description。
    主 provider 不可用时，调用方应按 fallback_chain 顺序降级。
    不绑定单一模型，保持 provider-agnostic。
    """
    cap = (capability or 'daily').lower().strip()
    if cap not in _CAPABILITY_MODEL_MAP:
        cap = 'daily'  # 未知 capability 安全降级到 daily
    entry = dict(_CAPABILITY_MODEL_MAP[cap])
    entry['capability'] = cap
    # 运行时检查主 provider 可用性，不可用时标记并建议 fallback
    try:
        from provider_registry import is_provider_available, provider_status
        primary = entry['provider']
        entry['primary_available'] = is_provider_available(primary)
        entry['primary_status'] = provider_status(primary)
    except Exception:
        entry['primary_available'] = True
        entry['primary_status'] = 'UNKNOWN'
    return entry


# ============================================================
# 外接云端 AI 发送前脱敏（最高原则：敏感信息不出内网）
# 本地模型(ollama/lmstudio)不出网，不脱敏；仅云端 provider 发送前强制脱敏。
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

def _chat(system,user,temperature=0.1,max_tokens=1200,model=None,timeout=None):
    """AI 对话核心。

    显式选择本地 Provider 时，本地失败只降级到规则，不偷偷切换云端；
    这样本地优先与“云端仅显式启用”边界在运行时真正一致。
    """
    d=_provider_config()
    # CPU Ollama needs a longer, independently bounded window for structured
    # content generation.  Keep the cloud timeout unchanged, and never let a
    # local request fall through to a cloud provider when that window expires.
    if timeout is not None:
        _to = timeout
    elif d and d[0] in ('ollama', 'lmstudio', 'llama_cpp'):
        try:
            _to = int(_env("OLLAMA_TIMEOUT_SECONDS", "180"))
        except (TypeError, ValueError):
            _to = 180
    else:
        try:
            _to = int(_env("AI_TIMEOUT_SECONDS", "90"))
        except (TypeError, ValueError):
            _to = 90
    # 本地模型（ollama/lmstudio/llama_cpp）保持原逻辑，不走云端故障转移
    if d and d[0] in ('ollama','lmstudio','llama_cpp'):
        provider,model_default,base=d
        model = model or model_default
        try:
            req=urllib.request.Request(base+'/api/chat',data=json.dumps({'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user}],'stream':False,'options':{'temperature':temperature,'num_predict':max_tokens}},ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(req,timeout=_to) as resp:
                data=json.loads(resp.read().decode('utf-8','replace'))
            _tu = data.get('usage',{}) or {}
            try:
                _pt = int(_tu.get('prompt_tokens', 0) or data.get('prompt_eval_count', 0) or 0)
                _ct = int(_tu.get('completion_tokens', 0) or data.get('eval_count', 0) or 0)
                _tt = int(_tu.get('total_tokens', 0) or 0) or (_pt + _ct)
            except Exception:
                _pt, _ct, _tt = 0, 0, 0
            _set_call_meta(provider=provider, model=model, prompt_tokens=_pt, completion_tokens=_ct, total_tokens=_tt)
            return data.get('message',{}).get('content'), provider
        except Exception as exc:
            print('[AI] local failed, falling back to local rule:',exc)
            _set_call_meta(provider='rule', model='deterministic_rule', prompt_tokens=0, completion_tokens=0, total_tokens=0)
            return None, 'rule'

    # 云端：多 Provider 故障转移（智谱 L1 → ark L2 → qwen L3 → rule L6）
    system_r, user_r = redact_for_cloud(system), redact_for_cloud(user)
    # V1.0: 构建 cloud fallback 链（zhipu L1 → ark L2 → qwen L3）
    # 本地 Provider（ollama/lmstudio）由 _provider_config 单独处理，不混入 cloud 链
    # 根据传入 model 前缀判断主 provider：最小输出豆包优先，大算力智谱优先
    _model_lower = str(model or '').lower()
    if _model_lower.startswith(('doubao', 'ark-')):
        _preferred = ('ark', 'zhipu', 'qwen')
    else:
        _preferred = ('zhipu', 'ark', 'qwen')
    chain = []
    for _p in _preferred:
        _key_env = {'zhipu': 'ZHIPU_API_KEY', 'ark': 'ARK_API_KEY', 'qwen': 'DASHSCOPE_API_KEY'}.get(_p, '')
        if _key_env and _env(_key_env):
            chain.append(_p)
    if not chain:
        chain = ['zhipu']  # 至少有 zhipu（无 key 时会在 _call_cloud 中报错并 fallback）
    primary = chain[0] if chain else 'zhipu'

    def _call_cloud(prov):
        """对单个云端 Provider 构造请求并调用（复用 StableChannel 重试+熔断+UTF-8）。
        测试期真实出网由 tests/conftest.py 的 socket 出网守卫统一拦截（放行回环、阻断公网），
        不在业务层短路，以免误伤在 urllib 层 mock 的模型路由/参数构造测试。"""
        cfg_map = {
            'zhipu': (_env('ZHIPU_API_KEY',''), _env('ZHIPU_BASE_URL','https://open.bigmodel.cn/api/paas/v4'), _env('ZHIPU_MODEL','glm-4.5-air')),
            'ark': (_env('ARK_API_KEY',''), _env('ARK_BASE_URL','https://ark.cn-beijing.volces.com/api/v3'), _env('ARK_MODEL','doubao-pro-32k')),
            'qwen': (_env('DASHSCOPE_API_KEY',''), _env('DASHSCOPE_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1'), _env('DASHSCOPE_MODEL','qwen-turbo')),
            'openai': (_env('OPENAI_API_KEY',''), _env('OPENAI_BASE_URL','https://api.openai.com/v1'), _env('OPENAI_MODEL','gpt-4o-mini')),
            'deepseek': (_env('DEEPSEEK_API_KEY',''), _env('DEEPSEEK_BASE_URL','https://api.deepseek.com/v1'), _env('DEEPSEEK_MODEL','deepseek-chat')),
        }
        if prov not in cfg_map:
            raise ValueError(f'provider {prov} not configured')
        api_key, base, model_default = cfg_map[prov]
        if not api_key:
            raise ValueError(f'provider {prov} no api key')
        # 备用 Provider 切换为自身默认模型（避免用豆包模型名调智谱接口导致 404）
        m = model or model_default
        if prov != primary and model:
            _ml = str(model).lower()
            _zhipu_family = _ml.startswith(('glm-', 'web-search', 'chatglm'))
            _ark_family = _ml.startswith(('doubao', 'ark-'))
            _qwen_family = _ml.startswith(('qwen', 'qw-', 'qwen2'))
            if (prov == 'zhipu' and not _zhipu_family) or                (prov == 'ark' and not _ark_family) or                (prov == 'qwen' and not _qwen_family):
                m = model_default
        # 备用 Provider 用最小输出（省额度）；主通道用完整 max_tokens
        max_tokens_eff = max_tokens if prov == primary else min(max_tokens, 300)
        payload_obj={'model':m,'temperature':temperature,'max_tokens':max_tokens_eff,'messages':[{'role':'system','content':system_r},{'role':'user','content':user_r}]}
        if prov == 'zhipu' and not str(m).lower().startswith('glm-5.3'):
            payload_obj['thinking'] = {'type': 'disabled'}
        payload=json.dumps(payload_obj,ensure_ascii=False).encode('utf-8')
        proxy_url = {'openai': _env('OPENAI_PROXY','')}.get(prov, '')
        opener = (urllib.request.build_opener(urllib.request.ProxyHandler({'http':proxy_url,'https':proxy_url}))
                  if proxy_url else urllib.request.build_opener(urllib.request.ProxyHandler({})))
        _hdrs = {'Content-Type':'application/json','Authorization':f'Bearer {api_key}'}
        _body = ai_channel.post_with_retry(
            base.rstrip('/') + '/chat/completions', payload, _hdrs,
            timeout=_to, max_attempts=3, opener=opener)
        data = json.loads(_body[0].decode('utf-8','replace'))
        # V1.0: 提取 token usage 并记录（修复 token_usage=0 bug）
        try:
            _u = data.get('usage', {}) or {}
            _pt = int(_u.get('prompt_tokens', 0) or 0)
            _ct = int(_u.get('completion_tokens', 0) or 0)
            _tt = int(_u.get('total_tokens', 0) or 0) or (_pt + _ct)
        except Exception:
            _pt, _ct, _tt = 0, 0, 0
        _set_call_meta(provider=prov, model=m, prompt_tokens=_pt, completion_tokens=_ct, total_tokens=_tt)
        _msg = data['choices'][0]['message']
        _content = (_msg.get('content') or '').strip() or (_msg.get('reasoning_content') or '').strip()
        if not _content:
            raise ValueError('empty response content')
        return _content, prov

    try:
        result, used = ai_channel.route_with_fallback(_call_cloud, providers=chain)
        _cloud_meta = {'token_usage': 0}
        if isinstance(result, tuple) and len(result) >= 3:
            _cloud_meta = result[2] if isinstance(result[2], dict) else _cloud_meta
            result = result[0]
        return result, used
    except Exception as exc:
        print('[AI] all providers failed:', exc)
        _set_call_meta(provider='rule', model='deterministic_rule', prompt_tokens=0, completion_tokens=0, total_tokens=0)
        return None, 'rule'

def vision_chat(system, user_text, image_base64, model=None, temperature=0.2, max_tokens=2000, level='medium'):
    """视觉模型对话（glm-4.6v），支持图片输入。
    分级：level 决定超时（low 60s / medium 90s / high 120s / critical 180s，视觉较慢分档更大）。
    预算：检查并记录 glm_4_6v 视觉资源包（600万 tokens；require_confirmation=False（2026-09-04 用户放开，视觉模型随便用））。
    Args:
        system: 系统提示词
        user_text: 用户文本
        image_base64: 图片 base64 编码（不含 data:image/... 前缀）
        model: 模型名称，None → ZHIPU_VISION_MODEL（默认 glm-4.6v）
        temperature: 温度
        max_tokens: 最大输出 tokens
        level: low/medium/high/critical 任务分级（决定超时）
    Returns:
        (content, provider) 元组
    """
    if model is None:
        model = _env('ZHIPU_VISION_MODEL', 'glm-4.6v')
    api_key = _env('ZHIPU_API_KEY', '')
    base = _env('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
    if not api_key:
        return None, 'no_key'
    # 分级超时：视觉模型较慢，比文本分档更大
    _VISION_TIMEOUT = {'low': 60, 'medium': 90, 'high': 120, 'critical': 180}
    _to = _VISION_TIMEOUT.get((level or 'medium').lower(), 90)
    # 预算估算：图片大小分档（每张图约 1k-10k tokens）；纯文本 500
    est_tokens = 500
    if image_base64:
        try:
            img_bytes = len(image_base64) * 3 // 4
            if img_bytes < 200 * 1024:
                est_tokens = 1500
            elif img_bytes < 1024 * 1024:
                est_tokens = 3000
            elif img_bytes < 3 * 1024 * 1024:
                est_tokens = 6000
            else:
                est_tokens = 10000
        except Exception:
            est_tokens = 1500
    # 预算检查（glm_4_6v 600万 tokens；require_confirmation=False（2026-09-04 用户放开，视觉模型随便用），函数内不重复确认）
    try:
        import ai_resource_packs
        q = ai_resource_packs.check_quota('glm_4_6v', est_tokens)
        if not q.get('allowed'):
            return None, 'budget_blocked'
    except Exception:
        pass
    # 智谱视觉模型输入格式：content 为数组，包含 text 和 image_url
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    user_content = [{'type': 'text', 'text': user_text}]
    if image_base64:
        # 自动判断图片格式
        img_format = 'png'
        if image_base64.startswith('/9j/'):
            img_format = 'jpeg'
        elif image_base64.startswith('R0lGOD'):
            img_format = 'gif'
        elif image_base64.startswith('UklGR'):
            img_format = 'webp'
        user_content.append({
            'type': 'image_url',
            'image_url': {'url': f'data:image/{img_format};base64,{image_base64}'}
        })
    messages.append({'role': 'user', 'content': user_content})
    payload_obj = {
        'model': model,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'messages': messages,
        'thinking': {'type': 'disabled'}
    }
    payload = json.dumps(payload_obj, ensure_ascii=False).encode('utf-8')
    try:
        req = urllib.request.Request(
            base.rstrip('/') + '/chat/completions',
            data=payload,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=_to) as resp:
            data = json.loads(resp.read().decode('utf-8', 'replace'))
        # 预算记录：优先 API 真实 usage.total_tokens，拿不到用估算
        used_tokens = est_tokens
        try:
            _u = data.get('usage', {}) or {}
            used_tokens = int(_u.get('total_tokens', 0) or 0) or est_tokens
        except Exception:
            pass
        try:
            import ai_resource_packs
            ai_resource_packs.record_usage('glm_4_6v', used_tokens, endpoint='vision_chat', detail=(system or '')[:40])
        except Exception:
            pass
        return data['choices'][0]['message']['content'], model
    except Exception as exc:
        print(f'[AI-Vision] {model} failed:', exc)
        return None, 'error'


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

def review_note(note, rule_analysis):
    if not rule_analysis.get('verified'):
        return {'relevance':'irrelevant','verification':'rejected','confidence':1.0,'reason':rule_analysis.get('verify_reason','主体不匹配'),'provider':'rule'}
    title=note.get('title','') or ''; content=note.get('content','') or ''
    system='''你是广州太古汇舆情分析员。只根据文本判断，不补造事实。输出严格JSON：{"relevance":"relevant|noise|suspicious","verification":"verified|review|suspicious_fake","sentiment":"positive|neutral|negative","confidence":0-1,"fact_basis":"text|mixed|none","summary":"不超过45字","risk_reason":"不超过60字","event_hint":"不超过30字","topics":["最多5个"]}。positive=明确正向体验/认可；negative=明确投诉/争议/负面体验；neutral=事实、攻略、普通分享；noise=虽然出现主体词但主题并非广州太古汇；suspicious=营销、搬运、讽刺、信息不足。单一用户指控必须保持未证实。'''
    user=f'标题：{title}\n正文：{content[:6000]}\n规则初判：{json.dumps(rule_analysis,ensure_ascii=False)}'
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

def test_connection(text):
    status=ai_status()
    if not status.get('enabled'):
        return {'enabled':False,'provider':'local_rule','model':status.get('model'),'message':'当前没有可调用的本地模型，系统仍可使用本地规则引擎。','reply':'本地规则引擎已就绪。'}
    raw,provider,_=chat('你是广州太古汇舆情监测系统的本地AI测试助手。只回答一句简短中文。', text, level='low', use_cache=True, temperature=0.0, max_tokens=120, pack_id='glm_4_5_air')
    if raw:
        return {'enabled':True,'provider':provider,'model':status.get('model'),'message':'AI接口连接正常。','reply':raw.strip()}
    return {'enabled':False,'provider':status.get('provider'),'model':status.get('model'),'message':'发现本地AI但调用失败，系统已自动回退本地规则。','reply':'本地规则引擎已接管。'}

def translate_text(text,target='en'):
    if not text:return ''
    if target=='zh':return text
    labels={'en':'English','ko':'Korean'}
    raw,_,_=chat(f'Translate the following Chinese public-opinion text into {labels.get(target,target)}. Preserve Guangzhou Taikoo Hui and brand names. Return translation only.',text[:3000],level='medium',use_cache=True,temperature=0,max_tokens=700,pack_id='glm_4_5_air')
    return (raw or '').strip() or text


# ============================================================
# 云智(ARK) 已停用 → 智谱(zhipu) 驱动的通用 AI 能力（S1 OpenAI 智能功能补强）
# 复用 _chat（智谱网关）+ 脱敏 + 结构化 JSON 解析；失败回退规则/空值，绝不崩溃。
# 返回结构与旧 ark_llm.sentiment_analyse/generate_summary/extract_keywords 兼容。
# ============================================================

def analyze_sentiment(text, max_len=2000):
    """情感/摘要/关键词一站式分析（智谱驱动）。返回 {sentiment:-1/0/1, label, summary, keywords, provider}。"""
    if not text or not text.strip():
        return {'sentiment': 0, 'label': 'neutral', 'summary': '', 'keywords': [], 'provider': 'rule'}
    system = ('你是专业舆情分析助手，只输出严格JSON，不要其他文字。字段：'
              'sentiment(-1负面,0中性,1正面),label(positive/neutral/negative),'
              f'summary(不超过{max_len}字的简要总结),keywords(关键词数组最多10个)。')
    raw, provider, _ = chat(system, str(text)[:6000], level='medium', use_cache=True, temperature=0.1, max_tokens=800, pack_id='glm_4_5_air')
    data = _json_from_text(raw) or {}
    try:
        s = int(data.get('sentiment', 0))
    except Exception:
        s = 0
    label = data.get('label') or ({1: 'positive', -1: 'negative'}.get(s, 'neutral'))
    return {
        'sentiment': s,
        'label': label,
        'summary': str(data.get('summary', ''))[:max_len],
        'keywords': data.get('keywords', []) if isinstance(data.get('keywords', []), list) else [],
        'provider': provider,
    }


def generate_summary(text, max_length=200):
    """文本摘要（智谱驱动）。返回摘要字符串；失败回退前 max_length 字。"""
    if not text or not text.strip():
        return ''
    system = f'你是专业文本摘要助手，生成简洁准确的中文摘要，不超过{max_length}字。只输出摘要内容。'
    raw, provider, _ = chat(system, str(text)[:6000], level='medium', use_cache=False, temperature=0.3, max_tokens=max_length + 100, pack_id='glm_4_5_air')
    out = (raw or '').strip()
    if not out:
        return str(text)[:max_length] + ('...' if len(str(text)) > max_length else '')
    if len(out) > max_length:
        out = out[:max_length]
    return out


def extract_keywords(text, num_keywords=10):
    """关键词提取（智谱驱动）。返回关键词列表；失败回退空列表。"""
    if not text or not text.strip():
        return []
    system = f'你是关键词提取助手，提取{num_keywords}个最重要的关键词。只输出严格JSON：{{"keywords":[...]}}。'
    raw, provider, _ = chat(system, str(text)[:6000], level='medium', use_cache=True, temperature=0.2, max_tokens=400, pack_id='glm_4_5_air')
    data = _json_from_text(raw) or {}
    kws = data.get('keywords', [])
    if isinstance(kws, list):
        return [str(k)[:30] for k in kws[:num_keywords]]
    return []


def search_enhance(query, context='', max_results=5, model=None, level='medium'):
    """
    搜索增强（智谱 web-search-pro 联网搜索模型，真实返回带来源的搜索结果）。
    用于案例库搜索增强、品牌知识库 RAG、产品全局架构检索。
    【安全原则】搜索结果来自智谱真实联网检索且带来源(refer)，不直接写入生产数据库，仅作为参考。

    Args:
        query: 搜索查询
        context: 上下文信息（可选）
        max_results: 最大结果数
        model: 模型名称，None → ZHIPU_SEARCH_MODEL（默认 web-search-pro 官方联网搜索）
        level: low/medium/high/critical 任务分级（决定超时 30/60/90/120s；默认 medium=60s 与旧行为一致）

    Returns:
        dict: {ok, results: [{title, content, source, url}], summary, provider}
    """
    if not query or not query.strip():
        return {'ok': False, 'error': '查询不能为空', 'results': []}

    # 检查 AI 资源包额度（search-std 100次）
    try:
        import ai_resource_packs
        quota = ai_resource_packs.check_quota('search_std', 1)
        if not quota['allowed']:
            return {'ok': False, 'error': f'search-std 额度不足: {quota["reason"]}', 'results': []}
    except Exception:
        pass  # 额度检查失败不阻塞

    # 分级：level 决定超时（low/medium/high/critical）；model 默认读 ZHIPU_SEARCH_MODEL
    if model is None:
        model = _env('ZHIPU_SEARCH_MODEL', 'web-search-pro')
    _to = _LEVEL_CONFIG.get((level or 'medium').lower(), _LEVEL_CONFIG['medium'])['timeout']

    system_prompt = f'''你是一个联网搜索助手。请围绕用户查询联网搜索，返回最多{max_results}条真实、相关的结果。
要求：
1. 搜索并返回真实存在的网页内容，不得编造
2. 优先权威来源（官方网站、权威媒体）
3. 综合搜索结果给出简短摘要'''

    user_prompt = f'查询: {query}\n'
    if context:
        user_prompt += f'上下文: {context[:2000]}\n'
    user_prompt += '请执行联网搜索。'

    try:
        # 使用 web-search-pro 联网搜索模型，直接调用智谱 API
        import os, json, urllib.request, re as _re
        api_key = os.environ.get('ZHIPU_API_KEY', '')
        base_url = os.environ.get('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
        if not api_key:
            return {'ok': False, 'error': '智谱 API Key 未配置', 'results': []}

        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': 0.1,
            'max_tokens': 2000,
            'thinking': {'type': 'disabled'},
        }
        import ai_channel
        resp_bytes, _attempts = ai_channel.post_with_retry(
            base_url.rstrip('/') + '/chat/completions',
            json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key},
            timeout=_to,
            max_attempts=int(_env('AI_HTTP_MAX_RETRIES', '3') or 3),
        )
        data = json.loads(resp_bytes.decode('utf-8', 'replace'))

        # 记录 search-std 使用（100次增强搜索配额）
        try:
            import ai_resource_packs
            ai_resource_packs.record_usage('search_std', 1, endpoint='search_enhance', detail=query[:100])
        except Exception:
            pass

        # 解析 web-search-pro 返回：message.tool_calls[].search_result
        message = data.get('choices', [{}])[0].get('message', {})
        raw_results = []
        for tc in message.get('tool_calls', []):
            if tc.get('type') == 'search_result':
                raw_results.extend(tc.get('search_result') or [])
        if not raw_results:
            # 兜底：content 里可能是纯文本（非联网场景）
            content = message.get('content') or ''
            if content.strip():
                raw_results = [{'title': '搜索结果', 'content': content.strip(), 'refer': '', 'index': 0}]

        # 过滤有效结果
        valid_results = []
        for r in raw_results[:max_results]:
            if isinstance(r, dict) and r.get('title') and r.get('content'):
                title = str(r.get('title', ''))[:100]
                content = str(r.get('content', ''))[:500]
                # 从标题/正文提取来源，如「来源:XXX」「（发布时间：…）」
                source = '智谱搜索'
                m = _re.search(r'来源[:：]\s*([^\s，。；;]+)', content)
                if m:
                    source = m.group(1)[:30]
                valid_results.append({
                    'title': title,
                    'content': content,
                    'source': source,
                    'url': str(r.get('url', ''))[:200],
                })

        # 综合摘要：取前 3 条标题
        summary = '；'.join(str(r.get('title', ''))[:60] for r in raw_results[:3])[:200]

        return {
            'ok': True,
            'results': valid_results,
            'summary': summary,
            'provider': 'zhipu',
            'model': model,
            'query': query,
        }
    except Exception as e:
        return {'ok': False, 'error': str(e), 'results': []}


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
from concurrent.futures import ThreadPoolExecutor, as_completed

# 任务复杂度分级：LOW 简单快 / MEDIUM 常规 / HIGH 深度 / CRITICAL 最重要
_LEVEL_CONFIG = {
    'low':      {'timeout': 30,  'max_tokens': 200,  'temperature': 0.0},
    'medium':   {'timeout': 60,  'max_tokens': 800,  'temperature': 0.1},
    'high':     {'timeout': 90,  'max_tokens': 2000, 'temperature': 0.2},
    'critical': {'timeout': 120, 'max_tokens': 4000, 'temperature': 0.2},
}
# 强模型分层：HIGH/CRITICAL 用 ZHIPU_STRONG_MODEL（如 glm-4.7）；未配置则沿用默认模型（不强求）
def _strong_model():
    """动态读强模型配置（HIGH/CRITICAL 用），避免模块 import 时序问题。"""
    return _env('ZHIPU_STRONG_MODEL', '')

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


def chat(system, user, level='medium', use_cache=False, temperature=None, max_tokens=None, model=None, pack_id='glm_4_5_air', track=True, capability='daily'):
    """增强版智谱调用：任务分级 + 模型分层 + 确定性缓存 + 预算护栏。
    Args:
        level: low/medium/high/critical（决定 timeout/max_tokens/temperature，HIGH 用强模型）
        use_cache: 确定性任务（同输入同输出）开启缓存，命中省 token + 省时间
        temperature/max_tokens/model: 显式覆盖分级默认
        pack_id: 资源包配额（默认 per_call 按次）
        track: 成功调用是否计入预算
    Returns:
        (output, provider, meta)；失败/降级 (None, 'rule'/'budget_blocked', meta)。
    现有 _chat 行为不变；本函数为独立新入口。

    capability: 任务能力路由（默认 'daily'）。调用 select_model_by_capability 自动选模型，
                主 provider 不可用时按 fallback_chain 降级。显式 model 参数优先级高于 capability。
    """
    # 先看真实运行时 Provider。若本地模型已可用，不得把 daily/strong
    # 的云端模型名注入本地 Ollama 请求（例如把 doubao-lite-4k 送给 Ollama）。
    _runtime_local = False
    try:
        _runtime = _provider_config()
        _runtime_local = bool(_runtime and _runtime[0] in ('ollama', 'lmstudio', 'llama_cpp'))
    except Exception:
        _runtime = None

    # P1-5: capability-based 模型选择（显式 model 优先；本地运行时跳过云端选模）
    if model is None and capability and not _runtime_local:
        try:
            cap_cfg = select_model_by_capability(capability)
            if cap_cfg.get('primary_available', True):
                model = cap_cfg.get('model')
        except Exception:
            pass  # capability 路由失败不阻断，沿用 _level_params 默认
    p = _level_params(level, temperature, max_tokens, model)
    if _runtime_local:
        # HIGH/CRITICAL previously inherited a cloud model name from the
        # level config.  The local runtime owns the actual model identity.
        p['model'] = _runtime[1]
        try:
            local_timeout = int(_env('OLLAMA_TIMEOUT_SECONDS', '180'))
        except (TypeError, ValueError):
            local_timeout = 180
        p['timeout'] = max(p['timeout'], local_timeout)
    key = _cache_key(system, user, p['temperature'], p['max_tokens'], p['model']) if use_cache else None
    if use_cache:
        hit = _chat_cache_get(key)
        if hit:
            return hit[0], hit[1], {'cache': True, 'level': level, 'model': p['model']}
    # 云端资源包只约束云端调用；本地 Ollama 不应消耗或污染云端配额。
    if not _runtime_local and not _budget_check(pack_id, 1):
        return None, 'budget_blocked', {'cache': False, 'level': level, 'budget_blocked': True}
    t0 = time.time()
    out, provider = _chat(system, user, temperature=p['temperature'], max_tokens=p['max_tokens'], model=p['model'], timeout=p['timeout'])
    # V1.0: 从 _last_call_meta 获取真实 token 用量（修复 token_usage=0 bug）
    _call_meta = _get_call_meta()
    _real_tokens = int(_call_meta.get('total_tokens', 0) or 0)
    resolved_model = p['model'] or (_call_meta.get('model', '') if _runtime_local else '') or _env('ZHIPU_MODEL', '')
    meta = {'cache': False, 'level': level, 'model': resolved_model,
            'elapsed_ms': int((time.time() - t0) * 1000), 'provider': provider,
            'token_usage': _real_tokens,
            'prompt_tokens': int(_call_meta.get('prompt_tokens', 0) or 0),
            'completion_tokens': int(_call_meta.get('completion_tokens', 0) or 0)}
    if provider not in ('rule', None) and out:
        if use_cache:
            _chat_cache_set(key, out, provider)
        if track and not _runtime_local:
            _budget_record(pack_id, 1, endpoint='chat', detail=(str(system) or '')[:60])
    # V1.0: AI call logging — rule 兜底是正常确定性规则执行，记为 success，不计算在 AI 失败率内
    try:
        import ai_call_logger as _acl
        _is_rule = provider in ('rule', None, 'budget_blocked')
        _model_log = 'deterministic_rule' if _is_rule else (p.get('model') or _env('ZHIPU_MODEL', '') or _call_meta.get('model', ''))
        _tokens_log = 0 if _is_rule else _real_tokens
        # rule 兜底 = 正常降级执行，success=True；真实 AI 调用失败才记 success=False
        _success_log = True if _is_rule else bool(out)
        _fail_reason = '' if _success_log else (f'provider={provider}' if provider else 'unknown')
        _acl.log_call(
            provider=provider or 'rule',
            model=_model_log,
            prompt_version=f'chat:{level}',
            input_hash=_acl.compute_input_hash(system, user, level),
            output=(out or '')[:4000],
            confidence=0.0,
            latency_ms=meta.get('elapsed_ms', 0),
            token_usage=_tokens_log,
            success=_success_log,
            failure_reason=_fail_reason,
        )
    except Exception:
        pass  # logging must never block the AI call chain

    return out, provider, meta


def chat_batch(items, level='medium', max_workers=4, use_cache=False, pack_id='glm_4_5_air'):
    """并发批处理智谱调用（ThreadPoolExecutor；独立任务并发 → 批处理时间从'串行和'变'取最大'）。
    items: 每个元素为 dict{system, user, level?, use_cache?, temperature?, max_tokens?, model?} 或 (system, user) 元组。
    预算护栏：batch 总次数超限 → 整体降级（每项返回 budget_blocked，不硬崩）。
    Returns:
        [{index, ok, output, provider, error, elapsed_ms, cache}]
    """
    if not items:
        return []
    if not _budget_check(pack_id, len(items)):
        return [{'index': i, 'ok': False, 'output': None, 'provider': 'budget_blocked',
                 'error': 'per_call 额度不足', 'elapsed_ms': 0, 'cache': False} for i in range(len(items))]
    results = [None] * len(items)

    def work(idx, item):
        if isinstance(item, dict):
            system = item.get('system', '')
            user = item.get('user', '')
            lv = item.get('level', level)
            uc = item.get('use_cache', use_cache)
            tmp = item.get('temperature')
            mt = item.get('max_tokens')
            md = item.get('model')
        else:
            system, user = item[0], item[1]
            lv, uc, tmp, mt, md = level, use_cache, None, None, None
        t0 = time.time()
        try:
            out, provider, meta = chat(system, user, level=lv, use_cache=uc, temperature=tmp, max_tokens=mt, model=md, pack_id=pack_id)
            results[idx] = {'index': idx, 'ok': provider not in ('rule', 'budget_blocked') and out is not None,
                            'output': out, 'provider': provider, 'error': None,
                            'elapsed_ms': meta.get('elapsed_ms', int((time.time() - t0) * 1000)),
                            'cache': meta.get('cache', False)}
        except Exception as e:
            results[idx] = {'index': idx, 'ok': False, 'output': None, 'provider': 'error',
                            'error': str(e), 'elapsed_ms': int((time.time() - t0) * 1000), 'cache': False}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(work, i, it) for i, it in enumerate(items)]
        for f in as_completed(futs):
            f.result()
    return results

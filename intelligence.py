"""广州太古汇本地智能层。

设计目标：无预算也能工作；如果电脑本地已经运行 Ollama / LM Studio / llama.cpp，自动发现并调用本地模型；
否则自动退回可审计的本地规则智能引擎。外部 API Key 永远不是必需项。
"""
import json, os, re, urllib.request, urllib.error, time, shutil, platform

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
                    wanted=_env('OLLAMA_MODEL','')
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
                    ('qwen',_env('DASHSCOPE_API_KEY'),_env('DASHSCOPE_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1'),_env('QWEN_MODEL','qwen-plus')),
                    ('deepseek',_env('DEEPSEEK_API_KEY'),_env('DEEPSEEK_BASE_URL','https://api.deepseek.com/v1'),_env('DEEPSEEK_MODEL','deepseek-chat')),
                    ('ark',_env('ARK_API_KEY'),_env('ARK_BASE_URL','https://ark.cn-beijing.volces.com/api/v3'),_env('ARK_MODEL','doubao-pro-32k')),
                    ('openai',_env('OPENAI_API_KEY'),_env('OPENAI_BASE_URL','https://api.openai.com/v1'),_env('OPENAI_MODEL','gpt-4.1-mini')),
                ]:
                    if key: detected=(p,model,base.rstrip('/')); break
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

def _chat(system,user,temperature=0.1,max_tokens=1200,model=None):
    d=_provider_config()
    if not d: return None,'rule'
    provider,model_default,base=d
    model = model or model_default
    if provider != 'ollama':  # 仅云端脱敏，本地模型保留原文
        system, user = redact_for_cloud(system), redact_for_cloud(user)
    payload_obj={'model':model,'temperature':temperature,'max_tokens':max_tokens,'messages':[{'role':'system','content':system},{'role':'user','content':user}]}
    payload=json.dumps(payload_obj,ensure_ascii=False).encode('utf-8')
    try:
        if provider=='ollama':
            req=urllib.request.Request(base+'/api/chat',data=json.dumps({'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user}],'stream':False,'options':{'temperature':temperature,'num_predict':max_tokens}},ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(req,timeout=int(_env('AI_TIMEOUT_SECONDS','90'))) as resp:
                data=json.loads(resp.read().decode('utf-8','replace'))
            return data.get('message',{}).get('content'),'ollama'
        # 云端提供商：base已包含/v1或/v3，直接拼接/chat/completions
        api_key_map = {
            'zhipu': _env('ZHIPU_API_KEY', ''),
            'ark': _env('ARK_API_KEY', ''),
            'qwen': _env('DASHSCOPE_API_KEY', ''),
            'openai': _env('OPENAI_API_KEY', ''),
            'deepseek': _env('DEEPSEEK_API_KEY', ''),
        }
        api_key = api_key_map.get(provider, _env('LOCAL_AI_DUMMY_KEY', 'local'))
        # 仅海外 OpenAI 走可配置本地代理(OPENAI_PROXY)；ark/qwen/deepseek 国内端点显式直连，互不影响
        proxy_url = {'openai': _env('OPENAI_PROXY', '')}.get(provider, '')
        opener = (urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}))
                  if proxy_url else urllib.request.build_opener(urllib.request.ProxyHandler({})))
        if provider == 'zhipu':
            # GLM 思考模型默认先输出 reasoning_content 会挤空正式结果；关闭思考，直接出最终 JSON。
            # glm-5.3 系列为"始终思考"模型，任何 thinking 参数都会 400，必须完全不传（思考结果在 reasoning_content）。
            if not str(model).lower().startswith('glm-5.3'):
                payload_obj['thinking'] = {'type': 'disabled'}
            payload = json.dumps(payload_obj, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(base.rstrip('/') + '/chat/completions', data=payload, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}, method='POST')
        with opener.open(req,timeout=int(_env('AI_TIMEOUT_SECONDS','90'))) as resp:
            data=json.loads(resp.read().decode('utf-8','replace'))
        _msg = data['choices'][0]['message']
        # 优先正式 content；glm-5.3 思考模型若 content 为空，回退 reasoning_content 兜底
        _content = (_msg.get('content') or '').strip() or (_msg.get('reasoning_content') or '').strip()
        return _content, provider
    except Exception as exc:
        print('[AI] local/provider failed:',exc)
        return None,'rule'

def vision_chat(system, user_text, image_base64, model='glm-4.6v', temperature=0.2, max_tokens=2000):
    """视觉模型对话（glm-4.6v），支持图片输入。
    Args:
        system: 系统提示词
        user_text: 用户文本
        image_base64: 图片 base64 编码（不含 data:image/... 前缀）
        model: 模型名称，默认 glm-4.6v
        temperature: 温度
        max_tokens: 最大输出 tokens
    Returns:
        (content, provider) 元组
    """
    api_key = _env('ZHIPU_API_KEY', '')
    base = _env('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
    if not api_key:
        return None, 'no_key'
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
        with urllib.request.urlopen(req, timeout=int(_env('AI_TIMEOUT_SECONDS', '120'))) as resp:
            data = json.loads(resp.read().decode('utf-8', 'replace'))
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
    raw,provider=_chat(system,user,0.0,700)
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
    raw,provider=_chat(system,json.dumps({'event':event,'mentions':sample},ensure_ascii=False),0.0,700)
    data=_json_from_text(raw)
    if data:data['provider']=provider;return data
    neg=sum(1 for n in notes if n.get('sentiment')=='negative'); high=sum(1 for n in notes if n.get('risk_level')=='high')
    return {'title':event.get('title','事件')[:24],'summary':f'相关提及{len(notes)}条，负面{neg}条，高风险{high}条；目前仅能确认存在相关讨论，事实仍需核验。','fact_status':'unconfirmed','impact':'negative' if neg else 'neutral','risk_reason':'存在负面讨论' if neg else '暂未发现明显风险','recommended_action':'核查原始来源并持续观察传播变化。','provider':'rule'}

def test_connection(text):
    status=ai_status()
    if not status.get('enabled'):
        return {'enabled':False,'provider':'local_rule','model':status.get('model'),'message':'当前没有可调用的本地模型，系统仍可使用本地规则引擎。','reply':'本地规则引擎已就绪。'}
    raw,provider=_chat('你是广州太古汇舆情监测系统的本地AI测试助手。只回答一句简短中文。', text, 0.0, 120)
    if raw:
        return {'enabled':True,'provider':provider,'model':status.get('model'),'message':'AI接口连接正常。','reply':raw.strip()}
    return {'enabled':False,'provider':status.get('provider'),'model':status.get('model'),'message':'发现本地AI但调用失败，系统已自动回退本地规则。','reply':'本地规则引擎已接管。'}

def translate_text(text,target='en'):
    if not text:return ''
    if target=='zh':return text
    labels={'en':'English','ko':'Korean'}
    raw,_=_chat(f'Translate the following Chinese public-opinion text into {labels.get(target,target)}. Preserve Guangzhou Taikoo Hui and brand names. Return translation only.',text[:3000],0,700)
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
    raw, provider = _chat(system, str(text)[:6000], 0.1, 800)
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
    raw, provider = _chat(system, str(text)[:6000], 0.3, max_length + 100)
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
    raw, provider = _chat(system, str(text)[:6000], 0.2, 400)
    data = _json_from_text(raw) or {}
    kws = data.get('keywords', [])
    if isinstance(kws, list):
        return [str(k)[:30] for k in kws[:num_keywords]]
    return []


def search_enhance(query, context='', max_results=5, model='search-std'):
    """
    搜索增强（智谱 search-std 模型）。
    用于案例库搜索增强、品牌知识库 RAG、产品全局架构检索。
    【安全原则】搜索结果必须有来源标注，不直接写入生产数据库，仅作为参考。

    Args:
        query: 搜索查询
        context: 上下文信息（可选）
        max_results: 最大结果数
        model: 模型名称，默认 search-std

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

    system_prompt = f'''你是搜索增强助手。根据用户查询和上下文，返回{max_results}条最相关的搜索结果。
要求：
1. 每条结果必须包含：title(标题)、content(内容摘要)、source(来源)、url(链接，如无可为空)
2. 结果必须真实可查，不得编造
3. 优先返回权威来源（官方网站、权威媒体、学术论文）
4. 只输出严格JSON格式：{{"results":[{{"title":"","content":"","source":"","url":""}}],"summary":""}}
5. summary 是对所有结果的综合摘要，不超过200字'''

    user_prompt = f'查询: {query}\n'
    if context:
        user_prompt += f'上下文: {context[:2000]}\n'
    user_prompt += '请返回搜索结果。'

    try:
        # 使用 search-std 模型（通过 _chat 调用，但模型名需要临时替换）
        # 由于 _chat 使用默认模型，这里直接调用智谱 API
        import os, json, urllib.request
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
        req = urllib.request.Request(
            base_url.rstrip('/') + '/chat/completions',
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8', 'replace'))
        raw = data['choices'][0]['message']['content']

        # 记录 search-std 使用
        try:
            import ai_resource_packs
            ai_resource_packs.record_usage('search_std', 1, endpoint='search_enhance', detail=query[:100])
        except Exception:
            pass

        # 解析结果
        result_data = _json_from_text(raw) or {}
        results = result_data.get('results', [])
        if not isinstance(results, list):
            results = []
        # 过滤无效结果
        valid_results = []
        for r in results[:max_results]:
            if isinstance(r, dict) and r.get('title') and r.get('content'):
                valid_results.append({
                    'title': str(r.get('title', ''))[:100],
                    'content': str(r.get('content', ''))[:500],
                    'source': str(r.get('source', '未知'))[:50],
                    'url': str(r.get('url', ''))[:200],
                })

        return {
            'ok': True,
            'results': valid_results,
            'summary': str(result_data.get('summary', ''))[:200],
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
    raw, provider = _chat(system, json.dumps(data, ensure_ascii=False)[:8000], 0.4, 1500)
    out = (raw or '').strip()
    if out:
        return out
    # 规则回退：列出关键数据点
    lines = [f'# {title}', '']
    if isinstance(data, dict):
        for k, v in list(data.items())[:20]:
            lines.append(f'- {k}: {v}')
    return '\n'.join(lines)

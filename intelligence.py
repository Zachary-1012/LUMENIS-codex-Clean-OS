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
            key,base,model=configs[requested]
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

def _chat(system,user,temperature=0.1,max_tokens=1200):
    d=_provider_config()
    if not d: return None,'rule'
    provider,model,base=d
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
            # GLM 思考模型默认先输出 reasoning_content 会挤空正式结果；关闭思考，直接出最终 JSON
            payload_obj['thinking'] = {'type': 'disabled'}
            payload = json.dumps(payload_obj, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(base.rstrip('/') + '/chat/completions', data=payload, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + api_key}, method='POST')
        with opener.open(req,timeout=int(_env('AI_TIMEOUT_SECONDS','90'))) as resp:
            data=json.loads(resp.read().decode('utf-8','replace'))
        return data['choices'][0]['message']['content'],provider
    except Exception as exc:
        print('[AI] local/provider failed:',exc)
        return None,'rule'

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

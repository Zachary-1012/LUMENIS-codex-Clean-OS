# -*- coding: utf-8 -*-
"""案例 AI 评估：AI 为增强层，失败回退本地模板，不决定生产事实。"""
import json
import os
import time
import urllib.request

_ZHIPU_KEY = os.environ.get('ZHIPU_API_KEY', '').strip()
_ZHIPU_URL = os.environ.get('ZBC_ZHIPU_URL', 'https://open.bigmodel.cn/api/paas/v4/chat/completions')
_ZHIPU_MODEL = os.environ.get('ZBC_ZHIPU_MODEL', 'glm-4.5-air')


def _chat(prompt, max_tokens=1000):
    if not _ZHIPU_KEY:
        return ''
    body = {'model': _ZHIPU_MODEL, 'messages': [{'role': 'user', 'content': prompt}],
            'stream': True, 'thinking': {'type': 'disabled'}, 'max_tokens': max_tokens}
    data = json.dumps(body).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(_ZHIPU_URL, data=data, headers={
                'Content-Type': 'application/json', 'Authorization': 'Bearer ' + _ZHIPU_KEY})
            with urllib.request.urlopen(req, timeout=75) as r:
                buf = b''
                while True:
                    chunk = r.read(4096)
                    if not chunk: break
                    buf += chunk
            out=[]
            for line in buf.decode('utf-8',errors='ignore').splitlines():
                line=line.strip()
                if line.startswith('data:') and line != 'data: [DONE]':
                    try:
                        delta=json.loads(line[5:].strip())['choices'][0].get('delta',{})
                        if delta.get('content'): out.append(delta['content'])
                    except Exception: pass
            result=''.join(out).strip()
            if result: return result
        except Exception as e:
            print('[case_ai_evaluate] attempt',attempt,'err',e)
            time.sleep(3)
    return ''


def _summarize_case(case):
    parts=[]
    for label,key,limit in [('案例','case_title',80),('品牌','brand',40),('行业','industry',40),('类型','case_type',40)]:
        if case.get(key): parts.append(label+':'+str(case[key])[:limit])
    for f in ('basic_info','strategy','results'):
        v=case.get(f)
        if v:
            if isinstance(v,(list,dict)): v=json.dumps(v,ensure_ascii=False)
            parts.append(('结果:' if f=='results' else '')+str(v)[:200])
    return '；'.join(parts)[:600]


def evaluate_case(case):
    summary=_summarize_case(case)
    from case_templates import match_templates
    kw=' '.join(filter(None,[str(case.get('case_title','')),str(case.get('case_type','')),str(case.get('industry',''))]))
    templates=match_templates(kw,limit=2)
    ai={'enabled':False,'score':{},'advice':'','error':''}
    if _ZHIPU_KEY:
        raw=_chat('你是品牌营销与舆情危机评估专家。评估以下营销案例，输出JSON（不要其他文字）：{"impact":0-10,"innovation":0-10,"replicability":0-10,"risk":0-10,"advice":"中文建议60字内"}。案例：'+summary,700)
        if raw:
            try:
                d=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
                ai={'enabled':True,'score':{'impact':_clamp(d.get('impact')),'innovation':_clamp(d.get('innovation')),'replicability':_clamp(d.get('replicability')),'risk':_clamp(d.get('risk')),'overall':round((_num(d.get('impact'))+_num(d.get('innovation'))+_num(d.get('replicability'))+(10-_num(d.get('risk'))))/4,1)},'advice':str(d.get('advice',''))[:200],'error':''}
            except Exception as e: ai['error']='AI解析失败: '+str(e)[:80]
    return {'ai':ai,'templates':templates}


def _num(v):
    try: return float(v)
    except Exception: return 5.0

def _clamp(v):
    try: return min(10.0,max(0.0,float(v)))
    except Exception: return 5.0

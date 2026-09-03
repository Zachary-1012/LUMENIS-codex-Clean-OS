# -*- coding: utf-8 -*-
"""
case_ai_evaluate.py — 案例库 AI 评估（智谱增强层）
对单个案例做 4 维评分（影响力/创新性/可复制性/风险系数）+ 推荐处置模板 + 建议
性质：纯增量增强层；AI 失败不阻断，回退到本地模板匹配结果
智谱调用策略：stream + thinking disabled + 精简输入 + timeout 75 + 重试2
"""
import json
import time
import io
import urllib.request

# 从 .env 读 ZHIPU_API_KEY
_ZHIPU_KEY = None
try:
    for line in io.open(r'D:\Taikoo-monitor-new\.env', encoding='utf-8', errors='ignore'):
        if line.startswith('ZHIPU_API_KEY'):
            _ZHIPU_KEY = line.split('=', 1)[1].strip().strip('"').strip("'")
            break
except Exception:
    pass

_ZHIPU_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'


def _chat(prompt, max_tokens=1000):
    """智谱 stream 调用（thinking disabled + 精简输入，避免挂起）"""
    if not _ZHIPU_KEY:
        return ''
    body = {
        "model": "glm-4.5-air",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "thinking": {"type": "disabled"},
        "max_tokens": max_tokens,
    }
    data = json.dumps(body).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                _ZHIPU_URL, data=data,
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + _ZHIPU_KEY})
            with urllib.request.urlopen(req, timeout=75) as r:
                buf = b""
                while True:
                    chunk = r.read(4096)
                    if not chunk:
                        break
                    buf += chunk
            text = buf.decode('utf-8', errors='ignore')
            out = []
            for line in text.splitlines():
                line = line.strip()
                if line.startswith('data:') and line != 'data: [DONE]':
                    try:
                        d = json.loads(line[5:].strip())
                        delta = d['choices'][0].get('delta', {})
                        c = delta.get('content')
                        if c:
                            out.append(c)
                    except Exception:
                        pass
            res = ''.join(out).strip()
            if res:
                return res
        except Exception as e:
            print('[case_ai_evaluate] attempt', attempt, 'err', e)
            time.sleep(3)
    return ''


def _summarize_case(case):
    """精简案例为评估输入（控制 token）"""
    parts = []
    if case.get('case_title'):
        parts.append('案例:' + str(case['case_title'])[:80])
    if case.get('brand'):
        parts.append('品牌:' + str(case['brand'])[:40])
    if case.get('industry'):
        parts.append('行业:' + str(case['industry'])[:40])
    if case.get('case_type'):
        parts.append('类型:' + str(case['case_type'])[:40])
    for f in ('basic_info', 'strategy'):
        v = case.get(f)
        if v:
            if isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            parts.append(str(v)[:200])
    if case.get('results'):
        v = case['results']
        if isinstance(v, (list, dict)):
            v = json.dumps(v, ensure_ascii=False)
        parts.append('结果:' + str(v)[:150])
    return '；'.join(parts)[:600]


def evaluate_case(case):
    """对案例做 AI 评估，返回 4 维评分 + 建议 + 推荐模板"""
    summary = _summarize_case(case)
    # 1) 本地模板匹配（不依赖 AI，作为基础结果）
    from case_templates import match_templates
    kw = ' '.join(filter(None, [
        str(case.get('case_title', '')),
        str(case.get('case_type', '')),
        str(case.get('industry', '')),
    ]))
    templates = match_templates(kw, limit=2)

    # 2) 智谱 AI 评估（增强层，失败不阻断）
    ai = {'enabled': False, 'score': {}, 'advice': '', 'error': ''}
    if _ZHIPU_KEY:
        prompt = (
            '你是品牌营销与舆情危机评估专家。评估以下营销案例，输出JSON（不要其他文字）：'
            '{"impact":0-10,"innovation":0-10,"replicability":0-10,"risk":0-10,"advice":"中文建议60字内"}。'
            '案例：' + summary
        )
        raw = _chat(prompt, 700)
        if raw:
            try:
                # 提取 JSON
                s = raw[raw.find('{'): raw.rfind('}') + 1]
                d = json.loads(s)
                ai = {
                    'enabled': True,
                    'score': {
                        'impact': _clamp(d.get('impact')),
                        'innovation': _clamp(d.get('innovation')),
                        'replicability': _clamp(d.get('replicability')),
                        'risk': _clamp(d.get('risk')),
                        'overall': round(
                            (_num(d.get('impact')) + _num(d.get('innovation')) + _num(d.get('replicability')) + (10 - _num(d.get('risk')))) / 4, 1),
                    },
                    'advice': str(d.get('advice', ''))[:200],
                    'error': '',
                }
            except Exception as e:
                ai['error'] = 'AI解析失败: ' + str(e)[:80]
    return {'ai': ai, 'templates': templates}


def _num(v):
    try:
        return float(v)
    except Exception:
        return 5.0


def _clamp(v):
    try:
        return min(10.0, max(0.0, float(v)))
    except Exception:
        return 5.0

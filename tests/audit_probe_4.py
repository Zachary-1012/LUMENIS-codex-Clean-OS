# -*- coding: utf-8 -*-
"""只读审计探查4：主体LOCK/时间口径/事件模型/传播主体/业务模块/AI解耦。"""
import os,re,glob
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));os.chdir(ROOT)
OUT=os.path.join(ROOT,'docs','audit_evidence');os.makedirs(OUT,exist_ok=True)
buf=[];p=buf.append
SKIP=('.venv','node_modules','__pycache__','audit_evidence','_zbmp_docs','backups','edge-cdp')
def files(exts=('.py',)):
    for f in glob.glob('**/*',recursive=True):
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in exts and not any(s in f.replace('\\','/') for s in SKIP):
            yield f
def count_hit(rx):
    rx=re.compile(rx); out={}
    for f in files():
        t=open(f,encoding='utf-8',errors='ignore').read()
        n=len(rx.findall(t))
        if n: out[f]=n
    return out
def show(title,rx,limit=30):
    p(f'\n## {title}')
    h=count_hit(rx)
    if not h: p('  (无证据)')
    for f,n in sorted(h.items(),key=lambda x:-x[1])[:limit]: p(f'  {n:3d}  {f}')

show('1 SUBJECT_WORDS / EXCLUDE 定义与引用',r'SUBJECT_WORDS|SUBJECT_EXCLUDE_WORDS')
show('2 subject_hit() 引用',r'subject_hit')
show('3 _subject_sql_and_values 引用',r'_subject_sql_and_values|subject_sql')
show('4 aggregate_events 引用',r'aggregate_events')
show('5 publish_datetime / captured_at 代码使用',r'publish_datetime|captured_at')
show('6 event_date 代码使用',r'event_date')
show('7 三类事件 营销/传播/舆情 event_type',r'营销事件|传播事件|舆情事件|event_type')
show('8 传播主体 KOL/KOS/KOC/主体画像',r'\bKOS\b|\bKOL\b|\bKOC\b|传播主体|subject_profile|六维')
show('9 content_type / subject_type',r'content_type|subject_type')
show('10 event_relation / lifecycle 事件关系/生命周期',r'event_relation|lifecycle|事件关系|生命周期')
show('11 品牌营销案例库 pr_case',r'pr_case|品牌营销案例|case_engine')
show('12 话题监测 topic_campaign / 15周年',r'topic_campaign|15周年|周年')
show('13 报告 daily/weekly/monthly/annual',r'build_daily_report|weekly|monthly|annual|年报|周报|月报')
show('14 品牌对标 / 消费者需求',r'品牌对标|竞品|consumer|消费者需求|consumer_need')
show('15 AI 模块引用分布',r'\bark_llm\b|ollama|local_ai|ai_gateway|import ai_|from ai_|intelligence')
# 核心模块是否硬依赖 AI（import 不在 try 内）
p('\n## 16 关键业务模块顶部 import AI 情况（判断AI解耦）')
for f in ['data_collector.py','risk_engine.py','daily_report.py','collector_automation.py','xhs_cookie_bridge.py']:
    if not os.path.exists(f): p(f'  {f} 不存在'); continue
    ls=open(f,encoding='utf-8',errors='ignore').read().split('\n')
    hits=[(i+1,l.strip()) for i,l in enumerate(ls[:60]) if re.search(r'import.*(ark|ollama|ai_|intelligence|llm)',l,re.I)]
    p(f'  {f}: '+(str(hits) if hits else '顶部无AI导入(解耦)'))
# app.py 中 ark/ollama 是否 try 包裹
ap=open('app.py',encoding='utf-8',errors='ignore').read().split('\n')
p('\n## 17 app.py AI import 上下文(50-60行)')
for i in range(45,61):
    if i-1<len(ap): p(f'  {i}: {ap[i-1][:110]}')
open(os.path.join(OUT,'04_model_ai.txt'),'w',encoding='utf-8').write('\n'.join(buf))
print('written 04 lines',len(buf))

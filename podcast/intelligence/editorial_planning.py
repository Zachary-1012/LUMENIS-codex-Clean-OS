"""Explainable guest vectors and human-gated editable interview planning.

No model, web lookup, inferred guest facts, or automatic guest selection.
SavedWork remains the only persistence/version/authorization owner.
"""
from __future__ import annotations
from collections import Counter
import hashlib,json,math,re,unicodedata

GATES=('unique_experience_public_value','expression_and_willingness','resonance')
DIMENSIONS=('IP定位','受众承诺','选题架构','嘉宾架构','嘉宾选题匹配','问题架构','追问深度','故事密度',
            '冲突密度','情绪密度','洞察密度','时长架构','开场钩子','章节架构','金句切片产出','分发包装',
            '跨平台转译','受众反应','增长与时长序列','有证据的制作成本','失败案例','可复用性','因果置信度','证据质量')
SOP=('约人','提纲','拍摄间','开场','叫停','追问','结束','剪辑')


def _text(value,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(unicodedata.category(c).startswith('C') and c not in '\n\t' for c in value):
        raise ValueError('PODCAST_EDITORIAL_TEXT_INVALID')
    return value


def _digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()


def _guests(values):
    if not isinstance(values,list) or not 1<=len(values)<=200:raise ValueError('PODCAST_GUEST_LIBRARY_INVALID')
    guests=[];seen=set()
    for raw in values:
        if not isinstance(raw,dict) or set(raw)!={'guest_id','name','domains','prior_programmes','viewpoints','source_refs'}:
            raise ValueError('PODCAST_GUEST_RECORD_INVALID')
        guest_id=_text(raw['guest_id'],100)
        if not re.fullmatch(r'[A-Za-z0-9_-]+',guest_id) or guest_id in seen:raise ValueError('PODCAST_GUEST_ID_INVALID')
        seen.add(guest_id);record={'guest_id':guest_id,'name':_text(raw['name'],100)}
        for field in ('domains','prior_programmes','viewpoints','source_refs'):
            if not isinstance(raw[field],list) or len(raw[field])>30:raise ValueError('PODCAST_GUEST_RECORD_INVALID')
            record[field]=[_text(value,1000) for value in raw[field]]
        if not any(record[field] for field in ('domains','prior_programmes','viewpoints')):raise ValueError('PODCAST_GUEST_PROFILE_EMPTY')
        guests.append(record)
    return guests


def _terms(text):
    terms=re.findall(r'[a-z0-9]+',text.lower())
    for run in re.findall(r'[\u3400-\u9fff]+',text):
        terms.extend(run[i:i+2] for i in range(len(run)-1))
        if len(run)==1:terms.append(run)
    return Counter(terms)


def rank_guests(topic,guests,*,limit=10):
    topic=_text(topic,2000);guests=_guests(guests)
    if type(limit) is not int or not 1<=limit<=50:raise ValueError('PODCAST_GUEST_LIMIT_INVALID')
    counts=[_terms(topic)]+[_terms('\n'.join(g['domains']+g['prior_programmes']+g['viewpoints'])) for g in guests]
    df=Counter(term for row in counts for term in row);n=len(counts)
    def vector(row):
        weighted={term:(1+math.log(count))*(math.log((1+n)/(1+df[term]))+1) for term,count in row.items()}
        length=math.sqrt(sum(value*value for value in weighted.values()))
        return {term:value/length for term,value in weighted.items()} if length else {}
    vectors=[vector(row) for row in counts];query=vectors[0];ranked=[]
    for guest,features in zip(guests,vectors[1:]):
        contributions=sorted(((term,value*query[term]) for term,value in features.items() if term in query),key=lambda item:(-item[1],item[0]))
        score=sum(value for _,value in contributions)
        ranked.append({'guest_id':guest['guest_id'],'name':guest['name'],'similarity':round(score,8),
                       'matching_terms':[{'term':term,'contribution':round(value,8)} for term,value in contributions[:12]],
                       'reason':'仅依据用户提供资料的共享词项与稀疏向量相似度' if contributions else '没有共享词项，无法提供匹配依据',
                       'source_refs':guest['source_refs'],'facts_status':'user_supplied_not_independently_verified'})
    ranked.sort(key=lambda row:(-row['similarity'],row['guest_id']))
    return {'method':'character_bigram_word_tfidf_cosine_v1','semantic_embedding':False,'automatic_selection':False,
            'topic':topic,'input_hash':_digest({'topic':topic,'guests':guests}),'candidates':ranked[:limit]}


def build_editorial_preview(topic,guests,*,selected_guest_id=None,gates=None,include_sop=False):
    topic=_text(topic,2000);guests=_guests(guests);ranking=rank_guests(topic,guests)
    if type(include_sop) is not bool:raise ValueError('PODCAST_SOP_OPTION_INVALID')
    if selected_guest_id is None:
        return {'state':'selection_required','ranking':ranking,'automatic_selection':False}
    selected=next((g for g in guests if g['guest_id']==selected_guest_id),None)
    if selected is None:raise ValueError('PODCAST_GUEST_SELECTION_INVALID')
    if not isinstance(gates,dict) or set(gates)!=set(GATES):raise ValueError('PODCAST_MANUAL_GATES_REQUIRED')
    checked={}
    for key in GATES:
        item=gates[key]
        if not isinstance(item,dict) or set(item)!={'decision','note'} or not isinstance(item['decision'],str) or item['decision'] not in {'pass','fail','unknown'}:
            raise ValueError('PODCAST_MANUAL_GATE_INVALID')
        checked[key]={'decision':item['decision'],'note':_text(item['note'],2000)}
    blocked=[key for key,value in checked.items() if value['decision']!='pass']
    if blocked:return {'state':'manual_gate_blocked','ranking':ranking,'selected_guest_id':selected_guest_id,'gates':checked,'blocked_gates':blocked,'outline':None}
    mainline=[{'id':f'main-{i+1}','question':question,'user_answer':'','followups':followups} for i,(question,followups) in enumerate([
        ('关于这个选题，你最想从哪一次亲身经历讲起？',['当时在哪里？','具体发生了什么？','哪些细节可以核实？']),
        ('那次经历里的关键选择是什么？',['还有哪些备选？','为什么当时这样决定？','代价由谁承担？']),
        ('有没有让事情改变方向的时刻？',['变化前后有什么可观察差异？','还有其他解释吗？']),
        ('你遇到过什么失败或反例？',['它挑战了哪一个判断？','哪些结论因此不能推广？']),
        ('这段经历对听众有什么公共价值？',['适用于谁？','在哪些条件下不适用？','有哪些可靠资料可供核对？']),
        ('如果回到开始，你会保留或改变什么？',['哪些仍然不确定？','有什么重要背景我们遗漏了？'])])]
    subtext=[{'id':f'subtext-{i+1}','question':question,'user_answer':''} for i,question in enumerate([
        '当时的感受与现在回看有什么不同？','你最在意但还没有展开的价值或顾虑是什么？',
        '这个选择如何影响你对自己和他人的理解？','哪些内容你不愿公开，哪些表述需要录后再次确认？'])]
    outline={'topic':topic,'guest_id':selected_guest_id,'mainline':mainline,'subtext':subtext,
             'research_checks':[{'dimension':name,'note':'','evidence_status':'not_observed'} for name in DIMENSIONS],
             'optional_recording_sop':list(SOP) if include_sop else [],'template_origin':'repository_liangzi_benchmark_mechanisms_not_surface_style_copy'}
    payload={'guest_library':guests,'guest_matching':ranking,'guest_selection':{'guest_id':selected_guest_id,'selection_method':'explicit_user_selection'},
             'manual_gates':checked,'interview_outline':outline,'facts_status':'user_supplied_not_independently_verified'}
    markdown=f'# 前采提纲：{topic}\n\n嘉宾：{selected["name"]}\n\n资料与人工Gate由用户提供，尚未独立核实。\n\n## 明线\n'+''.join(f'\n{i+1}. {item["question"]}\n'+''.join(f'   - {x}\n' for x in item['followups']) for i,item in enumerate(mainline))+'\n## 暗线\n'+''.join(f'\n- {item["question"]}\n' for item in subtext)
    return {'state':'editable_draft','ranking':ranking,'selected_guest_id':selected_guest_id,'manual_gates':checked,
            'automatic_selection':False,'source_facts_verified':False,'input_hash':_digest(payload),
            'saved_work_draft':{'title':('前采提纲：'+topic)[:300],'kind':'podcast_episode','markdown':markdown,'payload':payload,'citations':[],
                'contract':{'id':'lumenis.podcast-editorial','version':'1','required_payload_paths':['guest_library','guest_matching','guest_selection','manual_gates','interview_outline']}}}

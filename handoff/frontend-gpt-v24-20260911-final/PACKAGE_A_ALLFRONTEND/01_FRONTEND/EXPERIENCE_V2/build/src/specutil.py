# -*- coding: utf-8 -*-
"""Helpers + shared prototype fixtures for screen section specs.
Section dict schema mirrors LumSections renderers (assets/sections.js).
Business data lives HERE (fixture/viewmodel), NEVER in i18n copy. Every emitted
screen root is marked data-source=prototype; no fake endpoint is ever declared."""

def head(eyebrow, title, desc=None, actions=None, badge=None, eyebrowKey=None, titleKey=None):
    d={"type":"head","eyebrow":eyebrow,"title":title}
    if eyebrowKey: d["eyebrowKey"]=eyebrowKey
    if titleKey: d["titleKey"]=titleKey
    if desc: d["desc"]=desc
    if actions: d["actions"]=actions
    if badge: d["badge"]=badge
    return d

def btn(label, variant="primary", ico=None, act="", cls="NAVIGATION", scope="UNKNOWN", target="UNKNOWN", perm="UNKNOWN", risk=False, size=None):
    a={"label":label,"variant":variant,"id":act,"cls":cls,"scope":scope,"target":target,"permission":perm}
    if ico:a["ico"]=ico
    if risk:a["risk"]=True
    if size:a["size"]=size
    return a

def kpis(items): return {"type":"kpis","items":items}
def metric(label,value,unit=None,delta=None,deltaUnit="%",spark=None,icon="trend",source="EV: UNKNOWN",fresh="live",decimals=0,badge=None):
    m={"label":label,"value":value,"icon":icon,"source":source,"fresh":fresh,"decimals":decimals}
    if unit is not None:m["unit"]=unit
    if delta is not None:m["delta"]=delta;m["deltaUnit"]=deltaUnit
    if spark is not None:m["spark"]=spark
    if badge:m["badge"]=badge
    return m
def evidence(title,items): return {"type":"evidence","title":title,"items":items}
def ev(kind,eid,chain,quote,time,source,conf=88,provider=None):
    e={"kind":kind,"id":eid,"chain":chain,"quote":quote,"time":time,"source":source,"conf":conf}
    if provider:e["provider"]=provider
    return e
def insight(text,why=None,kind=None,cites=None,actions=None):
    d={"type":"insight","text":text}
    if why:d["why"]=why
    if kind:d["kind"]=kind
    if cites:d["evidence"]=cites
    if actions:d["actions"]=actions
    return d
def events(title,items,more=True): return {"type":"events","title":title,"items":items,"more":more}
def evt(time,title,desc=None,date=None,level="low",tags=None,eid=""):
    return {"time":time,"title":title,"desc":desc,"date":date,"level":level,"tags":tags or [],"evidence":eid}
def risks(items): return {"type":"risks","items":items}
def risk(level,title,desc=None,score=None,eid=""):
    r={"level":level,"title":title,"evidence":eid}
    if desc:r["desc"]=desc
    if score is not None:r["score"]=score
    return r
def timeline(title,items,label=None): return {"type":"timeline","title":title,"items":items,"label":label}
def tl(time,title,desc=None,done=False): return {"time":time,"title":title,"desc":desc,"done":done}
def table(title,columns,rows,action=None):
    d={"type":"table","title":title,"columns":columns,"rows":rows}
    if action:d["action"]=action
    return d
def col(label,key,numeric=False,ctype=None,toneKey=None):
    c={"label":label,"key":key}
    if numeric:c["numeric"]=True
    if ctype:c["type"]=ctype
    if toneKey:c["toneKey"]=toneKey
    return c
def chart(title,kind,**kw):
    d={"type":"chart","title":title,"kind":kind};d.update(kw);return d
def filters(chips): return {"type":"filters","chips":chips}
def chip(label,on=False): return {"label":label,"on":on}
def cards(items,cols=3): return {"type":"cards","items":items,"cols":cols}
def card(title,desc=None,ico=None,badge=None,meta=None,action=None):
    c={"title":title}
    if desc:c["desc"]=desc
    if ico:c["ico"]=ico
    if badge:c["badge"]=badge
    if meta:c["meta"]=meta
    if action:c["action"]=action
    return c
def actions(title,items): return {"type":"actions","title":title,"items":items}
def act(id,title,desc=None,icon="zap",cls="NAVIGATION",scope="UNKNOWN",target="UNKNOWN",perm="UNKNOWN",risk=False):
    a={"id":id,"title":title,"icon":icon,"cls":cls,"scope":scope,"target":target,"permission":perm}
    if desc:a["desc"]=desc
    if risk:a["risk"]=True
    return a
def upload(title,files,dropTitle,dropHint=None): return {"type":"upload","title":title,"files":files,"dropTitle":dropTitle,"dropHint":dropHint}
def runtime(title,items): return {"type":"runtime","title":title,"items":items}
def rt(name,state,detail=""): return {"name":name,"state":state,"detail":detail}
def ai(thread=None,steps=None,children=None,title=None):
    d={"type":"ai"}
    if title:d["title"]=title
    if thread:d["thread"]=thread
    if steps:d["steps"]=steps
    if children:d["children"]=children
    return d
def msg(who,text,cites=None,tools=None):
    m={"who":who,"text":text}
    if cites:m["cites"]=cites
    if tools:m["tools"]=tools
    return m
def split(main,side=None): return {"type":"split","main":main,"side":side or []}
def stack(children,gap=6): return {"type":"stack","children":children,"gap":gap}
def tabs(id,tabs_): return {"type":"tabs","id":id,"tabs":tabs_}
def tab(label,sections): return {"label":label,"sections":sections}
def steps(items,children=None,title=None):
    d={"type":"steps","items":items}
    if title:d["title"]=title
    if children:d["children"]=children
    return d
def st(label,state="active"): return {"label":label,"state":state}
def form(title,fields,actions_=None):
    d={"type":"form","title":title,"fields":fields}
    if actions_:d["actions"]=actions_
    return d
def field(label,type="input",ph="",opts=None):
    f={"label":label,"type":type,"ph":ph}
    if opts:f["opts"]=opts
    return f
def note(text,kind="NOTE",code=None):
    d={"type":"note","text":text,"kind":kind}
    if code:d["code"]=code
    return d
def raw(html): return {"type":"raw","html":html}

# ---- shared prototype business fixtures (NOT i18n) ----
SUBJECTS=[
 {"subject_id":"subj_taikoo_hui","subject_type":"commercial_property","scope":"mall_group","name":"广州太古汇"},
 {"subject_id":"subj_taikoo_hui_north","subject_type":"commercial_property","scope":"wing","name":"广州太古汇·北区"},
 {"subject_id":"brand_dior","subject_type":"brand","scope":"brand","name":"Dior（场内品牌）"},
 {"subject_id":"brand_lululemon","subject_type":"brand","scope":"brand","name":"lululemon（竞品对标）"},
 {"subject_id":"subj_spring_campaign","subject_type":"campaign","scope":"campaign","name":"2026 春季会员日"},
]
SPARK7=[12,18,15,22,19,26,24]; SPARK7B=[20,17,22,19,25,21,28]; SPARK12=[8,10,9,13,12,15,14,18,16,20,19,22]
DAYS30=["9/2","9/5","9/8","9/11","9/14","9/17","9/20","9/23","9/26","9/29","10/2","10/5"]

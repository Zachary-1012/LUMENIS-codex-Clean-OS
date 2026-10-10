"""Exact frozen function mechanisms, isolated from product startup and data.
These probes use controlled dependencies. They are not running-product E2E.
"""
from __future__ import annotations
import ast
import datetime
import hashlib
import json
import pathlib
import socket
import sqlite3
import subprocess
import sys
import tempfile
import types
import typing

root, output = map(pathlib.Path, sys.argv[1:3])
BASE='01588e9fd9568e3fcaf1e6c3d957bc498436fa48'
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],timeout=10).decode().strip()==BASE

def denied(*args,**kwargs): raise RuntimeError('AUDIT_NETWORK_FORBIDDEN')
socket.socket.connect=denied; socket.socket.connect_ex=denied; socket.create_connection=denied

sources={}
def source(path):
    if path not in sources:
        data=(root/path).read_bytes()
        sources[path]={'sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),'tree':ast.parse(data,filename=path)}
    return sources[path]['tree']

def load(path,names,bindings):
    tree=source(path)
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
    assert set(names)=={n.name for n in nodes}
    for node in nodes: node.decorator_list=[]
    namespace={'Dict':typing.Dict,'Any':typing.Any,'List':typing.List,'Optional':typing.Optional,**bindings}
    compiled=ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[]))
    exec(compile(compiled,path,'exec'),namespace)
    return namespace

results=[]
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
g=load('content_generation.py',['evaluate_content'],{'json':json,'_now_iso':lambda:now,'content_type_cfg':lambda *a:'xhs'})
for label,payload in [('empty_object',{}),('blank_title',{'title':''}),('null_body',{'body':None}),('empty_segments',{'segments':[]}),('thirty_blank_fields',{f'field_{i}':'' for i in range(30)})]:
    result=g['evaluate_content'](payload,{},'xhs')
    results.append({'probe':'content_without_substantive_work','case':label,'overall':result['overall'],'method':result['method'],'scores':result['scores']})

with tempfile.TemporaryDirectory(prefix='lumenis-mechanism-audit-') as temporary:
    db=pathlib.Path(temporary)/'events.sqlite3'
    def event_connect():
        connection=sqlite3.connect(db); connection.row_factory=sqlite3.Row; return connection
    with event_connect() as connection:
        connection.executescript('CREATE TABLE events(id INTEGER PRIMARY KEY,event_key TEXT,keywords TEXT,negative_confirmed INTEGER,negative_confirmed_at TEXT,negative_confirmed_by TEXT);CREATE TABLE event_mentions(event_id INTEGER,source_id TEXT);CREATE TABLE notes(note_id TEXT,title TEXT,summary TEXT,event_hint TEXT,sentiment TEXT,negative_confirmed INTEGER,negative_confirmed_at TEXT,negative_confirmed_by TEXT,subject_id TEXT);')
        connection.execute('INSERT INTO events(id,event_key,keywords) VALUES(1,?,?)',('event-A',json.dumps(['fixture-promotion'])))
        connection.execute('INSERT INTO event_mentions VALUES(1,?)',('linked-A',))
        connection.executemany('INSERT INTO notes(note_id,title,summary,event_hint,sentiment,negative_confirmed,subject_id) VALUES(?,?,?,?,?,?,?)', [('linked-A','fixture-promotion','','','negative',0,'SUBJECT-A'),('unlinked-B','fixture-promotion','','','negative',0,'SUBJECT-B')])
    g=load('app.py',['_event_set_review'],{'get_repository':lambda:types.SimpleNamespace(connect=event_connect),'sqlite3':sqlite3,'datetime':datetime.datetime,'json':json})
    first=g['_event_set_review'](1,1)
    with event_connect() as connection: before=connection.execute('SELECT negative_confirmed FROM notes WHERE note_id=?',('unlinked-B',)).fetchone()[0]
    second=g['_event_set_review'](1,1)
    with event_connect() as connection: after=connection.execute('SELECT negative_confirmed FROM notes WHERE note_id=?',('unlinked-B',)).fetchone()[0]
    results.append({'probe':'event_confirmation_reentry','first':first,'second':second,'unlinked_other_subject_before_second':before,'unlinked_other_subject_after_second':after,'global_http_auth_exercised':False})

    db2=pathlib.Path(temporary)/'professional.sqlite3'
    def professional_connect():
        connection=sqlite3.connect(db2);connection.row_factory=sqlite3.Row;return connection
    schema=next(ast.literal_eval(n.value) for n in source('kos_professional.py').body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_SCHEMA' for t in n.targets))
    with professional_connect() as connection: connection.executescript(schema)
    g=load('kos_professional.py',['is_enabled','enable','import_metrics','get_metrics'],{'_get_conn':professional_connect,'datetime':datetime.datetime})
    for brand in ('BRAND-A','BRAND-B'):g['enable'](brand,'xiaohongshu','same-account')
    a=g['import_metrics']('BRAND-A','same-account',[{'metric_date':'2026-10-10','impressions':101}])
    b=g['import_metrics']('BRAND-B','same-account',[{'metric_date':'2026-10-10','impressions':202}])
    with professional_connect() as connection: retained=[dict(row) for row in connection.execute('SELECT brand_id,account_id,metric_date,impressions FROM professional_metrics')]
    results.append({'probe':'professional_metric_identity_collision','first_import':a,'second_import':b,'retained_rows':retained})
    rejected=g['import_metrics']('DISABLED-BRAND','same-account',[{'metric_date':'2026-10-10'}])
    request=types.SimpleNamespace(get_json=lambda **kw:{'brand_id':'DISABLED-BRAND','account_id':'same-account','metrics':[{'metric_date':'2026-10-10'}]})
    route=load('lumenis_agg_api.py',['kos_professional_import'],{'_kos_pro':lambda:types.SimpleNamespace(import_metrics=g['import_metrics']),'request':request,'jsonify':lambda x:x})
    wrapped=route['kos_professional_import']()
    results.append({'probe':'professional_route_masks_owner_refusal','owner_result':rejected,'route_result':wrapped,'http_middleware_exercised':False})
    all_failed=g['import_metrics']('BRAND-A','same-account',[None])
    results.append({'probe':'all_metric_rows_invalid','owner_result':all_failed})

record={'baseline':BASE,'observed_at':now,'boundary':'EXACT_SOURCE_FUNCTIONS_WITH_CONTROLLED_DEPENDENCIES','source_blobs':{p:v['sha'] for p,v in sources.items()},'production_db_accessed':False,'external_effects':False,'model_calls':False,'source_modified':False,'results':results}
(output/'mechanism-probes.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))

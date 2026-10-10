"""Read every frozen Git blob; index code without importing or executing it.
Machine traversal and syntax parsing are NOT full semantic review or acceptance.
Outputs contain paths/identifiers and structural signals, never source bodies.
"""
from __future__ import annotations
import ast
import collections
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import warnings

SHA = '01588e9fd9568e3fcaf1e6c3d957bc498436fa48'
root, output = map(pathlib.Path, sys.argv[1:3])
output.mkdir(parents=True, exist_ok=True)

def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=45)

assert git('rev-parse', 'HEAD').decode().strip() == SHA
CODE = set('.py .pyi .dart .js .mjs .cjs .ts .tsx .jsx .astro .vue .svelte .html .htm .css .scss .sass .sql .sh .bash .zsh .ps1 .psm1 .bat .cmd .rs .go .java .kt .kts .swift .c .cc .cpp .h .hpp .m .mm .cmake .r .ipynb .rules'.split())
CONFIG = set('.json .yaml .yml .toml .ini .cfg .conf .xml .plist .lock .properties'.split())
ledger, symbols, imports, routes, signals, registrations = [], [], {}, [], [], []
problems, snippets = [], {}
rows = [row for row in git('ls-tree', '-rz', '--full-tree', SHA).split(b'\0') if row]
batch = subprocess.Popen(['git', '-C', str(root), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def read_blob(sha):
    batch.stdin.write((sha + '\n').encode()); batch.stdin.flush()
    header = batch.stdout.readline().decode().split()
    if len(header) != 3 or header[1] != 'blob':
        raise RuntimeError('BLOB_UNAVAILABLE:' + sha)
    size = int(header[2]); data = batch.stdout.read(size)
    if len(data) != size or batch.stdout.read(1) != b'\n':
        raise RuntimeError('BLOB_READ_INCOMPLETE:' + sha)
    assert hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + data).hexdigest() == sha
    return data

def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None

def dotted(node):
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute): return dotted(node.value) + '.' + node.attr
    return ''

for raw in rows:
    meta, path_raw = raw.split(b'\t', 1)
    mode, kind, blob = meta.decode().split(); path = path_raw.decode('utf-8')
    if kind != 'blob':
        ledger.append({'path':path,'kind':kind,'sha':blob,'read':'NOT_A_BLOB','semantic_review':'NOT_REVIEWED'})
        continue
    data = read_blob(blob)
    p = pathlib.PurePosixPath(path); suffix = p.suffix.lower()
    classification = ('code' if suffix in CODE or p.name in {'Dockerfile','Makefile','CMakeLists.txt','Procfile'} or data.startswith(b'#!') else 'configuration' if suffix in CONFIG else 'other')
    context = ('test' if 'tests' in p.parts or p.name.startswith('test_') else 'vendor' if 'vendor' in p.parts else 'historical_directory' if '99-ARCHIVE' in p.parts else 'engineering' if path.startswith(('.github/','.codex/','.agents/','scripts/')) else 'product_or_support')
    entry = {'path':path,'blob_sha':blob,'bytes':len(data),'classification':classification,'context':context,'read':'FULL_BYTES_HASH_VERIFIED','semantic_review':'NOT_REVIEWED','syntax':'NOT_APPLICABLE'}
    try:
        text = data.decode('utf-8-sig')
        if '\0' in text: raise UnicodeError('binary')
        entry['text']='FULL_UTF8'; entry['lines']=len(text.splitlines())
    except UnicodeError:
        entry['text']='BINARY_OR_NON_UTF8'
        if classification=='code': problems.append({'path':path,'reason':'CODE_ENCODING_REQUIRES_REVIEW'})
        ledger.append(entry); continue
    if suffix in {'.py','.pyi'}:
        try:
            with warnings.catch_warnings(record=True):
                tree = ast.parse(text, filename=path)
            entry['syntax']='PYTHON_AST_PARSED'
        except SyntaxError as exc:
            entry['syntax']='PYTHON_AST_ERROR'; problems.append({'path':path,'line':exc.lineno,'reason':exc.msg})
            ledger.append(entry); continue
        modules = []
        prefixes = {}
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                modules.extend([x.name for x in node.names] if isinstance(node,ast.Import) else ['.'*node.level + (node.module or '')])
            if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and dotted(node.value.func).endswith('Blueprint'):
                prefix = next((literal(k.value) for k in node.value.keywords if k.arg=='url_prefix'), '')
                for target in node.targets:
                    if isinstance(target,ast.Name): prefixes[target.id]=prefix
            if isinstance(node,ast.Call) and dotted(node.func).endswith('.register_blueprint'):
                registrations.append({'path':path,'line':node.lineno,'callee':dotted(node.args[0]) if node.args else ''})
        imports[path]=sorted(set(modules))
        for node in ast.walk(tree):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
            calls = sorted(set(dotted(n.func) for n in ast.walk(node) if isinstance(n,ast.Call)))
            symbols.append({'path':path,'name':node.name,'line':node.lineno,'end':node.end_lineno,'arguments':[x.arg for x in node.args.args],'keyword_only':[x.arg for x in node.args.kwonlyargs],'calls':calls})
            for decorator in node.decorator_list:
                if not isinstance(decorator,ast.Call): continue
                name = dotted(decorator.func); method=name.rsplit('.',1)[-1]
                if method not in {'route','get','post','put','patch','delete'} or not decorator.args: continue
                route=literal(decorator.args[0])
                if not isinstance(route,str): continue
                owner=name.rsplit('.',1)[0]; prefix=prefixes.get(owner,'')
                methods=next((literal(k.value) for k in decorator.keywords if k.arg=='methods'), ['GET'] if method=='route' else [method.upper()])
                routes.append({'path':path,'function':node.name,'line':node.lineno,'owner':owner,'route':(prefix or '')+route,'prefix_resolved_locally':owner in prefixes or owner=='app','methods':methods,'production_reachability':'REQUIRES_REGISTRATION_REVIEW'})
            flags=[]
            for n in ast.walk(node):
                if isinstance(n,ast.ExceptHandler) and (n.type is None or dotted(n.type) in {'Exception','BaseException'}):
                    if any(isinstance(x,ast.Pass) for x in n.body): flags.append('BROAD_EXCEPTION_PASS')
                    if any(isinstance(x,ast.Return) and literal(x.value) in (True, [], {}) for x in n.body if isinstance(x,ast.Return) and x.value is not None): flags.append('EXCEPTION_RETURNS_DEFAULT')
                if isinstance(n,ast.Call):
                    name=dotted(n.func)
                    if name in {'pickle.loads','pickle.load','eval','exec','shutil.copy2','shutil.rmtree','os.system'}: flags.append('REVIEW_SINK:'+name)
                    if name in {'requests.get','requests.post','requests.request','urllib.request.urlopen','httpx.get','httpx.post'} and not any(k.arg=='timeout' for k in n.keywords): flags.append('NETWORK_TIMEOUT_NOT_EXPLICIT')
            if flags: signals.append({'path':path,'function':node.name,'line':node.lineno,'flags':sorted(set(flags)),'state':'UNTRIAGED_NOT_A_CONFIRMED_DEFECT'})
    ledger.append(entry)

batch.stdin.close(); batch.wait(timeout=15)
module_files = {x['path'][:-3].replace('/','.'):x['path'] for x in ledger if x['path'].endswith('.py')}
module_files.update({k[:-9]:v for k,v in list(module_files.items()) if k.endswith('.__init__')})
edges=[]
for path,names in imports.items():
    package=path[:-3].replace('/','.').split('.')[:-1]
    for name in names:
        if name.startswith('.'):
            level=len(name)-len(name.lstrip('.')); name='.'.join(package[:len(package)-level+1]+[name.lstrip('.')]).strip('.')
        target=module_files.get(name)
        if target: edges.append({'from':path,'to':target})
reached={'app.py'}; changed=True
while changed:
    new={e['to'] for e in edges if e['from'] in reached}-reached
    reached.update(new); changed=bool(new)
for entry in ledger:
    entry['static_import_reachable_from_app']=entry['path'] in reached
    entry['runtime_loaded']='NOT_VERIFIED'
counts=collections.Counter(x['classification'] for x in ledger if 'classification' in x)
byext=collections.Counter(pathlib.PurePosixPath(x['path']).suffix.lower() or '(none)' for x in ledger if x.get('classification')=='code')
route_groups=collections.defaultdict(list)
for route in routes:
    if route['path'] not in reached: continue
    for method in route['methods'] or []:
        route_groups[(method,route['route'])].append(route)
duplicates=[{'method':key[0],'route':key[1],'definitions':values,'state':'UNTRIAGED_REGISTRATION_ORDER_REQUIRED'} for key,values in route_groups.items() if len(values)>1]
summary={'baseline':SHA,'tree':git('rev-parse','HEAD^{tree}').decode().strip(),'observed_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'tracked_objects':len(ledger),'classifications':dict(counts),'code_by_extension':dict(byext),'python_ast_parsed':sum(x.get('syntax')=='PYTHON_AST_PARSED' for x in ledger),'python_functions':len(symbols),'route_definitions':len(routes),'static_import_reachable_modules':len(reached),'structural_signals':len(signals),'duplicate_route_candidates':len(duplicates),'read_or_syntax_issues':problems,'full_semantic_review':'NOT_COMPLETED','local_candidate':'NOT_VERIFIED_REMOTE_AGENT_OFFLINE','runtime':'NOT_EXECUTED','production_database':'NOT_ACCESSED','network_in_product':'NOT_EXECUTED','product_source_modified':False}
for name,value in {'summary':summary,'file-ledger':ledger,'symbols':symbols,'routes':routes,'imports':imports,'static-edges':edges,'blueprint-registrations':registrations,'structural-candidates':signals,'route-collision-candidates':duplicates}.items():
    (output/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
assert all(x.get('read')=='FULL_BYTES_HASH_VERIFIED' for x in ledger if x.get('kind')!='commit')

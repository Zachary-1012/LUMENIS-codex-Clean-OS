"""Bundle only the review's constrained static named-import ESM subset.
Reject unknown syntax/exports/cycles rather than guessing. No downloads or eval.
The browser artifact uses function scopes per module, not concatenated globals.
"""
from pathlib import Path
import re, json, base64, hashlib
ROOT=Path(__file__).resolve().parents[1]
IMPORT=re.compile(r"^import\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"];?",re.M)
EXPORT=re.compile(r'\bexport\s+(?:async\s+)?(?:function|const|let|class)\s+([A-Za-z_$][\w$]*)')
modules={};order=[];visiting=set()
def visit(name):
 if name in modules:return
 if name in visiting:raise ValueError('Import cycle: '+name)
 visiting.add(name);p=ROOT/'src'/name
 if p.parent.resolve()!=(ROOT/'src').resolve():raise ValueError('Nonlocal module')
 source=p.read_text();bindings=[]
 for match in IMPORT.finditer(source):
  target=match[2]
  if not target.startswith('./'):raise ValueError('External import')
  target=target[2:];visit(target)
  for binding in match[1].split(','):
   pieces=binding.strip().split(' as ')
   if len(pieces)>2 or not all(re.fullmatch(r'[A-Za-z_$][\w$]*',x) for x in pieces):raise ValueError('Unsupported binding')
   public=pieces[0];local=pieces[-1]
   if public not in modules[target]['exports']:raise ValueError(f'Missing export {target}/{public}')
   bindings.append(f'const {local}=__modules[{json.dumps(target)}][{json.dumps(public)}];')
 body=IMPORT.sub('',source)
 if re.search(r'^\s*import\b',body,re.M):raise ValueError('Unsupported import syntax')
 exports=EXPORT.findall(body);body=re.sub(r'\bexport\s+(?=(?:async\s+)?(?:function|const|let|class)\s)', '',body)
 if re.search(r'^\s*export\b',body,re.M):raise ValueError('Unsupported export syntax')
 modules[name]={'exports':exports,'body':'\n'.join(bindings)+'\n'+body,'sha256':hashlib.sha256(source.encode()).hexdigest()}
 visiting.remove(name);order.append(name)
visit('app.mjs')
chunks=['const __modules=Object.create(null);']
for name in order:
 m=modules[name];chunks.append('__modules['+json.dumps(name)+']=(()=>{\n'+m['body']+'\nreturn {'+','.join(m['exports'])+'};\n})();')
# Keep an inspectable script and a manifest beside the final self-contained file.
script='\n'.join(chunks)
asset=ROOT/'assets/aigc-paper-study.png';script=script.replace('assets/aigc-paper-study.png','data:image/png;base64,'+base64.b64encode(asset.read_bytes()).decode())
script=script.replace('</script','<\\/script')
html=(ROOT/'index.html').read_text();css=(ROOT/'src/style.css').read_text()
css_tag='<link rel="stylesheet" href="src/style.css">';js_tag='<script type="module" src="src/app.mjs"></script>'
assert html.count(css_tag)==html.count(js_tag)==1
html=html.replace(css_tag,'<style>'+css+'</style>').replace(js_tag,'<script type="module">'+script+'</script>')
(ROOT/'offline.html').write_text(html)
(ROOT/'evidence/offline-bundle.js').write_text(script)
(ROOT/'evidence/OFFLINE_BUILD_MANIFEST.json').write_text(json.dumps({'type':'NEW_OFFLINE_BUILD_FROM_WORKING_SOURCE','entry':'app.mjs','modules':[{'name':n,'exports':modules[n]['exports'],'sha256':modules[n]['sha256']} for n in order],'offline_sha256':hashlib.sha256(html.encode()).hexdigest(),'asset_sha256':hashlib.sha256(asset.read_bytes()).hexdigest()},indent=2)+'\n')
print('Bundled',len(order),'modules;',len(html.encode()),'bytes')

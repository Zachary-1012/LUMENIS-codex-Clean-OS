import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {CONTENT_LANGUAGES,UI_LANGUAGES} from '../src/content-language.mjs';
import {RESUMABLE_LIMITS as L,RESUMABLE_STORAGE_KEY,RESUMABLE_SCHEMA,chunkPlan,sha256Bytes,createLocalByteSink,createResumableWorkbench,saveResumableSnapshot,readResumableSnapshot,validateResumableSnapshot,inspectBackendAdapter,validateBackendReceiptShape,BACKEND_RESUME_CONTRACT} from '../src/resumable-file.mjs';
import {resumableStudy,createResumableFile} from '../src/resumable-study.mjs';
const bytes=(n=3500)=>Uint8Array.from({length:n},(_,i)=>(i*37+11)%256);
const hash=x=>createHash('sha256').update(x).digest('hex');
function selected(data=bytes(),name='素材 e\u0301 한국어 العربية 👩🏽‍💻.bin',options={}){
 const calls=[];return{name,size:data.length,lastModified:123456789,slice(start,end){calls.push([start,end]);return{arrayBuffer:async()=>{if(options.read)return options.read(start,end,data);return data.slice(start,end).buffer;}};},calls};
}
function memory(){const map=new Map();return{map,getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k)};}
function controller(options={}){let id=0;return createResumableWorkbench({clock:()=>2000000000000,idFactory:()=>`local-session-${++id}`,...options});}
async function prepared(options={},file=selected()){const w=controller(options);assert.equal((await w.prepare(file,{chunkBytes:1024})).ok,true);return{w,file};}
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return{promise,resolve,reject};};
const turns=async()=>{for(let i=0;i<5;i++)await Promise.resolve();};

test('catalogue is seven-tuple, source requirement stays bounded and content languages are separate',()=>{
 assert.equal(resumableStudy.length,7);assert.deepEqual(resumableStudy.slice(0,2),['resumablefile','69']);assert.equal(CONTENT_LANGUAGES.length,12);assert.deepEqual(UI_LANGUAGES,['zh','en','ko']);
});
test('chunk ranges are contiguous, bounded, exact for last partial and empty files',()=>{
 assert.deepEqual(chunkPlan(2500,1024),[{index:0,offset:0,length:1024},{index:1,offset:1024,length:1024},{index:2,offset:2048,length:452}]);
 assert.deepEqual(chunkPlan(0,1024),[{index:0,offset:0,length:0}]);
 for(const n of [-1,NaN,1.5,L.fileBytes+1])assert.throws(()=>chunkPlan(n));
 assert.throws(()=>chunkPlan(1,0));assert.throws(()=>chunkPlan(1,L.chunkBytes+1));assert.throws(()=>chunkPlan(L.fileBytes,1024),/TOO_MANY/);
});
test('hashes actual selected bytes and full file; preserves exact Unicode filename and content tag',async()=>{
 const data=bytes(),file=selected(data),w=controller();await w.prepare(file,{chunkBytes:1024,contentLanguage:'ar'});const s=w.getState(),m=s.manifest;
 assert.equal(m.file.name,file.name);assert.equal(m.fingerprint,hash(data));assert.equal(m.contentLanguage,'ar');assert.equal(m.chunks.length,4);for(const c of m.chunks)assert.equal(c.sha256,hash(data.slice(c.offset,c.offset+c.length)));
 assert.deepEqual(file.calls,[[0,1024],[1024,2048],[2048,3072],[3072,3500]]);assert.equal(s.preparedBytes,3500);assert.equal(s.localVerifiedBytes,0);assert.equal(m.preparedAt,2000000000000);assert.equal(m.timeAuthority,'LOCAL_PREPARATION_OBSERVATION');assert.equal(s.backend.state,'UNBOUND');assert.equal(s.backend.serverReceivedBytes,null);
});
test('no reads before file selection; bounds, path, malformed name and oversize reject before slice',async()=>{
 let reads=0;const w=controller();assert.equal(w.getState().phase,'IDLE');const baseline=w.getState();for(const change of [{size:L.fileBytes+1},{name:'../private.bin'},{name:'a'.repeat(L.nameUnits+1)},{name:'bad\ud800'}]){const f={name:'safe',size:1,lastModified:0,slice(){reads++;},...change};await assert.rejects(w.prepare(f));}
 assert.equal(reads,0);assert.deepEqual(w.getState(),baseline);
});
test('empty file gets real SHA-256 and exact zero-byte block verification',async()=>{
 const{w}=await prepared({},selected(new Uint8Array()));assert.equal(w.getState().manifest.fingerprint,hash(new Uint8Array()));await w.run();assert.equal(w.getState().phase,'LOCAL_COMPLETE');assert.deepEqual(w.getState().verifiedIndices,[0]);assert.equal(w.getState().localVerifiedBytes,0);
});
test('step, pause, cancel, missing-only resume and no repeated write for verified chunks',async()=>{
 const sink=createLocalByteSink(),{w}=await prepared({sink});await w.run({maxChunks:1});assert.equal(sink.stats().writes,1);assert.equal(w.getState().phase,'PAUSED');assert.deepEqual(w.getState().missingIndices,[1,2,3]);
 w.pause();w.cancel();assert.equal(w.getState().phase,'CANCELLED');await w.resume();assert.equal(w.getState().phase,'LOCAL_COMPLETE');assert.equal(sink.stats().writes,4);await w.resume();assert.equal(sink.stats().writes,4);
 assert.equal(w.getState().localVerifiedBytes,3500);assert.equal(w.getState().backend.productMaterial,'UNAVAILABLE');assert.equal(w.getState().rights,'UNKNOWN');
 w.forgetChunk(1);assert.deepEqual(w.getState().missingIndices,[1]);await w.resume();assert.equal(sink.stats().writes,5);assert.equal(sink.stats().chunks,4);
});
test('failure retries exact missing chunk and does not duplicate successfully verified bytes',async()=>{
 const sink=createLocalByteSink(),write=sink.write;let failed=false;sink.write=(request,b,current)=>{if(request.index===1&&!failed){failed=true;throw Error('INJECTED_LOCAL_WRITE_FAILURE');}return write(request,b,current);};
 const{w}=await prepared({sink});const result=await w.run();assert.equal(result.error,'INJECTED_LOCAL_WRITE_FAILURE');assert.deepEqual(w.getState().verifiedIndices,[0]);assert.equal(sink.stats().writes,1);await w.retry();assert.equal(w.getState().phase,'LOCAL_COMPLETE');assert.equal(sink.stats().writes,4);
});
test('sink exact readback failure never counts a chunk; retry removes actual corrupted block',async()=>{
 const sink=createLocalByteSink(),read=sink.read;let corrupt=true;sink.read=request=>{const b=read(request);if(b&&corrupt)b[0]^=255;return b;};
 const{w}=await prepared({sink});await w.run();assert.equal(w.getState().lastError,'LOCAL_EXACT_BYTE_READBACK_FAILED');assert.deepEqual(w.getState().verifiedIndices,[]);corrupt=false;await w.retry();assert.equal(w.getState().phase,'LOCAL_COMPLETE');assert.equal(sink.stats().writes,4);
});
test('file mutation between prepare and processing is blocked by chunk hashes',async()=>{
 let changed=false;const data=bytes(),file=selected(data,'changing.bin',{read:(a,b,raw)=>{const part=raw.slice(a,b);if(changed&&a===1024)part[0]^=1;return part.buffer;}});const{w}=await prepared({},file);changed=true;await w.run();assert.equal(w.getState().lastError,'SELECTED_FILE_BYTES_CHANGED');assert.deepEqual(w.getState().verifiedIndices,[0]);
});
test('invalid slice lengths and unavailable crypto fail closed rather than random progress',async()=>{
 const{w}=await prepared();const wrong=selected(bytes(),'bad.bin',{read:()=>new Uint8Array(1).buffer});await w.prepare(wrong,{chunkBytes:1024});assert.equal(w.getState().lastError,'FILE_SLICE_LENGTH_MISMATCH');assert.equal(w.getState().preparedBytes,0);
 const noCrypto=controller({subtle:{}});await noCrypto.prepare(selected(),{chunkBytes:1024});assert.equal(noCrypto.getState().lastError,'SHA256_UNAVAILABLE');assert.equal(noCrypto.getState().manifest,null);
});
test('metadata serialization is real exact readback; new controller cannot recover byte storage or permission',async()=>{
 const store=memory(),{w}=await prepared();await w.run({maxChunks:2});const saved=saveResumableSnapshot(store,w.snapshot());assert.equal(saved.schema,RESUMABLE_SCHEMA);assert.equal(saved.bytesPersisted,false);assert.equal(saved.permissionPersisted,false);assert.equal(saved.serverReceipts,null);
 const raw=store.getItem(RESUMABLE_STORAGE_KEY);assert.equal(raw,JSON.stringify(saved));assert.equal(raw.includes('arrayBuffer'),false);const reopened=readResumableSnapshot(store);assert.deepEqual(reopened,saved);const next=controller();next.reopen(reopened);
 const s=next.getState();assert.equal(s.phase,'NEEDS_FILE');assert.equal(s.allowed,false);assert.equal(s.selectedFile,false);assert.equal(s.localVerifiedBytes,0);assert.deepEqual(s.verifiedIndices,[]);assert.deepEqual(s.historicalIndices,[0,1]);await assert.rejects(next.run(),/PERMISSION/);
 await next.reselect(selected());assert.deepEqual(next.getState().missingIndices,[0,1,2,3]);await next.resume();assert.equal(next.getState().phase,'LOCAL_COMPLETE');assert.equal(next.getState().backend.state,'UNBOUND');
});
test('metadata tampering never restores permissions, server receipt claims or invalid offset manifests',async()=>{
 const{w}=await prepared(),snapshot=w.snapshot();for(const mutate of [x=>x.permissionPersisted=true,x=>x.bytesPersisted=true,x=>x.serverReceipts=[],x=>x.extra=true,x=>x.schema='other',x=>x.localVerifiedIndices=[0,0],x=>x.localVerifiedIndices=[99],x=>x.manifest.chunks[1].offset=1,x=>x.manifest.file.name+='\ud800',x=>x.manifest.contentLanguage='xx',x=>x.manifest.fingerprint='not-a-hash']){const invalid=structuredClone(snapshot);mutate(invalid);assert.throws(()=>validateResumableSnapshot(invalid));}
});
test('storage denied, quota and exact-readback mismatch are honest and preserve original record when recoverable',async()=>{
 const{w}=await prepared(),snapshot=w.snapshot();for(const mode of ['quota','mismatch','read']){const store=memory();store.setItem(RESUMABLE_STORAGE_KEY,'previous');const get=store.getItem,set=store.setItem;store.setItem=(k,v)=>{if(mode==='quota'&&v!=='previous')throw Error('QuotaExceededError');set(k,v);};store.getItem=k=>{if(mode==='read')throw Error('SecurityError');const v=get(k);return mode==='mismatch'&&v!=='previous'?'different':v;};assert.throws(()=>saveResumableSnapshot(store,snapshot));assert.equal(store.map.get(RESUMABLE_STORAGE_KEY),'previous');}
 const store=memory();store.setItem(RESUMABLE_STORAGE_KEY,'{');assert.throws(()=>readResumableSnapshot(store));
});
test('same-size mismatched file blocked, matching renamed bytes preserves original Unicode filename',async()=>{
 const{w,file}=await prepared();await w.run({maxChunks:1});const snapshot=w.snapshot();w.reopen(snapshot);const other=bytes();other[0]^=1;assert.equal((await w.reselect(selected(other,file.name))).error,'RESELECT_FINGERPRINT_MISMATCH');assert.equal(w.getState().selectedFile,false);assert.equal(w.getState().manifest.file.name,file.name);await assert.rejects(w.run(),/RESELECT/);
 await w.reselect(selected(bytes(),'renamed.bin'));assert.equal(w.getState().manifest.file.name,file.name);assert.equal(w.getState().selectedFile,true);assert.deepEqual(w.getState().verifiedIndices,[]);await w.resume();assert.equal(w.getState().phase,'LOCAL_COMPLETE');
});
test('all 12 declared content tags and exact long Unicode filenames survive real save/reopen',async()=>{
 const name='e\u0301_日本語_العربية_👩🏽‍💻'.repeat(80)+'.bin';for(const language of CONTENT_LANGUAGES){const w=controller();await w.prepare(selected(bytes(1),name),{contentLanguage:language});const store=memory();saveResumableSnapshot(store,w.snapshot());const restored=readResumableSnapshot(store);assert.equal(restored.manifest.file.name,name);assert.equal(restored.manifest.contentLanguage,language);const next=controller();next.reopen(restored);assert.equal(next.getState().manifest.file.name,name);assert.equal(next.getState().manifest.contentLanguage,language);}
});
test('pause fences delayed prepare and newer file selection cannot be overwritten by old callback',async()=>{
 const d=deferred(),first=selected(bytes(),'old.bin',{read:()=>d.promise}),w=controller();const old=w.prepare(first,{chunkBytes:1024});w.pause();const frozen=w.getState();d.resolve(bytes(1024).buffer);assert.equal((await old).stale,true);assert.deepEqual(w.getState(),frozen);
 const d2=deferred(),late=w.prepare(selected(bytes(),'old-2.bin',{read:()=>d2.promise}),{chunkBytes:1024});await w.prepare(selected(bytes(1200),'current.bin'),{chunkBytes:1024});const current=w.getState();d2.resolve(bytes(1024).buffer);assert.equal((await late).stale,true);assert.deepEqual(w.getState(),current);
});
test('cancel and immediate retry fence stale delayed chunk attempt without changing new completion',async()=>{
 const data=bytes();let delay=false;const d=deferred(),file=selected(data,'source.bin',{read:(a,b,raw)=>delay?(delay=false,d.promise):raw.slice(a,b).buffer});const{w}=await prepared({},file);delay=true;const old=w.run();await turns();w.cancel();const fresh=w.resume();d.resolve(data.slice(0,1024).buffer);const [oldResult,newResult]=await Promise.all([old,fresh]);assert.equal(oldResult.stale,true);assert.equal(newResult.ok,true);assert.equal(w.getState().phase,'LOCAL_COMPLETE');assert.deepEqual(w.getState().verifiedIndices,[0,1,2,3]);
});
test('permission revocation clears file and bytes; explicit same-byte reselection grants only fresh local read',async()=>{
 const{w}=await prepared();await w.run({maxChunks:1});const before=w.getState().permissionVersion;w.revoke();assert.equal(w.getState().phase,'PERMISSION_REVOKED');assert.equal(w.getState().allowed,false);assert.equal(w.getState().selectedFile,false);assert.equal(w.getState().localVerifiedBytes,0);assert.ok(w.getState().permissionVersion>before);await assert.rejects(w.resume(),/PERMISSION/);await w.reselect(selected());await w.resume();assert.equal(w.getState().phase,'LOCAL_COMPLETE');assert.equal(w.getState().rights,'UNKNOWN');
});
test('scope guards isolate snapshots; delayed reads cannot resurrect revoked, switched or disposed state',async()=>{
 for(const action of ['revoke','scope','reopen','dispose']){
  const d=deferred();let delayed=false;const file=selected(bytes(),'source.bin',{read:(a,b,raw)=>delayed?d.promise:raw.slice(a,b).buffer});const{w}=await prepared({},file),snapshot=w.snapshot();delayed=true;const pending=w.run();await turns();
  if(action==='scope')w.setScope({actorId:'local-user',workspaceId:'independent-review',projectId:'other'});else if(action==='reopen')w.reopen(snapshot);else w[action]();const after=w.getState();d.resolve(bytes(1024).buffer);await pending;assert.deepEqual(w.getState(),after);
  if(action==='scope')assert.throws(()=>w.reopen(snapshot),/SCOPE/);
 }
});
test('stale sink writes use mandatory current predicate and cannot mutate replacement session',async()=>{
 const sink=createLocalByteSink(),write=sink.write,d=deferred();let delay=true;sink.write=async(r,b,current)=>{if(delay){delay=false;await d.promise;}return write(r,b,current);};const{w}=await prepared({sink});const old=w.run();while(delay)await new Promise(r=>setImmediate(r));w.cancel();await w.prepare(selected(bytes(1100),'new.bin'),{chunkBytes:1024});await w.run();const before=w.getState(),stats=sink.stats();d.resolve();assert.equal((await old).stale,true);assert.deepEqual(w.getState(),before);assert.deepEqual(sink.stats(),stats);
});
test('backend adapter injection is inspected, never invoked, and structural receipts cannot promote persistence',async()=>{
 let calls=0;const adapter=Object.fromEntries(BACKEND_RESUME_CONTRACT.methods.map(k=>[k,()=>{calls++;throw Error('must not run');}]));const{w}=await prepared({backendAdapter:adapter});await w.run();assert.equal(calls,0);assert.equal(w.getState().backend.state,'UNBOUND');assert.deepEqual(inspectBackendAdapter(adapter).missing,[]);
 const request={actorId:'user',workspaceId:'ws',projectId:'project',permissionVersion:1,operationId:'request-1',attempt:1,sessionId:'server-session',fingerprint:hash(bytes()),index:0,offset:0,length:1024,sha256:hash(bytes(1024))};const receipt={...request,origin:'SERVER',receiptId:'opaque',receivedAt:'2026-10-17T00:00:00Z',durability:'PERSISTED'};const shape=validateBackendReceiptShape(receipt,request);assert.equal(shape.authenticated,false);assert.equal(shape.backend,'UNBOUND');assert.throws(()=>validateBackendReceiptShape(null,request),/MISSING/);assert.throws(()=>validateBackendReceiptShape({...receipt,offset:'wrong'},request),/offset/);assert.throws(()=>validateBackendReceiptShape({...receipt,offset:-1},{...request,offset:-1}),/RANGE/);
});

class Node {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.style={};this.attributes={};this.value='';this.disabled=false;this.hidden=false;this.textContent='';}
 append(...nodes){for(const n of nodes)n.parent=this;this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=[];this.append(...nodes);}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this);}
 setAttribute(k,v){this.attributes[k]=String(v);}
 focus(){this.ownerDocument.activeElement=this;}
 emit(type,extra={}){return this['on'+type]?.({target:this,type,...extra});}
}
function mount(options={}){const doc={activeElement:null,defaultView:{localStorage:memory()}};doc.createElement=tag=>Object.assign(new Node(tag),{ownerDocument:doc});const stage=doc.createElement('section'),settingsRoot=doc.createElement('section');let cleanup;const c=createResumableFile({stage,settingsRoot,clock:()=>2000000000000,idFactory:()=>`view-session`,onDispose:fn=>cleanup=fn,...options});const choose=async(key,file)=>{c.nodes[key].files=[file];c.nodes[key].emit('change');await c.whenIdle();};const click=async key=>{c.nodes[key].emit('click');await c.whenIdle();};return{c,stage,settingsRoot,doc,choose,click,cleanup};}
const textTree=n=>[n.textContent,...n.children.map(textTree)].join('\n');
test('DOM defaults expose native file controls; parameters only settingsRoot; byte progress is truthful',async()=>{
 const{c,stage,settingsRoot,choose,click,cleanup}=mount();assert.equal(c.nodes.file.tagName,'INPUT');assert.equal(c.nodes.file.type,'file');assert.equal(c.nodes.file.attributes['aria-label'],'选择本地文件并准备分块清单');assert.equal(c.nodes.one.tagName,'BUTTON');assert.equal(c.nodes.chunkSize.parent.parent,settingsRoot.children[0]);assert.equal(c.nodes.language.children.length,13);assert.equal(c.nodes.server.textContent,'UNKNOWN · 未上传');assert.equal(c.nodes.one.disabled,true);
 c.nodes.chunkSize.value='65536';c.nodes.chunkSize.emit('change');const file=selected(bytes(140000));await choose('file',file);assert.equal(c.getState().manifest.chunks.length,3);assert.equal(c.nodes.read.textContent,'140000 B');assert.equal(c.nodes.local.textContent,'0 B');assert.ok(textTree(stage).includes(file.name));await click('one');assert.equal(c.getState().phase,'PAUSED');assert.equal(c.nodes.local.textContent,'65536 B');assert.equal(c.nodes.localProgress.value,65536);await click('resume');assert.equal(c.getState().phase,'LOCAL_COMPLETE');assert.equal(c.nodes.local.textContent,'140000 B');assert.equal(c.nodes.server.textContent,'UNKNOWN · 未上传');cleanup();assert.equal(stage.children.length,0);assert.equal(settingsRoot.children.length,0);
});
test('DOM serialized metadata confirmation restores no permission or bytes, rejects wrong reselect, handles retry',async()=>{
 const store=memory(),first=mount({storage:store});await first.choose('file',selected());await first.click('resume');await first.click('save');assert.match(first.c.nodes.live.textContent,/逐字读回/);first.cleanup();const{c,choose,click,cleanup}=mount({storage:store});await click('reopen');assert.equal(c.nodes.confirmation.hidden,false);assert.equal(c.getState().phase,'IDLE');await click('cancelReopen');assert.equal(c.getState().phase,'IDLE');await click('reopen');await click('confirm');assert.equal(c.getState().phase,'NEEDS_FILE');assert.equal(c.getState().allowed,false);assert.equal(c.nodes.local.textContent,'0 B');const wrong=bytes();wrong[0]^=1;await choose('reselect',selected(wrong));assert.equal(c.getState().selectedFile,false);assert.match(c.nodes.live.textContent,/字节不同/);await choose('reselect',selected());await click('resume');assert.equal(c.getState().phase,'LOCAL_COMPLETE');cleanup();
});
test('DOM revoke clears local bytes, controls protect permissions and explicit reselect resumes',async()=>{
 const{c,choose,click,cleanup}=mount();await choose('file',selected());await click('resume');await click('revoke');assert.equal(c.nodes.resume.disabled,true);assert.equal(c.nodes.local.textContent,'0 B');assert.equal(c.getState().allowed,false);await choose('reselect',selected());await click('resume');assert.equal(c.getState().phase,'LOCAL_COMPLETE');cleanup();
});
test('DOM disposal fences delayed file selection and removes callbacks and settings',async()=>{
 const d=deferred(),{c,choose,stage,settingsRoot}=mount();const pending=choose('file',selected(bytes(),'late.bin',{read:()=>d.promise}));c.dispose();const state=c.getState();d.resolve(bytes().buffer);await pending;assert.deepEqual(c.getState(),state);assert.equal(c.nodes.file.onchange,null);assert.equal(stage.children.length,0);assert.equal(settingsRoot.children.length,0);
});
test('DOM actual saved text shows full Unicode, literal markup and never assigns file names as HTML',async()=>{
 const name='<img src=x onerror=bad> e\u0301 العربية 👩🏽‍💻.bin';const{c,stage,choose,click,cleanup}=mount();await choose('file',selected(bytes(3),name));await click('save');assert.ok(textTree(stage).includes(name));assert.equal(c.getState().manifest.file.name,name);c.nodes.language.value='ja';c.nodes.language.emit('change');assert.equal(c.getState().manifest.contentLanguage,'ja');assert.equal(c.getState().manifest.file.name,name);cleanup();
});
test('source has no network/product effect path, random progress or HTML filename injection',()=>{
 for(const name of ['resumable-file.mjs','resumable-study.mjs']){const source=readFileSync(new URL('../src/'+name,import.meta.url),'utf8');assert.doesNotMatch(source,/\bfetch\s*\(|XMLHttpRequest|WebSocket|navigator\.sendBeacon|Math\.random\s*\(|\.innerHTML\s*=/);}
});

test('pause or cancel during preparation can explicitly retry the selected bytes with the same chunk preference',async()=>{
 for(const action of ['pause','cancel']){let first=true;const d=deferred(),file=selected(bytes(),'retry.bin',{read:(a,b,raw)=>first?(first=false,d.promise):raw.slice(a,b).buffer}),w=controller();const previous=w.prepare(file,{chunkBytes:1024,contentLanguage:'ko'});w[action]();const retry=w.retry();d.resolve(bytes(1024).buffer);assert.equal((await previous).stale,true);assert.equal((await retry).ok,true);assert.equal(w.getState().manifest.chunkBytes,1024);assert.equal(w.getState().manifest.contentLanguage,'ko');assert.equal(w.getState().phase,'READY');await w.resume();assert.equal(w.getState().phase,'LOCAL_COMPLETE');}
});
test('lost sink bytes are reconciled from actual readback even when in-memory verified indices say complete',async()=>{
 const sink=createLocalByteSink(),{w}=await prepared({sink});await w.run();sink.remove(2);assert.equal(w.getState().verifiedIndices.length,4);const before=sink.stats().writes;await w.resume();assert.equal(sink.stats().writes,before+1);assert.equal(w.getState().phase,'LOCAL_COMPLETE');assert.equal(sink.stats().byteLength,3500);
});
test('overlapping operations reject BUSY without changing attempt; delayed callback truly reaches pause fence',async()=>{
 const entered=deferred(),release=deferred();let delay=false;const file=selected(bytes(),'async.bin',{read:(a,b,raw)=>{if(delay){delay=false;entered.resolve();return release.promise;}return raw.slice(a,b).buffer;}}),{w}=await prepared({},file);delay=true;const old=w.run();await entered.promise;const before=w.getState().attempt;await assert.rejects(w.run(),/BUSY/);assert.equal(w.getState().attempt,before);w.pause();const frozen=w.getState();release.resolve(bytes(1024).buffer);assert.equal((await old).stale,true);assert.deepEqual(w.getState(),frozen);await w.resume();assert.equal(w.getState().phase,'LOCAL_COMPLETE');
});
test('invalid calendar timestamps are rejected before rendering or reopening metadata',async()=>{
 const{w}=await prepared();for(const field of ['preparedAt','savedAt','lastModified']){const snapshot=w.snapshot();if(field==='preparedAt')snapshot.manifest.preparedAt=Number.MAX_SAFE_INTEGER;else if(field==='lastModified')snapshot.manifest.file.lastModified=Number.MAX_SAFE_INTEGER;else snapshot.savedAt=Number.MAX_SAFE_INTEGER;assert.throws(()=>validateResumableSnapshot(snapshot));}
});
test('sink rejects changed session, scope, offset and length identities before accepting any bytes',async()=>{
 const sink=createLocalByteSink(),{w}=await prepared({sink}),m=w.getState().manifest,c=m.chunks[0],request={sessionId:m.sessionId,fingerprint:m.fingerprint,scope:m.scope,...c};
 for(const [key,value]of [['sessionId','another'],['offset',1],['length',1],['scope',{...m.scope,projectId:'another'}]])assert.throws(()=>sink.write({...request,[key]:value},bytes(1024),()=>true));
 assert.throws(()=>sink.write(request,bytes(1024),()=>false),/STALE/);assert.equal(sink.stats().writes,0);
});
test('the 16 MiB boundary uses bounded slices and computes the actual complete fingerprint',async()=>{
 const data=bytes(L.fileBytes),file=selected(data,'bound.bin'),w=controller();await w.prepare(file);assert.equal(w.getState().manifest.fingerprint,hash(data));assert.equal(w.getState().manifest.chunks.length,64);assert.ok(file.calls.every(([a,b])=>b-a===L.defaultChunkBytes));assert.equal(w.getState().preparedBytes,L.fileBytes);
});
test('DOM pending reopen is cancelled by new file selection and no settings controls leak into task area',async()=>{
 const{c,stage,choose,click,cleanup}=mount();await choose('file',selected(bytes(1200),'first.bin'));await click('save');await click('reopen');await choose('file',selected(bytes(2200),'second.bin'));assert.equal(c.nodes.confirmation.hidden,true);assert.equal(c.getState().manifest.file.name,'second.bin');await click('confirm');assert.equal(c.getState().manifest.file.name,'second.bin');assert.equal(textTree(stage).includes('下一份文件的块大小'),false);cleanup();
 const doc={createElement(tag){return Object.assign(new Node(tag),{ownerDocument:doc});}},stageOnly=doc.createElement('div');const view=createResumableFile({stage:stageOnly});assert.equal(view.nodes.chunkSize,undefined);view.dispose();
});
test('failed reconciliation cannot retain stale success counters after removing a bad local block',async()=>{
 const sink=createLocalByteSink(),read=sink.read;let breakRead=false;sink.read=request=>{const bytes=read(request);if(breakRead){if(request.index===1)throw Error('READ_DENIED');if(request.index===0&&bytes)bytes[0]^=1;}return bytes;};const{w}=await prepared({sink});await w.run();breakRead=true;await w.resume();assert.equal(w.getState().phase,'FAILED');assert.equal(w.getState().localVerifiedBytes,0);assert.deepEqual(w.getState().verifiedIndices,[]);assert.equal(sink.stats().chunks,3);breakRead=false;await w.retry();assert.equal(w.getState().phase,'LOCAL_COMPLETE');assert.equal(sink.stats().writes,5);
});

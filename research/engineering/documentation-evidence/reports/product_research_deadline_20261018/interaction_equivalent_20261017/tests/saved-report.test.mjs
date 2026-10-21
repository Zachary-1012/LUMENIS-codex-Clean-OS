import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createSavedReportController,validateSavedReportJournal,savedReportArtifactBytes,savedReportLocalEdits,createLockedReportStorage,SAVED_REPORT_LIMITS} from '../src/saved-report.mjs';
const sha256=async bytes=>createHash('sha256').update(bytes).digest('hex');
const clone=x=>JSON.parse(JSON.stringify(x));
function memory(){const map=new Map();return {map,getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};}
function setup(storage=memory(),extra={}){return {storage,c:createSavedReportController({storage,sha256,...extra})};}
const edit=(c,markdown='正文 e\u0301 👨‍👩‍👧‍👦 한국어 مرحبا\r\n<script>bad()</script>')=>c.edit({title:'作者文稿',markdown});
const first=async c=>{edit(c);const r=await c.save({requestId:'request_001'});assert.equal(r.ok,true,JSON.stringify(r));return r.version;};
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
function delayedSet(base){const entered=deferred(),release=deferred();let once=true;return {...base,entered,release,async setItem(k,v){if(once){once=false;entered.resolve();await release.promise;}base.setItem(k,v);}};}

test('complete author journey: UTF8 content, immutable linear revisions, old-view isolation, local reopen, review and exact export',async()=>{
 const {c,storage}=setup();const v1=await first(c);const original=clone(v1);assert.equal(v1.contentSha256,await sha256(savedReportArtifactBytes(v1)));
 edit(c,'修订正文\n# Chapter 🙂');const v2=(await c.save({requestId:'request_002',reason:'补充章节'})).version;
 assert.equal(v2.parentId,v1.localId);assert.equal(v2.version,2);assert.equal(v2.workId,v1.workId);assert.deepEqual(c.state().versions[0],original);
 c.viewVersion(v1.localId);assert.equal(c.state().draft.markdown,v2.markdown);assert.equal(c.state().draft.baseVersionId,v2.localId);
 c.edit({markdown:'尚未保存的新意见',selection:{start:1,end:4,direction:'forward',unit:'utf16'},scroll:82});assert.equal((await c.checkpoint()).ok,true);
 const reopened=setup(storage).c;assert.equal((await reopened.restore()).ok,true);assert.equal(reopened.state().draft.markdown,'尚未保存的新意见');assert.equal(reopened.state().draft.dirty,true);assert.equal(reopened.state().draft.scroll,82);
 reopened.viewVersion(v2.localId);assert.equal(reopened.reviewVersion({versionId:v2.localId,verdict:'reviewed',notes:'已读文字，事实未核',unknowns:['销售数值']}).ok,true);await reopened.checkpoint();
 const out=await reopened.prepareExport({versionId:v2.localId,format:'md'});assert.equal(out.ok,true);assert.equal(new TextDecoder().decode(out.bytes),v2.markdown);assert.equal(out.bytesSha256,await sha256(out.bytes));assert.equal(out.contentSha256,v2.contentSha256);assert.equal(out.diskDelivery,'NOT_VERIFIED');assert.equal(out.status,'bytes-prepared');
 assert.equal(reopened.state().productBinding,'UNBOUND');assert.equal(reopened.state().permissions.provenance,'FIXTURE_ONLY');
});

test('save snapshot and continued editing: readback never clears newer dirty draft',async()=>{
 const storage=delayedSet(memory()),{c}=setup(storage);edit(c,'snapshot');const p=c.save({requestId:'request_001'});await storage.entered.promise;
 c.edit({markdown:'newer draft'});const double=await c.save({requestId:'request_001'});assert.equal(double.code,'OPERATION_PENDING');assert.equal(c.state().pending.kind,'save');
 storage.release.resolve();assert.equal((await p).ok,true);assert.equal(c.state().versions[0].markdown,'snapshot');assert.equal(c.state().draft.markdown,'newer draft');assert.equal(c.state().draft.dirty,true);assert.equal(c.state().journalDirty,true);
 assert.equal((await c.checkpoint()).ok,true);const r=setup(storage).c;await r.restore();assert.equal(r.state().draft.markdown,'newer draft');
});

test('request retry is idempotent and changed input is refused, including after reopen',async()=>{
 const {c,storage}=setup();await first(c);assert.equal((await c.save({requestId:'request_001'})).replayed,true);assert.equal(c.state().versions.length,1);
 c.edit({markdown:'different'});assert.equal((await c.save({requestId:'request_001'})).code,'REQUEST_REUSE_CONFLICT');assert.equal(c.state().versions.length,1);
 const r=setup(storage).c;await r.restore();r.edit({markdown:'different'});assert.equal((await r.save({requestId:'request_001'})).code,'REQUEST_REUSE_CONFLICT');
});

test('adopting historical content creates next child of current head, never a branch',async()=>{
 const {c}=setup();const v1=await first(c);c.edit({markdown:'v2'});const v2=(await c.save({requestId:'request_002',reason:'change'})).version;
 c.adoptVersion(v1.localId);assert.equal(c.state().draft.baseVersionId,v2.localId);assert.equal(c.state().draft.dirty,true);
 const v3=(await c.save({requestId:'request_003',reason:'显式采用第一版'})).version;assert.equal(v3.parentId,v2.localId);assert.equal(v3.version,3);assert.equal(v3.markdown,v1.markdown);
});

test('local human review stays hash-bound and is not inherited by a new version',async()=>{
 const {c,storage}=setup();const v1=await first(c);c.reviewVersion({versionId:v1.localId,verdict:'reviewed',notes:'人工意见',unknowns:['未核事实']});
 c.edit({markdown:'v2'});const v2=(await c.save({requestId:'request_002',reason:'change'})).version;
 assert.equal(c.state().reviews.length,1);assert.equal(c.state().reviews[0].versionId,v1.localId);assert.equal(c.state().reviews.some(r=>r.versionId===v2.localId),false);
 const r=setup(storage).c;await r.restore();assert.equal(r.state().reviews[0].contentSha256,v1.contentSha256);
});

test('separate cooperating controllers detect conflicting head and preserve their own draft',async()=>{
 const {c,storage}=setup();await first(c);const other=setup(storage).c;await other.restore();c.edit({markdown:'winner'});other.edit({markdown:'loser retained'});
 const [a,b]=await Promise.all([c.save({requestId:'request_002',reason:'a'}),other.save({requestId:'request_003',reason:'b'})]);assert.equal(a.ok,true);assert.equal(b.code,'HEAD_CONFLICT');assert.equal(other.state().draft.markdown,'loser retained');assert.equal(other.state().versions.length,1);
 assert.equal((await other.restore({preserveDraft:true})).ok,true);assert.equal(other.state().draft.markdown,'loser retained');assert.equal(other.state().draft.baseVersionId,a.version.localId);
 const merged=await other.save({requestId:'request_004',reason:'明确采用最新父版'});assert.equal(merged.version.version,3);
});

test('storage write failure retains dirty input and confirmed head; same request retries',async()=>{
 const base=memory();let broken=false;const storage={...base,setItem(k,v){if(broken)throw Error('quota');base.setItem(k,v);}};const {c}=setup(storage);await first(c);c.edit({markdown:'unsaved'});broken=true;
 assert.equal((await c.save({requestId:'request_002',reason:'change'})).code,'STORAGE_UNAVAILABLE');assert.equal(c.state().versions.length,1);assert.equal(c.state().draft.markdown,'unsaved');assert.equal(c.state().draft.dirty,true);
 broken=false;const r=await c.save({requestId:'request_002',reason:'change'});assert.equal(r.ok,true);assert.equal(r.version.version,2);
});

test('readback mismatch is never success, then same request finds actual durable version without duplicate',async()=>{
 const base=memory();let bad=false;const storage={...base,getItem(k){if(bad){bad=false;return 'corrupt readback';}return base.getItem(k);},setItem(k,v){base.setItem(k,v);bad=true;}};
 const {c}=setup(storage);edit(c);const r=await c.save({requestId:'request_001'});assert.equal(r.code,'READBACK_MISMATCH');assert.equal(c.state().versions.length,0);assert.equal(c.state().draft.dirty,true);
 const retry=await c.save({requestId:'request_001'});assert.equal(retry.ok,true);assert.equal(retry.replayed,true);assert.equal(c.state().versions.length,1);
});

test('storage get error and malformed journal do not erase current input',async()=>{
 const base=memory(),{c}=setup(base);edit(c,'retain me');base.setItem(c.storageKey(),'{bad');assert.equal((await c.restore()).ok,false);assert.equal(c.state().draft.markdown,'retain me');assert.equal((await c.save({requestId:'request_001'})).ok,false);assert.equal(base.getItem(c.storageKey()),'{bad');
 const other=setup({getItem(){throw Error('denied');},setItem(){throw Error('denied');}}).c;edit(other);assert.equal((await other.restore()).code,'STORAGE_UNAVAILABLE');assert.equal(other.state().draft.dirty,true);
});

test('journal schema rejects chain, references, hash, reviews, dirty lies, unknown keys and bounded sizes',async()=>{
 const {c,storage}=setup();await first(c);const raw=storage.getItem(c.storageKey()),original=JSON.parse(raw);
 const mutations=[j=>j.versions.push(clone(j.versions[0])),j=>j.versions[0].parentId='local-report-x',j=>j.versions[0].markdown='tampered',j=>j.draft.baseVersionId='missing',j=>j.viewingVersionId='missing',j=>j.draft.dirty=true,j=>j.extra='unbounded',j=>j.productBinding='BOUND',j=>j.reviews.push({versionId:j.versions[0].localId,contentSha256:'f'.repeat(64),verdict:'reviewed',notes:'x',unknowns:[],kind:'LOCAL_HUMAN_REVIEW_ONLY'}),j=>j.draft.selection.end=999999];
 for(const mutate of mutations){const j=clone(original);mutate(j);await assert.rejects(validateSavedReportJournal(JSON.stringify(j),'report-demo',sha256));}
 await assert.rejects(validateSavedReportJournal(' '.repeat(SAVED_REPORT_LIMITS.journalBytes+1),'report-demo',sha256));
});

test('title limits are code points and UTF8 bytes reject unpaired surrogates without normalization',async()=>{
 const {c}=setup();assert.equal(c.edit({title:'🙂'.repeat(300),markdown:'e\u0301\r\n‮مرحبا'}).ok,true);const r=await c.save({requestId:'request_001'});assert.equal(r.ok,true);assert.equal(r.version.title.length,600);assert.equal(r.version.markdown,'e\u0301\r\n‮مرحبا');
 assert.equal(c.edit({title:'🙂'.repeat(301)}).code,'CONTENT_INVALID');assert.equal(c.edit({markdown:'\ud800'}).code,'CONTENT_INVALID');assert.equal(c.edit({markdown:'🙂'.repeat(65537)}).code,'CONTENT_INVALID');
});

test('local comparison uses exact full-field expected/value but cannot impersonate production expected_sha256',async()=>{
 const {c}=setup();const v=await first(c);const edits=savedReportLocalEdits(v,{title:'new',markdown:'👨‍👩‍👧‍👦 e\u0301'});assert.equal(edits.localParentSha256,v.contentSha256);assert.equal(edits.binding,'LOCAL_REVIEW_ONLY');assert.equal(Object.hasOwn(edits,'expected_sha256'),false);assert.deepEqual(edits.edits,[{pointer:'/title',expected:v.title,value:'new'},{pointer:'/markdown',expected:v.markdown,value:'👨‍👩‍👧‍👦 e\u0301'}]);
});

test('cancel before write prevents effect and late hash response cannot mutate state',async()=>{
 const gate=deferred();let calls=0;const storage=memory();const {c}=setup(storage,{sha256:async b=>{if(calls++===0)await gate.promise;return sha256(b);}});edit(c);const p=c.save({requestId:'request_001'});c.cancel();gate.resolve();assert.equal((await p).code,'OPERATION_INVALIDATED');assert.equal(storage.map.size,0);assert.equal(c.state().versions.length,0);
});

test('cancel during persistent write does not promise rollback; explicit reread recovers written version',async()=>{
 const storage=delayedSet(memory()),{c}=setup(storage);edit(c);const p=c.save({requestId:'request_001'});await storage.entered.promise;
 assert.match(c.cancel().status,/not-undone/);storage.release.resolve();const out=await p;assert.equal(out.code,'OPERATION_INVALIDATED');assert.equal(out.persistenceOutcome,'local-write-readback-confirmed');assert.equal(c.state().versions.length,0);assert.equal(c.state().persistence,'cancelled-outcome-unknown');
 assert.equal((await c.restore()).ok,true);assert.equal(c.state().versions.length,1);
});

test('scope switch isolates delayed save and leaves old-scope persisted result only in its own journal',async()=>{
 const storage=delayedSet(memory()),{c}=setup(storage);edit(c);const oldKey=c.storageKey();const p=c.save({requestId:'request_001'});await storage.entered.promise;c.switchWorkspace('another');storage.release.resolve();assert.equal((await p).code,'OPERATION_INVALIDATED');assert.equal(c.state().workspaceKey,'another');assert.equal(c.state().versions.length,0);assert.equal(storage.getItem(c.storageKey()),null);assert.notEqual(storage.getItem(oldKey),null);
});

test('fixture read/write/export are separate and read revocation hides saved content and reviews',async()=>{
 const {c}=setup();const v=await first(c);c.edit({markdown:'new input'});c.setPermissions({read:true,write:false,export:true});assert.equal(c.state().draft.markdown,'new input');assert.equal((await c.save({requestId:'request_002',reason:'x'})).code,'WRITE_DENIED');assert.equal((await c.prepareExport({versionId:v.localId,format:'txt'})).ok,true);
 c.setPermissions({read:true,write:true,export:false});assert.equal((await c.prepareExport({versionId:v.localId,format:'md'})).code,'EXPORT_DENIED');assert.equal(c.state().versions.length,1);assert.equal((await c.save({requestId:'request_002',reason:'x'})).ok,true);
 c.setPermissions({read:false,write:true,export:true});assert.equal(c.state().versions.length,0);assert.equal(c.state().draft.markdown,'');assert.equal(c.state().reviews.length,0);assert.equal(c.state().lastExport,null);assert.equal((await c.restore()).code,'READ_DENIED');
});

test('write revocation invalidates save already awaiting hash without losing entered text',async()=>{
 const gate=deferred();let calls=0;const {c,storage}=setup(memory(),{sha256:async b=>{if(calls++===0)await gate.promise;return sha256(b);}});edit(c,'keep');const p=c.save({requestId:'request_001'});c.setPermissions({read:true,write:false,export:true});gate.resolve();assert.equal((await p).code,'OPERATION_INVALIDATED');assert.equal(c.state().draft.markdown,'keep');assert.equal(storage.map.size,0);
});

test('export binds exact persisted version and refuses unsupported formats',async()=>{
 const {c}=setup();const v=await first(c);c.edit({markdown:'not exported'});for(const format of ['md','txt']){const out=await c.prepareExport({versionId:v.localId,format});assert.equal(new TextDecoder().decode(out.bytes),v.markdown);assert.equal(out.byteLength,new TextEncoder().encode(v.markdown).length);}
 assert.equal((await c.prepareExport({versionId:v.localId,format:'pdf'})).code,'EXPORT_FORMAT_UNBOUND');
});

test('selection change or export revocation rejects delayed export response',async()=>{
 const gate=deferred();let block=false;const {c}=setup(memory(),{sha256:async b=>{if(block)await gate.promise;return sha256(b);}});const v1=await first(c);c.edit({markdown:'v2'});const v2=(await c.save({requestId:'request_002',reason:'x'})).version;
 block=true;const p=c.prepareExport({versionId:v2.localId,format:'md'});c.viewVersion(v1.localId);gate.resolve();assert.equal((await p).code,'EXPORT_SELECTION_CHANGED');assert.equal(c.state().lastExport,null);
 const gate2=deferred();let block2=false;const r=setup(memory(),{sha256:async b=>{if(block2)await gate2.promise;return sha256(b);}}).c;const v=await first(r);block2=true;const p2=r.prepareExport({versionId:v.localId,format:'md'});r.setPermissions({read:true,write:true,export:false});gate2.resolve();assert.equal((await p2).code,'OPERATION_INVALIDATED');assert.equal(r.state().lastExport,null);
});

test('restore refuses to overwrite an edit made while async readback is pending',async()=>{
 const {c,storage}=setup();await first(c);const gate=deferred();const other=setup({...storage,async getItem(k){await gate.promise;return storage.getItem(k);}}).c;
 const p=other.restore();other.edit({title:'mine',markdown:'typed while opening'});gate.resolve();assert.equal((await p).code,'DRAFT_CHANGED_DURING_RESTORE');assert.equal(other.state().draft.markdown,'typed while opening');
});

test('read-only view changes are independent and discard only resets draft to current head',async()=>{
 const {c}=setup();const v=await first(c);c.edit({markdown:'temporary'});c.viewVersion(v.localId);assert.equal(c.state().draft.markdown,'temporary');c.discardDraft();assert.equal(c.state().draft.markdown,v.markdown);assert.equal(c.state().draft.dirty,false);assert.equal(c.state().versions.length,1);
});

test('missing host cross-context lock fails closed; injected lock manager is used',async()=>{
 const base=memory();const {c}=setup(createLockedReportStorage(base));edit(c);assert.equal((await c.save({requestId:'request_001'})).code,'EXCLUSIVE_LOCK_UNAVAILABLE');assert.equal(base.map.size,0);
 let name;const other=setup(createLockedReportStorage(base,{request:async(n,fn)=>{name=n;return fn();}})).c;await first(other);assert.match(name,/local-review/);assert.equal(other.state().concurrencyBoundary,'HOST_EXCLUSIVE_LOCK');
});

test('public state snapshots cannot mutate internal history',async()=>{
 const {c}=setup();await first(c);const s=c.state();s.versions[0].markdown='injected';s.draft.markdown='injected';s.permissions.read=false;assert.notEqual(c.state().versions[0].markdown,'injected');assert.equal(c.state().permissions.read,true);
});

test('same-head journal changes from another editor are not silently overwritten',async()=>{
 const {c,storage}=setup();const v=await first(c);const other=setup(storage).c;await other.restore();
 c.reviewVersion({versionId:v.localId,verdict:'needs-work',notes:'first editor note'});await c.checkpoint();other.edit({markdown:'second editor draft'});
 assert.equal((await other.checkpoint()).code,'JOURNAL_CONCURRENT_CHANGE');assert.equal((await other.save({requestId:'request_002',reason:'change'})).code,'JOURNAL_CONCURRENT_CHANGE');assert.equal(other.state().draft.markdown,'second editor draft');
 await other.restore({preserveDraft:true});assert.equal(other.state().reviews[0].notes,'first editor note');assert.equal((await other.save({requestId:'request_003',reason:'explicitly reconciled'})).ok,true);
});

test('retrying an older durable request cannot silently rebase onto another editor newer head',async()=>{
 const base=memory();let bad=false;const storage={...base,getItem(k){if(bad){bad=false;return 'bad';}return base.getItem(k);},setItem(k,v){base.setItem(k,v);bad=true;}};
 const {c}=setup(storage);edit(c);assert.equal((await c.save({requestId:'request_001'})).code,'READBACK_MISMATCH');
 const other=setup(base).c;await other.restore();other.edit({markdown:'advanced'});await other.save({requestId:'request_002',reason:'new head'});
 assert.equal((await c.save({requestId:'request_001'})).code,'HEAD_CONFLICT');assert.equal(c.state().confirmedHeadId,null);assert.equal(c.state().draft.dirty,true);
});

test('fresh controller cannot overwrite an existing unsaved journal without explicit restore',async()=>{
 const {c,storage}=setup();edit(c,'original unsaved journal');await c.checkpoint();const other=setup(storage).c;edit(other,'new accidental draft');
 assert.equal((await other.save({requestId:'request_001'})).code,'JOURNAL_CONCURRENT_CHANGE');assert.equal((await other.checkpoint()).code,'JOURNAL_CONCURRENT_CHANGE');
 await other.restore();assert.equal(other.state().draft.markdown,'original unsaved journal');
});

test('subscribe immediately publishes isolated state, unsubscribes and tolerates view callback failure',async()=>{
 const {c}=setup();let calls=0;const off=c.subscribe(s=>{calls++;s.draft.title='external mutation';});assert.equal(calls,1);assert.equal(c.state().draft.title,'');
 edit(c);assert.equal(calls,2);off();c.edit({markdown:'more'});assert.equal(calls,2);
 const removeBroken=c.subscribe(()=>{throw Error('view error');});assert.equal((await c.save({requestId:'request_001'})).ok,true);removeBroken();
});


test('local edits reject production-shaped or hash-only parent; removed Owner helper cannot manufacture a revise request',async()=>{
 const module=await import('../src/saved-report.mjs');assert.equal(Object.hasOwn(module,'savedReportOwnerEdits'),false);
 const draft={title:'new',markdown:'new body'};
 for(const parent of [{artifact_id:'ART-server',sha256:'a'.repeat(64),title:'old',markdown:'old body'},{contentSha256:'a'.repeat(64),title:'old',markdown:'old body'}]){
  assert.throws(()=>savedReportLocalEdits(parent,draft),{code:'LOCAL_PARENT_REQUIRED'});
 }
 const {c}=setup();const v=await first(c);const local=savedReportLocalEdits(v,draft);assert.deepEqual(Object.keys(local).sort(),['binding','edits','localParentId','localParentSha256']);
});

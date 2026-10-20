/** Independent review fixture. No network, product adapter, Evaluation or server IDs.
 * All storage is explicitly supplied by the host. Permission switches are fixtures.
 */
export const SAVED_REPORT_LIMITS = Object.freeze({title:300, markdownBytes:262144, reason:4000, versions:64, reviews:128, journalBytes:2097152});
const enc = new TextEncoder();
const copy = x => JSON.parse(JSON.stringify(x));
const fail = code => { throw Object.assign(new Error(code), {code}); };
const exact = (x, keys) => x && typeof x === 'object' && !Array.isArray(x) && Object.keys(x).sort().join('|') === [...keys].sort().join('|');
const str = (s,n,required=false) => typeof s === 'string' && [...s].length <= n && (!required || s.trim().length>0) && !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(s);
const hashOK = x => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);
const requestOK = x => typeof x === 'string' && /^[A-Za-z0-9_-]{8,128}$/.test(x);
const scopeOK = x => typeof x === 'string' && /^[A-Za-z0-9_-]{1,80}$/.test(x);
const head = j => j.versions.at(-1) || null;
const emptyDraft = () => ({title:'',markdown:'',baseVersionId:null,editRevision:0,selection:{start:0,end:0,direction:'none',unit:'utf16'},scroll:0,dirty:false});
const initial = workspaceKey => ({schemaVersion:1,identity:'LOCAL_REVIEW_ONLY',productBinding:'UNBOUND',workspaceKey,versions:[],draft:emptyDraft(),viewingVersionId:null,reviews:[]});
const documentFor = v => ({schema:'local-review.saved-report/v1',workspaceKey:v.workspaceKey,localId:v.localId,workId:v.workId,version:v.version,parentId:v.parentId,parentSha256:v.parentSha256,title:v.title,markdown:v.markdown,reason:v.reason,requestId:v.requestId,inputFingerprint:v.inputFingerprint});
export function savedReportArtifactBytes(version) { return enc.encode(JSON.stringify(documentFor(version))); }
export async function browserReportSha256(bytes) {
  if (!globalThis.crypto?.subtle) fail('SHA256_UNAVAILABLE');
  return [...new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
}
async function digest(sha256, bytes) { const result=await sha256(bytes); if(!hashOK(result)) fail('SHA256_INVALID'); return result; }
function validateContent(title,markdown,required=false) {
  if(!str(title,SAVED_REPORT_LIMITS.title,required) || !str(markdown,SAVED_REPORT_LIMITS.markdownBytes,required) || enc.encode(markdown).length>SAVED_REPORT_LIMITS.markdownBytes) fail('CONTENT_INVALID');
}
function validateDraft(d, versions) {
  if(!exact(d,['title','markdown','baseVersionId','editRevision','selection','scroll','dirty'])) fail('JOURNAL_SCHEMA_INVALID');
  validateContent(d.title,d.markdown);
  if(!Number.isSafeInteger(d.editRevision)||d.editRevision<0||typeof d.dirty!=='boolean'||!Number.isFinite(d.scroll)||d.scroll<0||d.scroll>1e8) fail('JOURNAL_SCHEMA_INVALID');
  const s=d.selection;
  if(!exact(s,['start','end','direction','unit'])||s.unit!=='utf16'||!['none','forward','backward'].includes(s.direction)||!Number.isInteger(s.start)||!Number.isInteger(s.end)||s.start<0||s.end<s.start||s.end>d.markdown.length) fail('SELECTION_INVALID');
  const base=versions.find(v=>v.localId===d.baseVersionId);
  if(d.baseVersionId!==null&&!base) fail('JOURNAL_REFERENCE_INVALID');
  if(d.baseVersionId!==(versions.at(-1)?.localId??null)) fail('JOURNAL_BASE_INVALID');
  const dirty=base ? d.title!==base.title||d.markdown!==base.markdown : Boolean(d.title||d.markdown);
  if(dirty!==d.dirty) fail('JOURNAL_DIRTY_INVALID');
}
function inputOf(v) {return {title:v.title,markdown:v.markdown,reason:v.reason,baseVersionId:v.parentId};}
export async function validateSavedReportJournal(raw,workspaceKey,sha256=browserReportSha256) {
  if(typeof raw!=='string'||enc.encode(raw).length>SAVED_REPORT_LIMITS.journalBytes) fail('JOURNAL_SIZE_INVALID');
  let j;try{j=JSON.parse(raw);}catch{fail('JOURNAL_JSON_INVALID');}
  if(!exact(j,['schemaVersion','identity','productBinding','workspaceKey','versions','draft','viewingVersionId','reviews'])||j.schemaVersion!==1||j.identity!=='LOCAL_REVIEW_ONLY'||j.productBinding!=='UNBOUND'||j.workspaceKey!==workspaceKey||!scopeOK(j.workspaceKey)||!Array.isArray(j.versions)||j.versions.length>SAVED_REPORT_LIMITS.versions||!Array.isArray(j.reviews)||j.reviews.length>SAVED_REPORT_LIMITS.reviews) fail('JOURNAL_SCHEMA_INVALID');
  const ids=new Set(), requests=new Set();
  for(let i=0;i<j.versions.length;i++) {
    const v=j.versions[i], p=j.versions[i-1];
    if(!exact(v,['workspaceKey','localId','workId','version','parentId','parentSha256','title','markdown','reason','requestId','inputFingerprint','contentSha256'])||v.workspaceKey!==workspaceKey||v.localId!==`local-report-${v.requestId}`||v.workId!==(p?.workId??`local-work-${v.requestId}`)||v.version!==i+1||v.parentId!==(p?.localId??null)||v.parentSha256!==(p?.contentSha256??null)||!requestOK(v.requestId)||ids.has(v.localId)||requests.has(v.requestId)||!hashOK(v.contentSha256)||!hashOK(v.inputFingerprint)||!str(v.reason,SAVED_REPORT_LIMITS.reason,i>0)) fail('JOURNAL_CHAIN_INVALID');
    validateContent(v.title,v.markdown,true);
    if(await digest(sha256,enc.encode(JSON.stringify(inputOf(v))))!==v.inputFingerprint||await digest(sha256,savedReportArtifactBytes(v))!==v.contentSha256) fail('JOURNAL_HASH_INVALID');
    ids.add(v.localId); requests.add(v.requestId);
  }
  validateDraft(j.draft,j.versions);
  if(j.viewingVersionId!==null&&!ids.has(j.viewingVersionId)) fail('JOURNAL_REFERENCE_INVALID');
  for(const r of j.reviews) {
    const v=j.versions.find(v=>v.localId===r?.versionId);
    if(!exact(r,['versionId','contentSha256','verdict','notes','unknowns','kind'])||!v||v.contentSha256!==r.contentSha256||r.kind!=='LOCAL_HUMAN_REVIEW_ONLY'||!['reviewed','needs-work'].includes(r.verdict)||!str(r.notes,4000,true)||!Array.isArray(r.unknowns)||r.unknowns.length>32||r.unknowns.some(s=>!str(s,500,true))) fail('JOURNAL_REVIEW_INVALID');
  }
  return j;
}
// An optional host lock must serialize all writers (e.g. Web Locks / a CAS adapter).
// The fallback protects cooperating controllers sharing this exact storage object only.
const mutexes=new WeakMap();
async function lock(storage,key,fn) {
  if(typeof storage.withLock==='function') return storage.withLock(key,fn);
  let map=mutexes.get(storage);if(!map){map=new Map();mutexes.set(storage,map);}
  const prior=map.get(key)||Promise.resolve();let release;
  const gate=new Promise(r=>release=r);const tail=prior.catch(()=>{}).then(()=>gate);map.set(key,tail);
  await prior.catch(()=>{});
  try{return await fn();}finally{release();if(map.get(key)===tail)map.delete(key);}
}
/** Wrap browser Storage with an explicitly supplied cross-context lock manager.
 * Without locks, writes fail closed instead of claiming atomic multi-tab persistence.
 */
export function createLockedReportStorage(storage,locks) {
  return {getItem:key=>storage.getItem(key),setItem:(key,value)=>storage.setItem(key,value),
    concurrencyBoundary:'HOST_EXCLUSIVE_LOCK',
    withLock:(key,fn)=>{if(!locks?.request)fail('EXCLUSIVE_LOCK_UNAVAILABLE');return locks.request(`local-review:${key}`,fn);}};
}
/** Local comparison only. Deliberately cannot be sent as an Owner revise request. */
export function savedReportLocalEdits(parent,draft) {
  validateContent(draft.title,draft.markdown,true);
  if(!parent||!requestOK(parent.requestId)||parent.localId!==`local-report-${parent.requestId}`||!scopeOK(parent.workspaceKey)||!hashOK(parent.contentSha256)) fail('LOCAL_PARENT_REQUIRED');
  validateContent(parent.title,parent.markdown,true);
  return {binding:'LOCAL_REVIEW_ONLY',localParentId:parent.localId,localParentSha256:parent.contentSha256,edits:[{pointer:'/title',expected:parent.title,value:draft.title},{pointer:'/markdown',expected:parent.markdown,value:draft.markdown}]};
}
export function createSavedReportController({storage,sha256=browserReportSha256,workspaceKey='report-demo',permissions={read:true,write:true,export:true},onChange=()=>{}}={}) {
  if(!storage||typeof storage.getItem!=='function'||typeof storage.setItem!=='function'||!scopeOK(workspaceKey)) fail('CONFIG_INVALID');
  let j=initial(workspaceKey), generation=0, viewGeneration=0, pending=null, persistence='unsaved', error=null, journalDirty=false, lastExport=null, knownRaw=null;
  let perms={read:false,write:false,export:false};const attempts=new Map(),listeners=new Set();
  function validPermissions(p){if(!exact(p,['read','write','export'])||Object.values(p).some(v=>typeof v!=='boolean'))fail('PERMISSION_FIXTURE_INVALID');return {...p};}
  perms=validPermissions(permissions);
  const keyFor=s=>`lumenis-review:saved-report:v1:${s}`;
  function state(){return copy({...j,...(!perms.read?{versions:[],reviews:[],draft:emptyDraft(),viewingVersionId:null}:{}),permissions:{...perms,provenance:'FIXTURE_ONLY'},pending:perms.read?pending:null,persistence,error,journalDirty,generation,lastExport:perms.read&&perms.export?lastExport:null,confirmedHeadId:perms.read?head(j)?.localId??null:null,concurrencyBoundary:storage.concurrencyBoundary||'SAME_STORAGE_OBJECT_ONLY',selectionUnit:'utf16-editor-only; owner edits use full fields'});}
  function emit(){for(const listener of [onChange,...listeners])try{listener(state());}catch{/* Rendering cannot falsify a persistence receipt. */}}
  function subscribe(listener){if(typeof listener!=='function')fail('LISTENER_INVALID');listeners.add(listener);try{listener(state());}catch{}return ()=>listeners.delete(listener);}
  function resultError(e){const code=e?.code||'STORAGE_UNAVAILABLE';error=code;emit();return {ok:false,code};}
  function need(action){if(!perms.read)fail('READ_DENIED');if(action&&!perms[action])fail(`${action.toUpperCase()}_DENIED`);}
  function active(g,scope,action){if(g!==generation||scope!==j.workspaceKey)fail('OPERATION_INVALIDATED');need(action);}
  function changed(){journalDirty=true;lastExport=null;emit();}
  function recompute(){const b=j.versions.find(v=>v.localId===j.draft.baseVersionId);j.draft.dirty=b?j.draft.title!==b.title||j.draft.markdown!==b.markdown:Boolean(j.draft.title||j.draft.markdown);}
  function readVersion(id){need();const v=j.versions.find(v=>v.localId===id);if(!v)fail('VERSION_UNKNOWN');return v;}
  async function readJournal(scope){const raw=await storage.getItem(keyFor(scope));return {raw,journal:raw===null?initial(scope):await validateSavedReportJournal(raw,scope,sha256)};}
  async function writeJournal(next, expectedRaw, g,scope,action){
    const raw=JSON.stringify(next);await validateSavedReportJournal(raw,scope,sha256);
    active(g,scope,action);
    // Detect even unrelated draft/review changes rather than overwrite them silently.
    if(await storage.getItem(keyFor(scope))!==expectedRaw)fail('JOURNAL_CONCURRENT_CHANGE');
    active(g,scope,action);
    await storage.setItem(keyFor(scope),raw);
    const actual=await storage.getItem(keyFor(scope));
    if(actual!==raw)fail('READBACK_MISMATCH');
    await validateSavedReportJournal(actual,scope,sha256);
    return raw;
  }
  function edit(patch){try{need('write');if(!patch||Object.keys(patch).some(k=>!['title','markdown','selection','scroll'].includes(k)))fail('EDIT_INVALID');
    const next={...j.draft,...copy(patch),editRevision:j.draft.editRevision+1};
    validateContent(next.title,next.markdown);
    if(!('selection'in patch)&&'markdown'in patch)next.selection={...next.selection,start:Math.min(next.selection.start,next.markdown.length),end:Math.min(next.selection.end,next.markdown.length)};
    const old=j.draft;j.draft=next;recompute();try{validateDraft(next,j.versions);}catch(e){j.draft=old;throw e;}changed();return {ok:true};
  }catch(e){return resultError(e);}}
  async function save({requestId,reason=''}={}) {
    if(pending)return {ok:false,code:'OPERATION_PENDING'};
    let g,scope,snapshot,input,writeStarted=false;
    try {
      need('write');if(pending)fail('OPERATION_PENDING');if(!requestOK(requestId))fail('REQUEST_ID_INVALID');
      validateContent(j.draft.title,j.draft.markdown,true);if(!str(reason,SAVED_REPORT_LIMITS.reason))fail('REASON_REQUIRED');
      snapshot=copy(j.draft);g=generation;scope=j.workspaceKey;
      const priorAttempt=attempts.get(requestId),priorVersion=j.versions.find(v=>v.requestId===requestId);
      input={title:snapshot.title,markdown:snapshot.markdown,reason,baseVersionId:priorAttempt?.baseVersionId??priorVersion?.parentId??snapshot.baseVersionId};
      // null is a legitimate original base for first-save retries.
      if(priorAttempt) input.baseVersionId=priorAttempt.baseVersionId;
      else if(priorVersion) input.baseVersionId=priorVersion.parentId;
      if(!str(reason,SAVED_REPORT_LIMITS.reason,Boolean(input.baseVersionId)))fail('REASON_REQUIRED');
      if(priorAttempt&&JSON.stringify(priorAttempt)!==JSON.stringify(input))fail('REQUEST_REUSE_CONFLICT');
      if(priorVersion&&JSON.stringify(inputOf(priorVersion))!==JSON.stringify(input))fail('REQUEST_REUSE_CONFLICT');
      if(attempts.size>=128&&!priorAttempt)fail('REQUEST_LIMIT_REACHED');
      attempts.set(requestId,copy(input));
      pending={kind:'save',requestId,inputFingerprint:null,baseVersionId:input.baseVersionId,editRevision:snapshot.editRevision,operationGeneration:g};persistence='writing';error=null;emit();
      const fingerprint=await digest(sha256,enc.encode(JSON.stringify(input)));active(g,scope,'write');pending.inputFingerprint=fingerprint;
      return await lock(storage,keyFor(scope),async()=>{
        active(g,scope,'write');const {raw,journal:stored}=await readJournal(scope);active(g,scope,'write');
        let version=stored.versions.find(v=>v.requestId===requestId),replayed=Boolean(version),confirmedRaw=raw;
        if(version&&version.inputFingerprint!==fingerprint)fail('REQUEST_REUSE_CONFLICT');
        if(version&&(head(stored)?.localId??null)!==(head(j)?.localId??null)&&head(stored)?.localId!==version.localId)fail('HEAD_CONFLICT');
        if(!version){
          const parent=head(stored);
          if((parent?.localId??null)!==input.baseVersionId||(head(j)?.localId??null)!==input.baseVersionId)fail('HEAD_CONFLICT');
          if(raw!==knownRaw)fail('JOURNAL_CONCURRENT_CHANGE');
          if(stored.versions.length>=SAVED_REPORT_LIMITS.versions)fail('VERSION_LIMIT_REACHED');
          version={workspaceKey:scope,localId:`local-report-${requestId}`,workId:parent?.workId??`local-work-${requestId}`,version:stored.versions.length+1,parentId:parent?.localId??null,parentSha256:parent?.contentSha256??null,title:input.title,markdown:input.markdown,reason,requestId,inputFingerprint:fingerprint,contentSha256:''};
          version.contentSha256=await digest(sha256,savedReportArtifactBytes(version));active(g,scope,'write');
          const next=copy(j);next.versions=[...stored.versions,version];next.reviews=[...stored.reviews,...j.reviews.filter(r=>!stored.reviews.some(s=>JSON.stringify(s)===JSON.stringify(r)))];
          next.draft.baseVersionId=version.localId;next.draft.dirty=next.draft.title!==version.title||next.draft.markdown!==version.markdown;next.viewingVersionId=version.localId;
          writeStarted=true;confirmedRaw=await writeJournal(next,raw,g,scope,'write');
        }
        if(g!==generation||scope!==j.workspaceKey) return {ok:false,code:'OPERATION_INVALIDATED',persistenceOutcome:writeStarted?'local-write-readback-confirmed':'existing-version-confirmed'};
        need('write');knownRaw=confirmedRaw;
        // A replay of an older request never rolls the head backward.
        const versions=replayed?stored.versions:[...stored.versions,version];j.versions=versions;j.reviews=[...stored.reviews,...j.reviews.filter(r=>!stored.reviews.some(s=>JSON.stringify(s)===JSON.stringify(r)))];j.draft.baseVersionId=head(j).localId;recompute();
        j.viewingVersionId=version.localId;viewGeneration++;pending=null;persistence='local-readback-confirmed';error=null;journalDirty=j.draft.editRevision!==snapshot.editRevision;lastExport=null;emit();
        return {ok:true,replayed,version:copy(version),persistence:'local-readback-confirmed',productBinding:'UNBOUND'};
      });
    }catch(e){if(g===undefined||g===generation&&scope===j.workspaceKey){pending=null;persistence=writeStarted?'failed-outcome-unknown':'failed';return resultError(e);}return {ok:false,code:'OPERATION_INVALIDATED',persistenceOutcome:writeStarted?'unknown':'not-written'};}
  }
  async function checkpoint(){
    if(pending)return {ok:false,code:'OPERATION_PENDING'};
    const g=generation,scope=j.workspaceKey;let captured;
    try{need('write');if(pending)fail('OPERATION_PENDING');pending={kind:'checkpoint',operationGeneration:g};emit();
      return await lock(storage,keyFor(scope),async()=>{active(g,scope,'write');const {raw,journal:stored}=await readJournal(scope);active(g,scope,'write');
        if((head(stored)?.localId??null)!==(head(j)?.localId??null))fail('HEAD_CONFLICT');
        if(raw!==knownRaw)fail('JOURNAL_CONCURRENT_CHANGE');
        captured=copy(j);const confirmedRaw=await writeJournal(captured,raw,g,scope,'write');active(g,scope,'write');knownRaw=confirmedRaw;pending=null;journalDirty=JSON.stringify(captured)!==JSON.stringify(j);error=null;emit();return {ok:true,status:'local-journal-readback-confirmed'};});
    }catch(e){if(g===generation&&scope===j.workspaceKey){pending=null;return resultError(e);}return {ok:false,code:'OPERATION_INVALIDATED'};}
  }
  async function restore({preserveDraft=false}={}) {
    if(pending)return {ok:false,code:'OPERATION_PENDING'};
    const g=generation,scope=j.workspaceKey,startSnapshot=JSON.stringify(j);
    try{need();if(pending)fail('OPERATION_PENDING');pending={kind:'restore',operationGeneration:g};emit();
      active(g,scope);const {raw,journal:stored}=await readJournal(scope);active(g,scope);
      if(JSON.stringify(j)!==startSnapshot)fail('DRAFT_CHANGED_DURING_RESTORE');
      if(raw===null){pending=null;emit();return {ok:true,status:'no-local-journal'};}
      if(preserveDraft){stored.draft=copy(j.draft);stored.draft.baseVersionId=head(stored)?.localId??null;}
      j=stored;knownRaw=raw;recompute();viewGeneration++;pending=null;journalDirty=preserveDraft;persistence=head(j)?'local-readback-confirmed':'unsaved';error=null;lastExport=null;emit();return {ok:true,status:'local-journal-restored',preservedDraft:preserveDraft};
    }catch(e){if(g===generation&&scope===j.workspaceKey){pending=null;return resultError(e);}return {ok:false,code:'OPERATION_INVALIDATED'};}
  }
  function viewVersion(id){try{readVersion(id);j.viewingVersionId=id;viewGeneration++;lastExport=null;changed();return {ok:true};}catch(e){return resultError(e);}}
  function adoptVersion(id){try{need('write');const v=readVersion(id);j.draft={...j.draft,title:v.title,markdown:v.markdown,baseVersionId:head(j)?.localId??null,editRevision:j.draft.editRevision+1,selection:{start:0,end:0,direction:'none',unit:'utf16'},scroll:0};recompute();changed();return {ok:true};}catch(e){return resultError(e);}}
  function discardDraft(){try{need('write');const v=head(j);j.draft=v?{...emptyDraft(),title:v.title,markdown:v.markdown,baseVersionId:v.localId,editRevision:j.draft.editRevision+1}:{...emptyDraft(),editRevision:j.draft.editRevision+1};changed();return {ok:true};}catch(e){return resultError(e);}}
  function reviewVersion({versionId,verdict,notes,unknowns=[]}={}){try{need('write');const v=readVersion(versionId);const r={versionId,contentSha256:v.contentSha256,verdict,notes,unknowns:copy(unknowns),kind:'LOCAL_HUMAN_REVIEW_ONLY'};
    if(!['reviewed','needs-work'].includes(verdict)||!str(notes,4000,true)||!Array.isArray(unknowns)||unknowns.length>32||unknowns.some(s=>!str(s,500,true))||j.reviews.length>=SAVED_REPORT_LIMITS.reviews)fail('REVIEW_INVALID');
    j.reviews.push(r);changed();return {ok:true,review:copy(r),persistence:'unsaved-local-review'};
  }catch(e){return resultError(e);}}
  async function prepareExport({versionId=j.viewingVersionId,format}={}){
    const g=generation,vg=viewGeneration,scope=j.workspaceKey;
    try{need('export');if(!['md','txt'].includes(format))fail('EXPORT_FORMAT_UNBOUND');const selected=copy(readVersion(versionId));
      // Reread persisted bytes, never export the mutable draft or trust a filename.
      const {journal:stored}=await readJournal(scope);active(g,scope,'export');
      const v=stored.versions.find(v=>v.localId===versionId);
      if(!v||v.contentSha256!==selected.contentSha256||v.version!==selected.version)fail('EXPORT_VERSION_MISMATCH');
      // Both formats intentionally preserve the author's Markdown verbatim; txt is not a Markdown stripping engine.
      const bytes=enc.encode(v.markdown),bytesSha256=await digest(sha256,bytes);active(g,scope,'export');if(vg!==viewGeneration)fail('EXPORT_SELECTION_CHANGED');
      lastExport={versionId,contentSha256:v.contentSha256,bytesSha256,format,status:'bytes-prepared',filename:`local-review-v${v.version}.${format}`,mime:format==='md'?'text/markdown;charset=utf-8':'text/plain;charset=utf-8',byteLength:bytes.length};emit();
      return {ok:true,...copy(lastExport),bytes,productBinding:'UNBOUND',diskDelivery:'NOT_VERIFIED'};
    }catch(e){if(g===generation&&scope===j.workspaceKey)return resultError(e);return {ok:false,code:'OPERATION_INVALIDATED'};}
  }
  function cancel(){const hadPending=Boolean(pending);generation++;viewGeneration++;pending=null;lastExport=null;persistence=hadPending?'cancelled-outcome-unknown':persistence;emit();return {ok:true,status:hadPending?'ui-operation-invalidated; persisted-write-not-undone':'no-pending-operation'};}
  function setPermissions(next){try{const p=validPermissions(next);if(JSON.stringify(p)!==JSON.stringify(perms)){generation++;viewGeneration++;pending=null;lastExport=null;if(persistence==='writing')persistence='cancelled-outcome-unknown';perms=p;emit();}return {ok:true};}catch(e){return resultError(e);}}
  function switchWorkspace(scope){try{if(!scopeOK(scope))fail('SCOPE_INVALID');generation++;viewGeneration++;j=initial(scope);pending=null;persistence='unsaved';error=null;journalDirty=false;lastExport=null;knownRaw=null;attempts.clear();emit();return {ok:true};}catch(e){return resultError(e);}}
  return Object.freeze({state,subscribe,edit,save,checkpoint,restore,viewVersion,adoptVersion,discardDraft,reviewVersion,prepareExport,cancel,setPermissions,switchWorkspace,storageKey:()=>keyFor(j.workspaceKey)});
}

/**
 * Demo 69 / IC-159. Independent LOCAL BYTE WORKBENCH, never a product uploader.
 * Source: main 4dab98ed6357133da9307de846180ed4f7bba5f5, 2026-10-17 readback;
 * FULL-PRODUCT-SKETCH.md:610, BMP-06.md:110. Existing owners remain Shared media,
 * shared_artifacts.py (hash/readback/Permission) and Web transport. Their bounded
 * binary-read paths do not establish a chunk upload endpoint for this demo.
 * Date.now() below means local observation time, never publication, server receipt,
 * ingestion, permission or persistence time. File.lastModified is browser metadata.
 */
import {CONTENT_LANGUAGES, contentDiagnostics} from './content-language.mjs';
export const RESUMABLE_LIMITS=Object.freeze({fileBytes:16*1024*1024,chunkBytes:1024*1024,minChunkBytes:1024,defaultChunkBytes:256*1024,chunks:256,metadataBytes:256*1024,nameUnits:12000});
export const RESUMABLE_SCHEMA='review-resumable-file/1';
export const RESUMABLE_STORAGE_KEY='lumenis-review:69:metadata:v1';
export const RESUMABLE_SOURCE=Object.freeze({requirement:'IC-159',main:'4dab98ed6357133da9307de846180ed4f7bba5f5',sketchLine:610,screen:'BMP-06:110',owner:'Shared media / shared_artifacts.py / existing Web transport',observedDate:'2026-10-17',boundary:'LOCAL_BYTE_WORKBENCH_ONLY'});
/**
 * Future adapter injection contract, deliberately NOT an implementation or grant.
 * An authorized product binder must supply all methods below, a real server-issued
 * session identity, fresh Permission, authenticated receipt verification and exact
 * server readback. A locally persisted manifest, returned boolean or HTTP success
 * is insufficient. This module never calls adapter methods or transmits bytes.
 */
export const BACKEND_RESUME_CONTRACT=Object.freeze({
 version:'unbound-resumable-adapter/1', methods:Object.freeze(['prepare','listReceived','putChunk','readChunk','finalize','verifyReceipt']),
 requestFields:Object.freeze(['actorId','workspaceId','projectId','permissionVersion','operationId','attempt','sessionId','fingerprint','index','offset','length','sha256']),
 requirements:Object.freeze(['authenticated server session, fresh scope and Permission','idempotency per session/index/offset/length/hash','missing chunks from verified server receipts, never local metadata','exact server byte readback and full-file fingerprint','cancel/permission/scope fencing before every effect and receipt commit','final Artifact/SourceUse checks separate from receipt and byte verification']),
});
const copy=x=>structuredClone(x), fail=message=>{throw Error(message);};
const check=(condition,message='INVALID_RESUMABLE_DATA')=>{if(!condition)fail(message);};
const int=(n,lo=0,hi=Number.MAX_SAFE_INTEGER)=>Number.isSafeInteger(n)&&n>=lo&&n<=hi;
const digestPattern=/^[a-f0-9]{64}$/;
const localTime=n=>int(n,0,8640000000000000);
const fields=(x,allowed)=>check(x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).length===allowed.length&&allowed.every(k=>Object.hasOwn(x,k)),'UNKNOWN_OR_MISSING_FIELDS');
const smallText=(x,max=120)=>typeof x==='string'&&x.length>0&&x.length<=max;
function scopeValue(scope){fields(scope,['actorId','workspaceId','projectId']);for(const v of Object.values(scope))check(smallText(v),'INVALID_SCOPE');return copy(scope);}
function same(a,b){return JSON.stringify(a)===JSON.stringify(b);}
function fileValue(file){
 check(file&&typeof file.slice==='function'&&int(file.size,0,RESUMABLE_LIMITS.fileBytes),'FILE_TOO_LARGE_OR_INVALID');
 check(smallText(file.name,RESUMABLE_LIMITS.nameUnits)&&!/[\\/\0]/.test(file.name),'INVALID_FILE_NAME_NO_PATHS');contentDiagnostics(file.name);
 check(localTime(file.lastModified??0),'INVALID_FILE_TIME');return{name:file.name,size:file.size,lastModified:file.lastModified??null};
}
function languageValue(value){check(value===null||CONTENT_LANGUAGES.includes(value),'INVALID_CONTENT_LANGUAGE');return value;}
export async function sha256Bytes(bytes,subtle=globalThis.crypto?.subtle){check(bytes instanceof Uint8Array&&bytes.byteLength<=RESUMABLE_LIMITS.fileBytes,'INVALID_HASH_BYTES');check(subtle?.digest,'SHA256_UNAVAILABLE');return Array.from(new Uint8Array(await subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');}
export function chunkPlan(size,chunkBytes=RESUMABLE_LIMITS.defaultChunkBytes){
 check(int(size,0,RESUMABLE_LIMITS.fileBytes),'FILE_TOO_LARGE_OR_INVALID');check(int(chunkBytes,RESUMABLE_LIMITS.minChunkBytes,RESUMABLE_LIMITS.chunkBytes),'INVALID_CHUNK_SIZE');
 const count=Math.max(1,Math.ceil(size/chunkBytes));check(count<=RESUMABLE_LIMITS.chunks,'TOO_MANY_CHUNKS');
 return Array.from({length:count},(_,index)=>({index,offset:index*chunkBytes,length:Math.min(chunkBytes,Math.max(0,size-index*chunkBytes))}));
}
export function inspectBackendAdapter(adapter=null){
 const provided=BACKEND_RESUME_CONTRACT.methods.filter(key=>typeof adapter?.[key]==='function');
 return{state:'UNBOUND',provided,missing:BACKEND_RESUME_CONTRACT.methods.filter(k=>!provided.includes(k)),receipts:'MISSING',serverReceivedBytes:null,productMaterial:'UNAVAILABLE',reason:'No authorized server invocation, authenticated receipt or exact server readback in this workbench.'};
}
/** Structure only. True is NOT receipt authentication, persistent storage or product availability. */
export function validateBackendReceiptShape(receipt,request){
 check(receipt&&request,'BACKEND_RECEIPT_MISSING');
 fields(request,BACKEND_RESUME_CONTRACT.requestFields);
 for(const key of ['actorId','workspaceId','projectId','operationId','sessionId'])check(smallText(request[key]),`INVALID_BACKEND_REQUEST:${key}`);
 check(int(request.permissionVersion,1)&&int(request.attempt,1)&&int(request.index,0,RESUMABLE_LIMITS.chunks-1)&&int(request.offset,0,RESUMABLE_LIMITS.fileBytes)&&int(request.length,0,RESUMABLE_LIMITS.chunkBytes)&&request.offset+request.length<=RESUMABLE_LIMITS.fileBytes&&digestPattern.test(request.fingerprint)&&digestPattern.test(request.sha256),'INVALID_BACKEND_REQUEST_RANGE_OR_HASH');
 for(const key of BACKEND_RESUME_CONTRACT.requestFields)check(Object.hasOwn(request,key)&&receipt[key]===request[key],`BACKEND_RECEIPT_MISMATCH:${key}`);
 check(receipt.origin==='SERVER'&&smallText(receipt.receiptId)&&typeof receipt.receivedAt==='string'&&Number.isFinite(Date.parse(receipt.receivedAt))&&receipt.durability==='PERSISTED','BACKEND_RECEIPT_INVALID');
 return{shapeValid:true,authenticated:false,exactReadback:false,backend:'UNBOUND',productMaterial:'UNAVAILABLE'};
}
function validateManifest(m){
 fields(m,['sessionId','scope','file','fingerprint','chunkBytes','chunks','contentLanguage','preparedAt','timeAuthority']);
 check(smallText(m.sessionId)&&/^[a-zA-Z0-9_-]+$/.test(m.sessionId),'INVALID_SESSION');scopeValue(m.scope);
 fields(m.file,['name','size','lastModified']);fileValue({...m.file,slice(){}});check(m.file.lastModified===null||localTime(m.file.lastModified),'INVALID_FILE_TIME');
 check(digestPattern.test(m.fingerprint),'INVALID_FINGERPRINT');languageValue(m.contentLanguage);check(localTime(m.preparedAt)&&m.timeAuthority==='LOCAL_PREPARATION_OBSERVATION','INVALID_PREPARATION_TIME');
 const plan=chunkPlan(m.file.size,m.chunkBytes);check(Array.isArray(m.chunks)&&m.chunks.length===plan.length,'INVALID_CHUNKS');
 for(let i=0;i<plan.length;i++){fields(m.chunks[i],['index','offset','length','sha256']);for(const k of ['index','offset','length'])check(m.chunks[i][k]===plan[i][k],'INVALID_CHUNK_RANGE');check(digestPattern.test(m.chunks[i].sha256),'INVALID_CHUNK_HASH');}
 return copy(m);
}
function identity(m,c){return{sessionId:m.sessionId,fingerprint:m.fingerprint,scope:copy(m.scope),index:c.index,offset:c.offset,length:c.length,sha256:c.sha256};}
/** In-memory sink owns actual byte copies; no snapshot can restore this Map. */
export function createLocalByteSink(){
 let manifest=null;const records=new Map();let writes=0;
 return{
  begin(m){manifest=validateManifest(m);records.clear();writes=0;},
  write(request,bytes,current=()=>false){
   check(current(),'STALE_ATTEMPT');check(manifest&&same(request,identity(manifest,manifest.chunks[request.index])),'SINK_SCOPE_OR_RANGE_MISMATCH');
   check(bytes instanceof Uint8Array&&bytes.length===request.length,'SINK_LENGTH_MISMATCH');check(current(),'STALE_ATTEMPT');records.set(request.index,bytes.slice());writes++;
  },
  read(request){check(manifest&&same(request,identity(manifest,manifest.chunks[request.index])),'SINK_SCOPE_OR_RANGE_MISMATCH');return records.get(request.index)?.slice()??null;},
  remove(index){records.delete(index);},
  clear(){manifest=null;records.clear();},
  stats(){return{byteLength:[...records.values()].reduce((n,x)=>n+x.length,0),chunks:records.size,writes,persistence:'MEMORY_ONLY'};},
 };
}
export function validateResumableSnapshot(value){
 fields(value,['schema','manifest','localVerifiedIndices','savedAt','timeAuthority','bytesPersisted','permissionPersisted','serverReceipts']);
 check(value.schema===RESUMABLE_SCHEMA&&value.bytesPersisted===false&&value.permissionPersisted===false&&value.serverReceipts===null,'NOT_A_LOCAL_METADATA_SNAPSHOT');validateManifest(value.manifest);
 check(localTime(value.savedAt)&&value.timeAuthority==='LOCAL_METADATA_SAVE_OBSERVATION','INVALID_SNAPSHOT_TIME');
 check(Array.isArray(value.localVerifiedIndices)&&value.localVerifiedIndices.length<=value.manifest.chunks.length&&new Set(value.localVerifiedIndices).size===value.localVerifiedIndices.length&&value.localVerifiedIndices.every(i=>int(i,0,value.manifest.chunks.length-1)),'INVALID_LOCAL_INDICES');
 check(new TextEncoder().encode(JSON.stringify(value)).length<=RESUMABLE_LIMITS.metadataBytes,'METADATA_TOO_LARGE');return copy(value);
}
export function saveResumableSnapshot(storage,value){
 const valid=validateResumableSnapshot(value),raw=JSON.stringify(valid);check(storage?.getItem&&storage?.setItem,'LOCAL_STORAGE_UNAVAILABLE');const before=storage.getItem(RESUMABLE_STORAGE_KEY);
 try{storage.setItem(RESUMABLE_STORAGE_KEY,raw);check(storage.getItem(RESUMABLE_STORAGE_KEY)===raw,'METADATA_EXACT_READBACK_FAILED');}
 catch(error){try{before===null?storage.removeItem(RESUMABLE_STORAGE_KEY):storage.setItem(RESUMABLE_STORAGE_KEY,before);}catch{}throw error;}return valid;
}
export function readResumableSnapshot(storage){
 check(storage?.getItem,'LOCAL_STORAGE_UNAVAILABLE');const raw=storage.getItem(RESUMABLE_STORAGE_KEY);if(raw===null)return null;check(typeof raw==='string'&&new TextEncoder().encode(raw).length<=RESUMABLE_LIMITS.metadataBytes,'METADATA_TOO_LARGE');return validateResumableSnapshot(JSON.parse(raw));
}
export function createResumableWorkbench({scope={actorId:'local-user',workspaceId:'independent-review',projectId:'demo69'},sink=createLocalByteSink(),backendAdapter=null,clock=()=>Date.now(),idFactory=()=>globalThis.crypto.randomUUID(),subtle=globalThis.crypto?.subtle,onChange=()=>{}}={}){
 let prepareOptions={chunkBytes:RESUMABLE_LIMITS.defaultChunkBytes,contentLanguage:null};
 let currentScope=scopeValue(scope),selectedFile=null,manifest=null,epoch=0,disposed=false,allowed=false,permissionVersion=0,attempt=0;
 let phase='IDLE',notice='NO_FILE_SELECTED',preparedBytes=0,verified=[],historical=[],lastError=null,active=false;
 const notify=()=>onChange(getState());
 const fence=()=>({epoch,permissionVersion,scope:copy(currentScope)});
 const isCurrent=t=>!disposed&&allowed&&t.epoch===epoch&&t.permissionVersion===permissionVersion&&same(t.scope,currentScope);
 const ensure=t=>check(isCurrent(t),'STALE_ATTEMPT');
 const invalidate=()=>{epoch++;active=false;};
 function getState(){return copy({phase,notice,manifest,scope:currentScope,selectedFile:!!selectedFile,allowed,permissionVersion,attempt,preparedBytes,verifiedIndices:verified,historicalIndices:historical,localVerifiedBytes:manifest?verified.reduce((n,i)=>n+manifest.chunks[i].length,0):0,missingIndices:manifest?manifest.chunks.filter(c=>!verified.includes(c.index)).map(c=>c.index):[],lastError,active,disposed,backend:inspectBackendAdapter(backendAdapter),rights:'UNKNOWN',sourceUse:'UNKNOWN',bytesPersistence:'MEMORY_ONLY'});}
 function guard(){check(!disposed,'WORKBENCH_DISPOSED');check(allowed,'LOCAL_PERMISSION_REQUIRED');check(manifest,'PREPARE_REQUIRED');check(same(manifest.scope,currentScope),'SCOPE_CHANGED');}
 async function readChunk(file,c,t){ensure(t);const blob=file.slice(c.offset,c.offset+c.length);check(blob&&typeof blob.arrayBuffer==='function','FILE_SLICE_UNAVAILABLE');const buffer=await blob.arrayBuffer();ensure(t);check(buffer instanceof ArrayBuffer&&buffer.byteLength===c.length,'FILE_SLICE_LENGTH_MISMATCH');return new Uint8Array(buffer);}
 async function build(file,chunkBytes,language,sessionId,t){
  const info=fileValue(file),plan=chunkPlan(info.size,chunkBytes),all=new Uint8Array(info.size),chunks=[];preparedBytes=0;
  for(const c of plan){const bytes=await readChunk(file,c,t);all.set(bytes,c.offset);const sha256=await sha256Bytes(bytes,subtle);ensure(t);chunks.push({...c,sha256});preparedBytes+=bytes.length;notify();}
  const fingerprint=await sha256Bytes(all,subtle);ensure(t);return validateManifest({sessionId,scope:copy(currentScope),file:info,fingerprint,chunkBytes,chunks,contentLanguage:languageValue(language),preparedAt:clock(),timeAuthority:'LOCAL_PREPARATION_OBSERVATION'});
 }
 function failure(error,t){if(!isCurrent(t))return{ok:false,stale:true};phase='FAILED';lastError=error.message;notice=error.message;active=false;notify();return{ok:false,error:error.message};}
 async function prepare(file,{chunkBytes=RESUMABLE_LIMITS.defaultChunkBytes,contentLanguage=null}={}){
  check(!disposed,'WORKBENCH_DISPOSED');fileValue(file);chunkPlan(file.size,chunkBytes);languageValue(contentLanguage);
  invalidate();prepareOptions={chunkBytes,contentLanguage};allowed=true;permissionVersion++;selectedFile=file;manifest=null;verified=[];historical=[];sink.clear();phase='PREPARING';lastError=null;notice='READING_SELECTED_FILE_ONLY';active=true;const t=fence();notify();
  try{const next=await build(file,chunkBytes,contentLanguage,idFactory(),t);ensure(t);manifest=next;sink.begin(manifest);phase='READY';active=false;notice='LOCAL_MANIFEST_READY_NOT_UPLOADED';notify();return{ok:true,manifest:copy(manifest)};}catch(error){return failure(error,t);}
 }
 async function reconcile(t){
  const found=[];verified=[];notify();
  for(const c of manifest.chunks){ensure(t);const bytes=await sink.read(identity(manifest,c));ensure(t);if(bytes!==null){if(bytes instanceof Uint8Array&&bytes.length===c.length){const hash=await sha256Bytes(bytes,subtle);ensure(t);if(hash===c.sha256){found.push(c.index);verified=[...found];notify();continue;}}sink.remove(c.index);}}
  ensure(t);verified=found;notify();return manifest.chunks.filter(c=>!found.includes(c.index));
 }
 async function run({maxChunks=RESUMABLE_LIMITS.chunks}={}){
  guard();check(selectedFile,'RESELECT_MATCHING_FILE_REQUIRED');check(!active,'OPERATION_BUSY');check(int(maxChunks,1,RESUMABLE_LIMITS.chunks),'INVALID_STEP_LIMIT');
  invalidate();attempt++;active=true;phase='VERIFYING_LOCAL_BYTES';lastError=null;notice='LOCAL_READBACK_IN_PROGRESS';const t=fence();notify();
  try{
   const missing=await reconcile(t);ensure(t);phase='READING';notify();let count=0;
   for(const c of missing){if(count>=maxChunks)break;ensure(t);const bytes=await readChunk(selectedFile,c,t);const hash=await sha256Bytes(bytes,subtle);ensure(t);check(hash===c.sha256,'SELECTED_FILE_BYTES_CHANGED');
    const request=identity(manifest,c);await sink.write(request,bytes,()=>isCurrent(t));ensure(t);const readback=await sink.read(request);ensure(t);
    check(readback instanceof Uint8Array&&readback.length===bytes.length&&readback.every((v,i)=>v===bytes[i]),'LOCAL_EXACT_BYTE_READBACK_FAILED');
    check(await sha256Bytes(readback,subtle)===c.sha256,'LOCAL_READBACK_HASH_MISMATCH');ensure(t);verified.push(c.index);verified.sort((a,b)=>a-b);count++;notice='LOCAL_CHUNK_VERIFIED_NOT_UPLOADED';notify();
   }
   ensure(t);phase=verified.length===manifest.chunks.length?'LOCAL_COMPLETE':'PAUSED';active=false;notice=phase==='LOCAL_COMPLETE'?'LOCAL_BYTES_VERIFIED_SERVER_UNBOUND':'LOCAL_STEP_DONE_MORE_CHUNKS_MISSING';notify();return{ok:true,state:getState()};
  }catch(error){return failure(error,t);}
 }
 async function retry(options){check(!disposed,'WORKBENCH_DISPOSED');check(allowed,'LOCAL_PERMISSION_REQUIRED');check(!active,'OPERATION_BUSY');return manifest?run(options):(check(selectedFile,'RESELECT_MATCHING_FILE_REQUIRED'),prepare(selectedFile,prepareOptions));}
 function pause(){check(!disposed,'WORKBENCH_DISPOSED');invalidate();phase='PAUSED';notice='PAUSED_OLD_ATTEMPT_FENCED';notify();}
 function cancel(){check(!disposed,'WORKBENCH_DISPOSED');invalidate();phase='CANCELLED';notice='CANCELLED_LOCAL_BYTES_RETAINED_EXPLICIT_RESUME_REQUIRED';notify();}
 function revoke(){check(!disposed,'WORKBENCH_DISPOSED');invalidate();allowed=false;permissionVersion++;selectedFile=null;verified=[];if(manifest)sink.begin(manifest);else sink.clear();phase='PERMISSION_REVOKED';notice='RESELECT_REQUIRED_NO_PERMISSION_RESTORED_FROM_METADATA';notify();}
 function setScope(next){check(!disposed,'WORKBENCH_DISPOSED');const valid=scopeValue(next);if(same(valid,currentScope))return;invalidate();currentScope=valid;allowed=false;permissionVersion++;selectedFile=null;manifest=null;verified=[];historical=[];sink.clear();phase='SCOPE_CHANGED';notice='OLD_SCOPE_BYTES_AND_CALLBACKS_CLEARED';notify();}
 async function reselect(file){
  check(!disposed,'WORKBENCH_DISPOSED');check(manifest,'NO_SAVED_MANIFEST');check(same(manifest.scope,currentScope),'SCOPE_CHANGED');fileValue(file);check(file.size===manifest.file.size,'RESELECT_SIZE_MISMATCH');
  invalidate();selectedFile=null;allowed=true;permissionVersion++;phase='PREPARING';active=true;lastError=null;const t=fence(),expected=copy(manifest);notice='VERIFYING_RESELECTED_BYTES';notify();
  try{const actual=await build(file,expected.chunkBytes,expected.contentLanguage,expected.sessionId,t);ensure(t);check(actual.fingerprint===expected.fingerprint&&same(actual.chunks,expected.chunks),'RESELECT_FINGERPRINT_MISMATCH');selectedFile=file;await reconcile(t);ensure(t);phase='READY';active=false;notice='SAME_BYTES_RESELECTED_ORIGINAL_NAME_PRESERVED';notify();return{ok:true};}catch(error){return failure(error,t);}
 }
 function snapshot(){guard();check(!active,'OPERATION_BUSY');return validateResumableSnapshot({schema:RESUMABLE_SCHEMA,manifest:copy(manifest),localVerifiedIndices:[...verified],savedAt:clock(),timeAuthority:'LOCAL_METADATA_SAVE_OBSERVATION',bytesPersisted:false,permissionPersisted:false,serverReceipts:null});}
 function reopen(value){
  check(!disposed,'WORKBENCH_DISPOSED');const valid=validateResumableSnapshot(value);check(same(valid.manifest.scope,currentScope),'SNAPSHOT_SCOPE_MISMATCH');
  invalidate();manifest=valid.manifest;historical=valid.localVerifiedIndices;verified=[];allowed=false;permissionVersion++;selectedFile=null;preparedBytes=0;lastError=null;sink.begin(manifest);phase='NEEDS_FILE';notice='METADATA_ONLY_RESELECT_SAME_BYTES_AND_PERMISSION';notify();return getState();
 }
 function setContentLanguage(language){check(!disposed,'WORKBENCH_DISPOSED');check(manifest&&!active,'PREPARED_IDLE_MANIFEST_REQUIRED');manifest.contentLanguage=languageValue(language);notify();}
 function forgetChunk(index){guard();check(!active,'OPERATION_BUSY');check(int(index,0,manifest.chunks.length-1),'INVALID_CHUNK_INDEX');sink.remove(index);verified=verified.filter(i=>i!==index);phase='PAUSED';notice='ACTUAL_LOCAL_CHUNK_REMOVED_RESUME_REQUIRES_REAL_BYTES';notify();}
 function dispose(){if(disposed)return;invalidate();disposed=true;allowed=false;permissionVersion++;selectedFile=null;sink.clear();verified=[];phase='DISPOSED';}
 return{getState,prepare,run,retry,resume:retry,pause,cancel,revoke,setScope,reselect,snapshot,reopen,setContentLanguage,forgetChunk,dispose};
}

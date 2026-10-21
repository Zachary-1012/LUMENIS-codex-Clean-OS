import{contentDiagnostics,contentSelectionRange,createContentSelectionIndex,CONTENT_LANGUAGES}from'./content-language.mjs';
import{browserReportSha256}from'./saved-report.mjs';
/** Local research notebook only: no production Evidence/SourceUse, body insertion or export. */
export const REFERENCE_LIMITS=Object.freeze({sourceBytes:65536,sources:16,quotes:128,note:2000,journalBytes:2097152});
const clone=x=>structuredClone(x),fail=code=>{throw Error(code)},enc=new TextEncoder(),hashOK=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const exact=(x,keys)=>x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join('|')===[...keys].sort().join('|');
function text(v,max){if(typeof v!=='string'||v.length>max)fail('TEXT_INVALID');contentDiagnostics(v,{Segmenter:null});return v}
const initial=scope=>({schema:'local-reference-draft/v1',identity:'LOCAL_REFERENCE_DRAFT',productBinding:'UNBOUND',scope,revision:0,sources:[],quotes:[]});
function scopeOK(s){return typeof s==='string'&&/^[A-Za-z0-9_-]{1,80}$/.test(s)}
function check(s){
 if(!exact(s,['schema','identity','productBinding','scope','revision','sources','quotes'])||s.schema!=='local-reference-draft/v1'||s.identity!=='LOCAL_REFERENCE_DRAFT'||s.productBinding!=='UNBOUND'||!scopeOK(s.scope)||!Number.isSafeInteger(s.revision)||s.revision<0)fail('JOURNAL_INVALID');
 if(!Array.isArray(s.sources)||s.sources.length>16||!Array.isArray(s.quotes)||s.quotes.length>128)fail('JOURNAL_LIMIT');
 s.sources.forEach((v,i)=>{if(!exact(v,['version','title','text','textSha256','language','withdrawn','rights'])||v.version!==i+1||!hashOK(v.textSha256)||typeof v.withdrawn!=='boolean'||v.rights!=='UNKNOWN'||!['und',...CONTENT_LANGUAGES].includes(v.language))fail('SOURCE_INVALID');text(v.title,256);text(v.text,65536);if(enc.encode(v.text).length>65536)fail('SOURCE_LIMIT')});
 const ids=new Set(),indexes=new Map();for(const [qi,q] of s.quotes.entries()){if(!exact(q,['id','sourceVersion','sourceSha256','start','end','offsetUnit','quote','relation','note','excluded'])||q.id!==`local_quote_${qi+1}`||ids.has(q.id)||!Number.isInteger(q.sourceVersion)||!Number.isInteger(q.start)||!Number.isInteger(q.end)||q.start<0||q.end<=q.start||q.offsetUnit!=='unicode_codepoint'||!['support','counter','context'].includes(q.relation)||typeof q.excluded!=='boolean')fail('QUOTE_INVALID');ids.add(q.id);text(q.quote,8192);text(q.note,2000);const v=s.sources[q.sourceVersion-1];if(!v||v.textSha256!==q.sourceSha256)fail('QUOTE_SOURCE_CHANGED');if(!indexes.has(v.version))indexes.set(v.version,createContentSelectionIndex(v.text));if(indexes.get(v.version).fromCodePoints(q.start,q.end).expected!==q.quote)fail('QUOTE_SOURCE_CHANGED')}
 return s;
}
export async function readReferenceDraft(raw,scope,sha256=browserReportSha256){if(typeof raw!=='string'||enc.encode(raw).length>REFERENCE_LIMITS.journalBytes)fail('JOURNAL_LIMIT');let s;try{s=JSON.parse(raw)}catch{fail('JOURNAL_INVALID')}check(s);if(s.scope!==scope)fail('SCOPE_MISMATCH');for(const source of s.sources){if(await sha256(enc.encode(source.text))!==source.textSha256)fail('SOURCE_HASH_MISMATCH')}return clone(s)}
export function createReferenceDraft({scope='report-demo',sha256=browserReportSha256,getPermissions=()=>({read:false,write:false})}={}){
 if(!scopeOK(scope))fail('SCOPE_INVALID');let s=initial(scope),generation=0;
 const need=write=>{const p=getPermissions();if(!p?.read||write&&!p.write)fail('PERMISSION_DENIED')},baseline=(revision,write=true)=>{need(write);if(revision!==s.revision)fail('STALE_REFERENCE_REVISION')},changed=next=>{check(next);next.revision=s.revision+1;s=next;return clone(s)};
 return Object.freeze({
 snapshot(){need(false);return clone(s)},
 async setSource({title,body,language='und',expectedRevision}){baseline(expectedRevision);text(title,256);text(body,65536);if(!body.trim()||enc.encode(body).length>65536)fail('SOURCE_LIMIT');if(!['und',...CONTENT_LANGUAGES].includes(language))fail('LANGUAGE_UNSUPPORTED');if(s.sources.length>=16)fail('SOURCE_VERSION_LIMIT');const token=generation,hash=await sha256(enc.encode(body));if(token!==generation)fail('CANCELLED');baseline(expectedRevision);if(!hashOK(hash))fail('SHA256_INVALID');const next=clone(s);next.sources.push({version:next.sources.length+1,title,text:body,textSha256:hash,language,withdrawn:false,rights:'UNKNOWN'});return changed(next)},
 addQuote({start,end,sourceVersion,sourceSha256,relation='context',note='',expectedRevision}){baseline(expectedRevision);if(s.quotes.length>=128)fail('QUOTE_LIMIT');const source=s.sources.at(-1);if(!source||source.version!==sourceVersion||source.textSha256!==sourceSha256||source.withdrawn)fail('SOURCE_NOT_CURRENT');const range=contentSelectionRange(source.text,start,end);if(!range.expected.length)fail('EMPTY_QUOTE');text(range.expected,8192);text(note,2000);if(!['support','counter','context'].includes(relation))fail('RELATION_INVALID');const next=clone(s);next.quotes.push({id:`local_quote_${next.quotes.length+1}`,sourceVersion,sourceSha256,start:range.start,end:range.end,offsetUnit:'unicode_codepoint',quote:range.expected,relation,note,excluded:false});return changed(next)},
 editQuote({id,note,relation,excluded,expectedRevision}){baseline(expectedRevision);const next=clone(s),q=next.quotes.find(q=>q.id===id);if(!q)fail('QUOTE_NOT_FOUND');if(note!==undefined)q.note=text(note,2000);if(relation!==undefined){if(!['support','counter','context'].includes(relation))fail('RELATION_INVALID');q.relation=relation}if(excluded!==undefined){if(typeof excluded!=='boolean')fail('EXCLUSION_INVALID');q.excluded=excluded}return changed(next)},
 withdrawSource({version,expectedRevision}){baseline(expectedRevision);const next=clone(s),v=next.sources[version-1];if(!v)fail('SOURCE_NOT_FOUND');v.withdrawn=true;return changed(next)},
 serialize(){need(false);check(s);const raw=JSON.stringify(s);if(enc.encode(raw).length>REFERENCE_LIMITS.journalBytes)fail('JOURNAL_LIMIT');return raw},
 async restore(raw,{expectedRevision}={}){baseline(expectedRevision,false);const token=generation,next=await readReferenceDraft(raw,scope,sha256);if(token!==generation)fail('CANCELLED');baseline(expectedRevision,false);next.revision=Math.max(s.revision,next.revision)+1;s=next;return clone(s)},
 cancel(){generation++},
 ownerCitation(){fail('EVIDENCE_SOURCEUSE_UNBOUND')},
 insertIntoReport(){fail('REFERENCE_DRAFT_ONLY')},
 exportReferences(){fail('REFERENCE_EXPORT_UNBOUND')}
 });
}

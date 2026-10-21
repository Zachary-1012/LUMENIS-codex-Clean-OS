import test from 'node:test';
import assert from 'node:assert/strict';
import {RESEARCH_LEVELS, createResearchState, evaluateLearning, reduceResearch, saveResearch, reopenResearch, compareMetricScopes} from '../src/research-learning.mjs';
const context = () => ({now:'2026-10-17T00:00:00Z', evidence:['a','b','c'].map(id => ({id,version:'v1',state:'active',locator:`fixture:${id}`,sourceGroup:`source-${id}`,validUntil:'2026-11-01T00:00:00Z'}))});
const ref = id => ({id,version:'v1'});
const initial = (extra={}) => createResearchState({id:'case-1',statement:'人工示例假设',status:'observed',evidenceRefs:[ref('a')],...extra});
const act = (s,type,extra={},ctx=context()) => reduceResearch(s,{type,expectedRevision:s.revision,...extra},ctx);
const add = (s,id,extra={}) => act(s,'add-validation',{validation:{id,outcome:'pass',independenceKey:`sample-${id}`,independenceBasis:'人工示例：不同原始样本；非Owner认证',candidateVersion:s.draft.candidateVersion,evidenceRefs:[ref(id)],...extra}});
const ready = () => add(add(initial(),'a'),'b');
const confirm = s => act(s,'confirm-review',{humanConfirmed:true,reviewer:'local-human'});
test('exact seven owner levels; AI and derived origins cannot become facts',()=>{
 assert.deepEqual(RESEARCH_LEVELS,['fact','observation','pattern','hypothesis','validation','transfer','dont_copy']);
 for(const status of ['ai_suggested','derived','unverified']) assert.throws(()=>initial({level:'fact',status}),/FACT_REQUIRES/);
 const s=initial({status:'ai_suggested'});
 assert.throws(()=>act(s,'edit-finding',{finding:{...s.draft.finding,status:'human_verified',level:'fact'}}),/OWNER_STATUS/);
 assert.throws(()=>act(s,'edit-finding',{finding:{...s.draft.finding,level:'fact'}}),/FACT_REQUIRES/);
});
test('zero and one validation cannot pass; two require explicit human confirmation',()=>{
 assert.equal(evaluateLearning(initial(),context()).independentValidationCount,0);
 assert.equal(evaluateLearning(add(initial(),'a'),context()).eligible,false);
 const s=ready(), before=saveResearch(s), e=evaluateLearning(s,context());
 assert.equal(e.status,'ready_for_human_review'); assert.equal(e.canonicalFact,false); assert.equal(e.productPromotion,'UNBOUND');
 assert.throws(()=>act(s,'confirm-review',{reviewer:'me'}),/HUMAN/);
 assert.equal(evaluateLearning(confirm(s),context()).status,'review_confirmed'); assert.equal(saveResearch(s),before);
});
test('ids alone do not establish independent validation; shared sample/source and missing basis fail',()=>{
 for(const extra of [{independenceKey:'sample-a'},{evidenceRefs:[ref('a')]},{independenceBasis:null},{independenceKey:null}]) {
  const s=add(add(initial(),'a'),'b',extra); assert.equal(evaluateLearning(s,context()).eligible,false);
 }
 const c=context(); c.evidence[1].sourceGroup='source-a'; assert.equal(evaluateLearning(ready(),c).eligible,false);
 assert.throws(()=>add(add(initial(),'a'),'a'),/DUPLICATE_VALIDATION/);
});
test('AI suggestion, unverified claim, and do-not-copy cannot become review-confirmed',()=>{
 for(const extra of [{status:'ai_suggested'},{status:'unverified'},{level:'dont_copy'}]) {
  const s=add(add(initial(extra),'a'),'b'); assert.equal(evaluateLearning(s,context()).eligible,false);assert.throws(()=>confirm(s),/BLOCKED/);
 }
});
test('missing evidence is unverified, never zero/known; no confidence shortcut',()=>{
 const s=initial({evidenceRefs:[]}); assert.equal(evaluateLearning(s,context()).evidenceLabel,'未核实');
 const c=context(); c.evidence=[]; assert.ok(evaluateLearning(ready(),c).reasons.some(r=>r.startsWith('EVIDENCE_MISSING')));
 assert.equal(evaluateLearning(ready(),c).independentValidationCount,0);
 assert.throws(()=>initial({evidenceRefs:[ref('a'),ref('a')]}),/DUPLICATE/);
});
test('counterexample veto survives expiry, edit and undo; source records append-only',()=>{
 let s=add(ready(),'c',{outcome:'counterexample'}); assert.equal(evaluateLearning(s,context()).status,'rejected');
 const c=context(); c.evidence[2].state='withdrawn'; assert.equal(evaluateLearning(s,c).status,'rejected');
 s=act(s,'edit-finding',{finding:{...s.draft.finding,statement:'修订说明'}}); assert.equal(evaluateLearning(s,c).status,'rejected');
 s=act(s,'undo'); assert.equal(evaluateLearning(s,c).status,'rejected'); assert.equal(s.draft.validations.length,3);
 assert.throws(()=>confirm(s),/BLOCKED/);
});
test('evidence withdrawal, unknown, expiry boundary, absence and version fence revoke eligibility',()=>{
 const s=confirm(ready());
 for(const patch of [{state:'withdrawn'},{state:'unknown'},{version:'v2'},{validUntil:'2026-10-17T00:00:00Z'},{validUntil:null},{locator:null},{sourceGroup:null}]) {
  const c=context();Object.assign(c.evidence[0],patch);const e=evaluateLearning(s,c);assert.equal(e.eligible,false);assert.notEqual(e.status,'review_confirmed');
 }
 const c=context();c.now='2026-11-02T00:00:00Z';assert.equal(evaluateLearning(s,c).eligible,false);
});
test('all writes fence exact revision and stale validations cannot support edited candidates',()=>{
 const s=ready();assert.throws(()=>reduceResearch(s,{type:'revoke-review',expectedRevision:0}),/STALE/);
 const changed=act(s,'edit-finding',{finding:{...s.draft.finding,statement:'新假设'}});
 assert.equal(evaluateLearning(changed,context()).independentValidationCount,0);
 assert.throws(()=>add(changed,'c',{candidateVersion:0}),/STALE_CANDIDATE/);
 assert.equal(s.draft.finding.statement,'人工示例假设');
 const undone=act(changed,'undo');assert.equal(undone.draft.finding.statement,s.draft.finding.statement);assert.ok(undone.revision>changed.revision);
 assert.equal(evaluateLearning(undone,context()).eligible,false);
});
test('drawer and save/reopen preserve reading location, original statements and append-only validations',()=>{
 let s=confirm(ready());s=act(s,'set-anchor',{anchor:'paragraph-29'});s=act(s,'open-evidence',{evidenceId:'a'});
 assert.equal(s.reader.anchor,'paragraph-29');assert.equal(evaluateLearning(s,context()).status,'review_confirmed');
 s=act(s,'close-evidence');assert.equal(s.reader.anchor,'paragraph-29');
 const reopened=reopenResearch(saveResearch(s),context());assert.equal(reopened.state.reader.anchor,'paragraph-29');
 assert.equal(reopened.state.confirmation,null);assert.equal(reopened.evaluation.status,'ready_for_human_review');
 assert.equal(reopenResearch(saveResearch(s),{...context(),evidence:[]}).evaluation.eligible,false);
 assert.throws(()=>act(s,'open-evidence',{evidenceId:'not-listed'}),/NOT_REFERENCED/);
});
test('saved data is structurally checked and cannot retain a forged confirmation',()=>{
 const s=confirm(ready());
 for(const mutate of [s=>s.revision=-1,s=>s.schema='other',s=>s.draft.finding.level='verified-fact',s=>s.draft.finding.status='auto_promoted',s=>s.extra=true,s=>s.history.push({})]) {
  const copy=structuredClone(s);mutate(copy);assert.throws(()=>reopenResearch(JSON.stringify(copy),context()));
 }
 assert.throws(()=>reopenResearch('{',context()));assert.throws(()=>reopenResearch('x'.repeat(4000001),context()));
 assert.equal(reopenResearch(saveResearch(s),context()).state.confirmation,null);
});
test('metric comparison forbids cross-platform denominator and all other dimension mismatch',()=>{
 const scope={platform:'platform-a',metric:'retention',definitionVersion:'v1',unit:'ratio',denominator:'episode-starts',population:'sample-1',windowStart:'2026-10-01',windowEnd:'2026-10-15'};
 assert.equal(compareMetricScopes(scope,scope).comparable,true);
 for(const key of Object.keys(scope)) {assert.equal(compareMetricScopes(scope,{...scope,[key]:'different'}).comparable,false);assert.equal(compareMetricScopes(scope,{...scope,[key]:null}).comparable,false);}
 for(const value of ['UNKNOWN','unverified','NOT_AVAILABLE','—']) assert.equal(compareMetricScopes({...scope,denominator:value},{...scope,denominator:value}).comparable,false);
 assert.equal(compareMetricScopes(scope,scope).aggregationPerformed,false);
});
test('explicit time and strict evidence input required; unsafe coercions rejected',()=>{
 for(const now of [null,0,'today','2026-10-17T00:00:00']) assert.throws(()=>evaluateLearning(ready(),{...context(),now}),/TIME/);
 const c=context(); c.evidence.push(c.evidence[0]);assert.throws(()=>evaluateLearning(ready(),c),/DUPLICATE_EVIDENCE/);
 for(const evidenceRefs of [null,{},true])assert.throws(()=>initial({evidenceRefs}));
});

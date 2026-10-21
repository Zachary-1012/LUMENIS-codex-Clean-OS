import test from 'node:test';
import assert from 'node:assert/strict';
import {TOPIC_SIGNALS, GUEST_GATES, evaluateTopic, classifyTopic, roundTopicScore, createTopicPlanning, topicPlanningReduce as reduce, compareTopicSuggestion, guestQualification, canEnterPodcastPath, serializeTopicPlanning, reopenTopicPlanning} from '../src/topic-planning.mjs';
const all = value => Object.fromEntries(TOPIC_SIGNALS.map(s => [s.key, value]));
const suggest = (s, value = .8) => reduce(s, {type:'suggest', id:'simulation-1', simulation:true, baseRevision:s.revision, signals:all(value), rationale:'人工模拟示例；未运行模型'});
test('ten owner signals, weights and complete golden scores', () => {
  assert.equal(TOPIC_SIGNALS.length, 10);
  for (const [positive,risk,cost,expected] of [[0,0,0,0],[1,0,0,90],[1,1,1,80],[.5,.5,.5,40]]) {
    const result=evaluateTopic({...all(positive),risk,cost}); assert.equal(result.score,expected); assert.equal(result.state,'scored');
  }
});
for (const {key} of TOPIC_SIGNALS) {
  test(`${key}: absent/null stays unknown, observed zero retained`, () => {
    for (const mode of ['absent','null']) { const input=all(.5); if(mode==='absent')delete input[key]; else input[key]=null;
      assert.deepEqual(evaluateTopic(input).missing_signals,[key]); assert.equal(evaluateTopic(input).score,null); assert.equal(evaluateTopic(input).stage,null); }
    assert.equal(evaluateTopic({[key]:0}).signals[key],0);
  });
  test(`${key}: invalid values rejected without coercion`, () => {
    for (const value of [true,false,NaN,Infinity,-Infinity,'0.5','',[],{},-.1,1.1,undefined]) assert.throws(()=>evaluateTopic({...all(.5),[key]:value}));
  });
}
test('invalid objects/unknown keys rejected',()=>{for(const x of [null,[],true,1,'signals',{typo:1}])assert.throws(()=>evaluateTopic(x));});
test('classification precedence and threshold boundaries',()=>{
  for (const [score,time,stage] of [[34.99,1,'rejected'],[35,.85,'now'],[75,.849,'soon'],[74.99,.849,'evergreen'],[55,0,'evergreen'],[54.99,0,'watch'],[35,0,'watch'],[90,1,'now']]) assert.equal(classifyTopic(score,time),stage);
  assert.equal(classifyTopic(null,.5),null);
  for(const bad of [true,NaN,Infinity,'0',-1]){assert.throws(()=>classifyTopic(bad,.5));assert.throws(()=>classifyTopic(50,bad));}
});
test('Python binary-float decimal rounding: no JS epsilon or Math.round ties',()=>{
  for(const [x,y] of [[2.675,2.67],[2.685,2.69],[1.125,1.12],[1.375,1.38],[.005,.01],[.015,.01],[.025,.03],[99.995,100],[Number.MIN_VALUE,0]])assert.equal(roundTopicScore(x),y);
  assert.equal(evaluateTopic({...all(0),demand:.12349}).score,1.98); // input not rounded to three places first
});
test('edit/undo are immutable, revision monotonic and original bytes preserved',()=>{
  const original='  原文\r\n한글 e\u0301 <script>literal</script>\n';
  const state=createTopicPlanning({originalText:original,sourceRef:'人工来源 原文\r\n'});
  const changed=reduce(state,{type:'edit-text',key:'editedText',value:'校对'});
  assert.equal(state.draft.editedText,original); assert.equal(changed.draft.originalText,original);
  const undone=reduce(changed,{type:'undo'});assert.deepEqual(undone.draft,state.draft);assert.equal(undone.revision,2);
  assert.throws(()=>reduce(state,{type:'edit-text',key:'originalText',value:'覆盖'}));
  assert.equal(reopenTopicPlanning(serializeTopicPlanning(changed)).draft.originalText,original);
});
test('simulated proposal compare, accept, undo and reject never claim AI run',()=>{
  const initial=createTopicPlanning({signals:all(.5)}), proposed=suggest(initial);
  assert.equal(proposed.draft.signals.demand,.5);const comparison=compareTopicSuggestion(proposed);
  assert.equal(comparison.simulation,true);assert.equal(comparison.changes.length,10);
  assert.equal(comparison.current.score,40);assert.equal(comparison.proposed.score,64);
  const accepted=reduce(proposed,{type:'accept-suggestion',id:'simulation-1'});
  assert.equal(accepted.draft.signals.demand,.8);assert.equal(accepted.suggestion.status,'accepted');
  assert.deepEqual(reduce(accepted,{type:'undo'}).draft,initial.draft);
  const rejected=reduce(proposed,{type:'reject-suggestion',id:'simulation-1'});assert.deepEqual(rejected.draft,initial.draft);
  assert.throws(()=>reduce(rejected,{type:'accept-suggestion',id:'simulation-1'}));
  assert.throws(()=>reduce(initial,{type:'suggest',id:'x',baseRevision:0,signals:all(.8),rationale:'missing label'}));
});
test('manual edits and edit-undo invalidate suggestion; rejected late result never overwrites',()=>{
  const state=suggest(createTopicPlanning());const edited=reduce(state,{type:'edit-signal',key:'demand',value:0});
  for(const candidate of [edited,reduce(edited,{type:'undo'})]){
    assert.equal(compareTopicSuggestion(candidate).stale,true);
    assert.throws(()=>reduce(candidate,{type:'accept-suggestion',id:'simulation-1'}),/STALE/);
    assert.throws(()=>reduce(candidate,{type:'suggest',id:'late',simulation:true,baseRevision:0,signals:all(1),rationale:'late'}),/STALE/);
  }
  assert.equal(edited.draft.signals.demand,0);
});
test('all three gates human-only, missing/false never qualified; existing owned audio/script independent',()=>{
  let state=createTopicPlanning();assert.equal(guestQualification(state).qualified,false);
  for(const {key} of GUEST_GATES){
    assert.equal(canEnterPodcastPath(state,'owned-audio').allowed,true);assert.equal(canEnterPodcastPath(state,'owned-script').allowed,true);
    assert.equal(canEnterPodcastPath(state,'guest-outline').allowed,false);
    state=reduce(state,{type:'edit-gate',key,value:true});
  }
  assert.equal(guestQualification(state).qualified,true);assert.equal(canEnterPodcastPath(state,'guest-outline').allowed,true);
  state=reduce(state,{type:'edit-gate',key:GUEST_GATES[0].key,value:false});assert.equal(guestQualification(state).qualified,false);
  assert.equal(canEnterPodcastPath(state,'owned-audio').allowed,true);assert.equal(canEnterPodcastPath(state,'owned-audio').productionPermission,'NOT_VERIFIED');
  assert.equal(evaluateTopic(state.draft.signals).score,null);
});
test('save/reopen exact draft, history, nulls, proposal and gate truth',()=>{
  let state=createTopicPlanning({title:'节目',originalText:'\r\n原文  ',sourceRef:'自有手稿'});
  state=reduce(state,{type:'edit-gate',key:'expression',value:false});state=suggest(state);
  assert.deepEqual(reopenTopicPlanning(serializeTopicPlanning(state)),state);
});
test('corrupt or unsupported saved content is rejected, no fallback fabricated success',()=>{
  for(const raw of ['', '{bad','null','[]','{"schema":"old"}'])assert.throws(()=>reopenTopicPlanning(raw));
  const corruptions=[s=>s.schema='future',s=>s.revision=-1,s=>s.draft.signals.demand=true,s=>delete s.draft.signals.cost,s=>s.draft.gates.expression='yes',s=>s.draft.originalText=7,s=>s.history=[{}],s=>s.extra=true,s=>s.suggestion={simulation:false}];
  for(const change of corruptions){const state=createTopicPlanning();change(state);assert.throws(()=>reopenTopicPlanning(JSON.stringify(state)));}
});

test('10,000 seeded cases agree with read-only current Python owner (when snapshot present)', async t => {
  const {existsSync} = await import('node:fs');
  const {fileURLToPath} = await import('node:url');
  const {execFileSync} = await import('node:child_process');
  const owner = process.env.LUMENIS_READONLY_TOPIC_OWNER || fileURLToPath(new URL('../../recovery_inspection_20261017/remote-main-readback/source/LUMENIS-codex-Clean-OS-main/podcast/intelligence/topic_scoring.py', import.meta.url));
  if (!existsSync(owner)) { t.skip('Read-only owner snapshot absent; no runtime parity claim'); return; }
  const script = `import importlib.util,sys,random,json
spec=importlib.util.spec_from_file_location('owner_topic',sys.argv[1]);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
r=random.Random(20261017);cases=[]
for i in range(10000):
 v={k:r.random() for k in m.TopicSignals.__dataclass_fields__};score=m.score_topic(m.TopicSignals(**v));cases.append({'signals':v,'score':score,'stage':m.classify_topic(score,v['timeliness'])})
print(json.dumps(cases))`;
  const cases=JSON.parse(execFileSync('python',['-B','-c',script,owner],{encoding:'utf8',maxBuffer:8*1024*1024}));
  for(const row of cases){const result=evaluateTopic(row.signals);assert.equal(result.score,row.score);assert.equal(result.stage,row.stage);}
});

test('partial suggestion patches preserve every unmentioned observed signal',()=>{
  const state=createTopicPlanning({signals:all(.5)});
  const proposed=reduce(state,{type:'suggest',id:'partial',simulation:true,baseRevision:0,signals:{demand:0},rationale:'明确的部分建议'});
  assert.equal(proposed.suggestion.signals.cost,.5);assert.equal(proposed.suggestion.signals.demand,0);
  assert.equal(compareTopicSuggestion(proposed).changes.length,1);
  const clear=reduce(state,{type:'suggest',id:'clear',simulation:true,baseRevision:0,signals:{demand:null},rationale:'明确清空'});
  assert.equal(clear.suggestion.signals.demand,null);assert.equal(clear.suggestion.signals.cost,.5);
});
test('history and text/storage budgets are bounded before accepting external saves',()=>{
  let state=createTopicPlanning();for(let i=0;i<100;i++) state=reduce(state,{type:'edit-signal',key:'demand',value:i/100});
  assert.equal(state.history.length,32);assert.equal(state.revision,100);
  assert.throws(()=>createTopicPlanning({originalText:'x'.repeat(20001)}));
  assert.throws(()=>reopenTopicPlanning(' '.repeat(4000001)));
  const bad=createTopicPlanning();bad.history=Array(33).fill(bad.draft);assert.throws(()=>reopenTopicPlanning(JSON.stringify(bad)));
  assert.throws(()=>reduce(state,{type:'edit-text',key:'title',value:'x'.repeat(501)}));
});

test('portable 256-case Owner golden fixture remains usable without the product tree',async()=>{
  const {readFile}=await import('node:fs/promises');
  const fixture=JSON.parse(await readFile(new URL('./fixtures/topic-owner-golden.json',import.meta.url),'utf8'));
  assert.equal(fixture.schema,'topic-owner-golden-v1');assert.match(fixture.source_sha256,/^[a-f0-9]{64}$/);assert.equal(fixture.cases.length,256);
  for(const row of fixture.cases){const result=evaluateTopic(row.signals);assert.equal(result.score,row.score);assert.equal(result.stage,row.stage);}
});

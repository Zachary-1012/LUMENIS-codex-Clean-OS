import test from 'node:test';
import assert from 'node:assert/strict';
import {createMore} from '../src/more-studies.mjs';

function deferredFile(name='pending.txt') {
 let resolve,reject,reads=0;
 const promise=new Promise((yes,no)=>{resolve=yes;reject=no});
 return {file:{name,size:20,text:()=>{reads++;return promise}},resolve,reject,get reads(){return reads}};
}

function mountIntake(t,saved=null) {
 const mutations=[],statuses=[],writes=[],buttons=new Map(),cleanups=[];
 let mounted=true;
 const nodes=new Map(['localFile','intakeState','original','analysisNote'].map(id=>{
  let value='',textContent=id==='intakeState'?'未选择资料':'';
  const node={files:[],onchange:null,
   get value(){return value},set value(v){value=v;mutations.push([id,'value',v])},
   get textContent(){return textContent},set textContent(v){textContent=v;mutations.push([id,'textContent',v])},
  };
  return ['#'+id,node];
 }));
 const oldStorage=Object.getOwnPropertyDescriptor(globalThis,'localStorage');
 const storage=new Map();
 if(saved!==null)storage.set('review-local-intake',JSON.stringify(saved));
 Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{
  getItem:key=>storage.get(key)??null,
  setItem:(key,value)=>{writes.push([key,value]);storage.set(key,value)},
 }});
 t.after(()=>{if(oldStorage)Object.defineProperty(globalThis,'localStorage',oldStorage);else delete globalThis.localStorage});
 const stage={innerHTML:'',querySelector:selector=>mounted?nodes.get(selector):null};
 createMore('intake',{
  stage,button:(name,run)=>{buttons.set(name,run);return {}},status:message=>statuses.push(message),
  reduce:()=>false,listen:()=>{},onDispose:dispose=>cleanups.push(dispose),
 });
 return {
  nodes,statuses,writes,mutations,storage,
  get original(){return nodes.get('#original').textContent},
  get note(){return nodes.get('#analysisNote').value},
  set note(value){nodes.get('#analysisNote').value=value},
  get state(){return nodes.get('#intakeState').textContent},
  click:name=>buttons.get(name)(),
  choose(file){nodes.get('#localFile').files=file?[file]:[];return nodes.get('#localFile').onchange()},
  dispose(){for(const dispose of cleanups)dispose();mounted=false},
 };
}

const saved={id:'saved-v1',name:'saved.txt',source:'Saved original',note:'Saved note',ingestedAt:17,publishedAt:null};

test('intake: explicitly reopened version and later manual note beat a pending read',async t=>{
 const h=mountIntake(t,saved),old=deferredFile();
 const pending=h.choose(old.file);
 h.click('重开本地版本');
 h.note='Manual note after reopening';
 const messageCount=h.statuses.length;
 old.resolve('Late incoming original');await pending;
 assert.equal(h.original,saved.source);
 assert.equal(h.note,'Manual note after reopening');
 assert.match(h.state,/已重开/);
 assert.equal(h.statuses.length,messageCount);
 assert.equal(h.writes.length,0);
});

test('intake: rejection after dispose is handled without DOM/status/storage effects',async t=>{
 const h=mountIntake(t),old=deferredFile();
 const pending=h.choose(old.file);
 h.dispose();
 const before={mutations:h.mutations.length,statuses:h.statuses.length};
 old.reject(new Error('Late local file error'));
 await assert.doesNotReject(pending);
 assert.equal(h.mutations.length,before.mutations);
 assert.equal(h.statuses.length,before.statuses);
 assert.equal(h.writes.length,0);
});

test('intake: success after dispose cannot write a detached or newly mounted view',async t=>{
 const h=mountIntake(t),old=deferredFile();
 const pending=h.choose(old.file);
 h.dispose();
 const before=h.mutations.length;
 old.resolve('Late content');await pending;
 assert.equal(h.mutations.length,before);
 assert.equal(h.original,'');
 assert.equal(h.writes.length,0);
});

test('intake: cancel preserves displayed original and note and clears pending status',async t=>{
 const h=mountIntake(t,saved);
 h.click('重开本地版本');h.note='Keep this manual note';
 const old=deferredFile(),pending=h.choose(old.file);
 assert.match(h.state,/正在本地读取/);
 h.click('取消读取');
 assert.doesNotMatch(h.state,/正在本地读取/);
 assert.match(h.state,/已取消/);
 const before=h.mutations.length;
 old.resolve('Cancelled content');await pending;
 assert.equal(h.original,saved.source);
 assert.equal(h.note,'Keep this manual note');
 assert.equal(h.mutations.length,before);
 const rejected=deferredFile(),bad=h.choose(rejected.file);
 h.click('取消读取');const count=h.statuses.length;
 rejected.reject(new Error('Cancelled error'));await assert.doesNotReject(bad);
 assert.equal(h.statuses.length,count);
 assert.equal(h.writes.length,0);
});

test('intake: latest selected file beats older success and failure',async t=>{
 const h=mountIntake(t),first=deferredFile('first.txt'),second=deferredFile('second.csv');
 const p1=h.choose(first.file),p2=h.choose(second.file);
 second.resolve('SECOND');await p2;
 const settled=h.mutations.length;
 first.resolve('FIRST');await p1;
 assert.equal(h.original,'SECOND');assert.match(h.state,/second.csv/);
 assert.equal(h.mutations.length,settled);
 const third=deferredFile('third.txt'),fourth=deferredFile('fourth.txt');
 const p3=h.choose(third.file),p4=h.choose(fourth.file);
 fourth.resolve('FOURTH');await p4;
 const latest=h.mutations.length;
 third.reject(new Error('Obsolete error'));await assert.doesNotReject(p3);
 assert.equal(h.original,'FOURTH');assert.equal(h.mutations.length,latest);
 assert.equal(h.writes.length,0);
});

test('intake: failed or missing reopen still invalidates pending read without losing current work',async t=>{
 const h=mountIntake(t,saved);
 h.click('重开本地版本');h.note='Keep edited note';
 for(const value of [null,'{broken','{"id":"bad"}']){
  if(value===null)h.storage.delete('review-local-intake');else h.storage.set('review-local-intake',value);
  const old=deferredFile(),pending=h.choose(old.file);
  h.click('重开本地版本');
  old.resolve('Must not replace current original');await pending;
  assert.equal(h.original,saved.source);assert.equal(h.note,'Keep edited note');
  assert.doesNotMatch(h.state,/正在本地读取/);
 }
 assert.equal(h.writes.length,0);
});

test('intake: clear selection invalidates a pending read and keeps the visible version',async t=>{
 const h=mountIntake(t,saved);h.click('重开本地版本');
 const old=deferredFile(),pending=h.choose(old.file);
 await h.choose(null);
 old.resolve('Must remain cancelled');await pending;
 assert.equal(h.original,saved.source);assert.equal(h.note,saved.note);
 assert.doesNotMatch(h.state,/正在本地读取/);
 assert.equal(h.writes.length,0);
});

test('intake: storage is written once per explicit save, never by reopen or late completion',async t=>{
 const h=mountIntake(t,saved),old=deferredFile(),pending=h.choose(old.file);
 h.click('重开本地版本');h.note='Explicitly saved note';
 assert.equal(h.writes.length,0);
 h.click('保存本地审核笔记');
 assert.equal(h.writes.length,1);
 assert.equal(JSON.parse(h.writes[0][1]).note,'Explicitly saved note');
 old.resolve('Old read');await pending;
 assert.equal(h.writes.length,1);
 assert.equal(h.note,'Explicitly saved note');
 h.dispose();h.click('保存本地审核笔记');
 assert.equal(h.writes.length,1);
});

test('intake: invalid and current failed reads preserve the prior original and notes',async t=>{
 const h=mountIntake(t,saved);h.click('重开本地版本');h.note='Untouched note';
 let reads=0;
 await h.choose({name:'large.txt',size:1000001,text:()=>{reads++;return 'bad'}});
 await h.choose({name:'script.js',size:10,text:()=>{reads++;return 'bad'}});
 assert.equal(reads,0);assert.match(h.state,/读取失败/);
 const failed=deferredFile(),pending=h.choose(failed.file);
 failed.reject(new Error('Current read failure'));await assert.doesNotReject(pending);
 assert.match(h.state,/Current read failure/);
 assert.equal(h.original,saved.source);assert.equal(h.note,'Untouched note');
 assert.equal(h.writes.length,0);
});

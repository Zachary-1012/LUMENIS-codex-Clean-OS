import test from 'node:test';
import assert from 'node:assert/strict';
import {createChapters} from '../src/chapter-study.mjs';
import {createReviewSession} from '../src/review-session.mjs';

// Minimal DOM/media contract, not a browser, audio decoder, layout or accessibility test.
class Node {
  constructor(tag='div') { this.tag=tag; this.children=[]; this.handlers=new Map(); this.dataset={}; this.style={}; this.value=''; this.scrollTop=0; this.selectionStart=0; this.selectionEnd=0; this.selectionDirection='none'; this.paused=true; this.currentTime=0; this.readyState=1; this.loop=false; this.plays=0; this.pauses=0; }
  addEventListener(type,fn) { if(!this.handlers.has(type))this.handlers.set(type,new Set());this.handlers.get(type).add(fn); }
  removeEventListener(type,fn) {this.handlers.get(type)?.delete(fn);}
  fire(type, extra={}) {for(const fn of this.handlers.get(type)||[])fn({target:this,preventDefault(){},...extra});}
  setAttribute(key,val){this[key]=val;}
  removeAttribute(key){delete this[key];}
  append(node){this.children.push(node);}
  replaceChildren(){this.children=[];}
  querySelectorAll(){return this.children.flatMap(n=>n.tag==='button'?[n]:n.querySelectorAll());}
  closest(){return this.tag==='button'?this:null;}
  focus(){}
  setSelectionRange(a,b,d='none'){this.selectionStart=a;this.selectionEnd=b;this.selectionDirection=d;}
  get currentSrc(){return this.src;}
  pause(){this.pauses++;this.paused=true;}
  load(){this.currentTime=0;}
  play(){this.plays++;this.paused=false;return this.playResult||Promise.resolve();}
}
function harness(t) {
  const originalDoc=globalThis.document, create=URL.createObjectURL, revoke=URL.revokeObjectURL;
  const doc=new Node(), revoked=[], urls=[];doc.createElement=tag=>new Node(tag);globalThis.document=doc;
  URL.createObjectURL=()=>{const u='blob:test-'+urls.length;urls.push(u);return u;};URL.revokeObjectURL=u=>revoked.push(u);
  t.after(()=>{globalThis.document=originalDoc;URL.createObjectURL=create;URL.revokeObjectURL=revoke;});
  return {doc,revoked,urls,mount(session){
    const ids=['chapterSource','chapterAudio','chapterPosition','chapterPlayback','chapterList','chapterName','chapterStart','chapterProposal'];
    const nodes=Object.fromEntries(ids.map(id=>[id,new Node(id==='chapterAudio'?'audio':'div')]));nodes.body=new Node();
    const stage=new Node();stage.querySelector=s=>s==='.lab-scroll'?nodes.body:nodes[s.slice(1)];
    const buttons=new Map(), cleanups=[], notices=[];
    createChapters({stage,button:(label,fn)=>buttons.set(label,fn),status:m=>notices.push(m),onDispose:fn=>cleanups.push(fn),session});
    return {nodes,stage,notices,click:label=>buttons.get(label)(),dispose:()=>cleanups.forEach(fn=>fn()),switchTo(i){nodes.chapterSource.value=String(i);nodes.chapterSource.fire('change');},select(id){nodes.chapterList.fire('click',{target:nodes.chapterList.querySelectorAll().find(n=>n.dataset.chapter===id)});}};
  }};
}
const preview='预览章节修订',apply='应用章节修订';
function edit(h,name,start){h.nodes.chapterName.value=name;h.nodes.chapterStart.value=start;h.nodes.chapterName.fire('input');h.click(preview);}

test('adapter preserves per-fixture revisions, pending proposals, selection, undo and raw drafts on route return',t=>{
  const env=harness(t),session=createReviewSession(['chapters']);let h=env.mount(session);
  edit(h,'A adopted','0');h.click(apply);h.select('a2');edit(h,'A pending','1.5');
  h.switchTo(1);h.select('b2');h.nodes.chapterName.value='  未提交 B  ';h.nodes.chapterStart.value='2.125';
  h.nodes.chapterName.setSelectionRange(2,5,'backward');h.nodes.chapterName.scrollTop=11;h.nodes.body.scrollTop=173;
  h.dispose();h=env.mount(session);
  assert.equal(h.nodes.chapterSource.value,'1');assert.equal(h.nodes.chapterName.value,'  未提交 B  ');assert.equal(h.nodes.chapterStart.value,'2.125');
  assert.equal(h.nodes.chapterName.selectionStart,2);assert.equal(h.nodes.chapterName.selectionEnd,5);assert.equal(h.nodes.chapterName.selectionDirection,'backward');assert.equal(h.nodes.body.scrollTop,173);
  h.switchTo(0);assert.match(h.nodes.chapterProposal.textContent,/A pending/);h.click(apply);h.dispose();
  let saved=session.read('chapters').sources['tone-a'].state;assert.equal(saved.selected,'a2');assert.equal(saved.chapters[1].name,'A pending');assert.equal(saved.history.length,2);
  h=env.mount(session);h.click('撤销章节修订');h.dispose();saved=session.read('chapters').sources['tone-a'].state;assert.equal(saved.chapters[0].name,'A adopted');assert.equal(saved.chapters[1].name,'人工章：观察');assert.equal(saved.history.length,1);
});

test('cancel and Escape remain cancelable after return; stop clears loop without adopting pending edit',t=>{
  const env=harness(t),session=createReviewSession(['chapters']);let h=env.mount(session);
  edit(h,'Not adopted','0');h.dispose();h=env.mount(session);h.click('取消待修订');assert.match(h.nodes.chapterProposal.textContent,/没有待应用/);
  edit(h,'Escape pending','0');h.stage.fire('keydown',{key:'Escape'});h.dispose();
  const state=session.read('chapters').sources['tone-a'].state;assert.equal(state.proposal,null);assert.equal(state.chapters[0].name,'人工章：开场');assert.equal(state.loop,null);
});

test('dispose stops real adapter media, revokes URL, removes listeners and stale play rejection cannot affect return',async t=>{
  const env=harness(t),session=createReviewSession(['chapters']);let h=env.mount(session);let reject;
  h.nodes.chapterAudio.playResult=new Promise((_,r)=>reject=r);h.click('开始所选章节循环');assert.equal(h.nodes.chapterAudio.plays,1);assert.equal(h.nodes.chapterAudio.loop,true);
  const old=h, oldUrl=old.nodes.chapterAudio.src;old.dispose();assert.equal(old.nodes.chapterAudio.paused,true);assert.equal(old.nodes.chapterAudio.loop,false);assert.equal(old.nodes.chapterAudio.src,undefined);assert.ok(env.revoked.includes(oldUrl));
  assert.equal([...old.nodes.chapterAudio.handlers.values()].reduce((n,s)=>n+s.size,0),0);assert.equal(env.doc.handlers.get('visibilitychange').size,0);
  h=env.mount(session);const notices=h.notices.length;reject(Error('late'));await Promise.resolve();await Promise.resolve();
  assert.equal(h.nodes.chapterAudio.plays,0);assert.equal(h.nodes.chapterAudio.loop,false);assert.equal(h.notices.length,notices);h.dispose();assert.equal(env.revoked.length,env.urls.length);
});

test('explicit stop and page hiding pause playback; reentry is never autoplay',t=>{
  const env=harness(t),session=createReviewSession(['chapters']);let h=env.mount(session);
  h.click('开始所选章节循环');h.click('停止试听 / 停止循环');assert.equal(h.nodes.chapterAudio.loop,false);assert.equal(h.nodes.chapterAudio.paused,true);
  h.click('开始所选章节循环');env.doc.hidden=true;env.doc.fire('visibilitychange');assert.equal(h.nodes.chapterAudio.loop,false);assert.equal(h.nodes.chapterAudio.paused,true);
  h.dispose();h=env.mount(session);assert.equal(h.nodes.chapterAudio.plays,0);h.dispose();
});

test('malformed or stale snapshots cannot crash adapter or inject permission/runtime objects',t=>{
  const env=harness(t),session=createReviewSession(['chapters']);let h=env.mount(session);h.dispose();const good=session.read('chapters');
  for(const mutate of [s=>{s.sources['tone-a'].state.history=[null]},s=>{s.sources['tone-a'].state.chapters=[{}]},s=>{s.sources['tone-a'].state.source.version='old'},s=>{s.sources['tone-a'].state.selected='absent'},s=>{s.sources['tone-a'].state.proposal={base:1}},s=>{s.sources['tone-a'].ui={name:{value:'draft',start:Infinity,end:-9},scroll:Infinity}}]){
    const bad=structuredClone(good);mutate(bad);session.write('chapters',bad);assert.doesNotThrow(()=>{h=env.mount(session);h.dispose();});
  }
  const injected=structuredClone(good);injected.sources['tone-a'].state.permission={allowed:true};injected.sources['tone-a'].state.loop={id:'a1'};session.write('chapters',injected);h=env.mount(session);h.dispose();const saved=session.read('chapters').sources['tone-a'].state;assert.equal(saved.permission,undefined);assert.equal(saved.loop,null);
});

test('optional or failing session still cleans media without throwing',t=>{
  const env=harness(t);for(const session of [undefined,{read(){throw Error('read')},write(){throw Error('write')}}]){
    const h=env.mount(session),url=h.nodes.chapterAudio.src;assert.doesNotThrow(()=>h.dispose());assert.ok(env.revoked.includes(url));
  }
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {getEventListeners} from 'node:events';
import {createRelations} from '../src/relations-study.mjs';
import {createWordEdit} from '../src/word-study.mjs';

// Mounted event-handler tests, not source-marker assertions. This tiny DOM
// models ownership and events only; native animation/focus/layout need browser QA.
class Element extends EventTarget {
 constructor(tag,owner){super();this.tagName=tag;this.ownerDocument=owner;this.children=[];this.dataset={};this.attributes={};this.value='';this.textContent='';this.open=false;this.isConnected=true;this.pauses=0;this.loads=0}
 set innerHTML(html){this.replaceChildren();for(const [,tag,id] of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g)){const child=new Element(tag,this.ownerDocument);child.id=id;this.append(child)}}
 append(...children){for(const child of children){child.parent=this;this.children.push(child)}}
 replaceChildren(...children){for(const child of this.children)child.isConnected=false;this.children=[];this.append(...children)}
 querySelector(selector){const data=selector.match(/^\[data-(\w+)="([^"]+)"\]$/),match=node=>selector[0]==='#'?node.id===selector.slice(1):data&&node.dataset[data[1]]===data[2];for(const child of this.children){if(match(child))return child;const nested=child.querySelector(selector);if(nested)return nested}return null}
 setAttribute(name,value){this.attributes[name]=String(value)}
 removeAttribute(name){delete this.attributes[name];if(name==='src')this.src=''}
 focus(){this.ownerDocument.activeElement=this}
 showModal(){this.open=true}
 close(){this.open=false}
 remove(){this.isConnected=false;if(this.parent)this.parent.children=this.parent.children.filter(child=>child!==this)}
 pause(){this.pauses++}
 load(){this.loads++}
 animate(frames,options){
  if(this.ownerDocument.failAnimation)throw Error('Animation unavailable');
  const animation={node:this,frames,options,playState:'running',cancels:0,onfinish:null,oncancel:null,
   cancel(){this.cancels++;this.playState='idle';this.oncancel?.()},
   finish(){this.playState='finished';this.onfinish?.()},
  };
  this.ownerDocument.animations.push(animation);return animation;
 }
}

function replace(t,target,key,value){const prior=Object.getOwnPropertyDescriptor(target,key);Object.defineProperty(target,key,{configurable:true,writable:true,value});t.after(()=>{if(prior)Object.defineProperty(target,key,prior);else delete target[key]})}

function mount(t,kind,{withListen=true,reduced=false}={}){
 const window=new EventTarget(),document=new EventTarget();
 document.hidden=false;document.visibilityState='visible';document.animations=[];
 document.createElement=tag=>new Element(tag,document);document.createElementNS=(_,tag)=>new Element(tag,document);
 document.body=document.createElement('body');
 replace(t,globalThis,'window',window);replace(t,globalThis,'document',document);
 const blobs=new Map(),created=[],revoked=[],statuses=[],buttons=new Map(),moduleCleanups=[],hostCleanups=[],registrations=[];
 replace(t,URL,'createObjectURL',blob=>{const url='blob:motion-'+(created.length+1);created.push(url);blobs.set(url,blob);return url});
 replace(t,URL,'revokeObjectURL',url=>revoked.push(url));
 const stage=document.createElement('main');document.body.append(stage);
 const options={stage,button:(label,run)=>buttons.set(label,run),status:value=>statuses.push(value),reduce:()=>reduced,onDispose:fn=>moduleCleanups.push(fn)};
 if(withListen)options.listen=(target,type,handler,opts)=>{registrations.push({target,type,handler});target.addEventListener(type,handler,opts);hostCleanups.push(()=>target.removeEventListener(type,handler,opts))};
 (kind==='relations'?createRelations:createWordEdit)(options);
 let disposed=false;
 const h={stage,window,document,statuses,buttons,registrations,created,revoked,blobs,animations:document.animations,
  q:selector=>stage.querySelector(selector),click:label=>buttons.get(label)(),
  select(id){stage.querySelector(`[data-${kind==='relations'?'edge':'word'}="${id}"]`).onclick()},
  motion(value){reduced=value;window.dispatchEvent(new Event('review-motion-change'))},
  visibility(hidden){document.hidden=hidden;document.visibilityState=hidden?'hidden':'visible';document.dispatchEvent(new Event('visibilitychange'))},
  dispose(){if(disposed)return;disposed=true;for(const fn of moduleCleanups)fn();for(const fn of hostCleanups)fn();stage.remove()},
 };
 t.after(()=>h.dispose());return h;
}

function adopt(h,id='w0'){h.select(id);h.click('预览删词剪切');h.click('采纳剪切')}

test('relations: preference changes cancel the owned effect and preserve selected evidence',t=>{
 const h=mount(t,'relations');h.select('ab');
 const first=h.animations[0],detail=h.q('#relationDetail').textContent,selected=h.q('[data-edge="ab"]');
 assert.equal(first.options.duration,400);assert.equal(selected.attributes['aria-pressed'],'true');
 h.motion(true);assert.equal(first.cancels,1);assert.equal(h.q('#relationDetail').textContent,detail);assert.equal(h.document.activeElement,selected);
 h.select('ab');assert.equal(h.animations.length,1);assert.match(h.q('#relationDetail').textContent,/样例引用/);
 h.motion(false);assert.equal(h.animations.length,1,'enabling motion cannot replay a cancelled effect');
 h.select('ab');assert.equal(h.animations.length,2);assert.equal(h.animations[1].playState,'running');
});

test('relations: replacement and stale completion cannot detach ownership of the latest effect',t=>{
 const h=mount(t,'relations');h.select('ab');const old=h.animations[0],lateFinish=old.onfinish;
 assert.equal(typeof lateFinish,'function');h.select('ab');const current=h.animations[1];
 assert.equal(old.cancels,1);lateFinish();h.motion(true);assert.equal(current.cancels,1);
 h.motion(false);h.select('ab');const completed=h.animations[2];completed.finish();h.motion(true);
 assert.equal(completed.cancels,0,'a naturally completed effect no longer needs cancellation');
});

test('relations: filter and permission changes cancel animation without retaining stale relationships',t=>{
 const h=mount(t,'relations');h.select('ab');const first=h.animations[0];
 h.q('#relationFilter').onchange({target:{value:'推断'}});assert.equal(first.cancels,1);assert.equal(h.q('[data-edge="ab"]'),null);assert.equal(h.q('#relationList').children.length,0);
 h.q('#relationFilter').onchange({target:{value:'all'}});h.select('ab');h.click('查看所选关系依据');const dialog=h.document.body.children.find(n=>n.tagName==='dialog');assert.equal(dialog.open,true);
 const second=h.animations[1];h.click('审核事件：撤回权限');assert.equal(second.cancels,1);assert.equal(dialog.open,false);
 assert.equal(h.q('#relationList').children.length,0);assert.equal(h.q('#relationGraph').children.length,0);assert.match(h.q('#relationDetail').textContent,/权限不足/);
});

test('relations: disposal releases animation, listeners and dialog; retained handlers are inert',t=>{
 const h=mount(t,'relations');h.select('ab');const effect=h.animations[0],oldSelect=h.q('[data-edge="ab"]').onclick,oldFilter=h.q('#relationFilter').onchange;
 assert.ok(h.registrations.some(x=>x.type==='review-motion-change'));
 h.dispose();assert.equal(effect.cancels,1);assert.equal(h.document.body.children.some(n=>n.tagName==='dialog'),false);
 assert.equal(getEventListeners(h.window,'review-motion-change').length,0);assert.equal(getEventListeners(h.document,'visibilitychange').length,0);
 const before={animations:h.animations.length,statuses:h.statuses.length};
 oldSelect();oldFilter({target:{value:'all'}});h.click('审核事件：撤回权限');h.click('查看所选关系依据');h.motion(true);h.visibility(true);
 assert.deepEqual({animations:h.animations.length,statuses:h.statuses.length},before);assert.equal(effect.cancels,1);
});

test('word edit: reduced motion cancels adoption emphasis without undoing samples or draft',t=>{
 const h=mount(t,'word');adopt(h);const effect=h.animations[0],audio=h.q('#wordAudio'),url=audio.src,correction=h.q('#wordCorrection');
 assert.equal(effect.options.duration,150);assert.equal(h.blobs.get(url).size,44+24000*2);assert.match(h.q('#wordDuration').textContent,/v2.*3\.000秒/);
 correction.value='Unsaved correction';correction.selectionStart=2;correction.selectionEnd=7;correction.scrollTop=19;audio.currentTime=.4;
 correction.focus();h.motion(true);assert.equal(effect.cancels,1);
 assert.equal(audio.src,url);assert.equal(audio.currentTime,.4);assert.equal(correction.value,'Unsaved correction');assert.equal(correction.selectionStart,2);assert.equal(correction.selectionEnd,7);assert.equal(correction.scrollTop,19);assert.equal(h.document.activeElement,correction);assert.equal(h.q('[data-word="w0"]').attributes['aria-pressed'],'true');
 h.motion(false);assert.equal(h.animations.length,1);h.motion(true);adopt(h,'w1');
 assert.equal(h.animations.length,1);assert.match(h.q('#wordDuration').textContent,/v3.*2\.000秒/);assert.equal(h.blobs.get(audio.src).size,44+16000*2);
 h.click('撤销上次编辑');assert.match(h.q('#wordDuration').textContent,/v4.*3\.000秒/);
});

test('word edit: newer work cancels adoption emphasis and obsolete completion cannot clear the latest effect',t=>{
 const h=mount(t,'word');adopt(h);const old=h.animations[0],lateFinish=old.onfinish;
 assert.equal(typeof lateFinish,'function');adopt(h,'w1');const current=h.animations[1];assert.equal(old.cancels,1);
 lateFinish();h.motion(true);assert.equal(current.cancels,1);h.motion(false);adopt(h,'w2');
 const last=h.animations[2];h.click('撤销上次编辑');assert.equal(last.cancels,1);assert.match(h.q('#wordDuration').textContent,/2\.000秒/);
});

test('word edit: completed animation is released and an invalid adoption never starts an effect',t=>{
 const h=mount(t,'word');h.click('采纳剪切');assert.equal(h.animations.length,0);
 adopt(h);const finished=h.animations[0];finished.finish();h.motion(true);assert.equal(finished.cancels,0);
 h.motion(false);h.select('w1');h.click('预览删词剪切');h.q('#wordCorrection').value='A real manual correction';h.click('只修改校对文字');
 h.click('采纳剪切');assert.equal(h.animations.length,1);assert.match(h.statuses.at(-1),/稿件版本已改变/);assert.match(h.q('#wordDuration').textContent,/3\.000秒/);
});

test('word edit: disposal cancels animation and releases audio without allowing stale controls to restart work',t=>{
 const h=mount(t,'word');adopt(h);const effect=h.animations[0],audio=h.q('#wordAudio'),oldSelect=h.q('[data-word="w1"]').onclick;
 assert.ok(h.registrations.some(x=>x.type==='review-motion-change'));
 h.dispose();assert.equal(effect.cancels,1);assert.equal(audio.src,'');assert.equal(audio.oncanplay,null);assert.deepEqual(h.revoked,h.created);
 assert.equal(getEventListeners(h.window,'review-motion-change').length,0);assert.equal(getEventListeners(h.document,'visibilitychange').length,0);
 const before={animations:h.animations.length,statuses:h.statuses.length,urls:h.created.length,pauses:audio.pauses,loads:audio.loads};
 oldSelect();for(const run of h.buttons.values())run();h.motion(true);h.visibility(true);
 assert.deepEqual({animations:h.animations.length,statuses:h.statuses.length,urls:h.created.length,pauses:audio.pauses,loads:audio.loads},before);assert.equal(effect.cancels,1);
});

for(const kind of ['relations','word']){
 test(`${kind}: hiding cancels the effect; background work and returning visible never replay it`,t=>{
  const h=mount(t,kind);if(kind==='relations')h.select('ab');else adopt(h);
  const effect=h.animations[0];h.visibility(true);assert.equal(effect.cancels,1);
  if(kind==='relations')h.select('ab');else adopt(h,'w1');assert.equal(h.animations.length,1);
  h.visibility(false);assert.equal(h.animations.length,1);assert.equal(effect.cancels,1);
 });
 test(`${kind}: standalone mounting owns listener cleanup even without host listen`,t=>{
  const h=mount(t,kind,{withListen:false});if(kind==='relations')h.select('ab');else adopt(h);
  const effect=h.animations[0];h.motion(true);assert.equal(effect.cancels,1);h.dispose();h.motion(false);assert.equal(effect.cancels,1);
  assert.equal(getEventListeners(h.window,'review-motion-change').length,0);assert.equal(getEventListeners(h.document,'visibilitychange').length,0);
 });
 test(`${kind}: unavailable decorative animation leaves the real action and result usable`,t=>{
  const h=mount(t,kind);h.document.failAnimation=true;
  assert.doesNotThrow(()=>{if(kind==='relations')h.select('ab');else adopt(h)});
  if(kind==='relations'){assert.equal(h.q('[data-edge="ab"]').attributes['aria-pressed'],'true');assert.match(h.q('#relationDetail').textContent,/样例引用/)}
  else{assert.match(h.q('#wordDuration').textContent,/v2.*3\.000秒/);h.click('撤销上次编辑');assert.match(h.q('#wordDuration').textContent,/4\.000秒/)}
 });
}

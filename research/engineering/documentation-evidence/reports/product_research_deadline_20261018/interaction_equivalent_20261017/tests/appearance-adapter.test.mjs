import test from 'node:test';
import assert from 'node:assert/strict';
import {createExtra} from '../src/studies.mjs';

// This exercises the mounted adapter's event handlers in a minimal DOM model.
// Native focus, layout, contrast and wallpaper decoding still need browser QA.
class Element {
 constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.style={};this.files=[];this._value=''}
 append(...nodes){this.children.push(...nodes)}
 get value(){return this._value}
 set value(value){this._value=String(value)}
 querySelector(selector){return this.children.find(node=>node.tagName.toLowerCase()===selector)||null}
}

function replaceProperty(t,target,key,value){
 const prior=Object.getOwnPropertyDescriptor(target,key);
 Object.defineProperty(target,key,{configurable:true,writable:true,value});
 t.after(()=>{if(prior)Object.defineProperty(target,key,prior);else delete target[key]});
}

function mountAppearance(t,initial={bg:'#dbe2d3',size:17,blur:true}){
 let preferences={...initial},gets=0,markupWrites=0,mounted=true;
 const updates=[],statuses=[],cleanups=[],settings=new Map(),created=[],revoked=[],localReads=[],localWrites=[];
 const window=new EventTarget(),document={createElement:tag=>new Element(tag)};
 replaceProperty(t,globalThis,'window',window);
 replaceProperty(t,globalThis,'document',document);
 replaceProperty(t,globalThis,'localStorage',{
  getItem(key){localReads.push(key);throw Error('Appearance must use its host preference owner')},
  setItem(key,value){localWrites.push([key,value]);throw Error('Appearance must not save independently')},
  removeItem(key){localWrites.push([key,null]);throw Error('Appearance must not reset storage independently')},
 });
 replaceProperty(t,URL,'createObjectURL',file=>{const value='blob:local-wallpaper-'+(created.length+1);created.push({file,value});return value});
 replaceProperty(t,URL,'revokeObjectURL',url=>revoked.push(url));
 const preview=new Element('div'),article=new Element('article'),draft=new Element('textarea');
 draft.value='My unchanged draft';draft.selectionStart=3;draft.selectionEnd=9;draft.scrollTop=23;
 article.append(draft);preview.append(article);
 const stage={
  set innerHTML(_){markupWrites++},
  querySelector:selector=>mounted?({'#appearancePreview':preview,'#appearanceDraft':draft}[selector]||null):null,
 };
 const settingsRoot=new Element('section');
 createExtra('appearance',{
  stage,settingsRoot,button:()=>{throw Error('Appearance controls belong in unified settings')},
  status:message=>statuses.push(message),reduce:()=>false,
  onDispose:dispose=>cleanups.push(dispose),
  listen:(target,event,handler)=>{target.addEventListener(event,handler);cleanups.push(()=>target.removeEventListener(event,handler))},
  settingButton:(name,handler)=>{settings.set(name,handler);return new Element('button')},
  getAppearance:()=>{gets++;return {...preferences}},
  setAppearance:value=>{preferences={...value};updates.push({...value})},
 });
 const inputs=settingsRoot.children[0].children.map(label=>label.children[0]);
 const controls=Object.fromEntries(inputs.map(input=>[input.type,input]));
 return {
  preview,article,draft,controls,updates,statuses,created,revoked,localReads,localWrites,settings,
  get preferences(){return preferences},get gets(){return gets},get markupWrites(){return markupWrites},
  click:name=>settings.get(name)(),
  reset(value){preferences={...value};window.dispatchEvent(new Event('review-appearance-reset'))},
  dispose(){for(const cleanup of cleanups)cleanup();mounted=false},
 };
}

function assertDraftRetained(h){
 assert.equal(h.draft.value,'My unchanged draft');
 assert.equal(h.draft.selectionStart,3);assert.equal(h.draft.selectionEnd,9);assert.equal(h.draft.scrollTop,23);
 assert.equal(h.markupWrites,1);
}

test('appearance adapter reads initial host preferences and renders them without local storage',t=>{
 const h=mountAppearance(t);
 assert.equal(h.gets,1);
 assert.deepEqual(h.preferences,{bg:'#dbe2d3',size:17,blur:true});
 assert.equal(h.controls.color.value,'#dbe2d3');assert.equal(h.controls.range.value,'17');
 assert.equal(h.preview.style.backgroundColor,'#dbe2d3');assert.equal(h.preview.style.fontSize,'17px');
 assert.equal(h.article.style.backdropFilter,'blur(12px)');
 assertDraftRetained(h);
 assert.deepEqual(h.localReads,[]);assert.deepEqual(h.localWrites,[]);
 assert.equal(h.settings.has('保存颜色与字号'),false);
});

test('appearance color/font edits update host state and preview without resetting the draft',t=>{
 const h=mountAppearance(t);
 h.controls.color.value='#335577';h.controls.color.oninput();
 h.controls.range.value='18';h.controls.range.oninput();
 assert.deepEqual(h.preferences,{bg:'#335577',size:18,blur:true});
 assert.deepEqual(h.updates.at(-1),h.preferences);
 assert.equal(h.preview.style.backgroundColor,'#335577');assert.equal(h.preview.style.fontSize,'18px');
 assertDraftRetained(h);
 assert.deepEqual(h.localReads,[]);assert.deepEqual(h.localWrites,[]);
});

test('appearance presets keep the swatch and host preference in sync',t=>{
 const h=mountAppearance(t);
 for(const [name,bg] of [['纯白','#ffffff'],['纯黑','#000000']]){
  h.click(name);
  assert.equal(h.preferences.bg,bg);assert.equal(h.preview.style.backgroundColor,bg);
  assert.equal(h.controls.color.value,bg);
 }
 h.click('切换局部磨砂');
 assert.equal(h.preferences.blur,false);assert.equal(h.article.style.backdropFilter,'none');
 assertDraftRetained(h);assert.deepEqual(h.localWrites,[]);
});

test('appearance host reset refreshes all controls, releases wallpaper, and preserves text/selection',t=>{
 const h=mountAppearance(t),file={type:'image/png',size:32,name:'wallpaper.png'};
 h.controls.file.files=[file];h.controls.file.value='local-image';h.controls.file.onchange();
 assert.equal(h.created.length,1);assert.match(h.preview.style.backgroundImage,/blob:local-wallpaper-1/);
 h.reset({bg:'#eef0e6',size:14,blur:false});
 assert.equal(h.gets,2);assert.deepEqual(h.preferences,{bg:'#eef0e6',size:14,blur:false});
 assert.equal(h.controls.color.value,'#eef0e6');assert.equal(h.controls.range.value,'14');
 assert.equal(h.controls.file.value,'');assert.equal(h.preview.style.backgroundImage,'none');
 assert.equal(h.preview.style.fontSize,'14px');assert.equal(h.article.style.backdropFilter,'none');
 assert.deepEqual(h.revoked,['blob:local-wallpaper-1']);
 assertDraftRetained(h);assert.deepEqual(h.localReads,[]);assert.deepEqual(h.localWrites,[]);
 h.dispose();assert.deepEqual(h.revoked,['blob:local-wallpaper-1']);
});

test('appearance local defaults use the host owner and do not claim durable saving',t=>{
 const h=mountAppearance(t);
 h.click('恢复局部外观默认');
 assert.deepEqual(h.preferences,{bg:'#eef0e6',size:14,blur:false});
 assert.equal(h.controls.color.value,'#eef0e6');assert.equal(h.controls.range.value,'14');
 assert.match(h.statuses.at(-1),/统一保存当前偏好/);
 assertDraftRetained(h);assert.deepEqual(h.localWrites,[]);
});

test('appearance wallpaper stays memory-local, rejects unsupported input, and cleans up lifecycle',t=>{
 const h=mountAppearance(t);
 for(const file of [{type:'text/plain',size:3},{type:'image/png',size:8*1024*1024+1}]){
  h.controls.file.files=[file];h.controls.file.onchange();
 }
 assert.equal(h.created.length,0);
 h.controls.file.files=[{type:'image/png',size:32}];h.controls.file.onchange();
 h.controls.file.files=[{type:'image/jpeg',size:64}];h.controls.file.onchange();
 assert.equal(h.created.length,2);assert.deepEqual(h.revoked,['blob:local-wallpaper-1']);
 assert.deepEqual(Object.keys(h.preferences).sort(),['bg','blur','size']);
 const updateCount=h.updates.length;h.dispose();
 assert.deepEqual(h.revoked,['blob:local-wallpaper-1','blob:local-wallpaper-2']);
 h.reset({bg:'#ffffff',size:16,blur:false});
 assert.equal(h.updates.length,updateCount);
 assert.deepEqual(h.localReads,[]);assert.deepEqual(h.localWrites,[]);
});

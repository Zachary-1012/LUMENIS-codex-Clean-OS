import test from 'node:test';
import assert from 'node:assert/strict';
import {createCommands} from '../src/command-study.mjs';
import {createReviewSession,canOpenDialog} from '../src/review-session.mjs';

// Actual adapter mounted on a minimal event/DOM double, not browser focus/layout proof.
class Node {
 constructor(doc,tag='div'){Object.assign(this,{doc,tag,children:[],handlers:new Map(),style:{},value:'',textContent:'',scrollTop:0,selectionStart:0,selectionEnd:0,selectionDirection:'none',isConnected:false,open:false});}
 set innerHTML(html){this.html=html;this.nodes={};for(const m of html.matchAll(/<(textarea|input|p|div|button)[^>]*id="([^"]+)"[^>]*>([^<]*)/g)){const n=new Node(this.doc,m[1]);n.value=m[1]==='textarea'?m[3]:'';n.textContent=m[3];n.isConnected=this.isConnected;this.nodes[m[2]]=n;}if(html.includes('class="lab-scroll"')){this.nodes.body=new Node(this.doc);this.nodes.body.isConnected=true;}}
 querySelector(s){return s==='.lab-scroll'?this.nodes.body:this.nodes[s.slice(1)];}
 setAttribute(k,v){this[k]=v;}
 addEventListener(t,fn){if(!this.handlers.has(t))this.handlers.set(t,new Set());this.handlers.get(t).add(fn);}
 removeEventListener(t,fn){this.handlers.get(t)?.delete(fn);}
 fire(type,extra={}){const e={target:this,defaultPrevented:false,preventDefault(){this.defaultPrevented=true},...extra};for(const fn of this.handlers.get(type)||[])fn(e);this['on'+type]?.(e);return e;}
 append(n){this.children.push(n);n.isConnected=this.isConnected;for(const child of Object.values(n.nodes||{}))child.isConnected=n.isConnected;}
 replaceChildren(){this.children=[];}
 focus(){if(this.isConnected)this.doc.activeElement=this;}
 setSelectionRange(a,b,d='none'){this.selectionStart=a;this.selectionEnd=b;this.selectionDirection=d;}
 showModal(){this.open=true;}
 close(){this.open=false;}
 remove(){this.isConnected=false;this.doc.body.children=this.doc.body.children.filter(n=>n!==this);for(const n of Object.values(this.nodes||{}))n.isConnected=false;}
}
function harness(t){
 const old={document:globalThis.document,window:globalThis.window};const doc={};doc.body=new Node(doc);doc.body.isConnected=true;doc.createElement=tag=>new Node(doc,tag);doc.querySelectorAll=()=>doc.body.children.filter(n=>n.tag==='dialog'&&n.open);const win=new Node(doc);globalThis.document=doc;globalThis.window=win;
 t.after(()=>Object.assign(globalThis,old));
 return {doc,win,mount(session){const stage=new Node(doc);stage.isConnected=true;const buttons=new Map(),cleanups=[],notices=[];createCommands({stage,button:(label,fn)=>buttons.set(label,fn),status:s=>notices.push(s),onDispose:fn=>cleanups.push(fn),session});const dialog=doc.body.children.at(-1);return {stage,dialog,notices,editor:stage.querySelector('#commandDraft'),query:dialog.querySelector('#commandQuery'),result:stage.querySelector('#commandResult'),open:buttons.get('打开命令面板'),close:()=>dialog.querySelector('#commandClose').fire('click'),dispose:()=>cleanups.forEach(fn=>fn())};}};
}

test('command adapter returns raw draft, selection, both scrolls and local result without reopening modal',t=>{
 const env=harness(t),session=createReviewSession(['commands']);let h=env.mount(session);
 h.editor.value='  原稿 <script>不是执行</script>  ';h.editor.setSelectionRange(2,7,'backward');h.editor.scrollTop=19;h.stage.querySelector('.lab-scroll').scrollTop=132;h.editor.focus();h.open();h.query.value='compare';h.query.fire('input');h.query.fire('keydown',{key:'Enter'});const result=h.result.textContent;assert.match(result,/B未知/);
 h.open();h.dispose();assert.equal(h.dialog.open,false);assert.equal(h.dialog.isConnected,false);
 h=env.mount(session);assert.equal(h.editor.value,'  原稿 <script>不是执行</script>  ');assert.deepEqual([h.editor.selectionStart,h.editor.selectionEnd,h.editor.selectionDirection],[2,7,'backward']);assert.equal(h.editor.scrollTop,19);assert.equal(h.stage.querySelector('.lab-scroll').scrollTop,132);assert.equal(h.result.textContent,result);assert.equal(h.dialog.open,false);assert.equal(h.query.value,'');assert.equal(session.read('commands').open,undefined);h.dispose();
});

test('settings modal and command modal are mutually exclusive, and shortcuts respect existing ownership',t=>{
 const env=harness(t),h=env.mount();const settings=env.doc.createElement('dialog');env.doc.body.append(settings);settings.showModal();settings.focus();h.open();assert.equal(h.dialog.open,false);const blocked=env.win.fire('keydown',{key:'k',ctrlKey:true});assert.equal(blocked.defaultPrevented,false);assert.equal(env.doc.activeElement,settings);
 settings.close();env.win.fire('keydown',{key:'k',metaKey:true,defaultPrevented:true});assert.equal(h.dialog.open,false);
 env.win.fire('keydown',{key:'K',ctrlKey:true});assert.equal(h.dialog.open,true);assert.equal(canOpenDialog(settings,env.doc.querySelectorAll('dialog[open]')),false);h.dispose();
});

test('native Escape cancel and explicit close restore connected origin or editor fallback',t=>{
 const env=harness(t),h=env.mount();const origin=env.doc.createElement('button');env.doc.body.append(origin);origin.focus();h.open();assert.equal(env.doc.activeElement,h.query);const e=h.dialog.fire('cancel');assert.equal(e.defaultPrevented,true);assert.equal(h.dialog.open,false);assert.equal(env.doc.activeElement,origin);
 origin.focus();h.open();h.close();assert.equal(env.doc.activeElement,origin);
 h.open();origin.remove();h.close();assert.equal(env.doc.activeElement,h.editor);h.dispose();
});

test('empty search Enter is inert; arrows choose only registered local actions; prevented Enter is respected',t=>{
 const env=harness(t),h=env.mount();h.open();h.query.value='not-a-command';h.query.fire('input');const before=h.result.textContent;h.query.fire('keydown',{key:'Enter'});assert.equal(h.result.textContent,before);assert.equal(h.notices.length,0);assert.equal(h.dialog.open,true);h.query.fire('keydown',{key:'ArrowDown'});
 h.query.value='';h.query.fire('input');h.query.fire('keydown',{key:'ArrowUp'});h.query.fire('keydown',{key:'Enter',defaultPrevented:true});assert.equal(h.notices.length,0);h.query.fire('keydown',{key:'Enter'});assert.match(h.result.textContent,/未触发保存/);assert.equal(h.dialog.open,false);h.dispose();
});

test('unmount removes modal and all listeners; captured callbacks cannot write or reopen after return',t=>{
 const env=harness(t),session=createReviewSession(['commands']),h=env.mount(session);h.open();const staleButton=h.dialog.querySelector('#commandItems').children[0].onclick;const staleKey=[...env.win.handlers.get('keydown')][0];h.dispose();const saved=session.read('commands');const next=env.mount(session);staleButton();h.open();staleKey({key:'k',ctrlKey:true,preventDefault(){throw Error('stale')}});h.editor.value='late';h.dispose();assert.deepEqual(session.read('commands'),saved);assert.equal(next.dialog.open,false);assert.equal(h.notices.length,0);assert.equal(h.dialog.isConnected,false);
 for(const node of [h.dialog,h.query,h.dialog.querySelector('#commandClose')])assert.equal([...node.handlers.values()].reduce((n,s)=>n+s.size,0),0);
 assert.equal(env.win.handlers.get('keydown').size,1);next.dispose();assert.equal(env.win.handlers.get('keydown').size,0);
});

test('optional/throwing session and malformed snapshots remain local and cleanly disposable',t=>{
 const env=harness(t);for(const session of [undefined,{read(){throw Error('read')},write(){throw Error('write')}},{read(){return {version:1,draft:'abc',start:Infinity,end:-4,direction:'evil',scroll:Infinity,executed:'__proto__',permission:true,open:true}},write(){}}]){const h=env.mount(session);assert.equal(h.dialog.open,false);assert.match(h.result.textContent,/还没有/);assert.equal(h.editor.selectionStart,0);assert.doesNotThrow(()=>h.dispose());assert.equal(h.dialog.isConnected,false);}
});

import{canOpenDialog}from'./review-session.mjs';
import{searchCommands,chooseCommand}from'./command-palette.mjs';
export const commandStudy=['commands','25','KEYBOARD / SEARCH / RETURN','不离开手中的工作','用⌘K/Ctrl+K或按钮打开命令面板，筛选、方向键选择、Enter执行局部动作；Escape返回原文稿。','规划§18.2 F0命令面板、§4键盘等价；仅注册本地动作，不执行任意命令或产品写入。',[]];
const results={inspect:'依据：人工审核文案，没有真实业务来源。',compare:'对照：本地示例A有0项；B未知，不能相减。',draft:'继续当前稿件，未触发保存。'};
const initialResult='还没有执行局部动作。';
export function createCommands({stage,button,status,onDispose,session}){
 stage.innerHTML='<section class="lab-scroll"><label>当前文稿<textarea id="commandDraft">命令面板打开时，编辑仍属于这里。</textarea></label><p id="commandResult">还没有执行局部动作。</p></section>';
 const q=x=>stage.querySelector(x),editor=q('#commandDraft'),body=q('.lab-scroll');
 let previous=null,items=[],selected=0,disposed=false,executed=null;
 const nonnegative=n=>Number.isFinite(n)?Math.max(0,n):0;
 let saved;try{saved=session?.read('commands')}catch{}
 if(saved?.version===1&&typeof saved.draft==='string'){
  editor.value=saved.draft;
  const start=Math.min(editor.value.length,nonnegative(saved.start));
  const end=Math.max(start,Math.min(editor.value.length,nonnegative(saved.end)));
  editor.setSelectionRange(start,end,['forward','backward','none'].includes(saved.direction)?saved.direction:'none');
  editor.scrollTop=nonnegative(saved.editorScroll);body.scrollTop=nonnegative(saved.scroll);
  if(Object.hasOwn(results,saved.executed))executed=saved.executed;
 }
 q('#commandResult').textContent=executed?results[executed]:initialResult;
 const d=document.createElement('dialog');d.setAttribute('aria-label','本地命令面板');d.style.cssText='width:min(82vw,480px);padding:22px;background:#f5f4ed;border:1px solid #9aac97;border-radius:10px';
 d.innerHTML='<h2>本地命令</h2><label>搜索命令<input id="commandQuery" autocomplete="off"></label><p role="status" id="commandCount"></p><div id="commandItems"></div><button id="commandClose">关闭并返回</button>';document.body.append(d);
 const x=k=>d.querySelector(k),cleanups=[];
 function bind(node,type,fn){node.addEventListener(type,fn);cleanups.push(()=>node.removeEventListener(type,fn))}
 function finish(){if(disposed||!d.open)return;d.close();if(previous?.isConnected)previous.focus();else if(editor.isConnected)editor.focus();previous=null}
 function run(id){if(disposed||!d.open)return;const result=chooseCommand(id,items);if(!result.accepted){status(result.reason);return}executed=id;q('#commandResult').textContent=results[id];finish();status('执行了本地注册动作，原稿未改变。')}
 function draw(){if(disposed)return;items=searchCommands(x('#commandQuery').value);selected=Math.min(selected,Math.max(0,items.length-1));x('#commandCount').textContent=items.length+'个当前可用本地动作';x('#commandItems').replaceChildren();items.forEach((c,i)=>{const b=document.createElement('button');b.textContent=(i===selected?'→ ':'')+c.label;b.setAttribute('aria-current',String(i===selected));b.onclick=()=>run(c.id);x('#commandItems').append(b)})}
 function open(){if(disposed||d.open||!canOpenDialog(d,document.querySelectorAll('dialog[open]')))return;previous=document.activeElement;x('#commandQuery').value='';selected=0;draw();d.showModal();x('#commandQuery').focus()}
 bind(x('#commandQuery'),'input',()=>{selected=0;draw()});
 bind(x('#commandQuery'),'keydown',e=>{if(disposed||e.defaultPrevented)return;if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();if(items.length)selected=(selected+(e.key==='ArrowDown'?1:-1)+items.length)%items.length;draw()}if(e.key==='Enter'){e.preventDefault();if(items[selected])run(items[selected].id)}});
 bind(x('#commandClose'),'click',finish);bind(d,'cancel',e=>{e.preventDefault();finish()});
 bind(window,'keydown',e=>{if(disposed||e.defaultPrevented)return;if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){if(!d.open&&!canOpenDialog(d,document.querySelectorAll('dialog[open]')))return;e.preventDefault();open()}});
 button('打开命令面板',open,true);
 onDispose(()=>{if(disposed)return;
  try{session?.write('commands',{version:1,draft:editor.value,start:editor.selectionStart,end:editor.selectionEnd,direction:editor.selectionDirection,editorScroll:editor.scrollTop,scroll:body.scrollTop,executed})}catch{}
  disposed=true;cleanups.forEach(fn=>fn());if(d.open)d.close();d.remove();previous=null;
 });
}

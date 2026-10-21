import {relationView} from './relations.mjs';

export const relationsStudy=['relations','31','SOURCE-BOUND PATHS','沿关系看依据','选择有依据的提及或转载关系。缺证据候选只提示缺口，不画实线或虚线；图和列表同源，关闭依据回原关系。','CTH-04屏合同§Intelligent UI（当前142行）缺证据不画边；BMP-04传播路径。400ms强调只定位有证样例边，不生成因果或业务事实。',[]];

export function createRelations({stage,button,status,reduce,onDispose,listen}) {
 const data={nodes:[{id:'a',label:'原文 A',x:55,y:90},{id:'b',label:'转载 B',x:245,y:45},{id:'c',label:'观察 C',x:245,y:145}],edges:[{id:'ab',from:'a',to:'b',kind:'转载',source:'样例引用行A→B',review:'人工样例，不是真实来源'},{id:'ac',from:'a',to:'c',kind:'推断',source:null,review:'没有来源支持；未核实'}]};
 let state={selected:null,kind:'all',permission:true},animation=null,opener=null,disposed=false;
 const localCleanups=[];
 stage.innerHTML='<section class="lab-scroll"><label>关系类型<select id="relationFilter"><option value="all">全部</option><option>转载</option><option>提及</option><option>推断</option></select></label><svg id="relationGraph" viewBox="0 0 330 200" role="img" aria-label="样例关系图；下方列表提供完整等价操作"></svg><div id="relationList" class="actions"></div><p id="relationDetail" role="status"></p></section>';
 const q=x=>stage.querySelector(x),svg=q('#relationGraph'),NS='http://www.w3.org/2000/svg',dialog=document.createElement('dialog');
 dialog.className='context-dialog';dialog.setAttribute('aria-label','关系依据');
 dialog.innerHTML='<h2>关系依据</h2><p id="relationSource"></p><button id="relationReturn">返回原关系</button>';document.body.append(dialog);

 function bind(target,event,handler) {
  if(listen)listen(target,event,handler);else target.addEventListener(event,handler);
  localCleanups.push(()=>target.removeEventListener(event,handler));
 }
 function cancelAnimation() {
  const current=animation;animation=null;
  if(current){current.onfinish=current.oncancel=null;current.cancel()}
 }
 function emphasize() {
  cancelAnimation();
  if(disposed||reduce()||document.hidden||typeof svg.animate!=='function')return;
  // Presentation failure must leave the selected relation and its evidence usable.
  try {
   const current=svg.animate([{opacity:.45},{opacity:1}],{duration:400,easing:'ease-out'});
   animation=current;
   current.onfinish=current.oncancel=()=>{
    if(animation!==current)return;
    animation=null;current.onfinish=current.oncancel=null;
   };
  } catch {cancelAnimation()}
 }
 function el(tag,attrs,text) {
  const n=document.createElementNS(NS,tag);
  for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);
  if(text)n.textContent=text;return n;
 }
 function draw() {
  if(disposed)return;
  cancelAnimation();
  const v=relationView(data,state);svg.replaceChildren();q('#relationList').replaceChildren();
  for(const edge of v.edges) {
   const a=v.nodes.find(n=>n.id===edge.from),b=v.nodes.find(n=>n.id===edge.to);
   const line=el('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:edge.id===v.selected?'#326d66':'#98a49a','stroke-width':edge.id===v.selected?5:2,'stroke-dasharray':edge.kind==='推断'?'5 5':'none'});
   svg.append(line);
   const btn=document.createElement('button');btn.textContent=`${a.label} → ${b.label} · ${edge.kind}`;btn.dataset.edge=edge.id;btn.setAttribute('aria-pressed',String(edge.id===v.selected));
   btn.onclick=()=>{
    if(disposed||!relationView(data,state).edges.some(item=>item.id===edge.id))return;
    state.selected=edge.id;draw();q(`[data-edge="${edge.id}"]`)?.focus();emphasize();
   };
   q('#relationList').append(btn);
  }
  for(const n of v.nodes)svg.append(el('circle',{cx:n.x,cy:n.y,r:22,fill:'#eee8d7',stroke:'#697e68'}),el('text',{x:n.x,y:n.y+4,'text-anchor':'middle','font-size':10,fill:'#25342d'},n.label));
  const e=v.edges.find(e=>e.id===v.selected);
  q('#relationDetail').textContent=e?`${e.kind}：${e.review}。${e.source||'没有依据，不可作为已核事实。'}`:v.notice;status(v.notice);
 }
 q('#relationFilter').onchange=e=>{if(disposed)return;state.kind=e.target.value;state.selected=null;draw()};
 button('查看所选关系依据',()=>{
  if(disposed)return;
  const v=relationView(data,state),e=v.edges.find(e=>e.id===v.selected);
  if(!e){status('先从列表选择关系');return}
  opener=e.id;dialog.querySelector('#relationSource').textContent=e.source?e.source+'。这里只是人工示例引用，不是实采材料。':'没有来源支持；保留未核实状态。';dialog.showModal();
 },true);
 function close(){if(disposed)return;dialog.close();q(`[data-edge="${opener}"]`)?.focus()}
 dialog.querySelector('#relationReturn').onclick=close;
 bind(dialog,'cancel',e=>{e.preventDefault();close()});
 button('审核事件：撤回权限',()=>{if(disposed)return;state.permission=false;state.selected=null;if(dialog.open)dialog.close();draw()});
 bind(window,'review-motion-change',cancelAnimation);
 bind(document,'visibilitychange',()=>{if(document.hidden)cancelAnimation()});
 onDispose(()=>{
  if(disposed)return;
  disposed=true;cancelAnimation();for(const cleanup of localCleanups)cleanup();dialog.remove();
 });
 draw();
}

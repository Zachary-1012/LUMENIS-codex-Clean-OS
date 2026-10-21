import{initialStream,streamReduce,STREAM_LIMITS,validStreamSnapshot}from'./contracts.mjs';
// Local fixture transport: no real model, server checkpoint, saved-work receipt or authorization.
export function createStreamStudy({stage,status=()=>{},onDispose=()=>{},settingsRoot,session}={}){
 const doc=stage.ownerDocument||document,el=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n},root=el('section'),nodes={},rows=new Map(),handlers=[];
 const resetFingerprint=()=>JSON.stringify({s,views:capture(),visible:[...rows].map(([id,r])=>[id,r.edit.value])});
 let disposed=false,s=initialStream('local-stream-1'),round=1,paused=false,dirtyPause=false,resetIntent=null,snapshot;
 try{snapshot=session?.read('stream');if(validStreamSnapshot(snapshot?.state)){s=structuredClone(snapshot.state);round=Number.isSafeInteger(snapshot.round)?snapshot.round:1;paused=!!snapshot.paused;}}catch{}
 const bind=(n,k,f)=>{n['on'+k]=e=>{if(!disposed)return f(e||{})};handlers.push(()=>n['on'+k]=null)};
 function button(key,label,fn,parent=root){const b=el('button',label);b.type='button';b.style.minHeight='44px';parent.append(b);nodes[key]=b;bind(b,'click',fn);return b}
 root.className='lab-scroll';root.style.cssText='padding:24px;background:#fbf8ef;line-height:1.7';stage.append(root);
 root.append(el('h3','同一任务逐步呈现'),el('p','仅本地手工事件示例。没有模型请求、生产传输或正式保存；设置中可注入资料和故障。'));
 nodes.live=el('p');nodes.live.setAttribute('role','status');root.append(nodes.live);
 button('pause','暂停阅读更新',()=>{paused=true;drawStatus()});button('resume','继续阅读更新',()=>{paused=false;dirtyPause=false;draw()});button('cancel','取消本轮接收',()=>send({type:'cancel'}));
 button('restart','开始新轮…',()=>{resetIntent=resetFingerprint();nodes.confirm.hidden=false;nodes.confirmText.textContent='确认清空本轮本地展示与人工编辑，开始新轮？这不是服务端任务。';nodes.confirmReset.focus?.({preventScroll:true})});
 nodes.confirm=el('section');nodes.confirm.hidden=true;nodes.confirmText=el('p');nodes.confirm.append(nodes.confirmText);root.append(nodes.confirm);
 button('confirmReset','确认开始',()=>{if(resetIntent!==resetFingerprint()){closeReset();status('内容或状态已变化，请重新检查后开始。');return}closeReset();send({type:'restart',run:'local-stream-'+(++round)});nodes.restart.focus?.({preventScroll:true})},nodes.confirm);
 button('keep','保留本轮',()=>{closeReset();nodes.restart.focus?.({preventScroll:true})},nodes.confirm);
 nodes.list=el('section');root.append(nodes.list);const settings=el('section');settingsRoot?.append(settings);settings.append(el('p','11 人工事件夹具；不会启动真实任务'));
 button('add','加入一段人工资料',()=>{const id='block-'+(s.order.length+1);send({type:'block',id,revision:1,kind:'text',text:'人工资料 '+id+'：区分观察、判断与缺口。'})},settings);
 const first=()=>s.order[0];button('correction','更正第一段',()=>{const id=first();if(!id)return;const b=s.blocks[id];send({type:'block',id,revision:Math.max(b.revision,b.seenRevision||0,b.suggestion?.revision||0)+1,kind:'text',text:'来源更正示例：样本不足，需要保留限制。'})},settings);
 button('duplicate','重复第一段',()=>{const id=first();if(id)send({type:'block',id,revision:s.blocks[id].revision,kind:'text',text:'迟到重复'})},settings);
 button('old','旧任务迟到',()=>send({type:'block',run:'other-run',id:'late',revision:1,kind:'text',text:'不会进入'}),settings);
 button('malformed','无效结构',()=>send({type:'block',id:'bad',revision:1,kind:'executable-html',text:'不执行'}),settings);
 button('disconnect','连接断开',()=>send({type:'disconnect'}),settings);button('reconnect','本地恢复事件接收',()=>send({type:'resume'}),settings);button('complete','本地终止事件',()=>send({type:'complete'}),settings);
 button('revoke','撤回读取夹具权限',()=>send({type:'revoke'}),settings);
 function closeReset(){resetIntent=null;nodes.confirm.hidden=true}
 function drawStatus(){nodes.live.textContent=`${s.status} · ${s.order.length}个本地块 · ${s.rejected}个隔离事件 · ${paused?'阅读更新暂停'+(dirtyPause?'，有待展示变化':''):'即时展示'} · 未保存`;status(nodes.live.textContent);nodes.pause.disabled=paused||!s.allowed;nodes.resume.disabled=!paused||!s.allowed;nodes.cancel.disabled=!s.allowed||['complete','cancelled'].includes(s.status);nodes.restart.disabled=!s.allowed;nodes.confirmReset.disabled=!s.allowed;}
 function capture(){const views={};for(const[id,r]of rows)views[id]={start:r.edit.selectionStart||0,end:r.edit.selectionEnd||0,direction:r.edit.selectionDirection||'none',scroll:r.edit.scrollTop||0,raw:r.invalid?r.edit.value:null};return views}
 function makeRow(id){const box=el('section');box.style.cssText='padding:12px;margin-block:12px;background:#fffdfa;border-left:3px solid #7d9d8e';const label=el('label','人工示例分段 '+id),edit=el('textarea');edit.maxLength=STREAM_LIMITS.text;edit.dir='auto';edit.style.cssText='width:100%;min-height:90px;unicode-bidi:plaintext';label.append(edit);const correction=el('section'),message=el('p');correction.append(message);box.append(label,correction);nodes.list.append(box);const r={box,edit,correction,message};rows.set(id,r);
 const adopt=el('button','采用这次更正'),reject=el('button','保留我的内容');adopt.type=reject.type='button';correction.append(adopt,reject);r.adopt=adopt;r.reject=reject;const undo=el('button','撤销刚才采用');undo.type='button';box.append(undo);r.undo=undo;bind(undo,'click',()=>send({type:'undo-adopt',id}));
 bind(edit,'input',()=>{const previous=s;s=streamReduce(s,{type:'edit',run:s.run,id,text:edit.value});closeReset();if(s.rejected>previous.rejected){r.invalid=true;status('文本容量超限，输入仍在原框；请缩短后再继续。');return}r.invalid=false;r.correction.hidden=true;drawStatus()});
 bind(adopt,'click',()=>send({type:'adopt',id}));bind(reject,'click',()=>send({type:'reject',id}));return r;}
 function draw(){
  if(!s.allowed){for(const r of rows.values()){r.edit.value='';r.message.textContent='';r.box.remove()}rows.clear();nodes.list.replaceChildren();paused=false;dirtyPause=false;closeReset();drawStatus();return}
  for(const[id,r]of rows)if(!Object.hasOwn(s.blocks,id)){r.box.remove();rows.delete(id)}
  for(const id of s.order){const b=s.blocks[id],r=rows.get(id)||makeRow(id);if(!r.invalid&&r.edit.value!==b.text){const a=r.edit.selectionStart||0,z=r.edit.selectionEnd||0,dir=r.edit.selectionDirection||'none',scroll=r.edit.scrollTop||0;r.edit.value=b.text;r.edit.setSelectionRange?.(Math.min(a,b.text.length),Math.min(z,b.text.length),dir);r.edit.scrollTop=scroll}r.correction.hidden=r.invalid||!b.suggestion;r.message.textContent=b.suggestion?'待检查更正（版本 '+b.suggestion.revision+'）：'+b.suggestion.text:'';r.adopt.disabled=!b.suggestion;r.reject.disabled=!b.suggestion;r.undo.disabled=!b.undoAdoption||r.invalid;}
  drawStatus();
 }
 function send(event){if(disposed)return;const e={run:s.run,...event};s=streamReduce(s,e);closeReset();if(paused&&e.type==='block'&&s.allowed){dirtyPause=true;drawStatus()}else draw()}
 bind(root,'keydown',e=>{if(e.key==='Escape'&&!nodes.confirm.hidden){e.preventDefault?.();closeReset();nodes.restart.focus?.({preventScroll:true})}});
 draw();for(const[id,v]of Object.entries(snapshot?.views||{})){const r=rows.get(id);if(r&&typeof v.raw==='string'&&v.raw.length<=1000000){r.invalid=true;r.edit.value=v.raw}if(r&&Number.isInteger(v.start)&&Number.isInteger(v.end)&&v.start>=0&&v.end>=v.start&&v.end<=r.edit.value.length){r.edit.setSelectionRange?.(v.start,v.end,v.direction);r.edit.scrollTop=Number.isFinite(v.scroll)&&v.scroll>=0?v.scroll:0}}root.scrollTop=Number.isFinite(snapshot?.scroll)?snapshot.scroll:0;
 onDispose(()=>{try{session?.write('stream',{state:s,round,paused,views:capture(),scroll:root.scrollTop||0})}catch{}disposed=true;handlers.forEach(f=>f());for(const r of rows.values()){r.edit.value='';r.message.textContent=''}root.remove();settings.remove()});
 return{root,nodes,rows,send,getState:()=>structuredClone(s)};
}

import{initialVersion,versionReduce}from'./version-conflict.mjs';
export const versionStudy=['conflict','24','DRAFT / CONFLICT / ADOPT','两份修改，都留下','制造一个本地版本冲突，逐项比较并编辑合并文稿。保存、冲突、选择与取消各自可见。','完整草图§5保存失败/版本冲突：本地并发模型，仅演示交互和接线合同；不冒称服务器保存。',[]];
export function createVersion({stage,status=()=>{},onDispose=()=>{},session,settingsRoot}={}){
 const doc=stage.ownerDocument||document,nodes={},cleanup=[];let disposed=false,s=initialVersion(),previous;
 try{previous=session?.read('conflict');if(previous?.state)s=structuredClone(previous.state)}catch{}
 const el=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n},root=el('section');root.className='lab-scroll';stage.append(root);
 const bind=(n,event,fn)=>{n['on'+event]=e=>{if(!disposed)fn(e)};cleanup.push(()=>n['on'+event]=null)},action=(text,fn,parent=root)=>{const n=el('button',text);n.type='button';bind(n,'click',fn);parent.append(n);return n};
 for(const [key,label]of [['own','我的编辑'],['merge','明确采用前，自己编辑合并']]){const l=el('label',label);nodes[key]=el('textarea');nodes[key].maxLength=200000;nodes[key].dir='auto';l.append(nodes[key]);nodes[key+'Label']=l;root.append(l)}
 nodes.summary=el('p');nodes.remote=el('pre');nodes.remote.style.whiteSpace='pre-wrap';nodes.live=el('p');nodes.live.setAttribute('role','status');root.append(nodes.summary,nodes.remote,nodes.live);
 const say=text=>{nodes.live.textContent=text;status(text)};
 function draw(){if(nodes.own.value!==s.draft)nodes.own.value=s.draft;nodes.summary.textContent=`编辑基线 v${s.base.version} · 另一路 ${s.remote?'v'+s.remote.version:'不可读'} · ${s.status}`;nodes.remote.textContent=s.remote?.text??'已撤权；旧结果清除';nodes.mergeLabel.hidden=!s.proposal;if(nodes.merge.value!==(s.proposal?.text??''))nodes.merge.value=s.proposal?.text??'';say(s.status==='conflict'?'发现版本冲突；两份修改保留，请重新比较。':s.status==='denied'?'权限已撤回；本地草稿保留，不可保存或采用。':s.status==='invalid-draft'?'输入格式或长度无效；原稿保留。':s.status==='saved-local'?'本地模型产生新版本；没有服务器写入。':'本地版本实验；真正保存需接原 Owner 回执。')}
 function send(event){s=versionReduce(s,event);draw()}
 bind(nodes.own,'input',()=>send({type:'edit',text:nodes.own.value}));bind(nodes.merge,'input',()=>send({type:'merge-edit',text:nodes.merge.value}));
 action('按基线保存',()=>send({type:'save'}));action('比较并编辑合并',()=>send({type:'compare'}));action('明确采用合并稿',()=>send({type:'accept'}));action('取消合并',()=>send({type:'cancel'}));
 const fixtures=el('details');fixtures.append(el('summary','本地并发审核夹具'));(settingsRoot||root).append(fixtures);
 action('注入另一路新修改',()=>send({type:'remote',version:(s.remote?.version||0)+1,text:'另一位本地编辑：请补充依据。'}),fixtures);action('模拟撤权',()=>send({type:'revoke'}),fixtures);action('重置本地实验',()=>{s=initialVersion();draw()},fixtures);
 draw();if(previous){for(const key of ['own','merge']){const p=previous[key];if(p&&typeof nodes[key].setSelectionRange==='function')nodes[key].setSelectionRange(p.start,p.end,p.direction);if(Number.isFinite(p?.scroll))nodes[key].scrollTop=p.scroll}}
 onDispose(()=>{try{const ranges={};for(const key of ['own','merge'])ranges[key]={start:nodes[key].selectionStart,end:nodes[key].selectionEnd,direction:nodes[key].selectionDirection,scroll:nodes[key].scrollTop};session?.write('conflict',{state:s,...ranges})}catch{}disposed=true;cleanup.forEach(fn=>fn());fixtures.remove();root.remove()});return{nodes,getState:()=>structuredClone(s)};
}

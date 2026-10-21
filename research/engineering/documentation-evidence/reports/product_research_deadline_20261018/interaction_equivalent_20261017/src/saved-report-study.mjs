import{createReferenceDraftStudy}from'./reference-draft-study.mjs';
import{createManuscriptOutline}from'./manuscript-outline-study.mjs';
import {createSavedReportController,createLockedReportStorage} from './saved-report.mjs';
export const savedReportStudy=['savedreport','73','SHARED / AUTHOR REPORT','写成文稿，再放心继续','从自己的标题和 Markdown 开始。保存修订，查看历史，把人工审阅留在准确版本上。','LOCAL_REVIEW_ONLY · Backend / Permission / Evaluation：UNBOUND。12种内容语言保留原文；三语完整界面仍待接入。',[]];
const sessions=new WeakMap();
const styles=`.saved-report-paper{height:100%;overflow:auto;background:#faf7ef;color:#302e28;padding:24px clamp(16px,4vw,44px);box-sizing:border-box;line-height:1.65}.saved-report-paper *{box-sizing:border-box}.saved-report-paper h3{font:600 19px Georgia,serif;margin:25px 0 10px}.saved-report-paper label{display:block;margin:12px 0}.saved-report-paper input,.saved-report-paper textarea,.saved-report-paper select{display:block;width:100%;max-width:100%;background:#fffdf7;border:1px solid #aaa18c;border-radius:3px;padding:10px;color:inherit;font:inherit}.saved-report-paper textarea{min-height:130px;resize:vertical}.saved-report-paper .report-manuscript{min-height:280px;font:16px/1.85 Georgia,serif;tab-size:4}.saved-report-paper button{min-height:44px;padding:8px 14px;margin:5px 8px 5px 0;white-space:normal}.saved-report-paper button:focus-visible,.saved-report-paper input:focus-visible,.saved-report-paper textarea:focus-visible{outline:3px solid #346a61;outline-offset:3px}.saved-report-paper pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;border-left:2px solid #b9ac90;padding:12px 18px;background:#f3eee2}.saved-report-paper details{border-top:1px solid #cdc3af;margin-top:18px;padding-top:12px}.saved-report-paper summary{cursor:pointer;min-height:44px}.saved-report-paper .report-receipt{font-size:13px;overflow-wrap:anywhere}.saved-report-paper [hidden]{display:none!important}.saved-report-settings label{display:block;margin:10px 0}.saved-report-settings input[type=checkbox]{margin-right:8px}`;
export function createSavedReportStudy({stage,status=()=>{},onDispose=()=>{},session,settingsRoot,storage:providedStorage}={}){
 const doc=stage.ownerDocument||document,win=doc.defaultView||globalThis,nodes={},handlers=[];
 let disposed=false,controller=null,state=null,prepared=null,confirmation=null,confirmationBasis=null,opener=null,attempt=null,serial=0,uiGeneration=0;
 const cached=session&&sessions.get(session),fixture=cached?.fixture||{failNext:false,delay:0};
 let renderedVersion=null,outline=null,references=null;
 let savedRoute=null;try{savedRoute=session?.read('savedreport')}catch{}
 const el=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n};
 const root=el('section');root.className='saved-report-paper';root.setAttribute('aria-label','独立作者报告工作区');const style=el('style',styles);root.append(style);stage.append(root);
 const bind=(node,event,fn)=>{node['on'+event]=e=>{if(!disposed)return fn(e)};handlers.push(()=>node['on'+event]=null)};
 const say=text=>{if(disposed)return;nodes.live.textContent=text;status(text)};
 const act=(key,label,fn,parent=root)=>{const b=el('button',label);b.type='button';bind(b,'click',fn);parent.append(b);nodes[key]=b;return b};
 const field=(key,label,tag='input',parent=root)=>{const l=el('label',label),n=el(tag);n.dir='auto';n.style.unicodeBidi='plaintext';l.append(n);parent.append(l);nodes[key]=n;return n};
 root.append(el('p','LOCAL_REVIEW_ONLY · 真实 Backend / Permission / Evaluation：UNBOUND'),el('h3','写自己的文稿'));
 root.append(el('p','无需 AI 或来源前置。原文不会被翻译或归一化；12种内容语言可原样保存。当前界面以中文为主，完整中英韩界面仍待接入。'));
 field('title','文稿标题');field('markdown','Markdown 正文','textarea').className='report-manuscript';
 nodes.dirty=el('p');nodes.dirty.setAttribute('role','status');root.append(nodes.dirty);
 const preview=el('details');preview.append(el('summary','纯文本预览（不执行 HTML）'));nodes.preview=el('pre');nodes.preview.dir='auto';preview.append(nodes.preview);root.append(preview);
 const changes=el('details');changes.append(el('summary','与当前已保存基线比较'));nodes.diff=el('pre');nodes.diff.dir='auto';changes.append(nodes.diff);root.append(changes);nodes.outlineHost=el('div');root.append(nodes.outlineHost);nodes.referenceHost=el('div');root.append(nodes.referenceHost);
 field('reason','本次修改原因（首次保存可留空）','textarea');nodes.reason.style.minHeight='70px';
 act('save','保存本地版本',()=>save(false));act('retry','重试同次保存',()=>save(true));
 act('cancelOperation','取消等待',()=>{uiGeneration++;prepared=null;controller.cancel();say('迟到界面更新已失效；已写入的存储不会撤销，结果请重开核对。')});
 act('discard','撤销未保存编辑',()=>ask('discard','将当前稿恢复为最新已保存版本？',nodes.discard));
 act('checkpoint','保存草稿与审阅到本地 journal',()=>run(()=>controller.checkpoint(),'草稿与人工审阅已写入本地 journal 并读回；不代表新增文稿版本。'));
 act('reopen','重开本地 journal',()=>ask('reopen','选择保留当前草稿并接到已读回的 head，或替换为 journal 草稿。尚未执行读取或替换。',nodes.reopen));
 nodes.confirm=el('section');nodes.confirm.hidden=true;nodes.confirm.setAttribute('role','group');nodes.confirm.setAttribute('aria-label','确认工作稿操作');nodes.confirmText=el('p');nodes.confirm.append(nodes.confirmText);
 act('keepDraft','确认重开，保留当前草稿',()=>confirmRestore(true),nodes.confirm);
 act('replaceDraft','确认重开，替换当前草稿',()=>confirmRestore(false),nodes.confirm);
 act('confirmAction','确认采用',()=>{if(!validConfirmation())return;const action=confirmation;closeConfirm();if(action==='discard')controller.discardDraft();else if(action?.startsWith('adopt:'))controller.adoptVersion(action.slice(6));say('仅当前内存稿已改变；保存后才形成新的版本。')},nodes.confirm);
 act('cancelConfirm','取消，保留当前稿',()=>{closeConfirm();say('已取消，当前稿未替换。')},nodes.confirm);root.append(nodes.confirm);
 root.append(el('h3','查看已保存版本'));field('history','版本（查看不会覆盖编辑稿）','select');nodes.historyText=el('pre');nodes.historyText.dir='auto';root.append(nodes.historyText);nodes.receipt=el('p');nodes.receipt.className='report-receipt';root.append(nodes.receipt);
 act('adopt','把所选内容用于新修订',()=>ask(`adopt:${state.viewingVersionId}`,'将所选历史内容放入当前草稿，以最新 head 为基线；不会改写历史。',nodes.adopt));
 const review=el('details');review.append(el('summary','给所选版本留下人工审阅'));root.append(review);
 field('verdict','人工结论','select',review);for(const [v,t]of[['reviewed','已人工审阅'],['needs-work','仍需修改']]){const o=el('option',t);o.value=v;nodes.verdict.append(o)}nodes.verdict.value='reviewed';
 field('reviewNotes','人工审阅意见','textarea',review);field('unknowns','未核项，每行一项（可留空）','textarea',review);
 act('review','记录本地人工审阅',()=>{const r=controller.reviewVersion({versionId:state.viewingVersionId,verdict:nodes.verdict.value,notes:nodes.reviewNotes.value,unknowns:nodes.unknowns.value.split('\n').filter(s=>s.trim())});say(r.ok?'已记录于所选版本/hash，尚未持久保存；请保存 journal。不是产品 Evaluation，也不认证事实。':`记录未采用：${r.code}`)},review);
 nodes.reviewSummary=el('pre');review.append(nodes.reviewSummary);
 root.append(el('h3','导出所选已保存版本'),el('p','仅导出正文的 UTF-8 字节，md / txt 均保留 Markdown 原文。未保存编辑不进入文件。docx / pdf / xlsx 未接入。'));
 field('format','文件格式','select');for(const f of['md','txt']){const o=el('option',f);o.value=f;nodes.format.append(o)}nodes.format.value='md';
 act('prepare','准备导出字节',async()=>{const token=uiGeneration;const r=await controller.prepareExport({versionId:state.viewingVersionId,format:nodes.format.value});if(disposed||token!==uiGeneration)return;if(r.ok){prepared=r;render(controller.state());say(`已准备 ${r.byteLength} 字节 · ${r.filename}；尚未发出下载，磁盘落盘未验证。`)}else say(`导出未准备：${r.code}`)});
 act('download','下载已准备文件',()=>{const current=controller.state();if(!prepared||!current.permissions.read||!current.permissions.export||!current.lastExport||prepared.versionId!==current.viewingVersionId||prepared.format!==nodes.format.value||prepared.bytesSha256!==current.lastExport.bytesSha256)return;try{if(!win.Blob||!win.URL?.createObjectURL)throw Error('DOWNLOAD_UNAVAILABLE');const a=el('a');if(!('download'in a))throw Error('DOWNLOAD_UNAVAILABLE');const url=win.URL.createObjectURL(new win.Blob([prepared.bytes],{type:prepared.mime}));a.href=url;a.download=prepared.filename;root.append(a);try{a.click()}finally{a.remove();(win.setTimeout||globalThis.setTimeout)(()=>win.URL.revokeObjectURL(url),1000)}say('已向浏览器发出下载；磁盘落盘未验证。')}catch(e){say(`字节已准备，但未能发出下载：${e.message}`)}});
 nodes.exportStatus=el('p');root.append(nodes.exportStatus);nodes.live=el('p');nodes.live.setAttribute('role','status');nodes.live.setAttribute('aria-live','polite');root.append(nodes.live);
 const settings=el('section');settings.className='saved-report-settings';settings.append(el('p','仅本例审核夹具 · FIXTURE_ONLY，不是服务端 Permission。正常写作无需调参。'));
 const permissionInputs={};for(const [key,label]of[['read','允许读取'],['write','允许写入'],['export','允许导出']]){const l=el('label'),n=el('input');n.type='checkbox';n.checked=true;l.append(n,el('span',label));settings.append(l);permissionInputs[key]=n;bind(n,'change',()=>{invalidate();controller.setPermissions(Object.fromEntries(Object.entries(permissionInputs).map(([k,v])=>[k,v.checked])));say('权限夹具已更新；真实 Permission 仍未接入。')})}
 field('scope','样例工作区 key','input',settings).value='report-demo';act('switchScope','切换样例工作区',()=>{invalidate();const r=controller.switchWorkspace(nodes.scope.value);say(r.ok?'已切换样例范围；正文已清空。需要时显式重开该范围 journal。':`未切换范围：${r.code}`)},settings);
 field('delay','写入延迟毫秒（0–5000）','input',settings).value='0';nodes.delay.type='number';bind(nodes.delay,'change',()=>{fixture.delay=Math.max(0,Math.min(5000,Number(nodes.delay.value)||0))});act('failWrite','令下次写入失败',()=>{fixture.failNext=true;say('下次本地写入将模拟失败；现有存储不变。')},settings);
 if(settingsRoot)settingsRoot.append(settings);
 function invalidate(){uiGeneration++;prepared=null;attempt=null;closeConfirm();for(const key of['reason','reviewNotes','unknowns'])nodes[key].value='';nodes.live.textContent=''}
 let backing;function backingStore(){if(!backing)backing=providedStorage||createLockedReportStorage(win.localStorage,win.navigator?.locks);return backing}
 const storage={getItem:async key=>(await backingStore().getItem(key))??null,setItem:async(key,value)=>{if(fixture.delay)await new Promise(r=>(win.setTimeout||globalThis.setTimeout)(r,fixture.delay));if(fixture.failNext){fixture.failNext=false;throw Error('SIMULATED_WRITE_FAILURE')}return backingStore().setItem(key,value)},concurrencyBoundary:providedStorage?.concurrencyBoundary||(providedStorage?'SAME_ADAPTER_OBJECT_ONLY':'HOST_EXCLUSIVE_LOCK')};
 if(!providedStorage||providedStorage.withLock)storage.withLock=(key,fn)=>backingStore().withLock(key,fn);
 function render(s){if(disposed)return;state=s;const read=s.permissions.read,write=read&&s.permissions.write,selected=s.versions.find(v=>v.localId===s.viewingVersionId),base=s.versions.at(-1);if(!s.lastExport)prepared=null;
  if(renderedVersion!==s.viewingVersionId){nodes.reviewNotes.value='';nodes.unknowns.value='';renderedVersion=s.viewingVersionId;}
  for(const key of['title','markdown']){const value=read?s.draft[key]:'';if(nodes[key].value!==value)nodes[key].value=value;nodes[key].disabled=!write}
  nodes.preview.textContent=read?s.draft.markdown:'';nodes.diff.textContent=!read?'':base?`标题 · 原：${base.title}\n标题 · 现：${s.draft.title}\n\n原正文：\n${base.markdown}\n\n当前正文：\n${s.draft.markdown}`:'尚无已保存基线。';
  nodes.dirty.textContent=!read?'读取已撤销，正文隐藏。':`${s.pending?'正在处理，仍可继续编辑 · ':''}${s.draft.dirty?'当前稿有未保存修改':'当前稿与已保存基线一致'} · ${s.journalDirty?'journal 有未保存变化':'journal 无待写变化'} · ${s.persistence}${s.error?' · '+s.error:''}`;
  const signature=s.versions.map(v=>v.localId).join('|');if(nodes.history._signature!==signature){nodes.history.replaceChildren();for(const v of s.versions){const o=el('option',`v${v.version} · ${v.title}`);o.value=v.localId;nodes.history.append(o)}nodes.history._signature=signature}nodes.history.value=s.viewingVersionId||'';nodes.history.disabled=!read||!selected;
  nodes.historyText.textContent=selected?`${selected.title}\n\n${selected.markdown}`:'';nodes.receipt.textContent=selected?`本地 v${selected.version} · ${selected.localId}\nSHA-256 ${selected.contentSha256}\n修改原因：${selected.reason||'首次保存'}\n真实产品：UNBOUND`:'';
  nodes.reviewSummary.textContent=selected?s.reviews.filter(r=>r.versionId===selected.localId).map(r=>`${r.verdict} · ${r.contentSha256}\n${r.notes}\n未核：${r.unknowns.join('；')||'未填写（不代表均已核实）'}`).join('\n\n')||'所选版本尚无人工审阅。':'';
  for(const key of['reason','reviewNotes','unknowns','verdict'])nodes[key].disabled=!write;
  for(const key of['save','retry','checkpoint'])nodes[key].disabled=!write||Boolean(s.pending);nodes.retry.disabled ||= !attempt;
  nodes.discard.disabled=!write;nodes.reopen.disabled=!read||Boolean(s.pending);nodes.adopt.disabled=!write||!selected;nodes.review.disabled=!write||!selected;nodes.prepare.disabled=!read||!s.permissions.export||!selected;nodes.download.disabled=!prepared||!read||!s.permissions.export;nodes.cancelOperation.disabled=!s.pending;
  outline?.sync();references?.sync();nodes.exportStatus.textContent=prepared?`已准备 ${prepared.format} · ${prepared.byteLength} 字节 · SHA-256 ${prepared.bytesSha256} · 落盘 NOT_VERIFIED`:'';
 }
 controller=cached?.controller||createSavedReportController({storage});
 const unsubscribe=controller.subscribe(render);render(controller.state());
 outline=createManuscriptOutline({parent:nodes.outlineHost,status:say,getSnapshot:()=>({markdown:nodes.markdown.value,selectionStart:nodes.markdown.selectionStart,scope:state.workspaceKey,read:state.permissions.read,allowed:state.permissions.read&&state.permissions.write}),applyDraft:(markdown,start)=>{attempt=null;if(confirmation)closeConfirm(false);const r=controller.edit({markdown,selection:{start,end:start,direction:'none',unit:'utf16'}});if(!r.ok)throw Error(r.code);restoreSelection()}});
 references=createReferenceDraftStudy({parent:nodes.referenceHost,settingsRoot,session,status:say,getStorage:()=>backingStore(),getContext:()=>({scope:state.workspaceKey,read:state.permissions.read,write:state.permissions.write})});
 if(session)sessions.set(session,{controller,fixture});
 for(const [k,n]of Object.entries(permissionInputs))n.checked=state.permissions[k];nodes.scope.value=state.workspaceKey;nodes.delay.value=String(fixture.delay);
 function capture(){if(!state.permissions.read||!state.permissions.write)return;controller.edit({title:nodes.title.value,markdown:nodes.markdown.value,selection:{start:nodes.markdown.selectionStart||0,end:nodes.markdown.selectionEnd||0,direction:nodes.markdown.selectionDirection||'none',unit:'utf16'},scroll:root.scrollTop||0})}
 for(const key of['title','markdown'])bind(nodes[key],'input',()=>{attempt=null;if(confirmation)closeConfirm(false);capture()});
 bind(nodes.history,'change',()=>{prepared=null;controller.viewVersion(nodes.history.value)});bind(nodes.format,'change',()=>{uiGeneration++;prepared=null;render(controller.state())});
 bind(root,'keydown',e=>{if(e.key==='Escape'&&confirmation){e.preventDefault?.();closeConfirm();say('已取消，当前稿未替换。')}});
 function confirmationKey(){return JSON.stringify({title:nodes.title.value,markdown:nodes.markdown.value,workspace:state.workspaceKey,head:state.versions.at(-1)?.localId||null,viewing:state.viewingVersionId,permissions:state.permissions})}
 function validConfirmation(){if(!confirmation)return false;if(confirmationBasis!==confirmationKey()){closeConfirm(false);say('确认基线已改变；当前稿保留，请重新预览。');return false}return true}
 function ask(action,text,source){confirmation=action;confirmationBasis=confirmationKey();opener=source;nodes.confirm.hidden=false;nodes.confirmText.textContent=text;const reopen=action==='reopen';nodes.keepDraft.hidden=nodes.replaceDraft.hidden=!reopen;nodes.confirmAction.hidden=reopen;(reopen?nodes.keepDraft:nodes.confirmAction).focus?.({preventScroll:true})}
 function closeConfirm(restoreFocus=true){confirmation=null;confirmationBasis=null;nodes.confirm.hidden=true;if(restoreFocus)opener?.focus?.({preventScroll:true});opener=null}
 async function confirmRestore(preserveDraft){if(confirmation!=='reopen'||!validConfirmation())return;capture();closeConfirm();prepared=null;attempt=null;await run(()=>controller.restore({preserveDraft}),preserveDraft?'已重开本地 journal；保留当前草稿，尚未重新保存。':'已恢复本地 journal 草稿；这不是服务端回执。');restoreSelection()}
 async function run(action,success){const token=uiGeneration;try{const r=await action();if(!disposed&&token===uiGeneration)say(r.ok?(r.status==='no-local-journal'?'没有本地 journal；当前稿保留。':success):`操作未确认：${r.code}。当前内存稿保留；不确定写入请重开核对。`);return r}catch(e){if(!disposed&&token===uiGeneration)say(`操作未确认：${e.message}`);return {ok:false}}}
 async function save(retry){if(!retry){capture();attempt={requestId:`review_${Date.now()}_${++serial}_${Math.random().toString(36).slice(2,9)}`,reason:nodes.reason.value}}if(!attempt)return;return run(()=>controller.save(attempt),'所提交快照已保存到本机审核副本，并精确读回。之后的输入仍需另存；产品未提交。')}
 function restoreSelection(){if(!state.permissions.read)return;const s=state.draft.selection;nodes.markdown.setSelectionRange?.(s.start,s.end,s.direction);root.scrollTop=state.draft.scroll||0}
 const ready=Promise.resolve();if(cached){restoreSelection();nodes.reason.value=state.permissions.read?savedRoute?.reason||'':'';if(savedRoute?.focus&&nodes[savedRoute.focus])nodes[savedRoute.focus].focus?.({preventScroll:true});say(state.persistence==='cancelled-outcome-unknown'?'已返回会话内存稿；上次写入结果不确定，请显式重开 journal 核对。':'已返回本次会话内存稿；返回操作未执行持久保存。')}
 onDispose(()=>{if(disposed)return;capture();try{session?.write('savedreport',{reason:nodes.reason.value,focus:Object.keys(nodes).find(k=>nodes[k]===doc.activeElement)||null})}catch{}disposed=true;uiGeneration++;controller.cancel();unsubscribe();prepared=null;handlers.forEach(fn=>fn());outline?.dispose();references?.dispose();root.remove();settings.remove()});
 return {nodes,root,controller,outline,references,ready,getState:()=>controller.state()};
}

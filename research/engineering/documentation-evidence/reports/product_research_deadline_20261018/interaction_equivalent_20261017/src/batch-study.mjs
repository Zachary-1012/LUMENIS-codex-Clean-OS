import {BATCH_SAMPLE_LABEL,initialBatchReview,batchReviewReduce,visibleBatchItems,batchReviewSummary,pendingBatchJobs} from './batch-review.mjs';

export const batchStudy=['batchreview','35','BATCH ≠ A SINGLE RESULT','逐份审阅，保留每一次选择','展开批次里的原件，筛选后继续多选与记录排除理由。解析失败只重试失败项，取消不会抹掉成功结果。','SH-02 草图 lines 805–819：批次仅分组、逐原件、显式纳入/排除及理由、发布时间与真实入库时间分列。LOCAL SAMPLE 仅用虚构内联 TXT/CSV；本地载入时间不是服务端入库时间，未接产品上传、权限或保存。',[]];

export function createBatchReview({stage,button,status,onDispose}) {
  let state=initialBatchReview(),disposed=false;
  const timers=new Set();
  stage.innerHTML=`<section class="lab-scroll" aria-label="LOCAL SAMPLE 批次资料审阅" style="padding-top:44px">
    <p><strong>LOCAL SAMPLE</strong> · 四份虚构内联 TXT / CSV；两个错误刻意种入。没有真实文件、网络请求或模型调用。</p>
    <p>本页仅内存保留，离开此演示会清空。未上传、未服务端入库、未产品保存。UNKNOWN 权益 / SourceUse 不代表许可。</p>
    <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:end">
      <label style="flex:1 1 180px">搜索资料<input id="batchQuery" type="search" maxlength="120" placeholder="标题、批次或固定 ID"></label>
      <label>类型<select id="batchKind"><option value="all">全部类型</option><option value="txt">TXT</option><option value="csv">CSV</option></select></label>
      <label>范围<select id="batchInclusion"><option value="all">纳入与排除</option><option value="included">只看纳入</option><option value="excluded">只看排除</option></select></label>
      <label>解析状态<select id="batchStatus"><option value="all">全部状态</option><option value="idle">未解析</option><option value="running">解析中</option><option value="success">已解析</option><option value="failed">解析失败</option><option value="cancelled">已取消</option></select></label>
    </div>
    <p id="batchSummary" role="status" aria-live="polite"></p>
    <label>本次纳入 / 排除理由<input id="batchReason" maxlength="500" placeholder="先勾选资料；批量操作也包含已隐藏的勾选项"></label>
    <p>浏览按样例本地载入时间倒序；批次只分组。发布时间单列，未知始终保留 UNKNOWN。</p>
    <div id="batchList"></div>
  </section>`;
  const q=selector=>stage.querySelector(selector),scroll=q('.lab-scroll');
  const labels={idle:'未解析',running:'解析中',success:'已解析 / 基础计数就绪',failed:'解析失败',cancelled:'已取消'};
  const element=(tag,text,attrs={})=>{const node=document.createElement(tag);if(text!==null)node.textContent=text;for(const [key,value] of Object.entries(attrs))node.setAttribute(key,String(value));return node};
  const localButton=(text,action,key)=>{const b=element('button',text,{type:'button','data-batch-focus':key});b.style.minHeight='48px';b.onclick=action;return b};
  const focusKey=()=>document.activeElement?.getAttribute('data-batch-focus');
  function send(event,{draw=true}={}) {if(disposed)return;state=batchReviewReduce(state,event);if(draw)render();else status(state.notice)}

  function card(item) {
    const card=element('article',null,{'aria-label':item.name,'data-material-id':item.id});
    Object.assign(card.style,{padding:'16px',margin:'10px 0',border:'1px solid var(--line)',background:'#fffdf8',overflowWrap:'anywhere'});
    const choose=element('label',null);Object.assign(choose.style,{minHeight:'48px',display:'flex',gap:'10px',alignItems:'center'});
    const checkbox=element('input',null,{type:'checkbox','data-batch-focus':`select-${item.id}`,'aria-label':`勾选 ${item.name}`});checkbox.checked=state.selectedIds.includes(item.id);
    checkbox.onchange=()=>send({type:'select',id:item.id,selected:checkbox.checked});choose.append(checkbox,element('strong',item.name));card.append(choose);
    card.append(element('p',`${item.included?'纳入':'已排除'} · ${item.kind.toUpperCase()} · ${labels[item.status]} · 尝试 ${item.attempts} 次`));
    const metadata=element('dl',null);Object.assign(metadata.style,{display:'grid',gridTemplateColumns:'minmax(92px, .65fr) minmax(0, 1fr)',gap:'5px 10px',fontSize:'12px'});
    for(const [label,value] of [['固定资料 ID',item.id],['原发布时间',item.publishedAt??'UNKNOWN'],['样例本地载入时间',item.localIntakeAt],['服务端真实入库时间','UNKNOWN · 未连接'],['权益 / SourceUse',`${item.rights} / ${item.sourceUse}`]]){metadata.append(element('dt',label));const dd=element('dd',value);dd.style.margin='0';metadata.append(dd)}card.append(metadata);
    if(item.decision)card.append(element('p',`${item.decision.action==='exclude'?'排除':'纳入'}理由：${item.decision.reason}`));
    if(item.seededError)card.append(element('p',`审核错误夹具：${item.seededError}`));
    const open=state.expandedOriginalIds.includes(item.id),original=localButton(open?'收起这份原件':'展开这份原件',()=>send({type:'toggle-original',id:item.id}),`original-${item.id}`);
    original.setAttribute('aria-expanded',String(open));original.setAttribute('aria-controls',`batch-original-${item.id}`);card.append(original);
    if(open){const source=element('section',null,{id:`batch-original-${item.id}`,'aria-label':`${item.name} 不可变原件`});source.append(element('p','不可变内联原文 · 修改解析副本不会覆盖这里。'));const pre=element('pre',item.originalText||'（空字符串）');pre.style.overflowWrap='anywhere';pre.style.borderLeft='2px solid var(--green)';pre.style.paddingLeft='10px';source.append(pre);card.append(source)}
    if(item.result){const result=element('section',null,{'aria-label':`${item.name} 独立基础分析`});result.style.borderTop='1px solid var(--line)';result.style.marginTop='14px';result.append(element('h3','基础计数 · 关联 '+item.id));const r=item.result;result.append(element('p',`${BATCH_SAMPLE_LABEL} · 解析副本 v${r.inputRevision} · ${r.characters} 字符 / ${r.lines} 行 / ${r.nonEmptyLines} 非空行`));if(item.kind==='csv')result.append(element('p',`${r.rows} 条数据记录 · ${r.columns} 列 · ${r.duplicateRows} 条重复记录 · ${r.missingCells} 个空单元格（保留为空，不补零）`));result.append(element('p','仅确定性字符串统计；不构成业务结论，也不表示产品导入完成。'));card.append(result)}
    if(item.error)card.append(element('p',`${item.error.code}：${item.error.message}`,{role:'status'}));
    if(['failed','cancelled'].includes(item.status)){
      const edit=element('label','解析副本（可修正后重新运行）'),input=element('textarea',null,{'data-batch-focus':`parser-${item.id}`,'aria-label':`${item.name} 解析副本`,maxlength:1000000});input.value=item.parserText;input.oninput=()=>send({type:'edit-parser',id:item.id,text:input.value},{draw:false});edit.append(input);card.append(edit);
      if(item.correctedText!==null)card.append(localButton('填入明确的修复样例',()=>send({type:'edit-parser',id:item.id,text:item.correctedText}),`fix-${item.id}`));
      card.append(element('p','填入或手改副本只改输入；只有再次解析才会产生成功结果。'));
    }
    const notes=element('label','人工核对笔记（筛选、排除与重试均保留）'),note=element('textarea',null,{'aria-label':`${item.name} 人工核对笔记`,'data-batch-focus':`note-${item.id}`,maxlength:2000});note.value=item.note;note.oninput=()=>send({type:'note',id:item.id,text:note.value},{draw:false});notes.append(note);card.append(notes);
    return card;
  }

  function render() {
    const focus=focusKey(),active=document.activeElement,selection=Number.isInteger(active?.selectionStart)&&Number.isInteger(active?.selectionEnd)?{start:active.selectionStart,end:active.selectionEnd}:null,top=scroll.scrollTop;
    const list=q('#batchList');list.replaceChildren();const visible=visibleBatchItems(state),summary=batchReviewSummary(state);
    q('#batchSummary').textContent=`${summary.visible}/${summary.total} 份可见；勾选 ${summary.selected} 份（筛选隐藏 ${summary.hiddenSelected} 份）。纳入 ${summary.included} / 排除 ${summary.excluded}；成功 ${summary.success} / 失败 ${summary.failed} / 取消 ${summary.cancelled} / 正在解析 ${summary.running}。`;
    if(!visible.length)list.append(element('p','没有匹配资料。清除搜索或调整筛选即可找回；勾选与笔记仍在。'));
    const batches=[...new Set(visible.map(item=>item.batchId))];
    for(const batchId of batches){const items=visible.filter(item=>item.batchId===batchId),section=element('section',null,{'aria-label':items[0].batchLabel}),expanded=state.expandedBatches.includes(batchId);const toggle=localButton(`${expanded?'收起':'展开'} ${items[0].batchLabel} · 本筛选 ${items.length} 份`,()=>send({type:'toggle-batch',id:batchId}),`batch-${batchId}`);toggle.setAttribute('aria-expanded',String(expanded));toggle.setAttribute('aria-controls',`batch-group-${batchId}`);section.append(toggle);const group=element('div',null,{id:`batch-group-${batchId}`});group.hidden=!expanded;if(expanded)for(const item of items)group.append(card(item));section.append(group);list.append(section)}
    if(focus){const target=[...stage.querySelectorAll('[data-batch-focus]')].find(node=>node.getAttribute('data-batch-focus')===focus);target?.focus({preventScroll:true});if(selection&&target?.setSelectionRange)target.setSelectionRange(selection.start,selection.end)}
    scroll.scrollTop=top;status(state.notice);
  }

  function start(mode) {
    if(disposed)return;
    const generation=state.generation;send({type:'start',mode});
    if(state.generation===generation)return;
    for(const [index,job] of pendingBatchJobs(state).entries()){
      // Fixed local scheduling makes partial completion/cancellation reviewable. The reducer
      // actually parses captured strings when each callback arrives; no simulated results.
      const timer=setTimeout(()=>{timers.delete(timer);if(!disposed)send({type:'settle-item',...job})},0);timers.add(timer);
    }
  }
  q('#batchQuery').oninput=e=>send({type:'filter',key:'query',value:e.target.value});
  for(const [id,key] of [['#batchKind','kind'],['#batchInclusion','inclusion'],['#batchStatus','status']])q(id).onchange=e=>send({type:'filter',key,value:e.target.value});
  q('#batchReason').oninput=e=>send({type:'reason',text:e.target.value},{draw:false});
  button('勾选当前筛选全部',()=>send({type:'select-visible'}));
  button('清空全部勾选',()=>send({type:'clear-selection'}));
  button('按理由排除勾选项',()=>send({type:'set-included',included:false}));
  button('按理由纳入勾选项',()=>send({type:'set-included',included:true}));
  button('撤销上次纳入 / 排除',()=>send({type:'undo-inclusion'}));
  button('解析纳入的未处理项',()=>start('initial'),true);
  button('仅重试纳入的失败项',()=>start('retry-failed'));
  button('继续纳入的取消项',()=>start('resume-cancelled'));
  button('取消本轮解析',()=>send({type:'cancel'}));
  onDispose(()=>{state=batchReviewReduce(state,{type:'cancel'});disposed=true;for(const timer of timers)clearTimeout(timer);timers.clear()});
  render();
  return {getState:()=>structuredClone(state)};
}

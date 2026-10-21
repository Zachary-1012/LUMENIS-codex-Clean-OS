/** Isolated SH-02 interaction contract. No files, network, storage or product writes. */
export const BATCH_SAMPLE_LABEL = 'LOCAL SAMPLE';
export const batchFixtures = Object.freeze([
  Object.freeze({id:'sample-notes',batchId:'batch-a',batchLabel:'批次 A · 观察练习',name:'虚构观察.txt',kind:'txt',publishedAt:null,localIntakeAt:'2026-10-14T10:00:04Z',text:'LOCAL SAMPLE\n纸桥模型有三个入口。\n观察记录只用于交互审核。'}),
  Object.freeze({id:'sample-counts',batchId:'batch-a',batchLabel:'批次 A · 观察练习',name:'虚构计数.csv',kind:'csv',publishedAt:'2026-10-12',localIntakeAt:'2026-10-14T10:00:03Z',text:'位置,计数\n入口甲,3\n入口乙,\n入口甲,3'}),
  Object.freeze({id:'sample-broken-csv',batchId:'batch-b',batchLabel:'批次 B · 错误与恢复练习',name:'种入错误-引号.csv',kind:'csv',publishedAt:null,localIntakeAt:'2026-10-14T09:00:02Z',text:'名称,说明\n纸桥,"未闭合的引号',seededError:'刻意种入：CSV 引号未闭合。',correctedText:'名称,说明\n纸桥,"已闭合的引号"\n纸塔,补充样例'}),
  Object.freeze({id:'sample-empty-txt',batchId:'batch-b',batchLabel:'批次 B · 错误与恢复练习',name:'种入错误-空白.txt',kind:'txt',publishedAt:null,localIntakeAt:'2026-10-14T09:00:01Z',text:' \n\n',seededError:'刻意种入：TXT 只有空白，没有可分析正文。',correctedText:'LOCAL SAMPLE\n已补入两行虚构正文。'})
]);

const copy = value => structuredClone(value);
const parseError = (code,message,row=null) => ({ok:false,error:{code,message,row},analysis:null});

/** Small strict CSV parser: quoted commas/newlines and escaped quotes are supported. */
function csvRows(text) {
  const rows=[]; let row=[],field='',quoted=false,closed=false,line=1;
  for(let i=0;i<text.length;i++) {
    const c=text[i];
    if(quoted) {
      if(c==='"') {if(text[i+1]==='"'){field+='"';i++}else{quoted=false;closed=true}}
      else {field+=c;if(c==='\n')line++}
      continue;
    }
    if(c==='"') {
      if(field||closed)return parseError('CSV_QUOTE','引号只能出现在字段开头。',line);
      quoted=true;continue;
    }
    if(c===','){row.push(field);field='';closed=false;continue}
    if(c==='\n'||c==='\r') {
      if(c==='\r'&&text[i+1]==='\n')i++;
      row.push(field);rows.push(row);row=[];field='';closed=false;line++;continue;
    }
    if(closed)return parseError('CSV_AFTER_QUOTE','闭合引号之后应是逗号或换行。',line);
    field+=c;
  }
  if(quoted)return parseError('CSV_UNCLOSED_QUOTE','CSV 引号未闭合；请修正解析副本再重试。',line);
  if(field||row.length||closed) {row.push(field);rows.push(row)}
  return {ok:true,rows};
}

/** Analysis is computed from the actual supplied string, never a supplied success flag. */
export function parseBatchText(text,kind) {
  if(typeof text!=='string')return parseError('INVALID_TEXT','解析输入必须是文字。');
  if(text.length>1000000)return parseError('TEXT_LIMIT','本地样例上限为 1,000,000 个 UTF-16 单元。');
  if(!['txt','csv'].includes(kind))return parseError('UNSUPPORTED_KIND','这里只支持内联 TXT / CSV 样例。');
  if(!text.trim())return parseError('EMPTY_TEXT','没有可分析正文；请补入解析副本再重试。');
  const lines=text.split(/\r\n|\n|\r/);
  const analysis={characters:[...text].length,lines:lines.length,nonEmptyLines:lines.filter(x=>x.trim()).length,rows:null,columns:null,headers:[],duplicateRows:null,missingCells:null};
  if(kind==='txt')return {ok:true,error:null,analysis};
  const parsed=csvRows(text.replace(/^\uFEFF/,''));
  if(!parsed.ok)return parsed;
  const [header,...data]=parsed.rows;
  if(!header?.length||header.some(x=>!x.trim()))return parseError('CSV_HEADER','CSV 表头不能为空。',1);
  if(new Set(header.map(x=>x.trim())).size!==header.length)return parseError('CSV_DUPLICATE_HEADER','CSV 表头重复，无法唯一识别字段。',1);
  const bad=data.findIndex(row=>row.length!==header.length);
  if(bad!==-1)return parseError('CSV_WIDTH',`第 ${bad+2} 条 CSV 记录有 ${data[bad].length} 列，应为 ${header.length} 列。`,bad+2);
  const seen=new Set();let duplicateRows=0,missingCells=0;
  for(const row of data){const key=JSON.stringify(row);if(seen.has(key))duplicateRows++;seen.add(key);missingCells+=row.filter(x=>!x.trim()).length}
  return {ok:true,error:null,analysis:{...analysis,rows:data.length,columns:header.length,headers:header,duplicateRows,missingCells}};
}

export function initialBatchReview(fixtures=batchFixtures) {
  const ids=new Set();
  const items=fixtures.map(f=>{
    if(!f.id||ids.has(f.id)||!f.batchId||typeof f.text!=='string'||!Number.isFinite(Date.parse(f.localIntakeAt)))throw Error('Invalid or duplicate batch fixture');
    ids.add(f.id);
    return [f.id,{id:f.id,batchId:f.batchId,batchLabel:f.batchLabel||f.batchId,name:f.name,kind:f.kind,
      publishedAt:f.publishedAt??null,localIntakeAt:f.localIntakeAt,timeAuthority:'LOCAL_FIXTURE',rights:'UNKNOWN',sourceUse:'UNKNOWN',
      originalText:f.text,parserText:f.text,inputRevision:1,note:'',included:true,decision:null,status:'idle',attempts:0,result:null,error:null,activeInput:null,
      seededError:f.seededError||null,correctedText:f.correctedText??null}];
  });
  return {schema:'batch-review/1',label:BATCH_SAMPLE_LABEL,uploadStatus:'NOT_PERFORMED',serverImportStatus:'NOT_CONNECTED',modelStatus:'NOT_CALLED',saveStatus:'MEMORY_ONLY',
    items:Object.fromEntries(items),order:items.map(([id])=>id).sort((a,b)=>Date.parse(items.find(([id])=>id===b)[1].localIntakeAt)-Date.parse(items.find(([id])=>id===a)[1].localIntakeAt)),
    selectedIds:[],filters:{query:'',kind:'all',inclusion:'all',status:'all'},expandedBatches:[...new Set(items.map(([,i])=>i.batchId))],expandedOriginalIds:[],
    reasonDraft:'',history:[],generation:0,run:{token:null,phase:'idle',mode:null,targetIds:[]},rejectedCallbacks:0,notice:'LOCAL SAMPLE · 先选择资料或直接解析纳入项；两个错误是刻意种入的测试。'};
}

export function visibleBatchItems(s) {
  const query=s.filters.query.trim().toLocaleLowerCase();
  return s.order.map(id=>s.items[id]).filter(item=>
    (!query||`${item.name} ${item.batchLabel} ${item.id}`.toLocaleLowerCase().includes(query))&&
    (s.filters.kind==='all'||item.kind===s.filters.kind)&&
    (s.filters.inclusion==='all'||(s.filters.inclusion==='included')===item.included)&&
    (s.filters.status==='all'||item.status===s.filters.status));
}

export function batchReviewSummary(s) {
  const items=s.order.map(id=>s.items[id]),visible=new Set(visibleBatchItems(s).map(i=>i.id));
  const counts=Object.fromEntries(['idle','running','success','failed','cancelled'].map(k=>[k,items.filter(i=>i.status===k).length]));
  return {...counts,total:items.length,included:items.filter(i=>i.included).length,excluded:items.filter(i=>!i.included).length,selected:s.selectedIds.length,hiddenSelected:s.selectedIds.filter(id=>!visible.has(id)).length,visible:visible.size};
}

export function pendingBatchJobs(s) {
  if(s.run.phase!=='running')return [];
  return s.run.targetIds.filter(id=>s.items[id].status==='running').map(id=>({id,token:s.run.token}));
}

function finishRun(s) {
  if(s.run.phase==='running'&&!s.run.targetIds.some(id=>s.items[id].status==='running')) {
    s.run.phase='settled';s.run.token=null;
    const failed=s.run.targetIds.filter(id=>s.items[id].status==='failed').length;
    const cancelled=s.run.targetIds.filter(id=>s.items[id].status==='cancelled').length;
    s.notice=`本轮本地解析结束：${s.run.targetIds.length-failed-cancelled} 份成功，${failed} 份失败，${cancelled} 份取消。成功项保留；没有上传或服务端入库。`;
  }
}

export function batchReviewReduce(state,event) {
  const s=copy(state),item=s.items[event.id];
  switch(event.type) {
    case 'filter':
      if(event.key==='query')s.filters.query=String(event.value).slice(0,120);
      if(event.key==='kind'&&['all','txt','csv'].includes(event.value))s.filters.kind=event.value;
      if(event.key==='inclusion'&&['all','included','excluded'].includes(event.value))s.filters.inclusion=event.value;
      if(event.key==='status'&&['all','idle','running','success','failed','cancelled'].includes(event.value))s.filters.status=event.value;
      s.notice='已更新浏览筛选；隐藏资料的勾选、笔记与纳入状态仍保留。';break;
    case 'select':
      if(item){const chosen=event.selected??!s.selectedIds.includes(item.id);s.selectedIds=chosen?[...new Set([...s.selectedIds,item.id])]:s.selectedIds.filter(id=>id!==item.id)}break;
    case 'select-visible':s.selectedIds=[...new Set([...s.selectedIds,...visibleBatchItems(s).map(i=>i.id)])];break;
    case 'clear-selection':s.selectedIds=[];break;
    case 'note':if(item){item.note=String(event.text).slice(0,2000);s.notice='人工核对笔记已保留在当前页内存；筛选、排除和重试不会清空。'}break;
    case 'reason':s.reasonDraft=String(event.text).slice(0,500);break;
    case 'toggle-batch':
      if(s.order.some(id=>s.items[id].batchId===event.id))s.expandedBatches=s.expandedBatches.includes(event.id)?s.expandedBatches.filter(id=>id!==event.id):[...s.expandedBatches,event.id];break;
    case 'toggle-original':if(item)s.expandedOriginalIds=s.expandedOriginalIds.includes(item.id)?s.expandedOriginalIds.filter(id=>id!==item.id):[...s.expandedOriginalIds,item.id];break;
    case 'set-included': {
      if(typeof event.included!=='boolean')break;
      const reason=String(event.reason??s.reasonDraft).trim().slice(0,500);
      if(!s.selectedIds.length){s.notice='先勾选一份或多份资料。';break}
      if(!reason){s.notice='请填写这次纳入或排除的明确理由；不要求通用用途表单。';break}
      const affected=s.selectedIds.filter(id=>s.items[id].included!==event.included);
      if(!affected.length){s.notice='所选资料已是该状态；没有重复更改。';break}
      s.history.push(affected.map(id=>({id,included:s.items[id].included,decision:copy(s.items[id].decision)})));
      for(const id of affected){const i=s.items[id];i.included=event.included;i.decision={action:event.included?'include':'exclude',reason};if(!i.included&&i.status==='running'){i.status='cancelled';i.activeInput=null}}
      finishRun(s);
      s.notice=`已${event.included?'纳入':'排除'} ${affected.length} 份（含筛选隐藏的勾选项）；原文、笔记与已有结果保留。`;break;
    }
    case 'undo-inclusion': {
      const previous=s.history.pop();if(!previous){s.notice='没有可撤销的纳入/排除操作。';break}
      for(const old of previous){s.items[old.id].included=old.included;s.items[old.id].decision=old.decision}
      s.notice='已撤销上次纳入/排除；之后写的笔记与解析结果保留，取消的任务不会自动重启。';break;
    }
    case 'edit-parser':
      if(item&&['failed','cancelled'].includes(item.status)){
        const text=String(event.text);if(text.length>1000000){s.notice='解析副本超过本地样例大小限制。';break}
        if(text!==item.parserText){item.parserText=text;item.inputRevision++}
        s.notice='解析副本已更新；原文与原发布时间不变。需要实际重试才能得到新结果。';
      }break;
    case 'start': {
      if(s.run.phase==='running'){s.notice='这一轮仍在解析；可取消，不能重复启动。';break}
      const modes={initial:'idle','retry-failed':'failed','resume-cancelled':'cancelled'},targetStatus=modes[event.mode||'initial'];
      if(!targetStatus)break;
      const targets=s.order.filter(id=>s.items[id].included&&s.items[id].status===targetStatus);
      if(!targets.length){s.notice='没有符合本动作的纳入项；成功结果不重复解析。';break}
      const token=++s.generation;s.run={token,phase:'running',mode:event.mode||'initial',targetIds:targets};
      for(const id of targets){const i=s.items[id];i.status='running';i.attempts++;i.error=null;i.activeInput={text:i.parserText,revision:i.inputRevision,token}}
      s.notice=`正在逐份解析 ${targets.length} 份本地样例；可随时取消。`;break;
    }
    case 'settle-item': {
      if(!item||s.run.phase!=='running'||event.token!==s.run.token||item.status!=='running'||item.activeInput?.token!==event.token||!item.included){s.rejectedCallbacks++;break}
      const input=item.activeInput,result=parseBatchText(input.text,item.kind);
      item.status=result.ok?'success':'failed';item.error=result.error;
      item.result=result.ok?{...result.analysis,inputRevision:input.revision,label:BATCH_SAMPLE_LABEL}:null;
      item.activeInput=null;s.notice=`${item.name}：${result.ok?'已完成真实字符串计数':result.error.message}`;finishRun(s);break;
    }
    case 'cancel':
      if(s.run.phase==='running'){
        for(const id of s.run.targetIds){const i=s.items[id];if(i.status==='running'){i.status='cancelled';i.activeInput=null}}
        s.generation++;s.run.token=null;s.run.phase='cancelled';s.notice='已取消未完成项；成功结果与笔记保留，旧 token 的迟到回调会被拒绝。';
      }break;
  }
  return s;
}

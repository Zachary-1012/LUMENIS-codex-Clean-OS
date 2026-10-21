/** BMP-04 independent review fixture. No network, attribution, or product mutations. */
export const PROPAGATION_SAMPLE_LABEL = '人工传播测试夹具 · 非实采品牌数据';
export const PROPAGATION_STAGES = Object.freeze([
  {id:'channel',label:'渠道'},{id:'content',label:'内容'},{id:'exposure',label:'曝光'},{id:'response',label:'响应'}
]);
export const PROPAGATION_RELATIONS = Object.freeze({collection:'收录关系',native_statistic:'来源统计对应',co_window:'同窗记录，非转化'});
const copy = value => structuredClone(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const windowA = {start:'2026-10-01',end:'2026-10-07',timezone:'UTC'};
const windowB = {start:'2026-09-24',end:'2026-09-30',timezone:'UTC'};
const scope = {domain:'BMP',kind:'FOCUS',brandFocusId:'fixture-brand-01',subjectId:'fixture-subject-01',marketId:'fixture-market-01',label:'测试品牌 A / 样例市场',canonical:true,lineageVerified:true,readAllowed:true,permissionMode:'FIXTURE_ONLY'};
const noDenominator = {kind:'not-required',definition:'原生计数，不适用分母'};
function metric(value,unit,key,definition,window,sourceId,stage,denominator=noDenominator) {
  return {state:'observed',value,unit,key,definition,window:copy(window),denominator:copy(denominator),source:{id:sourceId,version:1,trace:`${sourceId}/${stage}/v1`}};
}
function channel(id,label,window,values) {
  const sourceId=`fixture-${id}`;
  const denominator={kind:'observed',value:values.exposure,unit:values.exposureUnit||'次',key:values.exposureUnit==='人'?'unique-viewer':'impressions',definition:values.exposureUnit==='人'?'来源内去重查看人数':'来源记录的展示次数',window:copy(window)};
  const stages={
    channel:metric(1,'个','channel-count','本行已核对的测试渠道数量',window,sourceId,'channel'),
    content:metric(values.content,'篇','collected-content','本窗口已收录且匹配测试品牌的内容数量',window,sourceId,'content'),
    exposure:values.exposure===null?{state:'not-collected',reason:'夹具未提供曝光记录；不补零',unit:'次',window:copy(window),source:{id:sourceId,version:1,trace:`${sourceId}/exposure/v1`}}:metric(values.exposure,values.exposureUnit||'次',values.exposureUnit==='人'?'unique-viewer':'impressions',values.exposureUnit==='人'?'来源内去重查看人数':'来源记录的展示次数，非去重人数',window,sourceId,'exposure'),
    response:values.responseUnit==='次'?metric(values.response,'次','interaction-count','来源记录的评论、收藏与转载总次数',window,sourceId,'response'):metric(values.response,'%',values.exposureUnit==='人'?'unique-response-rate':'impression-response-rate',values.exposureUnit==='人'?'来源给出的响应人数 / 去重查看人数':'来源给出的响应次数 / 展示次数',window,sourceId,'response',denominator)
  };
  const edge=(from,to,kind)=>({id:`${id}-${from}-${to}`,from,to,kind,state:'observed',source:{id:sourceId,version:1,trace:`${sourceId}/relation-${from}-${to}/v1`},meaning:PROPAGATION_RELATIONS[kind]});
  return {id,label,scope:copy(scope),window:copy(window),sourceId,stages,edges:[edge('channel','content','collection'),...(values.exposure!==null?[edge('content','exposure','native_statistic'),edge('exposure','response','co_window')]:[])]};
}
export function propagationFixtures() {
  const channels=[channel('owned','自营渠道 A',windowA,{content:12,exposure:2400,response:4}),channel('community','社区渠道 B',windowA,{content:8,exposure:null,response:18,responseUnit:'次'}),channel('archive','历史渠道 C',windowB,{content:6,exposure:900,exposureUnit:'人',response:5})];
  return {label:PROPAGATION_SAMPLE_LABEL,scope:copy(scope),channels,sources:Object.fromEntries(channels.map(c=>[c.sourceId,{id:c.sourceId,label:`人工记录 · ${c.label}`,version:1,kind:'artificial-fixture',withdrawn:false,note:'此处数字、时间、范围与关系均为明确编写的测试输入，不代表真实品牌、平台、来源授权或业务结论。'}]))};
}
function validWindow(w) {
  return !!w && /^\d{4}-\d{2}-\d{2}$/.test(w.start) && /^\d{4}-\d{2}-\d{2}$/.test(w.end) && text(w.timezone) && Number.isFinite(Date.parse(w.start)) && Number.isFinite(Date.parse(w.end)) && new Date(w.start).toISOString().slice(0,10)===w.start && new Date(w.end).toISOString().slice(0,10)===w.end && w.start<=w.end;
}
export function propagationWindowKey(w) {return validWindow(w)?`${w.start}/${w.end}/${w.timezone}`:null}
export function propagationWindowLabel(w) {return validWindow(w)?`${w.start} — ${w.end} (${w.timezone})`:'时间窗未核验'}
function sameWindow(a,b) {return !!propagationWindowKey(a)&&propagationWindowKey(a)===propagationWindowKey(b)}
export function validPropagationScope(s) {
  if(!s||s.domain!=='BMP'||s.permissionMode!=='FIXTURE_ONLY'||s.readAllowed!==true||s.canonical!==true||s.lineageVerified!==true)return false;
  if(s.kind==='FOCUS')return text(s.brandFocusId)&&text(s.subjectId)&&s.brandFocusId!==s.subjectId;
  return s.kind==='GLOBAL_ALL'&&s.globalGrant===true&&s.canonicalScope==='GLOBAL_ALL'&&!s.brandFocusId&&!s.subjectId;
}
function scopeMatches(row,scope) {
  if(!validPropagationScope(row)||!validPropagationScope(scope)||row.kind!==scope.kind)return false;
  return scope.kind==='GLOBAL_ALL'||(row.brandFocusId===scope.brandFocusId&&row.subjectId===scope.subjectId&&row.marketId===scope.marketId);
}
function validSource(data,ref) {
  const source=data.sources?.[ref?.id];
  return !!source && source.kind==='artificial-fixture' && !source.withdrawn && Number.isInteger(ref.version) && ref.version===source.version && text(ref.trace);
}
function validDenominator(d,w) {
  if(!d||!text(d.definition))return false;
  if(d.kind==='not-required')return true;
  return d.kind==='observed'&&Number.isFinite(d.value)&&d.value>0&&text(d.unit)&&text(d.key)&&sameWindow(d.window,w);
}
export function propagationMetric(data,channel,stageId) {
  const raw=channel?.stages?.[stageId],unknown=reason=>({stageId,state:raw?.state==='not-collected'?'not-collected':'unavailable',value:null,label:'未取得',reason,source:raw?.source?copy(raw.source):null,unit:raw?.unit||null,window:validWindow(raw?.window)?copy(raw.window):null,definition:raw?.definition||null,denominator:raw?.denominator?copy(raw.denominator):null});
  if(!validPropagationScope(data?.scope)||!scopeMatches(channel?.scope,data.scope))return unknown('当前品牌范围或读取条件未核验');
  if(!raw||typeof raw!=='object'||raw.state!=='observed')return unknown(raw?.reason||'未提供已观测指标；不能按零展示');
  if(!validSource(data,raw.source)||raw.source.id!==channel.sourceId)return unknown('来源未核验、已撤回或版本不一致');
  if(!Number.isFinite(raw.value)||raw.value<0||!text(raw.unit)||!text(raw.definition)||!text(raw.key))return unknown('指标缺少有效数值、单位或定义');
  if(!validWindow(raw.window)||!sameWindow(raw.window,channel.window))return unknown('指标时间窗与渠道不一致');
  if(!validDenominator(raw.denominator,raw.window))return unknown('分母或分母时间窗未核验，不能展示为可用指标');
  if(raw.unit==='%'&&(raw.denominator.kind!=='observed'||raw.value>100))return unknown('比例需要有效分母与合理范围');
  return {...copy(raw),stageId,label:`${raw.value.toLocaleString('zh-CN')} ${raw.unit}`,reason:null};
}
function eligibleChannels(data) {
  if(!validPropagationScope(data?.scope))return [];
  return (Array.isArray(data.channels)?data.channels:[]).filter(c=>scopeMatches(c.scope,data.scope)&&validWindow(c.window));
}
export function propagationEdges(data,channel) {
  const metrics=Object.fromEntries(PROPAGATION_STAGES.map(stage=>[stage.id,propagationMetric(data,channel,stage.id)]));
  const seen=new Set();
  return (Array.isArray(channel?.edges)?channel.edges:[]).filter(edge=>{
    const from=PROPAGATION_STAGES.findIndex(s=>s.id===edge.from),to=PROPAGATION_STAGES.findIndex(s=>s.id===edge.to);
    const valid=text(edge.id)&&!seen.has(edge.id)&&edge.state==='observed'&&Object.hasOwn(PROPAGATION_RELATIONS,edge.kind)&&text(edge.meaning)&&from>=0&&to===from+1&&metrics[edge.from]?.state==='observed'&&metrics[edge.to]?.state==='observed'&&sameWindow(metrics[edge.from].window,metrics[edge.to].window)&&validSource(data,edge.source)&&edge.source.id===channel.sourceId;
    if(valid)seen.add(edge.id);return valid;
  }).map(copy);
}
export function initialPropagation(data=propagationFixtures()) {
  const dataset=copy(data),channels=eligibleChannels(dataset),selected=channels[0]?.id??null;
  return {schema:'propagation-review/1',dataset,selected,selectedStage:'content',selectedEdge:null,filter:{window:'all',relation:'all'},comparison:{channelId:channels[1]?.id??null,stageId:'content',result:null},detail:null,draft:'',draftContext:null,analysis:[],openedRevision:null,notice:'先沿渠道查看已提供的关系，再核对原生指标；所有内容均为人工测试输入。'};
}
export function propagationView(s) {
  if(!validPropagationScope(s.dataset?.scope)||(s.dataset.scope.kind==='GLOBAL_ALL'&&s.dataset.channels?.length>0&&eligibleChannels(s.dataset).length===0))return {blocked:true,label:PROPAGATION_SAMPLE_LABEL,scopeLabel:'BMP / 读取条件已撤回或未核验',channels:[],selected:null,table:[],edges:[],detail:null,analysis:[],draft:'',windows:[],notice:'当前范围不可查看；旧路径、来源与分析已清除。'};
  const all=eligibleChannels(s.dataset),channels=all.filter(c=>s.filter.window==='all'||propagationWindowKey(c.window)===s.filter.window).map(c=>({...copy(c),metrics:PROPAGATION_STAGES.map(stage=>propagationMetric(s.dataset,c,stage.id)),edges:propagationEdges(s.dataset,c).filter(e=>s.filter.relation==='all'||e.kind===s.filter.relation)}));
  const selected=channels.find(c=>c.id===s.selected)||null;
  const table=channels.flatMap(c=>c.metrics.map(m=>({channelId:c.id,channelLabel:c.label,selected:c.id===s.selected&&m.stageId===s.selectedStage,...m})));
  return {blocked:false,label:PROPAGATION_SAMPLE_LABEL,scopeLabel:`BMP / ${s.dataset.scope.label||s.dataset.scope.kind} / 仅夹具读取许可`,channels,selected,table,edges:channels.flatMap(c=>c.edges.map(e=>({...e,channelId:c.id}))),detail:s.detail?copy(s.detail):null,analysis:copy(s.analysis),draft:s.draft,windows:[...new Map(all.map(c=>[propagationWindowKey(c.window),copy(c.window)])).values()],notice:s.notice};
}
export function comparePropagationChannels(s,leftId,rightId,stageId) {
  const candidates=eligibleChannels(s.dataset),left=candidates.find(c=>c.id===leftId),right=candidates.find(c=>c.id===rightId),reasons=[];
  if(!left||!right||leftId===rightId||!['content','exposure','response'].includes(stageId))return {allowed:false,reasons:['请选择两个已核验的不同渠道与可比较阶段'],values:[]};
  const a=propagationMetric(s.dataset,left,stageId),b=propagationMetric(s.dataset,right,stageId);
  if(a.state!=='observed'||b.state!=='observed')reasons.push('存在未取得或未核验指标');
  if(!sameWindow(a.window,b.window))reasons.push('时间窗不同');
  if(a.unit!==b.unit)reasons.push('单位不同');
  if(a.key!==b.key||a.definition!==b.definition)reasons.push('原生指标定义不同');
  if(a.denominator?.kind!==b.denominator?.kind||a.denominator?.key!==b.denominator?.key||a.denominator?.unit!==b.denominator?.unit||a.denominator?.definition!==b.denominator?.definition)reasons.push('分母口径不同或缺失');
  return {allowed:reasons.length===0,reasons,values:reasons.length?[]:[{id:left.id,label:left.label,value:a.value,unit:a.unit},{id:right.id,label:right.label,value:b.value,unit:b.unit}],window:reasons.length?null:copy(a.window),definition:reasons.length?null:a.definition};
}
export function propagationDenominatorLabel(d) {
  if(d?.kind==='not-required')return `不适用：${d.definition}`;
  if(d?.kind==='observed'&&Number.isFinite(d.value))return `${d.value.toLocaleString('zh-CN')} ${d.unit} · ${d.definition}`;
  return '未知，不能据此推算转化';
}
function makeDraft(s,c) {
  const rows=PROPAGATION_STAGES.map(stage=>{const m=propagationMetric(s.dataset,c,stage.id);return `${stage.label}：${m.state==='observed'?m.label:`未取得（${m.reason}）`}`});
  return `人工审阅草稿 · ${PROPAGATION_SAMPLE_LABEL}\n${c.label}｜${propagationWindowLabel(c.window)}\n${rows.join('\n')}\n关系仅表示来源记录的对应，不证明因果、销售或个人转化。\n人工判断：`;
}
export function propagationReduce(state,event) {
  const s=copy(state);
  if(event.type==='revoke'||event.type==='change-scope') {
    s.dataset.scope=event.type==='revoke'?{...s.dataset.scope,readAllowed:false}:copy(event.scope||{});
    // A scope transition does not re-authorize or reuse the previous payload.
    s.dataset.channels=[];s.dataset.sources={};s.selected=null;s.selectedEdge=null;s.detail=null;s.comparison={channelId:null,stageId:'content',result:null};s.draft='';s.draftContext=null;s.analysis=[];s.openedRevision=null;s.notice='当前范围改变；旧路径、来源和分析呈现已清空。';return s;
  }
  if(!validPropagationScope(s.dataset.scope))return {...s,notice:'读取条件未核验；请显式重新载入人工夹具。'};
  const view=propagationView(s),channel=view.channels.find(c=>c.id===(event.channelId||event.id||s.selected));
  switch(event.type) {
    case 'select-channel':
      if(channel){s.selected=channel.id;s.selectedEdge=null;s.detail=null;s.comparison.result=null;s.notice=`已定位 ${channel.label}；图与同源矩阵同步。`}break;
    case 'select-stage':
      if(channel&&PROPAGATION_STAGES.some(x=>x.id===event.stageId)){s.selected=channel.id;s.selectedStage=event.stageId;s.selectedEdge=null;s.comparison.result=null;s.notice='已定位同一渠道与阶段；下方矩阵保留全部单位、定义与时间窗。'}break;
    case 'select-edge': {
      const edge=channel?.edges.find(x=>x.id===event.edgeId);
      if(edge){s.selected=channel.id;s.selectedEdge=edge.id;s.selectedStage=edge.to;s.notice=`已定位 ${edge.meaning}；这条关系不构成因果判断。`}break;
    }
    case 'filter-window':
      if(event.value==='all'||view.windows.some(w=>propagationWindowKey(w)===event.value)){s.filter.window=event.value;s.detail=null;s.comparison.result=null;s.notice='时间窗筛选已更新；原渠道选择保留，隐藏项不会改名为当前窗口。'}break;
    case 'filter-relation':
      if(event.value==='all'||Object.hasOwn(PROPAGATION_RELATIONS,event.value)){s.filter.relation=event.value;s.selectedEdge=null;s.detail=null;s.notice='只筛选明确提供的关系；缺口不会补线。'}break;
    case 'open-detail': {
      if(!channel||!PROPAGATION_STAGES.some(x=>x.id===event.stageId))break;
      s.selected=channel.id;s.selectedStage=event.stageId;
      const metric=propagationMetric(s.dataset,channel,event.stageId),source=s.dataset.sources?.[metric.source?.id];
      s.detail={channelId:channel.id,stageId:event.stageId,metric,source:source?copy(source):null,window:copy(channel.window)};s.notice='已打开本地来源记录；返回将保留当前渠道和筛选。';break;
    }
    case 'close-detail':s.detail=null;s.notice='已回到原渠道与阶段；时间窗和关系筛选保持。';break;
    case 'compare-target':
      if(eligibleChannels(s.dataset).some(c=>c.id===event.id)){s.comparison.channelId=event.id;s.comparison.result=null}break;
    case 'compare-stage':
      if(['content','exposure','response'].includes(event.stageId)){s.comparison.stageId=event.stageId;s.comparison.result=null}break;
    case 'compare':
      s.comparison.result=comparePropagationChannels(s,s.selected,s.comparison.channelId,s.comparison.stageId);s.notice=s.comparison.result.allowed?'同口径对照已生成；不计算跨平台总量或因果。':`比较被阻止：${s.comparison.result.reasons.join('；')}。`;break;
    case 'draft-analysis':
      if(s.draft.trim()){s.notice='已有未清空草稿；请先保存或明确清空后，再整理当前观测。';break}
      if(view.selected){s.draft=makeDraft(s,view.selected);s.draftContext={channelId:view.selected.id,sourceId:view.selected.sourceId,sourceVersion:s.dataset.sources[view.selected.sourceId]?.version};s.openedRevision=null;s.notice='已整理当前观测为可编辑本地草稿；人工判断仍待填写。'}break;
    case 'edit-analysis':
      if(!s.draftContext&&view.selected)s.draftContext={channelId:view.selected.id,sourceId:view.selected.sourceId,sourceVersion:s.dataset.sources[view.selected.sourceId]?.version};
      s.draft=String(event.text??'').slice(0,4000);break;
    case 'clear-draft':s.draft='';s.draftContext=null;s.openedRevision=null;s.notice='只清空当前分析草稿；已保留的历史版本仍在。';break;
    case 'save-analysis': {
      if(!view.selected||!s.draft.trim()){s.notice='先选择可见渠道并填写分析草稿。';break}
      const c=view.selected;
      if(!s.draftContext||s.draftContext.channelId!==c.id||s.draftContext.sourceId!==c.sourceId||s.draftContext.sourceVersion!==s.dataset.sources[c.sourceId]?.version){s.notice='草稿引用与当前渠道或来源版本不同；请返回原渠道或清空后重新整理。';break}
      const ref={id:c.sourceId,version:s.draftContext.sourceVersion};
      if(!s.dataset.sources[c.sourceId]||s.dataset.sources[c.sourceId].withdrawn){s.notice='来源已撤回，不能把旧草稿保存为当前分析。';break}
      const revision=s.analysis.length+1;s.analysis.push({revision,text:s.draft,channelId:c.id,scope:copy(s.dataset.scope),window:copy(c.window),sourceRefs:[ref],impacted:false});s.openedRevision=revision;s.notice=`本地分析 v${revision} 已保留于本页内存；已绑定来源版本。`;break;
    }
    case 'reopen-analysis': {
      const a=s.analysis.find(a=>a.revision===event.revision);
      if(a){s.draft=a.text;s.draftContext={channelId:a.channelId,sourceId:a.sourceRefs[0].id,sourceVersion:a.sourceRefs[0].version};s.openedRevision=a.revision;s.selected=a.channelId;s.detail=null;s.notice=`已重开本地分析 v${a.revision}${a.impacted?'；来源已撤回，此历史分析需重新核对':''}。`}break;
    }
    case 'withdraw-source': {
      const source=s.dataset.sources[event.sourceId||view.selected?.sourceId];
      if(source&&!source.withdrawn){source.withdrawn=true;source.version++;s.detail=null;s.selectedEdge=null;s.comparison.result=null;for(const a of s.analysis)if(a.sourceRefs.some(r=>r.id===source.id))a.impacted=true;s.notice='人工测试事件：来源已撤回；旧边与指标停止呈现，历史分析标记为受影响。'}break;
    }
  }
  return s;
}

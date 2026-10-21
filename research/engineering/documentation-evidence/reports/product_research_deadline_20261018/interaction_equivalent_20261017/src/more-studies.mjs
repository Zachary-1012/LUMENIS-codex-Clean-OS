import{createProvenanceStudy,createPresentationStudy}from'./proposal-study.mjs';
import {DATA_STATES,compareRows,orbitPosition,intakeText,initialProvenance,provenanceReduce,validatePresentation}from'./contracts.mjs';
export const moreStudies=[
 ['provenance','21','AI PROPOSAL / HUMAN ADOPTION','建议，最后由你决定','对照预生成AI草案，修改自己的正文，再采纳、拒绝或撤销；保留采用与修改记录；逐句来源仍未追踪。','规划§18.1：预生成AI示例与运行时调用分明。没有模型服务，不提供伪重生成。',[]],
 ['presentation','22','TYPED PROPOSAL / SAFE VIEW','界面提议，也要可拒绝','编辑一个有类型的表现建议，校验后由你采用；不支持、旧版、无权限按边界降级。','Experience §38：这里只实验当前屏组件白名单，不是通用页面引擎或真实模型推理。',[]],
 ['states','16','MISSING IS NOT ZERO','空缺，不会伪装成零','逐个切换状态，看内容、可用动作与恢复提示如何不同。','Experience §18：0/空/未知/未采集/过期/离线/拒绝/失败分别表达。',[]],
 ['comparison','17','SAME DATA / ALL VIEWS','比较，要先同口径','调整两条示例的值、期间与币种。表、图、文字和导出来自同一个结果。','CTH趋势对比/BMP活动资源：不可比时不做差，0可见，未知不补0。',[]],
 ['intake','18','LOCAL FILE / BASIC ANALYSIS','拿进来，自己看','选一份本地TXT/CSV，直接读取和基础统计，不请求AI；查看原文、编辑本地笔记、保存重开。','Shared普通资料路径的浏览器小样；不支持PDF/DOCX解析，不冒称完整Importer。文件留本设备。',[]],
 ['readaloud','19','LOCAL VOICE / USER CONTROL','文字，也可以听','选择可用本地声线和速率，主动朗读/停止；改正文会停止旧会话。','Experience §37：只预览授权可见文字，不生成配音、不改音视频时间轴。',[]],
 ['orbital','20','BROWSE / FOCUS / RETURN','拨动，再聚焦','拨动三个资料位置，从空间浏览聚焦同一资料并返回。也可直接列表选择。','Experience §6：任务型轨道/深度浏览，只用于资料探索，不套到编辑器或业务图表。',[]]
];
export function createMore(id,{stage,button,status,reduce,listen,onDispose,session,settingsRoot}){if(id==='provenance')return createProvenanceStudy({stage,status,onDispose,session});if(id==='presentation')return createPresentationStudy({stage,status,onDispose,session,settingsRoot});const $=s=>stage.querySelector(s);const elem=(tag,txt)=>{const e=document.createElement(tag);e.textContent=txt;return e};
 function states(){stage.innerHTML='<section class="lab-scroll"><h3 id="stateTitle"></h3><output id="stateValue"></output><p id="stateReason"></p></section>';function show(k){const s=DATA_STATES[k];$('#stateTitle').textContent=s.label;$('#stateValue').textContent=s.value===null?'—':String(s.value);$('#stateReason').textContent=s.reason;status(k==='denied'?'无读取权限：不能绕过；请选择允许的资料。':k==='error'?'失败项可单独重试，不重放成功项。':'主动选择的状态样例，无服务器事实。')}for(const[k,s]of Object.entries(DATA_STATES))button(s.label,()=>show(k));button('重试读取失败项',()=>{show('unknown');status('重试请求尚未绑定读取服务；结果仍未知，不补成零。')});show('unknown')}
 function comparison(){stage.innerHTML='<section class="lab-scroll"><label>A 数值<input id="va" type="number" value="0"></label><label>B 数值<input id="vb" type="number" value="12"></label><label><input id="missing" type="checkbox"> B未知</label><label>B币种<select id="currency"><option>CNY</option><option>USD</option></select></label><label>B期间<select id="period"><option>2026-09</option><option>2026-08</option></select></label><div id="view"></div></section>';let result;function draw(){result=compareRows([{name:'示例A',value:$('#va').value.trim()===''?null:+$('#va').value,state:$('#va').value.trim()===''?'unknown':'ready',unit:'元',currency:'CNY',period:'2026-09'},{name:'示例B',value:$('#missing').checked||$('#vb').value.trim()===''?null:+$('#vb').value,state:$('#missing').checked||$('#vb').value.trim()===''?'unknown':'ready',unit:$('#currency').value==='USD'?'美元':'元',currency:$('#currency').value,period:$('#period').value}]);const view=$('#view');view.replaceChildren();const table=document.createElement('table');table.innerHTML='<caption>人工输入示例 · 不是业务实测</caption><tr><th>项</th><th>数值</th><th>口径</th></tr>';for(const r of result.rows){const tr=document.createElement('tr');for(const v of[r.name,r.value===null?'—':r.value,`${r.period} ${r.currency} ${r.unit} · ${r.state}`])tr.append(elem('td',v));table.append(tr)}view.append(table,elem('p',result.delta===null?'差值：不可计算':`差值：${result.delta}元`));if(result.comparable){const graph=document.createElement('div');graph.setAttribute('role','img');graph.setAttribute('aria-label',result.rows.map(r=>r.name+' '+(r.value??'未知')).join('；'));const max=Math.max(1,...result.rows.map(r=>Math.abs(r.value||0)));for(const r of result.rows){const line=elem('div',r.name+': '+(r.value??'—'));line.style.cssText=`border-left:${r.value===null?0:Math.abs(r.value)/max*100}px solid #9eb691;padding:4px`;graph.append(line)}view.append(graph)}status(result.reason+'；未知与零分开。')}stage.querySelectorAll('input,select').forEach(e=>e.oninput=draw);button('导出同版数据',()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));a.href=url;a.download='comparison-local.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});draw()}
 function intake(){
  let item=null,generation=0,disposed=false,lastContentState='未选择资料';
  stage.innerHTML='<section class="lab-scroll"><label>本地TXT/CSV（≤1MB）<input id="localFile" type="file" accept=".txt,.csv,text/plain,text/csv"></label><p id="intakeState">未选择资料</p><details><summary>查看原文</summary><pre id="original" style="white-space:pre-wrap"></pre></details><label>可编辑分析笔记<textarea id="analysisNote"></textarea></label></section>';
  const fileInput=$('#localFile'),stateNode=$('#intakeState'),original=$('#original'),note=$('#analysisNote');
  const isCurrent=g=>!disposed&&g===generation;
  const invalidate=()=>{generation++};
  // A result belongs to this mounted view and the latest input intent. Reopen,
  // cancel and dispose invalidate both successful and failed pending reads.
  fileInput.onchange=async()=>{
   if(disposed)return;
   invalidate();
   const f=fileInput.files[0],g=generation;
   if(!f){stateNode.textContent=lastContentState;status('已清除文件选择；当前资料和笔记保留。');return}
   stateNode.textContent='正在本地读取…';
   try{
    if(f.size>1000000||!(/\.(txt|csv)$/i.test(f.name)))throw Error('仅支持1MB以内TXT/CSV');
    const source=await f.text();
    if(!isCurrent(g))return;
    const next=intakeText(source,f.name,Date.now());
    item=next;
    original.textContent=item.source;
    note.value=`${item.analysis.characters}个字符；${item.analysis.lines}行；${item.analysis.nonEmptyLines}非空行。\n这是确定性统计，不推断事实。`;
    lastContentState=`${item.name} · 本地读取/基础分析完成 · 未保存 · 原发布时间未知`;
    stateNode.textContent=lastContentState;
    status('原件仅内存，本地基础分析完成；模型未调用。');
   }catch(e){
    if(!isCurrent(g))return;
    stateNode.textContent='读取失败：'+e.message+(item?'；当前资料和笔记保留':'');
    status('本地读取失败；可重新选择文件，当前编辑未被覆盖。');
   }
  };
  button('取消读取',()=>{
   if(disposed)return;
   invalidate();
   stateNode.textContent=lastContentState+' · 未完成的读取已取消';
   status('已取消未完成的读取；旧结果不覆盖当前。');
  });
  button('保存本地审核笔记',()=>{
   if(disposed)return;
   if(!item){status('先选一份文本资料');return}
   try{
    const saved={...item,note:note.value};
    localStorage.setItem('review-local-intake',JSON.stringify(saved));
    const read=JSON.parse(localStorage.getItem('review-local-intake'));
    if(read.id!==item.id)throw Error('readback');
    status('本地保存已读回；不代表产品导入或服务器保存。');
   }catch{status('本地保存失败；原文与编辑仍可读取。')}
  },true);
  button('重开本地版本',()=>{
   if(disposed)return;
   invalidate();
   stateNode.textContent=lastContentState;
   try{
    const v=JSON.parse(localStorage.getItem('review-local-intake')||'null');
    if(!v){status('无本地保存版本；当前资料和笔记保留。');return}
    if(!v.id||typeof v.name!=='string'||typeof v.source!=='string'||typeof v.note!=='string')throw Error('invalid saved intake');
    item=v;original.textContent=v.source;note.value=v.note;
    lastContentState=v.name+' · 已重开；原入库时点未重置';
    stateNode.textContent=lastContentState;
    status('重开本地审核版本，不触发模型或采集。');
   }catch{status('本地版本无法读取；当前资料和笔记保留。')}
  });
  onDispose(()=>{invalidate();disposed=true});
 }
 function readaloud(){stage.innerHTML='<section class="lab-scroll"><label>授权可见的审核文字<textarea id="readText">这是一段用于审核朗读交互的本地文字。你可以随时修改或停止。</textarea></label><label>本地声线<select id="localVoice"></select></label><label>速率<select id="readRate"><option>.75</option><option selected>1</option><option>1.25</option></select></label><p id="voiceState"></p></section>';const synth=window.speechSynthesis;let voices=[],active=false;function stop(){if(synth)synth.cancel();active=false;status('已停止本地朗读；没有产生配音文件。')}function list(){voices=synth?synth.getVoices().filter(v=>v.localService):[];$('#localVoice').replaceChildren(...voices.map((v,i)=>{const o=elem('option',v.name+' · '+v.lang);o.value=i;return o}));$('#voiceState').textContent=voices.length?'仅列出系统报告为本地的声线；不会自动播放。':'没有可用本地声线，朗读不可用；正文仍可编辑。'}button('朗读',()=>{if(!synth||!voices.length){status('本地声线不可用，不切换云端服务。');return}stop();const u=new SpeechSynthesisUtterance($('#readText').value);u.voice=voices[+$('#localVoice').value];u.lang=u.voice.lang;u.rate=+$('#readRate').value;u.onend=()=>{active=false;status('本地朗读结束，未生成媒体文件。')};u.onerror=()=>{active=false;status('本地朗读失败；文字保留。')};synth.speak(u);active=true;status('已请求系统本地朗读；设备音频仍需实际听验。')},true);button('停止',stop);$('#readText').oninput=stop;$('#readRate').onchange=stop;$('#localVoice').onchange=stop;if(synth)listen(synth,'voiceschanged',list);onDispose(stop);listen(document,'visibilitychange',()=>{if(document.hidden)stop()});list()}
 function orbital(){let angle=0,selected=0,focus=false;stage.innerHTML='<div id="orbit" style="position:relative;height:260px"></div><p id="orbitContent" style="padding:15px"></p><label style="display:block;padding:15px">拨动资料<input id="orbitAngle" aria-label="拨动资料" type="range" min="-180" max="180" value="0"></label>';function draw(){const box=$('#orbit');box.replaceChildren();for(let i=0;i<3;i++){const pos=orbitPosition(i,3,angle),b=elem('button',`资料 ${i+1}`);b.style.cssText=reduce()?`margin:12px;background:${selected===i?'#b6c9a4':'#fff'}`:`position:absolute;left:calc(50% + ${focus?i===selected?0:160:pos.x}px);top:${focus?90:80+pos.y}px;transform:translateX(-50%) scale(${focus?i===selected?1.2:.65:.7+pos.depth*.35});opacity:${focus&&i!==selected?.3:1};z-index:${Math.round(pos.depth*10)};transition:transform .22s,top .22s,left .22s;background:${selected===i?'#b6c9a4':'#fff'}`;b.onclick=()=>{selected=i;draw()};box.append(b)}$('#orbitContent').textContent=focus?`资料${selected+1}：同一对象详情；来源为人工审核文案。`:`当前选择资料${selected+1}；可继续拨动或直接选按钮。`;status('空间位置仅辅助浏览，不暗示资料相关性/热度/权限。')}$('#orbitAngle').oninput=e=>{angle=+e.target.value*Math.PI/180;draw()};button('聚焦所选',()=>{focus=true;draw()},true);button('返回浏览',()=>{focus=false;draw()});button('选择下一个',()=>{selected=(selected+1)%3;draw()});listen(window,'review-motion-change',draw);draw()}
 ({states,comparison,intake,readaloud,orbital}[id]||(()=>status('尚未实现')))();}

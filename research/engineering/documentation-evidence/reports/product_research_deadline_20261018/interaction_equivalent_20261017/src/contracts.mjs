/** Standalone review contracts. All effects are LOCAL_ONLY; no server permission authority. */
export const CONTRACT_VERSION='review-interactions/0.3.0';
export const clone=x=>JSON.parse(JSON.stringify(x));
// Local event contract only. Production Task/run/attempt/scope and receipts remain UNBOUND.
export const STREAM_LIMITS=Object.freeze({blocks:128,text:20000,id:128,totalText:524288});
const streamId=x=>typeof x==='string'&&x.length>0&&x.length<=STREAM_LIMITS.id&&!['__proto__','prototype','constructor'].includes(x);
const streamText=x=>typeof x==='string'&&x.length<=STREAM_LIMITS.text;
export function initialStream(run='review-run-1'){if(!streamId(run))throw Error('INVALID_RUN');return{run,scope:'review',allowed:true,blocks:{},order:[],status:'pending',rejected:0}}
export function validStreamSnapshot(s){
 if(!s||!streamId(s.run)||s.scope!=='review'||typeof s.allowed!=='boolean'||!['pending','partial','offline','cancelled','complete','denied'].includes(s.status)||!Number.isSafeInteger(s.rejected)||s.rejected<0||!Array.isArray(s.order)||s.order.length>STREAM_LIMITS.blocks||new Set(s.order).size!==s.order.length||!s.blocks||Array.isArray(s.blocks)||typeof s.blocks!=='object'||Object.keys(s.blocks).length!==s.order.length)return false;
 if((!s.allowed||s.status==='denied')&&(s.allowed||s.status!=='denied'||s.order.length))return false;
 let total=0;
 for(const id of s.order){if(!streamId(id)||!Object.hasOwn(s.blocks,id))return false;const b=s.blocks[id];if(!b||b.id!==id||!streamText(b.text)||!Number.isSafeInteger(b.revision)||b.revision<1||typeof b.edited!=='boolean'||!['text','comparison'].includes(b.kind))return false;
 if(b.undoAdoption&&(!streamText(b.undoAdoption.text)||!['text','comparison'].includes(b.undoAdoption.kind)))return false;
 if(b.seenRevision!==undefined&&(!Number.isSafeInteger(b.seenRevision)||b.seenRevision<b.revision))return false;
 if(b.suggestion&&(!b.edited||!streamText(b.suggestion.text)||!Number.isSafeInteger(b.suggestion.revision)||b.suggestion.revision<=b.revision||!['text','comparison'].includes(b.suggestion.kind)))return false;
 total+=b.text.length+(b.suggestion?.text.length||0);if(total>STREAM_LIMITS.totalText)return false;
 }return true;
}
export function streamReduce(state,event){const s=clone(state),reject=()=>({...s,rejected:s.rejected+1});
 if(!event||typeof event!=='object'||Array.isArray(event))return reject();
 if(event.type==='revoke')return{...s,allowed:false,blocks:{},order:[],status:'denied'};
 if(event.type==='restart'){if(!s.allowed||!streamId(event.run)||event.run===s.run)return reject();return initialStream(event.run)}
 if(!s.allowed||event.run!==s.run||event.scope!==undefined&&event.scope!==s.scope)return reject();
 const local=['edit','adopt','reject','undo-adopt'].includes(event.type);
 if(!local&&['cancelled','complete'].includes(s.status))return reject();
 if(event.type==='cancel'){s.status='cancelled';return s}
 if(event.type==='complete'){s.status='complete';return s}
 if(event.type==='disconnect'){s.status='offline';return s}
 if(event.type==='resume'){if(s.status!=='offline')return reject();s.status=s.order.length?'partial':'pending';return s}
 if(event.type==='block'){
  if(s.status==='offline'||!streamId(event.id)||!Number.isSafeInteger(event.revision)||event.revision<1||!streamText(event.text)||!['text','comparison'].includes(event.kind))return reject();
  const old=Object.hasOwn(s.blocks,event.id)?s.blocks[event.id]:null;
  if(old&&event.revision<=Math.max(old.revision,old.seenRevision??old.revision,old.suggestion?.revision??old.revision)||!old&&s.order.length>=STREAM_LIMITS.blocks)return reject();
  // Bound both visible text and pending corrections, without silent truncation.
  const size=s.order.reduce((n,id)=>n+s.blocks[id].text.length+(s.blocks[id].suggestion?.text.length||0),0);
  if(size-(old?.edited?(old.suggestion?.text.length||0):(old?.text.length||0))+event.text.length>STREAM_LIMITS.totalText)return reject();
  if(old?.edited){s.blocks[event.id]={...old,undoAdoption:null,seenRevision:event.revision,suggestion:{text:event.text,revision:event.revision,kind:event.kind}};return s}
  s.blocks[event.id]={id:event.id,revision:event.revision,text:event.text,kind:event.kind,edited:false};if(!old)s.order.push(event.id);s.status='partial';return s;
 }
 if(!local||!streamId(event.id)||!Object.hasOwn(s.blocks,event.id))return reject();
 const b=s.blocks[event.id];
 if(event.type==='edit'){
  if(!streamText(event.text)||s.order.reduce((n,id)=>n+s.blocks[id].text.length+(s.blocks[id].suggestion?.text.length||0),0)-b.text.length-(b.suggestion?.text.length||0)+event.text.length>STREAM_LIMITS.totalText)return reject();
  // Any subsequent human edit invalidates the older adoption preview; seenRevision prevents replay.
  s.blocks[event.id]={...b,text:event.text,edited:true,suggestion:null,undoAdoption:null};
 }
 if(event.type==='adopt'){if(!b.suggestion)return reject();s.blocks[event.id]={...b,...b.suggestion,edited:false,suggestion:null,undoAdoption:{text:b.text,kind:b.kind}}}
 if(event.type==='undo-adopt'){if(!b.undoAdoption)return reject();s.blocks[event.id]={...b,text:b.undoAdoption.text,kind:b.undoAdoption.kind,edited:true,undoAdoption:null,suggestion:null}}
 if(event.type==='reject')s.blocks[event.id].suggestion=null;
 return s;
}
export function initialRevision(){return{version:1,parent:null,budgetCents:100000,days:10,note:'保留人工判断',proposal:null,history:[],permission:true}}
export function proposeRevision(state,budgetCents,days){const s=clone(state);if(!Number.isSafeInteger(budgetCents)||budgetCents<0||budgetCents>100000000||!Number.isInteger(days)||days<1||days>365)return{...s,error:'预算须为有效分值，天数1–365'};return{...s,error:null,proposal:{baseVersion:s.version,budgetCents,days,dailyCents:Math.floor(budgetCents/days),remainderCents:budgetCents%days}}}
export function revisionReduce(state,event){const s=clone(state);if(event.type==='edit'){s.note=event.text;return s}if(event.type==='reject'){s.proposal=null;return s}if(event.type==='revoke')return{...s,permission:false,proposal:null};if(event.type==='adopt'){if(!s.permission||!s.proposal||s.proposal.baseVersion!==s.version)return{...s,error:'不可采用：权限或基线已变更'};const old={version:s.version,parent:s.parent,budgetCents:s.budgetCents,days:s.days,note:s.note};s.history.push(old);s.parent=s.version;s.version++;s.budgetCents=s.proposal.budgetCents;s.days=s.proposal.days;s.proposal=null;return s}if(event.type==='undo'&&s.history.length){const old=s.history.pop();return{...s,...old,proposal:null}}return s}
export function initialTimeline(){return{duration:120,viewport:30,pan:0,playhead:15,selection:'a',clips:[{id:'a',start:4,end:18},{id:'b',start:28,end:46}],history:[]}}
export function timelineReduce(state,event){const s=clone(state),clamp=(v,a,b)=>Math.max(a,Math.min(b,Number.isFinite(+v)?+v:a));
 if(event.type==='pan')s.pan=clamp(event.value,0,s.duration-s.viewport);
 if(event.type==='seek')s.playhead=clamp(event.value,0,s.duration);
 if(event.type==='select'&&s.clips.some(x=>x.id===event.id))s.selection=event.id;
 if(event.type==='zoom'){const anchor=s.pan+s.viewport/2;s.viewport=clamp(event.value,5,120);s.pan=clamp(anchor-s.viewport/2,0,s.duration-s.viewport)}
 if(event.type==='move'){const clip=s.clips.find(x=>x.id===s.selection);if(clip){s.history.push(clone(s.clips));const d=clip.end-clip.start;clip.start=clamp(event.start,0,s.duration-d);clip.end=clip.start+d}}
 if(event.type==='undo'&&s.history.length)s.clips=s.history.pop();return s;
}
export function initialTasks(){return{selected:'a',items:{a:{label:'研究资料',attempt:1,status:'running',result:null},b:{label:'整理稿件',attempt:1,status:'running',result:null}},notices:[],quiet:false}}
export function taskReduce(state,e){const s=clone(state);if(e.type==='quiet'){s.quiet=!s.quiet;return s}if(e.type==='select'&&s.items[e.id]){s.selected=e.id;return s}const t=s.items[e.id];if(!t)return s;if(e.type==='cancel'){t.status='cancelled';return s}if(e.type==='retry'){t.attempt++;t.status='running';return s}if(e.attempt!==t.attempt||t.status==='cancelled')return s;if(e.type==='result'){t.status='complete';t.result=e.text;if(!s.quiet&&!s.notices.some(n=>n.key===e.id+':'+e.attempt))s.notices.push({key:e.id+':'+e.attempt,text:t.label+'：本地示例结果就绪'})}if(e.type==='approval'&&!s.notices.some(n=>n.key===e.id+':approval'))s.notices.push({key:e.id+':approval',text:t.label+'：需要用户选择',required:true});return s}
export function captureContext(context){return clone(context)}
export function restoreContext(saved){return clone(saved)}
export const motionVocabulary=['ENTER','EXIT','TRACE','OPEN','SELECT','SHIFT','MORPH','EXPAND','COLLAPSE','DRILL','RETURN','PROGRESS','COMPLETE','WARNING','ERROR','RECOVER'];
export function reduceMotionState(state,event){const s={...state};switch(event){case'ENTER':s.visible=true;break;case'EXIT':s.visible=false;break;case'OPEN':case'EXPAND':s.expanded=true;break;case'COLLAPSE':s.expanded=false;break;case'SELECT':s.selected=!s.selected;break;case'SHIFT':s.position=1-(s.position||0);break;case'MORPH':s.view=s.view==='summary'?'detail':'summary';break;case'TRACE':case'DRILL':s.layer='source';break;case'RETURN':s.layer='content';break;case'PROGRESS':s.progress=Math.min(3,(s.progress||0)+1);break;case'COMPLETE':s.status=s.progress===3?'complete':'incomplete';break;case'WARNING':s.status='warning';break;case'ERROR':s.status='error';break;case'RECOVER':s.status='ready';break;}return s}
export const DATA_STATES={zero:{value:0,label:'真实零',reason:'示例计数确为0'},null:{value:null,label:'空值',reason:'字段无值'},unknown:{value:null,label:'未知',reason:'尚无可信依据'},notCollected:{value:null,label:'未采集',reason:'没有采集记录'},stale:{value:12,label:'过期',reason:'仅历史值，不能当当前值'},offline:{value:null,label:'离线',reason:'连接不可用'},denied:{value:null,label:'无权限',reason:'当前范围不可读取'},error:{value:null,label:'读取失败',reason:'本次读取失败，可安全重试'}};
export function compareRows(rows){const valid=rows.filter(r=>r.state==='ready'&&Number.isFinite(r.value));const comparable=valid.length===rows.length&&valid.length>=2&&valid.every(r=>r.unit===valid[0]?.unit&&r.period===valid[0]?.period&&r.currency===valid[0]?.currency);return{rows:clone(rows),comparable,delta:comparable&&valid.length===2?valid[1].value-valid[0].value:null,reason:comparable?'仅同口径有效值可比较':'期间、单位或币种不同，不能直接相减'}}
export function orbitPosition(index,count,angle,radius=110){const theta=angle+index/count*Math.PI*2;return{x:Math.sin(theta)*radius,y:Math.cos(theta)*32,depth:(Math.cos(theta)+1)/2}}
export function intakeText(text,name,now){if(typeof text!=='string'||text.length>1000000)throw Error('Text limit');const lines=text.split(/\r?\n/);return{id:'local-'+now,name,ingestedAt:now,publishedAt:null,source:text,analysis:{characters:[...text].length,lines:lines.length,nonEmptyLines:lines.filter(x=>x.trim()).length},state:'analysed',origin:'USER_LOCAL_FILE',model:'NOT_CALLED'}}
export function validatePresentation(proposal,registry,context){
 if(context?.allowed!==true)return{accepted:false,fallback:'blocked',reason:'没有读取权限'};
 const reject=reason=>({accepted:false,fallback:'text',reason});
 if(!Array.isArray(registry)||registry.length>64||registry.some(x=>typeof x!=='string')||!Array.isArray(context.actions)||context.actions.length>64||context.actions.some(x=>typeof x!=='string'))return reject('当前屏注册合同无效');
 if(!proposal||typeof proposal!=='object'||Array.isArray(proposal))return reject('表现提案格式无效');
 if(Object.hasOwn(proposal,'html')||Object.hasOwn(proposal,'javascript'))return reject('不执行生成的HTML/JavaScript');
 if(Object.keys(proposal).some(k=>!['kind','version','scope','actions'].includes(k)))return reject('提案包含未注册字段');
 if(typeof proposal.kind!=='string'||!registry.includes(proposal.kind))return reject('不支持的表现类型');
 if(!Number.isSafeInteger(proposal.version)||proposal.version<1||proposal.version!==context.version||typeof proposal.scope!=='string'||!proposal.scope||proposal.scope.length>256||proposal.scope!==context.scope)return reject('范围或版本已变化');
 const actions=proposal.actions??[];if(!Array.isArray(actions)||actions.length>64||actions.some(x=>typeof x!=='string'||!x||x.length>100))return reject('动作提案格式无效');
 return{accepted:true,kind:proposal.kind,actions:[...new Set(actions.filter(x=>context.actions.includes(x)))],rejectedActions:[...new Set(actions.filter(x=>!context.actions.includes(x)))],reason:'已由当前屏支持类型/版本/范围/动作白名单校验；未产生业务执行'};
}
export function initialProvenance(){return{text:'记录你自己的观察。',origin:'human',proposal:null,history:[],revision:0,notice:'',undoBuffer:null}}
export function provenanceReduce(state,event){const s=clone(state),revision=Number.isSafeInteger(s.revision)?s.revision:0;if(['suggest','edit'].includes(event.type)&&(typeof event.text!=='string'||event.text.length>200000))return{...s,notice:'文本格式或容量无效；保留原稿'};if(event.type==='suggest')return{...s,proposal:{text:event.text,origin:'ai-pregenerated',baseRevision:revision,label:'预先由AI编写的文案样例，无运行时生成'},notice:'建议尚未采用'};if(event.type==='edit')return{...s,text:event.text,origin:s.origin==='human'?'human':'mixed',revision:revision+1,notice:'',undoBuffer:null};if(event.type==='reject')return{...s,proposal:null,notice:'已拒绝建议，正文保留'};if(event.type==='adopt'&&s.proposal){if(s.proposal.baseRevision!==revision)return{...s,notice:'正文已在建议之后修改；请重新查看新建议，未覆盖人工稿'};s.history.push({text:s.text,origin:s.origin});s.history=s.history.slice(-32);s.text=s.proposal.text;s.origin=s.proposal.origin;s.proposal=null;s.revision=revision+1;s.notice='已明确采纳本地示例';s.undoBuffer=null;return s}if(event.type==='redo'&&s.undoBuffer){const v=s.undoBuffer;s.history.push({text:s.text,origin:s.origin});return{...s,...v,history:s.history.slice(-32),proposal:null,revision:revision+1,undoBuffer:null,notice:'已恢复刚撤销的内容'}}if(event.type==='undo'&&s.history.length)return{...s,...s.history.pop(),proposal:null,revision:revision+1,undoBuffer:{text:s.text,origin:s.origin},notice:'已返回采纳前版本；后续修改也随此整体撤销'};return s}

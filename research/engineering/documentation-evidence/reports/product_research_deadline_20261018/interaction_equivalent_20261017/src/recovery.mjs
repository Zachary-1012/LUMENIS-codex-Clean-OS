// Pure recovery coordinator. Events are adapter-owned observations, never credentials.
export const recoveryKinds=Object.freeze(['AUTH_REQUIRED','LOGIN_FORM_REQUIRED','VERIFY','CAPTCHA','BLOCKED','IP_RISK','COOLDOWN']);
export function initialRecovery(items){return{items:items.map(x=>({...x,status:'suspended',attempt:0})),active:null,open:false,notice:'',revision:0}}
export function recoveryReduce(state,e){const s=structuredClone(state),item=s.items.find(x=>x.id===e.id);
 if(e.type==='open'&&item){if(s.active&&s.active!==item.id)return{...s,notice:'先处理或暂缓当前任务'};s.active=item.id;s.open=true;return s}
 if(e.type==='dismiss'){s.open=false;s.notice='仅关闭视图；任务仍暂停';return s}
 if(e.type==='defer'){s.open=false;s.active=null;s.notice='已暂缓；其它资料仍可继续';return s}
 if(e.type==='kind'&&item&&recoveryKinds.includes(e.kind)){if(item.kind===e.kind)return s;item.kind=e.kind;item.attempt++;item.status='suspended';s.revision++;s.notice='来源状态已变化；旧轮观察失效，任务保持暂停';return s}
 if(e.type==='begin'&&item&&s.active===item.id){if(['BLOCKED','IP_RISK','COOLDOWN'].includes(item.kind))return{...s,notice:'风险/冷却状态不能通过登录解决；等待真实状态恢复'};item.attempt++;item.status='waiting';s.revision++;return s}
 if(e.type==='observe'&&item&&s.active===item.id&&e.attempt===item.attempt&&item.attempt>0&&!['BLOCKED','IP_RISK','COOLDOWN'].includes(item.kind)&&['waiting','verifying'].includes(item.status)){if(e.health==='verified'){item.status='recovered';s.notice='适配器已核验；仅原任务可继续';s.active=null;s.open=false}else{item.status=e.health==='cooldown'?'cooldown':'verifying';s.notice='尚未核验恢复；不能继续原任务'}return s}
 return{...s,notice:'旧任务/旧轮观察已忽略'}
}
export function recoveryPresentation(kind){return{AUTH_REQUIRED:'等待平台提供的登录入口',LOGIN_FORM_REQUIRED:'需要受控登录表单',VERIFY:'明确的人机核验',CAPTCHA:'明确的验证码核验',BLOCKED:'来源受阻；不能用登录替代',IP_RISK:'网络风险；不能用登录替代',COOLDOWN:'等待真实冷却状态'}[kind]||'未知状态，暂停'}

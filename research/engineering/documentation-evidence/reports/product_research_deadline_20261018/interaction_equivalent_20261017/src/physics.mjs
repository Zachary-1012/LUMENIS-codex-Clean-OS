/** Review-only implementation, units: CSS px, seconds, relative mass. */
export const VERSION='review-physics/1.0.0';
export const defaults={mass:1.4,stiffness:180,damping:19,friction:3.2,restitution:.45,radius:95,strength:8,release:650,press:3,lift:18,tilt:7,follow:24};
export function parameters(p={}) {
 const ranges={mass:[.2,6],stiffness:[20,600],damping:[1,80],friction:[.2,12],restitution:[0,.85],radius:[15,180],strength:[.5,20],release:[100,1800],press:[0,10],lift:[0,40],tilt:[0,16],follow:[3,60]};
 return Object.fromEntries(Object.entries(defaults).map(([k,v])=>[k,Math.min(ranges[k][1],Math.max(ranges[k][0],Number.isFinite(+p[k])?+p[k]:v))]));
}
export function spring(s,target,dt,p=defaults) {
 const n=Math.max(1,Math.ceil(Math.min(.1,Math.max(0,dt))/(1/240))); const h=Math.min(.1,Math.max(0,dt))/n;
 let {x,v}=s; for(let i=0;i<n;i++){ v+=(-p.stiffness*(x-target)-p.damping*v)/p.mass*h;x+=v*h; }
 if(Math.abs(x-target)<.02&&Math.abs(v)<.05) return {x:target,v:0};
 return {x,v};
}
export function inertia(s,dt,max,p=defaults){
 const h=Math.min(.1,Math.max(0,dt));let v=Math.max(-1800,Math.min(1800,s.v));
 let x=s.x+v*(1-Math.exp(-p.friction*h))/p.friction;v*=Math.exp(-p.friction*h);
 if(x<0){x=-x;v=Math.abs(v)*p.restitution;} if(x>max){x=2*max-x;v=-Math.abs(v)*p.restitution;}
 x=Math.max(0,Math.min(max,x));if(Math.abs(v)<.5)v=0;return{x,v};
}
export function magnet(x,v,targets,p=defaults,captured=null){
 targets=Array.isArray(targets)?targets.filter(Number.isFinite):[];
 if(!Number.isFinite(x)||!Number.isFinite(v))throw new TypeError('Position and velocity must be finite');
 if(!targets.length)return{target:x,captured:null,force:0};
 if(captured!==null&&!targets.includes(captured))captured=null;
 const nearest=targets.reduce((a,b)=>Math.abs(x-b)<Math.abs(x-a)?b:a,targets[0]);
 if(captured!==null && Math.abs(v)<p.release && Math.abs(x-captured)<p.radius*1.35)return {target:captured,captured,force:(captured-x)*p.strength};
 if(Math.abs(v)>=p.release || Math.abs(x-nearest)>p.radius)return {target:x,captured:null,force:0};
 return {target:nearest,captured:nearest,force:(nearest-x)*p.strength*(1-Math.abs(x-nearest)/(p.radius*1.35))};
}
export function chooseUI(intent,{ai=false,permission=true}={}){
 if(!permission)return{type:'blocked',reason:'当前范围没有读取权限；不呈现旧结果。'};
 if(/比较|对比|compare/i.test(intent))return{type:'comparison',reason:'任务需要比较同一口径；使用对照表，并保留缺失原因。'};
 if(/时间|变化|timeline/i.test(intent))return{type:'timeline',reason:'任务关注先后变化；使用时间轴，区分观察与判断。'};
 if(/写|稿|创作|write/i.test(intent))return{type:'editor',reason:'任务是创作与修改；使用可编辑文稿，不要求业务前置。'};
 return{type:'text',reason:ai?'示例模式仅选择注册组件；不执行生成的 HTML 或脚本。':'无模型仍可按明确任务选择注册组件；不伪称 AI 推理。'};
}

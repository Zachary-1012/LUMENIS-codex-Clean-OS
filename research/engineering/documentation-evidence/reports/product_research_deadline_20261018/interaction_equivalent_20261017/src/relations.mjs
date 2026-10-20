// CTH-04: missing evidence must not create an edge, including a dashed inference.
// Inputs are authorized fixtures/Owner observations; this module does not verify evidence remotely.
export function relationView(data,{selected=null,kind='all',permission=true}={}){
 if(!permission)return{nodes:[],edges:[],unverified:[],selected:null,notice:'权限不足，关系及来源已清除'};
 const nodes=data.nodes.map(n=>({...n})),ids=new Set(nodes.map(n=>n.id));
 const candidates=data.edges.filter(e=>kind==='all'||e.kind===kind);
 const supported=e=>typeof e.source==='string'&&e.source.trim().length>0&&ids.has(e.from)&&ids.has(e.to);
 const edges=candidates.filter(supported).map(e=>({...e}));
 const unverified=candidates.filter(e=>!supported(e)).map(e=>({...e,reason:'缺少可定位依据或端点，不绘制关系边'}));
 return{nodes,edges,unverified,selected:edges.some(e=>e.id===selected)?selected:null,notice:(edges.length?'仅呈现带依据的关系':'此筛选没有有证关系，不补连线')+(unverified.length?`；${unverified.length}项关系候选依据不足，未画边`:'')};
}
export function adjacentRelations(view,node){return view.edges.filter(e=>e.from===node||e.to===node).map(e=>e.id)}

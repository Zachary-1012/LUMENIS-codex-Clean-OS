export const commandRegistry=Object.freeze([
 {id:'inspect',label:'查看当前资料依据',keywords:'来源 source inspect',scope:'local'},
 {id:'compare',label:'比较本地两份方案',keywords:'比较 compare',scope:'local'},
 {id:'draft',label:'继续编辑我的文稿',keywords:'文稿 draft',scope:'local'}]);
export function searchCommands(query,registry=commandRegistry){const words=query.trim().toLowerCase().split(/\s+/).filter(Boolean);return registry.filter(c=>words.every(w=>(c.label+' '+c.keywords).toLowerCase().includes(w)))}
export function chooseCommand(id,available){return available.some(c=>c.id===id)?{accepted:true,id}:{accepted:false,reason:'未知或不在当前允许范围的命令'}}

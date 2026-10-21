/** Restricted ATX/plain-paragraph outline; exact source permutation, not a Markdown parser. */
const fail=code=>{throw Error(code)};
const lines=text=>{const out=[];let at=0;for(const raw of text.match(/[^\r\n]*(?:\r\n|\r|\n|$)/g)||[]){if(!raw)continue;out.push({start:at,raw,body:raw.replace(/[\r\n]+$/,'')});at+=raw.length}return out};
export function inspectManuscript(text){
 if(typeof text!=='string'||(typeof text.isWellFormed==='function'&&!text.isWellFormed())||new TextEncoder().encode(text).length>262144)fail('DOCUMENT_INVALID');
 const rows=lines(text),headings=[],stack=[];let previous='';
 for(const row of rows){const t=row.body;
  if(/^(?: {4}| {0,3}\t| {0,3}(?:>|[-+*](?:[ \t]|$)|\d+[.)](?:[ \t]|$)|`{3,}|~{3,}|<))/.test(t)||/^[ \t]*[=-]+[ \t]*$/.test(t)&&previous.trim())fail('STRUCTURE_UNSUPPORTED');
  const m=/^ {0,3}(#{1,6})(?:[ \t]+(.*)|$)/.exec(t);
  if(m){while(stack.length&&stack.at(-1).level>=m[1].length)stack.pop();const node={index:headings.length,start:row.start,end:text.length,level:m[1].length,label:(m[2]||'').replace(/[ \t]+#+[ \t]*$/,'').trim(),parent:stack.at(-1)?.index??null};headings.push(node);if(headings.length>256)fail('OUTLINE_LIMIT');stack.push(node)}previous=t;
 }
 for(let i=0;i<headings.length;i++){const next=headings.slice(i+1).find(h=>h.level<=headings[i].level);headings[i].end=next?.start??text.length}
 return{format:'restricted-atx-v1',offsetUnit:'utf16',headings};
}
export function previewManuscriptMove(text,index,direction){
 if(!Number.isInteger(index)||!['up','down'].includes(direction))fail('MOVE_INVALID');const {headings}=inspectManuscript(text),node=headings[index];if(!node)fail('SECTION_NOT_FOUND');
 const siblings=headings.filter(h=>h.parent===node.parent),position=siblings.findIndex(h=>h.index===index),other=siblings[position+(direction==='up'?-1:1)];if(!other)fail('NO_SIBLING');if(other.level!==node.level)fail('HIERARCHY_CHANGE_REFUSED');
 const first=direction==='up'?other:node,second=direction==='up'?node:other;
 if(first.end!==second.start)fail('NON_ADJACENT_SECTIONS');const a=text.slice(first.start,first.end),b=text.slice(second.start,second.end);
 if(b&&!/[\r\n]$/.test(b))fail('SECTION_SEPARATOR_REQUIRED');
 const after=text.slice(0,first.start)+b+a+text.slice(second.end);inspectManuscript(after);
 return{schema:'manuscript-move-v1',before:text,after,index,direction,selectedStart:direction==='up'?first.start:first.start+b.length,offsetUnit:'utf16'};
}
export function applyManuscriptMove(current,proposal,{allowed=false}={}){if(!allowed)fail('PERMISSION_DENIED');if(proposal?.schema!=='manuscript-move-v1'||current!==proposal.before)fail('STALE_MANUSCRIPT');const verified=previewManuscriptMove(current,proposal.index,proposal.direction);if(verified.after!==proposal.after)fail('PROPOSAL_CHANGED');return{markdown:verified.after,selectionStart:verified.selectedStart,undo:{before:current,after:verified.after}}}
export function undoManuscriptMove(current,undo,{allowed=false}={}){if(!allowed)fail('PERMISSION_DENIED');if(typeof undo?.before!=='string'||current!==undo.after)fail('STALE_UNDO');inspectManuscript(undo.before);return undo.before}

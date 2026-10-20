/** View-neutral composition policy. Inputs are host observations, never permission grants. */
export const preferenceSchema=Object.freeze({motion:['system','full','reduce','off'],density:['automatic','comfortable','compact'],effects:['automatic','opaque'],input:['automatic','direct']});
export const defaultPreferences=Object.freeze({motion:'system',density:'automatic',effects:'automatic',input:'automatic'});
export function normalizePreferences(value={}){return Object.fromEntries(Object.entries(preferenceSchema).map(([k,allowed])=>[k,allowed.includes(value[k])?value[k]:defaultPreferences[k]]))}
export function resolveExperience(input={}){
 const p=normalizePreferences(input.preferences),width=Number.isFinite(input.width)?Math.max(0,input.width):0;
 const reduced=p.motion==='reduce'||p.motion==='off'||(p.motion==='system'&&input.systemReduced===true);
 const exact=input.semantic==='playhead'||input.semantic==='waveform'||input.semantic==='source-time';
 const modal=input.modalOpen===true,editing=input.editing===true;
 const blocked=input.access!=='allowed';
 const reasons=[];
 if(blocked)reasons.push('Access is unresolved or denied; presentation cannot grant an action.');
 if(exact)reasons.push('Media position represents exact source time; no spring or easing.');
 if(reduced)reasons.push('Respect the selected motion preference and system reduction.');
 if(modal)reasons.push('One modal owns focus; underlying task shortcuts are suspended.');
 if(editing)reasons.push('Preserve active editing; defer layout proposals until explicit adoption.');
 return Object.freeze({layout:width<600?'single-active-layer':'parallel-context',density:p.density==='automatic'?(input.coarsePointer?'comfortable':'compact'):p.density,transitionMs:reduced||exact?0:200,physics:!reduced&&!exact&&!blocked,opacity:p.effects==='opaque'||input.transparencyAvailable===false?'opaque':'local-surface',keyboardEquivalent:true,dragEnabled:!blocked&&!modal,shortcutScope:modal?'modal':editing?'editor':'task',autoAdoptLayout:false,mayOfferLayout:!editing&&!modal,actionEnabled:!blocked,reasons});
}

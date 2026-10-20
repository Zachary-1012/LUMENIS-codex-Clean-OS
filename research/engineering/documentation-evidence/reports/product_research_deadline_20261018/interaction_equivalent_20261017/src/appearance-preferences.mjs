export const appearanceDefaults=Object.freeze({bg:'#eef0e6',size:14,blur:false});
export function appearancePreferences(input={}){const v=input&&typeof input==='object'?input:{};return{bg:typeof v.bg==='string'&&/^#[0-9a-f]{6}$/i.test(v.bg)?v.bg:appearanceDefaults.bg,size:Number.isFinite(v.size)?Math.max(13,Math.min(18,v.size)):14,blur:v.blur===true}}

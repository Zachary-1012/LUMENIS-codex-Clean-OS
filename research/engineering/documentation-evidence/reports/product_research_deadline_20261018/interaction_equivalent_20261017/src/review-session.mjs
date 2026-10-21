/** Review-only route snapshots, never backend saves. One bounded slot per known route. */
export function createReviewSession(allowedRoutes){const allowed=new Set(allowedRoutes),states=new Map();return Object.freeze({
 read(id){return states.has(id)?structuredClone(states.get(id)):null},
 write(id,value){if(!allowed.has(id))return false;states.set(id,structuredClone(value));return true},
 clear(id){return states.delete(id)}
})}
/** Existing dialog owns focus. A shortcut must not open a second modal. */
export function canOpenDialog(candidate,openDialogs){return !Array.from(openDialogs).some(dialog=>dialog!==candidate&&dialog.open)}

/** View-independent pointer adapter: logical px and milliseconds in, px/s out. */
export const INPUT_VERSION='review-direct-input/1.0.0';
export function beginDrag({pointerId,clientX,clientY,timeMs,objectX,objectY,originX=0,originY=0}){return{pointerId,anchorX:clientX-originX-objectX,anchorY:clientY-originY-objectY,lastX:clientX,lastTime:timeMs,velocity:0,active:true}}
export function moveDrag(state,{pointerId,clientX,clientY,timeMs,originX=0,originY=0,minX=0,maxX=100,minY=0,maxY=100,maxSpeed=1800}){if(!state.active||pointerId!==state.pointerId)return{state,target:null};const dt=Math.max(.008,(timeMs-state.lastTime)/1000);const velocity=Math.max(-maxSpeed,Math.min(maxSpeed,(clientX-state.lastX)/dt));return{state:{...state,lastX:clientX,lastTime:timeMs,velocity},target:{x:Math.max(minX,Math.min(maxX,clientX-originX-state.anchorX)),y:Math.max(minY,Math.min(maxY,clientY-originY-state.anchorY))}}}
export function endDrag(state,timeMs,pointerId=state.pointerId){if(!state.active||pointerId!==state.pointerId)return state;return{...state,active:false,velocity:timeMs-state.lastTime>90?0:state.velocity}}
export function cancelDrag(state){return{...state,active:false,velocity:0}}

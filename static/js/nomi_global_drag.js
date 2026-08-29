/* v5.7.2 Nomi Global Floating Drag Patch
 * Uses Pointer Events + setPointerCapture for mouse/touch/pen continuity.
 * Persists position per browser and keeps the robot inside the viewport.
 */
(function(){
  'use strict';
  const KEY='taikoo_nomi_position_v572';
  const robot=()=>document.getElementById('nomiFloat');
  let drag=null;
  let suppressClickUntil=0;
  function read(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch(e){return null}}
  function clamp(x,y){
    const el=robot(); if(!el) return {x:16,y:16};
    const w=el.offsetWidth||64,h=el.offsetHeight||64;
    const pad=8;
    return {x:Math.max(pad,Math.min(window.innerWidth-w-pad,x)),y:Math.max(pad,Math.min(window.innerHeight-h-pad,y))};
  }
  function setPos(x,y,persist=true){
    const el=robot(); if(!el) return;
    const p=clamp(x,y);
    el.style.left=p.x+'px'; el.style.top=p.y+'px'; el.style.right='auto'; el.style.bottom='auto';
    el.dataset.nomiX=p.x; el.dataset.nomiY=p.y;
    if(persist) try{localStorage.setItem(KEY,JSON.stringify(p))}catch(e){}
  }
  function restore(){
    const p=read(); if(p && Number.isFinite(p.x) && Number.isFinite(p.y)) setPos(p.x,p.y,false);
    else {
      const el=robot(); if(!el) return;
      const x=window.innerWidth-(el.offsetWidth||64)-24;
      const y=window.innerHeight-(el.offsetHeight||64)-24;
      setPos(x,y,false);
    }
  }
  function reset(){localStorage.removeItem(KEY); const el=robot(); if(!el)return; setPos(window.innerWidth-(el.offsetWidth||64)-24,window.innerHeight-(el.offsetHeight||64)-24,false)}
  window.resetNomiPosition=reset;
  function onDown(e){
    const el=robot(); if(!el || e.button>0 && e.pointerType==='mouse') return;
    const r=el.getBoundingClientRect();
    drag={id:e.pointerId,startX:e.clientX,startY:e.clientY,origX:r.left,origY:r.top,moved:false};
    el.classList.add('nomi-dragging');
    try{el.setPointerCapture(e.pointerId)}catch(_){ }
    e.preventDefault();
  }
  function onMove(e){
    if(!drag || e.pointerId!==drag.id) return;
    const dx=e.clientX-drag.startX,dy=e.clientY-drag.startY;
    if(Math.abs(dx)+Math.abs(dy)>5) drag.moved=true;
    if(!drag.moved)return;
    setPos(drag.origX+dx,drag.origY+dy,true);
    e.preventDefault();
  }
  function onUp(e){
    if(!drag || e.pointerId!==drag.id)return;
    const el=robot();
    if(drag.moved){
      suppressClickUntil=Date.now()+350;
      // snap to nearest horizontal edge for a polished desktop/mobile finish
      const r=el.getBoundingClientRect();
      const targetX=(r.left+r.width/2<window.innerWidth/2)?8:window.innerWidth-r.width-8;
      setPos(targetX,r.top,true);
    }
    el && el.classList.remove('nomi-dragging');
    try{if(el.hasPointerCapture(e.pointerId))el.releasePointerCapture(e.pointerId)}catch(_){ }
    drag=null;
  }
  function bind(){
    const el=robot(); if(!el)return;
    el.setAttribute('role','button'); el.setAttribute('aria-label','拖拽诺米助手；点击打开聊天'); el.setAttribute('tabindex','0');
    el.addEventListener('pointerdown',onDown,{passive:false});
    el.addEventListener('pointermove',onMove,{passive:false});
    el.addEventListener('pointerup',onUp,{passive:false});
    el.addEventListener('pointercancel',onUp,{passive:false});
    el.addEventListener('click',function(e){if(Date.now()<suppressClickUntil){e.preventDefault();e.stopImmediatePropagation()}},true);
    el.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();if(window.toggleNomiChat)window.toggleNomiChat()}});
    el.addEventListener('contextmenu',e=>e.preventDefault());
    window.addEventListener('resize',()=>{const p=read(); if(p)setPos(p.x,p.y,false)});
    restore();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
})();

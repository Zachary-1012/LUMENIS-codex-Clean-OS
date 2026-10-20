import {initialWordEdit,wordEditReduce,renderWordAudio,wordSeekSample} from './word-edit.mjs';
import {makeSignal,encodeWav} from './audio-signal.mjs';

export const wordStudy=['wordedit','32','TEXT CORRECTION ≠ MEDIA CUT','改文字，还是剪掉这一段','同一份校对稿，两种不同动作。修改文字不改变声音；剪切提议经过确认才删除实际采样，可撤销。','规划§14 E2/P7、草图独立视频/播客§3.2/3.3。时间对齐为人工测试夹具，声音为测试音，非ASR/真实转写；产品需绑定原Timeline与素材时基。',[]];

export function createWordEdit({stage,button,status,reduce,onDispose,listen}) {
 const original=makeSignal(),rate=8000,localCleanups=[];
 let s=initialWordEdit(['开始','观察','比较','完成'].map((text,i)=>({id:'w'+i,text,start:i*8000,end:(i+1)*8000}))),url=null,showOriginal=false,animation=null,disposed=false;
 stage.innerHTML='<section class="lab-scroll"><p>人工时序夹具：每词对应1秒测试音，不代表识别到这些语音。</p><audio id="wordAudio" controls></audio><p id="wordPlayback" role="status">正在载入本地测试音</p><div id="wordTokens" class="actions"></div><label>所选词的校对文字<input id="wordCorrection" maxlength="120"></label><p id="wordDuration"></p><p id="wordProposal" role="status"></p></section>';
 const q=x=>stage.querySelector(x),player=q('#wordAudio');player.volume=.15;
 player.onloadstart=()=>{if(!disposed)q('#wordPlayback').textContent='正在载入本地音频字节；编辑已保留'};
 player.oncanplay=()=>{if(!disposed)q('#wordPlayback').textContent='浏览器已可播放当前本地测试音'};
 player.onerror=()=>{if(!disposed)q('#wordPlayback').textContent='浏览器当前无法播放；稿件与采样编辑保留，可撤销后重试'};

 function bind(target,event,handler) {
  if(listen)listen(target,event,handler);else target.addEventListener(event,handler);
  localCleanups.push(()=>target.removeEventListener(event,handler));
 }
 function cancelAnimation() {
  const current=animation;animation=null;
  if(current){current.onfinish=current.oncancel=null;current.cancel()}
 }
 function emphasize() {
  cancelAnimation();
  const tokens=q('#wordTokens');
  if(disposed||reduce()||document.hidden||typeof tokens?.animate!=='function')return;
  // This effect only locates the adopted edit; sample/version changes are already done.
  try {
   const current=tokens.animate([{opacity:.5},{opacity:1}],{duration:150});
   animation=current;
   current.onfinish=current.oncancel=()=>{
    if(animation!==current)return;
    animation=null;current.onfinish=current.oncancel=null;
   };
  } catch {cancelAnimation()}
 }
 function load() {
  player.pause();if(url)URL.revokeObjectURL(url);
  const a=renderWordAudio(original,s.words);
  if(a.length){url=URL.createObjectURL(new Blob([encodeWav(a,rate)],{type:'audio/wav'}));player.src=url}
  else{url=null;player.removeAttribute('src')}
  player.load();q('#wordDuration').textContent=`本地修订v${s.revision} · 当前${(a.length/rate).toFixed(3)}秒；原件4秒`;
 }
 function draw(reload=false) {
  if(disposed)return;
  cancelAnimation();q('#wordTokens').replaceChildren();
  for(const w of s.words) {
   const b=document.createElement('button');b.textContent=`${(showOriginal?w.originalText:w.text)||'空白校对'} ${w.start/rate}–${w.end/rate}s${w.removed?'（已剪）':''}`;b.dataset.word=w.id;b.setAttribute('aria-pressed',String(w.id===s.selected));
   b.onclick=()=>{if(disposed)return;s=wordEditReduce(s,{type:'select',id:w.id});draw();q(`[data-word="${w.id}"]`)?.focus()};q('#wordTokens').append(b);
  }
  q('#wordCorrection').value=s.words.find(w=>w.id===s.selected)?.text||'';
  q('#wordProposal').textContent=s.proposal?`待剪切：${s.words.find(w=>w.id===s.proposal.id).text}；基线v${s.proposal.base}`:'没有待采纳剪切';
  if(reload)load();
  q('#wordDuration').textContent=`本地修订v${s.revision} · 当前${(renderWordAudio(original,s.words).length/rate).toFixed(3)}秒；原件4秒`;status(s.notice||'先选一段，再决定只改文字或剪切。');
 }
 function send(e,reload=false) {
  if(disposed)return;
  if(e.type!=='select'&&e.type!=='propose-cut'&&e.type!=='reject')player.pause();
  s=wordEditReduce(s,e);draw(reload);
 }
 button('只修改校对文字',()=>{if(!disposed)send({type:'correct',text:q('#wordCorrection').value},false)});
 button('预览删词剪切',()=>send({type:'propose-cut'}));
 button('采纳剪切',()=>{if(disposed)return;const before=s.revision;send({type:'adopt'},true);if(before!==s.revision)emphasize()},true);
 button('保留音频',()=>send({type:'reject'}));
 button('撤销上次编辑',()=>send({type:'undo'},true));
 button('原文 / 校对切换',()=>{if(disposed)return;showOriginal=!showOriginal;draw();status(showOriginal?'查看不可变原文；校对稿仍保留':'查看当前校对稿；原音频不因改字改变')});
 button('定位所选词',()=>{
  if(disposed)return;
  const sample=wordSeekSample(s.words,s.selected);
  if(sample===null){status('先选择仍保留在当前音频中的词');return}
  player.pause();player.currentTime=sample/rate;status('已精确定位当前音频 '+(sample/rate).toFixed(3)+' 秒，不自动播放');
 });
 button('停止试听',()=>{if(disposed)return;player.pause();status('已停止当前测试音')});
 bind(window,'review-motion-change',cancelAnimation);
 bind(document,'visibilitychange',()=>{if(document.hidden)cancelAnimation()});
 onDispose(()=>{
  if(disposed)return;
  disposed=true;cancelAnimation();for(const cleanup of localCleanups)cleanup();
  player.onloadstart=player.oncanplay=player.onerror=null;player.pause();player.removeAttribute('src');player.load();if(url)URL.revokeObjectURL(url);url=null;
 });
 draw(true);
}

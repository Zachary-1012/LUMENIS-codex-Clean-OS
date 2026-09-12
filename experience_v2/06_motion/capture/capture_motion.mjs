// Record real interaction motion clips (M-source demos) on the live prototype.
import { chromium } from 'playwright';import { pathToFileURL } from 'node:url';import path from 'node:path';import fs from 'node:fs';
const ROOT='D:/LUMENIS_REBUILD/LUMENIS-codex-Clean-OS/experience_v2/10_prototype';
const OUT='D:/LUMENIS_REBUILD/LUMENIS-codex-Clean-OS/experience_v2/06_motion';
for(const d of ['capture/webm','mp4','gif','reduced-motion'])fs.mkdirSync(path.join(OUT,d),{recursive:true});
const URL=id=>pathToFileURL(path.join(ROOT,'index.html')).href+'#/'+id;
async function newPage(b,theme,reduced){const ctx=await b.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1.5,
  reducedMotion:reduced?'reduce':'no-preference',recordVideo:{dir:path.join(OUT,'capture/webm'),size:{width:1440,height:900}}});
 const p=await ctx.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
 await p.addInitScript(t=>{try{localStorage.setItem('lum-theme',t);sessionStorage.setItem('lum-launched','1')}catch(e){}},theme);
 return {ctx,p,errs};}
async function goto(p,id){await p.goto(URL(id),{waitUntil:'load'});
 await p.evaluate(t=>{document.documentElement.classList.add('lum-capture');const a=document.querySelector('.lum-app');if(a)a.dataset.theme=t;},'light');
 await p.waitForTimeout(900);await p.evaluate(async()=>{if(document.fonts&&document.fonts.ready)await document.fonts.ready;});await p.waitForTimeout(200);}
async function finish(ctx,b,name){const p=ctx.pages()[0];await p.close();await ctx.close();
 const dir=path.join(OUT,'capture/webm');let nw=null;for(const f of fs.readdirSync(dir)){if(f.endsWith('.webm')){const fp=path.join(dir,f);if(!nw||fs.statSync(fp).mtimeMs>fs.statSync(nw).mtimeMs)nw=fp;}}
 const target=path.join(dir,name+'.webm');if(fs.existsSync(target))fs.unlinkSync(target);fs.renameSync(nw,target);return target;}
const b=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,
 args:['--allow-file-access-from-files','--force-color-profile=srgb','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
// M04 page enter + M01 send press on AI-01
{const {ctx,p}=await newPage(b,'light');await goto(p,'AI-01');
 await p.waitForTimeout(700);
 const ta=await p.$('.lum-composer textarea, .lum-composer input, textarea');if(ta){await ta.click();await ta.fill('对比近30天三个主体的声量趋势并给出证据');await p.waitForTimeout(300);}
 const send=await p.$('.lum-composer .lum-btn--primary, .lum-btn--primary');if(send){await p.mouse.move(720,450);await send.hover();await p.waitForTimeout(150);await p.mouse.down();await p.waitForTimeout(120);await p.mouse.up();await p.waitForTimeout(900);}
 await p.waitForTimeout(800);await finish(ctx,b,'M01-M04_ai-composer-enter-press');}
// M03 tab shift on CTH-08
{const {ctx,p}=await newPage(b,'light');await goto(p,'CTH-08');
 const tabs=await p.$$('.lum-tabs button');for(let i=0;i<Math.min(tabs.length,3);i++){await tabs[i].click();await p.waitForTimeout(420);}
 await p.waitForTimeout(500);await finish(ctx,b,'M03_tab-shift');}
// M06 modal-in + M08 toast on AI-02 (EFFECT action -> confirm modal -> confirm -> toast)
{const {ctx,p}=await newPage(b,'light');await goto(p,'AI-02');
 const item=await p.$('.lum-action-item[data-act-class="EFFECT"], .lum-action-item');if(item){await item.click();await p.waitForTimeout(700);
  const ok=await p.$('.lum-modal .lum-btn--primary, .lum-modal__foot .lum-btn');if(ok){await ok.click();await p.waitForTimeout(900);}}
 await p.waitForTimeout(600);await finish(ctx,b,'M06-M08_modal-toast');}
// M12 orb flow idle (AI-01 dock)
{const {ctx,p}=await newPage(b,'light');await goto(p,'AI-01');
 const orb=await p.$('canvas.lum-orb');if(orb)await p.evaluate(()=>{if(window.LumOrb)window.LumOrb.setStatus('processing');});await p.waitForTimeout(2200);
 if(orb)await p.evaluate(()=>{if(window.LumOrb)window.LumOrb.setStatus('done');});await p.waitForTimeout(900);
 await finish(ctx,b,'M12_orb-flow');}
// reduced-motion composite: tab + enter
{const {ctx,p}=await newPage(b,'light',true);await goto(p,'AI-01');await p.waitForTimeout(500);
 const t=await p.$$('.lum-tabs button');if(t[1]){await t[1].click();await p.waitForTimeout(300);}
 await finish(ctx,b,'reduced-motion_composite');}
await b.close();console.log('MOTION CAPTURE DONE');

# -*- coding: utf-8 -*-
"""Capture 44 screens across 8 viewports + dark(1440) + state boards; structural
regression (missing-key markers, horizontal overflow, 130% text on critical)."""
import os, sys, json
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", r"D:\lum-toolchain\pw-browser")
sys.path.insert(0, r"D:\lum-toolchain\pylibs")
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.abspath(__file__)); EV=os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE,"src")); import screens_meta as SM
IDS=SM.SCREEN_IDS
SR=os.path.join(EV,"07_screens").replace("\\","/"); SHOTS=os.path.join(EV,"14_visual_regression","shots")
SB=os.path.join(EV,"14_visual_regression","stateboards"); PV=os.path.join(EV,"19_previews")
for d in (SHOTS,SB,PV): os.makedirs(d,exist_ok=True)
def furl(p): return "file:///"+p.replace("\\","/")
VPS=[("1920",1920,1080),("1440",1440,900),("1280",1280,800),("1024",1024,768),
     ("768",768,1024),("430",430,932),("390",390,844),("360",360,800)]
MASTERS={"1440","1024","390"}
CRITICAL=["AI-01","CTH-01","SH-01","AI-02","CTH-09","BMP-01"]
# Guarded: at document-start documentElement may still be null; defer until it exists.
CAP_INIT=("(function(){function a(){if(document.documentElement)"
          "document.documentElement.classList.add('lum-capture');}"
          "if(document.documentElement)a();else document.addEventListener('DOMContentLoaded',a);})();")
report={"viewports":[v[0] for v in VPS],"screens":{},"critical_130":{}}
errors=[]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--allow-file-access-from-files"])
    ctx=b.new_context(viewport={"width":1440,"height":900},device_scale_factor=1,reduced_motion="reduce")
    ctx.add_init_script(CAP_INIT)
    pg=ctx.new_page()
    for vname,w,h in VPS:
        pg.set_viewport_size({"width":w,"height":h})
        for sid in IDS:
            url=furl(f"{SR}/{sid}/{sid}.html"); pg.goto(url); pg.wait_for_timeout(160)
            pg.evaluate("document.documentElement.classList.add('lum-capture')")
            m=pg.evaluate("""()=>{const p=document.querySelector('#lum-page');
              const txt=p?p.innerHTML:'';
              return {ready:document.body.getAttribute('data-lum-ready'),
                bytes:txt.length,
                missing:(txt.match(/⟦[^⟧]+⟧/g)||[]).length,
                overflow:document.documentElement.scrollWidth-window.innerWidth,
                pageH:p?p.scrollHeight:0};}""")
            od=os.path.join(SHOTS,sid); os.makedirs(od,exist_ok=True)
            ext="png" if vname in MASTERS else "jpeg"
            pg.screenshot(path=os.path.join(od,f"{vname}.{ext}"), full_page=(w>=1024))
            rec={"ready":m["ready"],"bytes":m["bytes"],"missing_markers":m["missing"],
                 "h_overflow_px":m["overflow"],"page_h":m["pageH"]}
            report["screens"].setdefault(sid,{})[vname]=rec
            if m["ready"]!="true" or m["missing"] or m["overflow"]>2:
                errors.append((sid,vname,rec))
        print("viewport",vname,"done")
    # dark at 1440
    pg.set_viewport_size({"width":1440,"height":900})
    ctx2=b.new_context(viewport={"width":1440,"height":900},device_scale_factor=1,reduced_motion="reduce")
    ctx2.add_init_script(CAP_INIT)
    dpg=ctx2.new_page(); dpg.add_init_script("localStorage.setItem('lum-theme','dark');")
    for sid in IDS:
        dpg.goto(furl(f"{SR}/{sid}/{sid}.html")); dpg.wait_for_timeout(140)
        dpg.evaluate("document.documentElement.classList.add('lum-capture')")
        od=os.path.join(SHOTS,sid); os.makedirs(od,exist_ok=True)
        dpg.screenshot(path=os.path.join(od,"1440-dark.jpeg"))
    ctx2.close()
    # state boards at 1440
    pg.set_viewport_size({"width":1440,"height":900})
    for sid in IDS:
        pg.goto(furl(f"{SR}/{sid}/{sid}.state-board.html")); pg.wait_for_timeout(120)
        pg.evaluate("document.documentElement.classList.add('lum-capture')")
        cells=pg.evaluate("document.querySelectorAll('.lum-statecell').length")
        pg.screenshot(path=os.path.join(SB,f"{sid}.jpeg"), full_page=True)
        report["screens"].setdefault(sid,{})["state_cells"]=cells
    # critical 130% text overflow
    pg.set_viewport_size({"width":1440,"height":900})
    for sid in CRITICAL:
        pg.goto(furl(f"{SR}/{sid}/{sid}.html")); pg.wait_for_timeout(120)
        pg.evaluate("document.body.style.zoom='1.3'"); pg.wait_for_timeout(120)
        ov=pg.evaluate("document.documentElement.scrollWidth-window.innerWidth")
        report["critical_130"][sid]={"h_overflow_px":ov}
        pg.evaluate("document.body.style.zoom=''")
        if ov>2: errors.append((sid,"130%",ov))
    b.close()
report["errors"]=errors
with open(os.path.join(EV,"14_visual_regression","regression_report.json"),"w",encoding="utf-8",newline="\n") as f:
    json.dump(report,f,ensure_ascii=False,indent=2)
print("CAPTURE DONE screens",len(IDS),"errors",len(errors))
for e in errors[:30]: print("  ERR",e)

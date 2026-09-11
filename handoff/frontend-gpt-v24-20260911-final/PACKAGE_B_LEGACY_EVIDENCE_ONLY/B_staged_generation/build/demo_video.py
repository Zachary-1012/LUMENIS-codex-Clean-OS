# -*- coding: utf-8 -*-
"""Record a real interactive tour (motion ON); QA bar hidden; locale/optical driven by runtime API;
mobile uses real horizontal step-chain scroll (no accidental drawer). Outputs mp4/gif/contact-sheet."""
import os,sys,subprocess,glob,shutil
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", r"D:\lum-toolchain\pw-browser")
sys.path.insert(0, r"D:\lum-toolchain\pylibs")
from playwright.sync_api import sync_playwright
EV=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PV=os.path.join(EV,"19_previews"); REC=os.path.join(PV,"_rec"); os.makedirs(REC,exist_ok=True)
IDX="file:///"+os.path.join(EV,"10_prototype","index.html").replace("\\","/")
FF=r"D:\lum-toolchain\ffmpeg\bin\ffmpeg.exe"

def go(pg,h): pg.evaluate(f"location.hash='#/{h}'"); pg.wait_for_timeout(1100)
def loc(pg,l): pg.evaluate(f"window.LumI18n.setLocale('{l}')"); pg.wait_for_timeout(950)
def opt(pg,o): pg.evaluate(f"document.querySelector('.lum-app').dataset.optical='{o}'"); pg.wait_for_timeout(850)

def record(viewport,name,script):
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,args=["--allow-file-access-from-files","--autoplay-policy=no-user-gesture-required"])
        ctx=b.new_context(viewport=viewport,device_scale_factor=1,record_video_dir=REC,record_video_size=viewport)
        ctx.add_init_script("document.documentElement.classList.add('lum-capture')")  # QA hidden from first paint
        pg=ctx.new_page(); pg.goto(IDX); pg.wait_for_timeout(1400)
        pg.evaluate("document.documentElement.classList.add('lum-capture')")  # belt-and-suspenders
        script(pg)
        ctx.close(); b.close()
    vids=sorted(glob.glob(os.path.join(REC,"*.webm")),key=os.path.getmtime)
    dst=os.path.join(REC,name+".webm"); shutil.move(vids[-1],dst); return dst

def desktop(pg):
    pg.evaluate("document.querySelector('.lum-composer__input,textarea')?.focus()"); pg.wait_for_timeout(500)
    ta=pg.query_selector("textarea")
    if ta: ta.type("分析太古汇本周客流与负面声量，给出可执行处置并标注证据",delay=16); pg.wait_for_timeout(900)
    go(pg,"CTH-01")
    for y in (320,320,300): pg.mouse.wheel(0,y); pg.wait_for_timeout(650)
    pg.mouse.wheel(0,-900); pg.wait_for_timeout(700)
    opt(pg,"soft"); opt(pg,"opaque"); opt(pg,"high")
    go(pg,"SH-01")
    for t in ("素材 Assets","成片 Artifacts","创作 Create"):
        try: pg.get_by_text(t,exact=True).first.click(); pg.wait_for_timeout(850)
        except Exception: pass
    pg.mouse.wheel(0,500); pg.wait_for_timeout(700); pg.mouse.wheel(0,-500); pg.wait_for_timeout(500)
    loc(pg,"en"); loc(pg,"ko"); loc(pg,"zh-CN")
    btns=pg.query_selector_all(".lum-topbar__tools .lum-iconbtn, .lum-iconbtn")
    if len(btns)>=2: btns[1].click(); pg.wait_for_timeout(1100); btns[1].click(); pg.wait_for_timeout(800)

def mobile(pg):
    go(pg,"AI-01"); pg.wait_for_timeout(500)
    go(pg,"CTH-01"); pg.mouse.wheel(0,420); pg.wait_for_timeout(850)
    go(pg,"SH-01"); pg.wait_for_timeout(500)
    # real horizontal scroll of the 10-step chain (no tap -> no accidental drawer)
    pg.evaluate("var s=document.querySelector('.lum-steps');if(s)s.scrollBy({left:260,behavior:'smooth'})"); pg.wait_for_timeout(1000)
    pg.mouse.wheel(0,520); pg.wait_for_timeout(850)
    loc(pg,"en"); loc(pg,"zh-CN")

d=record({"width":1600,"height":900},"desktop",desktop)
m=record({"width":390,"height":844},"mobile",mobile)
print("raw",d,m)

dn=os.path.join(REC,"d.mp4"); mn=os.path.join(REC,"m.mp4")
subprocess.run([FF,"-y","-i",d,"-vf","scale=1600:900:force_original_aspect_ratio=decrease,pad=1600:900:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30","-c:v","libx264","-pix_fmt","yuv420p",dn],check=True)
# mobile: blurred cover backdrop + crisp phone foreground
vf=("[0:v]split=2[base][src];"
    "[base]scale=1600:900:force_original_aspect_ratio=increase,crop=1600:900,boxblur=24:2,eq=brightness=-0.12[bg];"
    "[src]scale=-2:900,setsar=1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30[out]")
subprocess.run([FF,"-y","-i",m,"-filter_complex",vf,"-map","[out]","-c:v","libx264","-pix_fmt","yuv420p",mn],check=True)
listf=os.path.join(REC,"list.txt"); open(listf,"w").write(f"file '{dn}'\nfile '{mn}'\n")
out=os.path.join(PV,"experience-overview.mp4")
subprocess.run([FF,"-y","-f","concat","-safe","0","-i",listf,"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",out],check=True)
gif=os.path.join(PV,"experience-overview.gif")
subprocess.run([FF,"-y","-t","14","-i",dn,"-vf","fps=12,scale=800:-2:flags=lanczos","-loop","0",gif],check=True)
cs=os.path.join(PV,"experience-contact-sheet.jpg")
subprocess.run([FF,"-y","-i",out,"-vf","fps=1/3,scale=480:-2,tile=4x3:padding=6:color=white","-frames:v","1","-update","1",cs],check=True)
print("DEMO DONE",out)

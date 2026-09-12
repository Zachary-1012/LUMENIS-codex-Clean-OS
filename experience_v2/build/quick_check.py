# -*- coding: utf-8 -*-
import os,sys
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", r"D:\lum-toolchain\pw-browser")
sys.path.insert(0, r"D:\lum-toolchain\pylibs")
from playwright.sync_api import sync_playwright
EV=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tgt=sys.argv[1] if len(sys.argv)>1 else "SH-01"; w=int(sys.argv[2]) if len(sys.argv)>2 else 390
url="file:///"+os.path.join(EV,"07_screens",tgt,f"{tgt}.html").replace("\\","/")
out=os.path.join(EV,"19_previews",f"_quick_{tgt}_{w}.png")
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--allow-file-access-from-files"])
    c=b.new_context(viewport={"width":w,"height":844},reduced_motion="reduce"); pg=c.new_page()
    pg.goto(url); pg.wait_for_timeout(300)
    ov=pg.evaluate("document.documentElement.scrollWidth-window.innerWidth")
    pg.screenshot(path=out,full_page=True); print("overflow",ov,"->",out); b.close()

# -*- coding: utf-8 -*-
"""Headless smoke: load SPA + key standalone pages, capture console/page errors,
assert #lum-page rendered non-empty. No network needed (file://)."""
import os, sys
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", r"D:\lum-toolchain\pw-browser")
sys.path.insert(0, r"D:\lum-toolchain\pylibs")
from playwright.sync_api import sync_playwright

EV = os.path.dirname(os.path.abspath(__file__)); EV = os.path.dirname(EV)
PROTO = os.path.join(EV, "10_prototype").replace("\\", "/")
SR = os.path.join(EV, "07_screens").replace("\\", "/")

def furl(p): return "file:///" + p.replace("\\", "/")

targets = [
    ("SPA-AI01", furl(PROTO + "/index.html")),
    ("ACC-01", furl(SR + "/ACC-01/ACC-01.html")),
    ("CTH-01", furl(SR + "/CTH-01/CTH-01.html")),
    ("CTH-05", furl(SR + "/CTH-05/CTH-05.html")),
    ("SH-01", furl(SR + "/SH-01/SH-01.html")),
    ("AI-01", furl(SR + "/AI-01/AI-01.html")),
    ("SH-01-state", furl(SR + "/SH-01/SH-01.state-board.html")),
]
os.makedirs(os.path.join(EV, "19_previews"), exist_ok=True)
problems = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("console", lambda m: problems.append(("console:" + m.type, m.text)) if m.type in ("error",) else None)
    pg.on("pageerror", lambda e: problems.append(("pageerror", str(e))))
    for name, url in targets:
        pg.goto(url); pg.wait_for_timeout(450)
        ready = pg.evaluate("document.body.getAttribute('data-lum-ready')")
        html_len = pg.evaluate("(document.querySelector('#lum-page')||{innerHTML:''}).innerHTML.length")
        missing = pg.evaluate("(window.LumI18n&&LumI18n.state&&LumI18n.state.missing)?LumI18n.state.missing.length:-1")
        cal = pg.evaluate("document.querySelectorAll('#cal-grid .lum-cal-cell').length")
        statecells = pg.evaluate("document.querySelectorAll('.lum-statecell').length")
        chrome = pg.evaluate("(document.querySelector('.lum-shell')||{}).getAttribute?document.querySelector('.lum-shell').getAttribute('data-chrome'):'NA'")
        print(f"{name:14s} ready={ready} pageBytes={html_len:6d} missingKeys={missing} calCells={cal} stateCells={statecells} chrome={chrome}")
        if not html_len or html_len < 200: problems.append((name, "page nearly empty"))
        if name in ("CTH-05",) and cal == 0: problems.append((name, "calendar not filled"))
        if name.endswith("state") and statecells == 0: problems.append((name, "state board empty"))
    # locale switch smoke on SH-01
    pg.goto(furl(SR + "/SH-01/SH-01.html")); pg.wait_for_timeout(300)
    pg.evaluate("LumI18n.setLocale('en')"); pg.wait_for_timeout(150)
    en_missing = pg.evaluate("(LumI18n.state.missing||[]).length")
    pg.evaluate("LumI18n.setLocale('ko')"); pg.wait_for_timeout(150)
    ko_missing = pg.evaluate("(LumI18n.state.missing||[]).length")
    print(f"locale-switch en missing={en_missing} ko missing={ko_missing}")
    pg.screenshot(path=os.path.join(EV, "19_previews", "_smoke_SH01_en.png"))
    b.close()

print("PROBLEMS:", len(problems))
for x in problems[:40]: print("  ", x)
sys.exit(1 if problems else 0)

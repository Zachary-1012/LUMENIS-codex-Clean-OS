# -*- coding: utf-8 -*-
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screens_meta as M
mods = ["spec_account","spec_cth","spec_bmp","spec_ai","spec_sys","spec_shared"]
allsp={}
for m in mods:
    mod=__import__(m); allsp.update(mod.SPECS); print(m, len(mod.SPECS))
ids=M.SCREEN_IDS
missing=[i for i in ids if i not in allsp]
extra=[i for i in allsp if i not in ids]
print("TOTAL specs:", len(allsp), "meta:", len(ids))
print("MISSING:", missing); print("EXTRA:", extra)
# section type coverage + counts
from collections import Counter
c=Counter(); secs=0; empty=[]
for i in ids:
    ss=allsp[i].get("sections",[])
    if not ss: empty.append(i)
    secs+=len(ss)
    for s in ss: c[s.get("type")]+=1
print("EMPTY screens:", empty, "total sections:", secs)
print("section types:", dict(c))
# every screen needs titleKey + viewmodel + binding
for i in ids:
    sp=allsp[i]
    for k in ("titleKey","viewmodel","binding"):
        if k not in sp: print("!!",i,"missing",k)
print("OK" if not missing and not extra and not empty and len(allsp)==44 else "PROBLEM")

# -*- coding: utf-8 -*-
"""Tile the 44 master (1440) screenshots into labeled contact sheets (phone-viewable)."""
import os,sys
sys.path.insert(0,r"D:\lum-toolchain\pylibs")
from PIL import Image,ImageDraw,ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); EV=os.path.dirname(HERE)
sys.path.insert(0,os.path.join(HERE,"src")); import screens_meta as SM
SH=os.path.join(EV,"14_visual_regression","shots"); OUT=os.path.join(EV,"19_previews"); os.makedirs(OUT,exist_ok=True)
def font(sz):
    for p in (r"C:\Windows\Fonts\msyh.ttc",r"C:\Windows\Fonts\segoeui.ttf"):
        if os.path.exists(p):
            try:return ImageFont.truetype(p,sz)
            except Exception:pass
    return ImageFont.load_default()
COLS=4; TW,TH=380,238; PAD=10; LAB=26; PER=8
def sheet(ids,idx):
    rows=(len(ids)+COLS-1)//COLS
    W=COLS*(TW+PAD)+PAD; H=rows*(TH+LAB+PAD)+PAD
    canvas=Image.new("RGB",(W,H),"white"); d=ImageDraw.Draw(canvas); f=font(15)
    for i,sid in enumerate(ids):
        r,c=divmod(i,COLS); x=PAD+c*(TW+PAD); y=PAD+r*(TH+LAB+PAD)
        ip=os.path.join(SH,sid,"1440.png")
        tile=Image.new("RGB",(TW,TH),(245,247,251))
        if os.path.exists(ip):
            im=Image.open(ip).convert("RGB"); sc=min(TW/im.width,TH/im.height)
            im=im.resize((int(im.width*sc),int(im.height*sc)))
            tile.paste(im,((TW-im.width)//2,(TH-im.height)//2))
        canvas.paste(tile,(x,y+LAB)); d.rectangle([x,y,x+TW,y+LAB-2],fill=(20,26,35))
        zh=SM.META[sid].get("zh",""); d.text((x+6,y+5),f"{sid}  {zh}",font=f,fill=(255,255,255))
    fp=os.path.join(OUT,f"experience-all-screens-{idx}.jpg"); canvas.save(fp,quality=86); print(fp)
ids=SM.SCREEN_IDS
for k in range(0,len(ids),PER):
    sheet(ids[k:k+PER],k//PER+1)
print("OVERVIEW SHEETS DONE",len(ids))

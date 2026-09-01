# -*- coding: utf-8 -*-
import glob, os
from PIL import Image, ImageDraw, ImageFont
BASE = r"D:\Taikoo-staging-ui\docs\reference\ui-research\analysis-0901-gpt"
FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 24)
JOBS = [("transE", 102.0, 6, 7), ("transF", 119.8, 6, 7)]
W, PAD, LABEL = 210, 10, 30
for name, start, fps, COLS in JOBS:
    frames = sorted(glob.glob(os.path.join(BASE, name, "*.jpg")))
    fh = int(W * 2622 / 1206); rows = (len(frames)+COLS-1)//COLS
    sw = COLS*W+(COLS+1)*PAD; sh = rows*(fh+LABEL)+(rows+1)*PAD
    canvas = Image.new("RGB",(sw,sh),"#e9e7e3"); d=ImageDraw.Draw(canvas)
    for i,fp in enumerate(frames):
        r,c=divmod(i,COLS); x=PAD+c*(W+PAD); y=PAD+r*(fh+LABEL+PAD)
        canvas.paste(Image.open(fp).convert("RGB").resize((W,fh)),(x,y))
        t=start+i/fps
        d.rectangle([x,y+fh,x+W,y+fh+LABEL],fill="#1c1917")
        d.text((x+8,y+fh+4),f"{t:0.2f}s",font=FONT,fill="#fafaf9")
    out=os.path.join(BASE,f"{name}_sheet.jpg"); canvas.save(out,quality=82)
    print("saved",out,canvas.size,len(frames))

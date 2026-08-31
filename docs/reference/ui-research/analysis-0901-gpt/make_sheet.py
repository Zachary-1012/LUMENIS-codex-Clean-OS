# -*- coding: utf-8 -*-
import glob, os
from PIL import Image, ImageDraw, ImageFont

BASE = r"D:\Taikoo-staging-ui\docs\reference\ui-research\analysis-0901-gpt"
frames = sorted(glob.glob(os.path.join(BASE, "frames3s", "f_*.jpg")))
try:
    FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 28)
except Exception:
    FONT = ImageFont.load_default()

W = 300
COLS, ROWS, PER = 3, 4, 12
PAD, LABEL = 16, 40
fw, fh = W, int(W * 2622 / 1206)  # 保持竖屏比例
sheet_w = COLS * W + (COLS + 1) * PAD
sheet_h = ROWS * (fh + LABEL) + (ROWS + 1) * PAD

nsheet = (len(frames) + PER - 1) // PER
for s in range(nsheet):
    chunk = frames[s * PER:(s + 1) * PER]
    canvas = Image.new("RGB", (sheet_w, sheet_h), "#f2f1ef")
    d = ImageDraw.Draw(canvas)
    for i, fp in enumerate(chunk):
        r, c = divmod(i, COLS)
        x = PAD + c * (W + PAD)
        y = PAD + r * (fh + LABEL + PAD)
        im = Image.open(fp).convert("RGB")
        if im.width != W:
            im = im.resize((W, fh))
        canvas.paste(im, (x, y))
        idx = s * PER + i + 1
        t = (idx - 1) * 3
        mm, ss = t // 60, t % 60
        d.rectangle([x, y + fh, x + W, y + fh + LABEL], fill="#1c1917")
        d.text((x + 10, y + fh + 6), f"#{idx:02d}  {mm}:{ss:02d}", font=FONT, fill="#fafaf9")
    out = os.path.join(BASE, f"sheet_{s+1}.jpg")
    canvas.save(out, quality=80)
    print("saved", out, canvas.size)
print("total frames", len(frames))

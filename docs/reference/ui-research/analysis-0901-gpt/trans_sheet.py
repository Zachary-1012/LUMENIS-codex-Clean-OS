# -*- coding: utf-8 -*-
import glob, os
from PIL import Image, ImageDraw, ImageFont

BASE = r"D:\Taikoo-staging-ui\docs\reference\ui-research\analysis-0901-gpt"
try:
    FONT = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 24)
except Exception:
    FONT = ImageFont.load_default()

# 目录, 起始秒, 帧率, 列数
JOBS = [("transA", 1.0, 5, 7), ("transB", 23.4, 5, 7),
        ("transC", 90.6, 4, 5), ("transD", 99.0, 5, 7)]
W, PAD, LABEL = 210, 10, 30

for name, start, fps, COLS in JOBS:
    frames = sorted(glob.glob(os.path.join(BASE, name, "*.jpg")))
    if not frames:
        continue
    fh = int(W * 2622 / 1206)
    rows = (len(frames) + COLS - 1) // COLS
    sw = COLS * W + (COLS + 1) * PAD
    sh = rows * (fh + LABEL) + (rows + 1) * PAD
    canvas = Image.new("RGB", (sw, sh), "#e9e7e3")
    d = ImageDraw.Draw(canvas)
    for i, fp in enumerate(frames):
        r, c = divmod(i, COLS)
        x = PAD + c * (W + PAD); y = PAD + r * (fh + LABEL + PAD)
        im = Image.open(fp).convert("RGB").resize((W, fh))
        canvas.paste(im, (x, y))
        t = start + i / fps
        d.rectangle([x, y + fh, x + W, y + fh + LABEL], fill="#1c1917")
        d.text((x + 8, y + fh + 4), f"{t:0.1f}s", font=FONT, fill="#fafaf9")
    out = os.path.join(BASE, f"{name}_sheet.jpg")
    canvas.save(out, quality=82)
    print("saved", out, canvas.size, len(frames))

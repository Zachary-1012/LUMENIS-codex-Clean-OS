import zipfile, re, os, sys
files = [
 r"D:\wps云空间\WPS Cloud\WPSDrive\280397037\WPS云盘\序境LUMENIS线上仓库源码级审计报告.docx",
 r"D:\wps云空间\WPS Cloud\WPSDrive\280397037\WPS云盘\ZBC 线上仓库源码级全域精细.docx",
]
outdir = r"D:\Taikoo-monitor-new\audit"
os.makedirs(outdir, exist_ok=True)
for i, f in enumerate(files, 1):
    name = os.path.basename(f)
    print(f"\n===== FILE {i}: {name} =====")
    try:
        with zipfile.ZipFile(f) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception as e:
        print("OPEN FAIL:", e); continue
    # 段落
    paras = re.split(r"</w:p>", xml)
    lines = []
    for p in paras:
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)
        line = "".join(texts)
        line = re.sub(r"&amp;", "&", line)
        line = re.sub(r"&lt;", "<", line); line = re.sub(r"&gt;", ">", line)
        if line.strip():
            lines.append(line.strip())
    out = os.path.join(outdir, f"online_audit_{i}.txt")
    with open(out, "w", encoding="utf-8") as w:
        w.write("\n".join(lines))
    print(f"段落数: {len(lines)}  输出: {out}")
    print("--- 前40行预览 ---")
    for l in lines[:40]:
        print(l[:200])

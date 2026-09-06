import zipfile, os
ws = r"C:\Users\28049\AppData\Local\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.sessions\38440403509048578\agents\m_0cwE2Y9qbOa"
zp = os.path.join(ws, "design_refs", "动态视觉及ui视觉交互参考.zip")
out = os.path.join(ws, "design_refs", "ref_dyn")
os.makedirs(out, exist_ok=True)
z = zipfile.ZipFile(zp)
n = 0
seq = 0
for info in z.infolist():
    raw = info.filename
    name = raw
    for enc in ("gbk", "utf-8"):
        try:
            name = raw.encode("cp437").decode(enc); break
        except Exception:
            continue
    if "__MACOSX" in name or name.endswith("/"):
        continue
    base = os.path.basename(name)
    for ch in '\\/:*?"<>|':
        base = base.replace(ch, "_")
    ext = os.path.splitext(base)[1]
    # 异常长名 / 网络签名文件 -> 短名
    if len(base) > 60 or "sign=" in base:
        seq += 1
        base = f"netclip_{seq:02d}{ext}"
    with open(os.path.join(out, base), "wb") as f:
        f.write(z.read(info))
    n += 1
print("extracted", n)
for f in sorted(os.listdir(out)):
    print(f, round(os.path.getsize(os.path.join(out, f)) / 1024, 1), "KB")

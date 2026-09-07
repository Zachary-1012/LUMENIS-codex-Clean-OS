import zipfile, os

# 使用环境变量替代硬编码路径（审计工具，非生产代码）
ws = os.environ.get('ZBC_AUDIT_WORKSPACE', os.path.join(os.path.dirname(__file__), '..', '..'))
zp = os.path.join(ws, "design_refs", "动态视觉及ui视觉交互参考.zip")
out = os.path.join(ws, "design_refs", "ref_dyn")
os.makedirs(out, exist_ok=True)

if not os.path.exists(zp):
    print(f"参考zip不存在: {zp}")
    exit(0)

z = zipfile.ZipFile(zp)
n = 0
seq = 0
for info in z.infolist():
    raw = info.filename
    if raw.endswith('/'):
        continue
    n += 1
    seq += 1
    target = os.path.join(out, f"ref_{seq:04d}_{os.path.basename(raw)}")
    with z.open(info) as src, open(target, 'wb') as dst:
        dst.write(src.read())
print(f"已提取 {n} 个文件到 {out}")

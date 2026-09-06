import os, re
root = "D:\\"
pat = re.compile(r'taikoo|zbc|zachary|osai|adrh|ggi|global-growth|brand|sici|dcc|monitor', re.I)
skip = (".venv", "node_modules", "__pycache__", "site-packages", ".git")
rows = []
try:
    names = [n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))]
except Exception as e:
    print("D盘读取失败", e); raise SystemExit
for name in sorted(names):
    if not pat.search(name):
        continue
    base = os.path.join(root, name)
    py = js = 0; size = 0
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in skip]
        for f in fn:
            p = os.path.join(dp, f)
            try:
                size += os.path.getsize(p)
            except Exception:
                pass
            if f.endswith(".py"): py += 1
            elif f.endswith((".js", ".html")): js += 1
    rows.append((name, py, js, round(size/1024/1024,1)))
for r in rows:
    print(f"{r[0]:<44} py={r[1]:<5} js/html={r[2]:<5} {r[3]}MB")
print("\n全部D盘一级目录(供确认有无遗漏):")
print(", ".join(names))

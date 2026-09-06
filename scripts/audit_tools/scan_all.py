import os
root = "D:\\"
skip = (".venv", "node_modules", "__pycache__", "site-packages", ".git")
out = []
for name in sorted(os.listdir(root)):
    base = os.path.join(root, name)
    if not os.path.isdir(base):
        continue
    py = js = doc = 0; size = 0
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in skip]
        for f in fn:
            try: size += os.path.getsize(os.path.join(dp, f))
            except Exception: pass
            if f.endswith(".py"): py += 1
            elif f.endswith((".js", ".html", ".css")): js += 1
            elif f.endswith((".md", ".docx", ".pdf", ".txt")): doc += 1
    if py or js or doc:
        out.append((name, py, js, doc, round(size/1024/1024,1)))
for r in out:
    print(f"{r[0]:<38} py={r[1]:<5} web={r[2]:<5} doc={r[3]:<5} {r[4]}MB")

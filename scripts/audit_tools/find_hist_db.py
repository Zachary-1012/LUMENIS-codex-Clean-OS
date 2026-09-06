import os, sqlite3

candidates = [
    r"D:\Taikoo-monitor-new\data",
    r"D:\Taikoo-monitor-new\archive",
    r"D:\Taikoo-monitor-new-backups",
    r"D:\Taikoo-staging-ui",
    r"D:\Taikoo-security",
    r"D:\Taikoo-monitor-new",
]
seen = set()
probe_tables = ["notes", "note_comments", "events", "swire_notes", "canonical_data",
                "zbc_canonical_data", "web_mentions", "topic_campaign_notes"]
for base in candidates:
    if not os.path.isdir(base):
        continue
    for dp, dn, fn in os.walk(base):
        if any(x in dp for x in [".venv", "node_modules", "__pycache__", "edge-cdp"]):
            continue
        for f in fn:
            if f.lower().endswith((".db", ".sqlite", ".sqlite3")):
                p = os.path.join(dp, f)
                if p in seen:
                    continue
                seen.add(p)
                try:
                    size = os.path.getsize(p)/1024/1024
                    con = sqlite3.connect(p)
                    tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
                    parts = []
                    for t in probe_tables:
                        if t in tabs:
                            try:
                                n = con.execute(f'select count(*) from "{t}"').fetchone()[0]
                                if n:
                                    parts.append(f"{t}={n}")
                            except Exception:
                                pass
                    total = 0
                    for t in tabs:
                        try:
                            total += con.execute(f'select count(*) from "{t}"').fetchone()[0]
                        except Exception:
                            pass
                    con.close()
                    flag = "  <<< 有历史采集" if any(("notes=" in x or "events=" in x or "swire_notes=" in x) for x in parts) else ""
                    print(f"{size:8.2f}MB 表{len(tabs):3d} 行{total:6d}  {', '.join(parts)}  {p}{flag}")
                except Exception as e:
                    print("ERR", p, str(e)[:60])

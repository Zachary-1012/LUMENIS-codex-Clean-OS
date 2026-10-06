"""LUMENIS Product Core startup minimal dependency check. exit 0=OK, 2=MISSING
输出 stdout 最后一行： OK 或 MISSING:a,b,c
"""
import sys
mods = ['flask','playwright','apscheduler','schedule','dotenv','requests','bs4']
missing = []
for m in mods:
    try:
        if m == 'dotenv':
            import dotenv  # noqa: F401
        else:
            __import__(m)
    except Exception:
        missing.append(m)
if missing:
    print('MISSING:' + ','.join(missing))
    sys.exit(2)
print('OK')

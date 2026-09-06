import sys
sys.path.insert(0, r'D:\Taikoo-monitor-new')
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader(r'D:\Taikoo-monitor-new\templates'))
pages = ['cth/realtime.html','cth/events.html','cth/risk.html','cth/xiaohongshu.html','cth/reports.html']
for p in pages:
    try:
        t = env.get_template(p)
        print(f'{p} => OK')
    except Exception as e:
        print(f'{p} => ERROR: {e}')

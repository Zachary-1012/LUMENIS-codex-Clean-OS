# -*- coding: utf-8 -*-
"""生成 Command Home 独立预览 HTML（相对路径，可直接双击在浏览器打开做 Visual QA）。
不启动服务、不改 app.py、不触达业务。"""
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

ZBC = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in dir() else r"D:\Taikoo-monitor-new"
ZBC = r"D:\Taikoo-monitor-new"
env = Environment(loader=FileSystemLoader(os.path.join(ZBC, "templates")),
                  autoescape=select_autoescape(["html"]))
# 相对路径：预览文件放在 templates/_preview/ 下，静态资源用 ../../static
env.globals["url_for"] = lambda endpoint, **kw: (
    "../../static/" + kw.get("filename", "") if endpoint == "static" else "#")
html = env.get_template("home/command_home.html").render(active_nav="home", home_url="../../")
outdir = os.path.join(ZBC, "templates", "_preview")
os.makedirs(outdir, exist_ok=True)
out = os.path.join(outdir, "command-home-preview.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("preview written:", out, len(html), "chars")

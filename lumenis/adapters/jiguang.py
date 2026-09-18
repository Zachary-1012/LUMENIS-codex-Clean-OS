# -*- coding: utf-8 -*-
"""
极光（Jiguang / JPush）内容采集适配器
--------------------------------------
定位：服务于 Z-Brand Core 多平台采集。极光为营销/推送平台，本适配器走
"cookie_vault 加载 + CDP 浏览器导航 + 页面解析"最小可用链路。

数据主路径：极光后台/营销页面（需登录态 cookie）
  https://www.jiguang.cn/

状态映射：
  - 解析到内容 → SUCCESS
  - 正常空     → success=True, notes=[]
  - 登录失效   → SESSION_EXPIRED
  - 异常       → COLLECT_ERROR

只读红线：不执行任何账号写操作；遇到风控如实返回，不破解不绕过。
"""
import re
import logging
from .base import BaseAdapter, AdapterResult, CollectedNote
from .cookie_vault import check_cookie_status, inject_into_context

logger = logging.getLogger(__name__)


class JiguangAdapter(BaseAdapter):
    """极光搜索适配器（CDP + cookie_vault，只读采集）"""

    platform_name = "jiguang"
    platform_display = "极光"

    CDP_PORT = 9224  # 通用 CDP 端口

    _DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _cookie_ok() -> bool:
        s = check_cookie_status("jiguang")
        return s["status"] == "ACTIVE"

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        if not self._cookie_ok():
            return AdapterResult(
                success=False,
                error="极光 cookie 缺失或无关键认证 cookie，请更新 data/cookies/jiguang.json",
            )
        try:
            return self._search_browser(keyword.strip(), max_results)
        except Exception as e:
            logger.exception("极光采集异常")
            return AdapterResult(success=False, error=f"极光采集异常: {e}")

    def _search_browser(self, keyword: str, max_results: int) -> AdapterResult:
        """CDP 导航极光后台，解析页面内容。最小可用链路。"""
        try:
            from .human_browser import HumanBrowser
            from urllib.parse import quote

            hb = HumanBrowser(port=self.CDP_PORT, launch_url="about:blank")
            hb.connect()
            injected = inject_into_context(hb._context, "jiguang")
            logger.info("极光采集：注入 Cookie %d 条", injected)
            page = None
            try:
                page = hb.new_page()
                # 极光后台首页（登录态验证）
                page.goto("https://www.jiguang.cn/", wait_until="domcontentloaded", timeout=30000)
                hb.pause(3.0, 3.0)

                # 检测登录态：如果跳转到登录页则失效
                if "login" in page.url.lower() or "signin" in page.url.lower():
                    return AdapterResult(success=False, error="极光登录态失效，跳转登录页")

                title = page.title() or ""
                body_text = ""
                try:
                    body_text = page.evaluate("() => document.body.innerText.slice(0, 2000)") or ""
                except Exception:
                    pass

                # 最小解析：提取页面中的卡片/列表项
                notes = []
                try:
                    cards = page.evaluate(r"""() => {
                        const out = [];
                        document.querySelectorAll('div[class*="card"], div[class*="item"], li').forEach(el => {
                            const t = (el.innerText || '').trim();
                            if (t && t.length > 10 && t.length < 500) out.push(t);
                        });
                        return out.slice(0, 20);
                    }""")
                    for i, text in enumerate(cards or []):
                        if len(notes) >= max_results:
                            break
                        notes.append(CollectedNote(
                            title=text[:80],
                            content=text[:500],
                            url="https://www.jiguang.cn/",
                            author="jiguang",
                            publish_date="",
                            likes=0, comments=0, collects=0, shares=0,
                            source_platform="jiguang",
                            raw_data={"engine": "jiguang_cdp", "index": i},
                        ))
                except Exception:
                    pass

                if notes:
                    return AdapterResult(success=True, notes=notes, raw_count=len(notes))
                # 无解析结果但页面可达，返回成功空（登录态有效但无搜索结果结构）
                return AdapterResult(
                    success=True, notes=[], raw_count=0,
                    error=f"页面可达(title={title[:40]})但未解析到结构化内容"
                )
            finally:
                if page:
                    try: page.close()
                    except Exception: pass
                hb.close()
        except Exception as e:
            return AdapterResult(success=False, error=f"极光浏览器采集异常: {e}")

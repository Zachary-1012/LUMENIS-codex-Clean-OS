# -*- coding: utf-8 -*-
"""
搜狗微信采集适配器 - 公众号文章搜索
================================================
定位：搜狗微信公众号文章搜索（weixin.sogou.com），免登可搜但有频控/反爬。
接入主链（只适配不重写）：
  · 统一走 cookie_vault 加载 cookie（如有，提升稳定性；无 cookie 仍可匿名搜）
  · 标准化 CollectedNote（source_platform=sogou_wechat）
  · content_hash + platform_id 去重（raw_data 携带，入库层 persist 消费）
  · subject 红线过滤由调用方/入库层执行，适配器不做业务过滤
  · 质量门禁：标题非空、URL 非空才产出；缺失字段显式空串不用 0/"未知"填
  · 风险评估：命中反爬验证页 → success=False（BLOCKED 语义），绝不空列表冒充成功
  · 采集结果 raw_data 带 product_id/domain_id（调用方注入，透传不篡改）
  · CTH 域过 subject_rules，ZBMP 域不被 CTH 199品牌/9业态隐式过滤（双域隔离，适配器不感知域）

工程约定（对齐系统六态，不制造"0 条假成功"）：
  · 正常返回但确无结果 -> success=True, notes=[]（由注册中心判 EMPTY）
  · 命中搜狗反爬验证页 / 网络异常 -> success=False（判 FAIL/BLOCKED 语义）
  · 缺代理/凭证时显式 BLOCKED，不伪造成功
"""
import re
import html
import time
import random
import hashlib
import datetime
import urllib.parse
import logging
from .base import BaseAdapter, AdapterResult, CollectedNote

logger = logging.getLogger(__name__)

# 命中即视为搜狗反爬/人机校验，需按 BLOCKED 处理而非"无结果"
_BLOCK_PATTERNS = [
    "antispider", "anti.min.css", "verify.css", "imgcode",
    "请输入验证码", "访问过于频繁", "用户您好", "网络不给力",
    "验证码", "unusual traffic", "请您输入验证码",
    "请输入验证码后继续", "seccode",
]

# 发布时间：2026年6月7日 / 2025-03-2 / 2025/03/02
_DATE_CN = re.compile(r"(20\d{2})\s*[年/\-\.]\s*(\d{1,2})\s*[月/\-\.]\s*(\d{1,2})")
# 相对时间：N小时前 / N天前 / 昨天
_REL_HOUR = re.compile(r"(\d+)\s*小时前")
_REL_DAY = re.compile(r"(\d+)\s*天前")


class SogouWechatAdapter(BaseAdapter):
    """搜狗微信公众号文章搜索适配器（接入主链，只适配不重写）"""

    platform_name = "sogou_wechat"
    platform_display = "搜狗微信"

    def __init__(self, product_id: str = "", domain_id: str = "", **kwargs):
        """初始化。

        Args:
            product_id: 产品ID（透传到 raw_data，双域隔离用）
            domain_id: 域ID（CTH/ZBMP，透传到 raw_data，不做隐式过滤）
        """
        super().__init__(**kwargs)
        self.product_id = product_id
        self.domain_id = domain_id

    # ---------- cookie_vault 统一加载（如有） ----------
    def _load_cookies(self):
        """统一走 cookie_vault 加载搜狗微信 cookie（如有）。无则返回空 dict。"""
        try:
            from .cookie_vault import to_requests_cookies
            cookies = to_requests_cookies("sogou_wechat")
            if cookies:
                logger.info("搜狗微信: 从 cookie_vault 加载 %d 条 cookie", len(cookies))
            return cookies
        except Exception as e:
            logger.warning("搜狗微信: cookie_vault 加载失败（降级匿名）: %s", e)
            return {}

    def _cookie_status(self) -> dict:
        """检查 cookie 文件级状态（不打印值）。"""
        try:
            from .cookie_vault import check_cookie_status
            return check_cookie_status("sogou_wechat")
        except Exception:
            return {"status": "MISSING", "cookie_count": 0, "has_auth_cookie": False}

    # ---------- 主入口 ----------
    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """搜狗微信公众号文章搜索（接入主链）。"""
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            import requests
        except ImportError:
            return AdapterResult(success=False, error="缺少 requests 依赖")

        cookies = self._load_cookies()
        url = ("https://weixin.sogou.com/weixin?type=2&query="
               + urllib.parse.quote(keyword) + "&num=" + str(max_results))
        headers = {
            "User-Agent": self.config["user_agent"]
                + " (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
            "Referer": "https://weixin.sogou.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        # 抓取（命中反爬时退避后最多重试一次，不硬刚风控）
        text = None
        last_err = ""
        for attempt in range(2):
            try:
                resp = requests.get(url, headers=headers, cookies=cookies,
                                    timeout=self.config["request_timeout"])
                resp.encoding = "utf-8"
                text = resp.text
                if not self._is_blocked(text):
                    break
                last_err = "命中搜狗微信反爬验证页"
                if attempt == 0:
                    time.sleep(random.uniform(4.0, 6.0))
                    continue
            except Exception as e:
                last_err = "网络异常 " + str(e)
                if attempt == 0:
                    time.sleep(random.uniform(2.0, 3.0))
                    continue

        if text is None or self._is_blocked(text):
            # 显式 BLOCKED，绝不返回空列表冒充成功
            return AdapterResult(
                success=False,
                error=last_err or "命中搜狗微信反爬验证页(已退避重试仍受限)",
            )

        # 解析（BeautifulSoup 优先，正则兜底——保留原有解析逻辑）
        notes = self._parse_results(text)
        return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))

    # ---------- 反爬检测 ----------
    @staticmethod
    def _is_blocked(text: str) -> bool:
        """识别搜狗微信反爬/人机校验页（命中即按 BLOCKED 处理，不当作 0 条）。"""
        if not text or len(text) < 800:
            return True  # 异常空壳页同样视为被拦
        low = text.lower()
        return any(p.lower() in low for p in _BLOCK_PATTERNS)

    # ---------- 解析（保留原有正则，增强 BeautifulSoup 优先） ----------
    def _parse_results(self, html_text: str) -> list:
        """解析搜狗微信搜索结果页。BeautifulSoup 优先，正则兜底。"""
        notes = []
        # 优先 BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, "html.parser")
            for item in soup.select("div.txt-box, li[id^='sogou_vr']"):
                anchor = item.find("h3")
                if anchor and anchor.find("a"):
                    a = anchor.find("a")
                else:
                    a = item.find("a", id=re.compile(r"sogou_vr"))
                if a is None:
                    continue
                title = html.unescape(a.get_text(" ", strip=True))
                href = a.get("href", "").strip()
                if not title or not href:
                    continue
                if href.startswith("/"):
                    href = "https://weixin.sogou.com" + href
                # 摘要
                snippet_el = item.select_one("p.txt-info, .txt-info")
                snippet = html.unescape(snippet_el.get_text(" ", strip=True)) if snippet_el else ""
                # 公众号名
                account_el = item.select_one("a[id^='sogou_vr_11002301'], .account, .s-p")
                account = html.unescape(account_el.get_text(" ", strip=True)) if account_el else ""
                # 发布时间
                pub_date = self._extract_date(item.get_text(" ", strip=True))
                notes.append(self._make_standard_note(
                    title=re.sub(r"\s+", " ", title),
                    content=re.sub(r"\s+", " ", snippet or ""),
                    url=href,
                    author=account or "",
                    publish_date=pub_date,
                ))
            if notes:
                return notes
        except ImportError:
            pass
        except Exception as e:
            logger.warning("搜狗微信 BeautifulSoup 解析失败，降级正则: %s", e)

        # 正则兜底（保留原有逻辑）
        pattern = (r'<div class="txt-box">.*?<h3>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
                   r'.*?<p class="txt-info"[^>]*>(.*?)</p>'
                   r'.*?<a[^>]*id="sogou_vr_11002301_box_[\d]+"[^>]*>(.*?)</a>')
        for url, title, content, account in re.findall(pattern, html_text, re.DOTALL):
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            clean_content = re.sub(r"<[^>]+>", "", content).strip()
            clean_account = re.sub(r"<[^>]+>", "", account).strip()
            if clean_title:
                full_url = "https://weixin.sogou.com" + url if url.startswith("/") else url
                notes.append(self._make_standard_note(
                    title=clean_title,
                    content=clean_content,
                    url=full_url,
                    author=clean_account or "",
                    publish_date="",
                ))
        return notes

    # ---------- 标准化笔记（content_hash + platform_id + product/domain 透传） ----------
    def _make_standard_note(self, title: str, content: str = "", url: str = "",
                            author: str = "", publish_date: str = "") -> CollectedNote:
        """创建标准化 CollectedNote，携带 content_hash/platform_id/product_id/domain_id。

        数据精准红线：缺失字段显式空串，不用 0 或"未知"静默填。
        """
        content_hash = hashlib.md5(
            (title + "|" + (url or "")).encode("utf-8", "ignore")
        ).hexdigest()
        platform_id = self.platform_name + "_" + content_hash[:16]
        raw_data = {
            "content_hash": content_hash,
            "platform_id": platform_id,
            "product_id": self.product_id,   # 透传，不篡改
            "domain_id": self.domain_id,     # 透传，双域隔离：CTH/ZBMP 不混用
            "engine": "sogou_wechat",
            "cookie_used": bool(self._load_cookies()),
        }
        return CollectedNote(
            title=title,
            content=content,
            url=url,
            author=author,
            author_id="",           # 搜狗微信不暴露公众号ID，显式空
            publish_date=publish_date,
            likes=0,                # 搜狗搜索页不展示互动量，显式0（非伪造）
            comments=0,
            collects=0,
            shares=0,
            cover="",
            source_platform=self.platform_name,
            raw_data=raw_data,
        )

    # ---------- 日期提取 ----------
    @staticmethod
    def _extract_date(text: str) -> str:
        """从文本提取发布日期：绝对日期优先，其次相对时间归一。缺失返回空串。"""
        if not text:
            return ""
        m = _DATE_CN.search(text)
        if m:
            y, mo, d = (int(x) for x in m.groups())
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return "{:04d}-{:02d}-{:02d}".format(y, mo, d)
        today = datetime.datetime.now()
        mh = _REL_HOUR.search(text)
        if mh:
            return (today - datetime.timedelta(hours=int(mh.group(1)))).strftime("%Y-%m-%d")
        if "昨天" in text:
            return (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        md = _REL_DAY.search(text)
        if md:
            return (today - datetime.timedelta(days=int(md.group(1)))).strftime("%Y-%m-%d")
        return ""  # 缺失显式空，不用当前日期伪造

    def get_status(self) -> dict:
        """获取适配器状态（含 cookie 状态）。"""
        status = super().get_status()
        status["cookie_status"] = self._cookie_status()
        return status

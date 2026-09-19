# -*- coding: utf-8 -*-
"""品牌 Profile 驱动小红书实时采集入口（链路：profile -> collect_keywords -> 采集 -> 主体过滤 -> 入库）。

用法：
  python -m lumenis.system.collector.runtime.run_profile --dry-run                 # 只打印激活品牌关键词（不采集）
  python -m lumenis.system.collector.runtime.run_profile --cdp-url <ws>            # 真采（需双账号登录态在场）
  python -m lumenis.system.collector.runtime.run_profile --brand hainan_cdf --max-scroll 3
"""
import argparse
import json

from subject_rules import get_active_brand, get_brand_config, collect_keywords_for, subject_hit_text


def main():
    p = argparse.ArgumentParser(description="品牌 Profile 驱动小红书采集（默认当前激活品牌）")
    p.add_argument("--brand", default="", help="品牌 key（如 hainan_cdf），默认当前激活品牌")
    p.add_argument("--max-scroll", type=int, default=3)
    p.add_argument("--max-details", type=int, default=20)
    p.add_argument("--max-comment-pages", type=int, default=5)
    p.add_argument("--cdp-url", default="", help="浏览器 CDP 地址（登录态会话）")
    p.add_argument("--no-comments", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="只打印配置与关键词，不真正采集")
    a = p.parse_args()

    brand = a.brand or get_active_brand()
    cfg = get_brand_config(brand)
    kws = collect_keywords_for(brand)
    if not kws:
        print(json.dumps({"ok": False, "error": "brand has no collect keywords", "brand": brand}, ensure_ascii=False))
        return 1

    if a.dry_run:
        print(json.dumps({
            "ok": True, "dry_run": True, "brand": brand,
            "display_name": cfg.get("display_name", brand),
            "subject_words_count": len(cfg.get("subject_words", [])),
            "exclude_words_count": len(cfg.get("exclude_words", [])),
            "keywords": kws,
        }, ensure_ascii=False, indent=2))
        return 0

    from .xhs.live_engine import run_live, persist_live

    # 统一委托 subject_rules 权威主体口径（排除词一票否决 + 正向词命中），不重写业务逻辑
    def subject_hit(text):
        try:
            return subject_hit_text(text)
        except Exception:
            return False

    all_stats = []
    for kw in kws:
        data = run_live(kw, max_scroll=a.max_scroll, max_details=a.max_details,
                        max_comment_pages=a.max_comment_pages, comments=not a.no_comments,
                        cdp_url=a.cdp_url or None)
        stats = persist_live(data, subject_hit)
        all_stats.append({
            "keyword": kw,
            "collector": data.get("stats", {}),
            "persist": stats,
            "verification_required": data.get("verification_required", False),
        })
    print(json.dumps({
        "ok": all(not x["verification_required"] for x in all_stats),
        "brand": brand, "results": all_stats,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

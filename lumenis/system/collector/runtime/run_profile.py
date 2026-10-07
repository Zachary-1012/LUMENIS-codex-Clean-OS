# -*- coding: utf-8 -*-
"""品牌 Profile 驱动小红书实时采集入口（链路：profile -> collect_keywords -> 采集 -> 主体过滤 -> 入库）。

用法：
  python -m lumenis.system.collector.runtime.run_profile --brand hainan_cdf --dry-run
  python -m lumenis.system.collector.runtime.run_profile --brand hainan_cdf --domain-id zbmp --product-id BMP --brand-focus-id hainan_cdf
"""
import argparse
import json

from subject_rules import get_brand_config, collect_keywords_for, subject_hit_for_brand


def main():
    p = argparse.ArgumentParser(description="品牌 Profile 驱动小红书采集（必须显式选择品牌）")
    p.add_argument("--brand", required=True, help="已注册品牌 key（如 hainan_cdf）")
    p.add_argument("--max-scroll", type=int, default=3)
    p.add_argument("--max-details", type=int, default=20)
    p.add_argument("--max-comment-pages", type=int, default=5)
    p.add_argument("--cdp-url", default="", help="浏览器 CDP 地址（登录态会话）")
    p.add_argument("--domain-id", default="")
    p.add_argument("--product-id", default="")
    p.add_argument("--subject-id", default="")
    p.add_argument("--brand-focus-id", default="")
    p.add_argument("--no-comments", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="只打印配置与关键词，不真正采集")
    a = p.parse_args()

    brand = a.brand
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

    try:
        from .xhs.live_engine import resolve_live_scope
        domain_id, product_id, subject_id, brand_focus_id, _ = resolve_live_scope(
            domain_id=a.domain_id or None, product_id=a.product_id or None,
            subject_id=a.subject_id or None, brand_focus_id=a.brand_focus_id or None,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "status": "scope_unavailable", "error": str(exc)}, ensure_ascii=False))
        return 2
    from .xhs.live_engine import run_live, persist_live

    # 统一委托 subject_rules 权威主体口径（排除词一票否决 + 正向词命中），不重写业务逻辑
    def subject_hit(text):
        try:
            return subject_hit_for_brand(title=text, brand_key=brand)
        except Exception:
            return False

    all_stats = []
    for kw in kws:
        data = run_live(kw, max_scroll=a.max_scroll, max_details=a.max_details,
                        max_comment_pages=a.max_comment_pages, comments=not a.no_comments,
                        cdp_url=a.cdp_url or None)
        stats = persist_live(
            data, subject_hit, domain_id=domain_id, product_id=product_id,
            subject_id=subject_id, brand_focus_id=brand_focus_id,
        )
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

"""XHS collection entrypoint.

This module supplies a thin multi-keyword wrapper. Collection, filtering, and
persistence behavior are owned by the canonical live engine under `.xhs.live_engine`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from .xhs.live_engine import persist_live, run_live


def run_keywords(
    keywords: Iterable[str],
    *,
    max_scroll: int = 5,
    max_details: int = 20,
    max_comment_pages: int = 5,
    comments: bool = True,
    cdp_url: str | None = None,
    account: str | None = None,
    subject_hit: Callable[[str], bool] | None = None,
    domain_id: str | None = None,
    product_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    brand_key: str | None = None,
) -> dict[str, Any]:
    """Run the canonical XHS engine for multiple keywords.

    The wrapper is deliberately thin: it delegates collection, normalization,
    deduplication, subject filtering, Evidence and Canonical Data writes to the
    existing live engine.  No vendor or alternate browser path is introduced.
    """

    try:
        from .xhs.live_engine import resolve_live_scope
        domain_id, product_id, subject_id, brand_focus_id, _scope = resolve_live_scope(
            domain_id=domain_id, product_id=product_id,
            subject_id=subject_id, brand_focus_id=brand_focus_id,
        )
    except ValueError as exc:
        return {"ok": False, "status": "scope_unavailable", "error": str(exc), "results": []}

    if subject_hit is None and brand_key:
        try:
            from subject_rules import subject_hit_for_brand
            subject_hit = lambda text: subject_hit_for_brand(title=text, brand_key=brand_key)
        except Exception:
            return {"ok": False, "status": "filter_unavailable", "error": "COLLECTION_FILTER_UNAVAILABLE", "results": []}
    if subject_hit is None:
        return {"ok": False, "status": "filter_unavailable", "error": "COLLECTION_FILTER_REQUIRED", "results": []}

    results: list[dict[str, Any]] = []
    for keyword in [str(item).strip() for item in keywords if str(item).strip()]:
        data = run_live(
            keyword,
            max_scroll=max_scroll,
            max_details=max_details,
            max_comment_pages=max_comment_pages,
            comments=comments,
            cdp_url=cdp_url,
            account=account,
        )
        persisted = persist_live(
            data, subject_hit, domain_id=domain_id, product_id=product_id,
            subject_id=subject_id, brand_focus_id=brand_focus_id,
        )
        results.append(
            {
                "keyword": keyword,
                "collector": data.get("stats", {}),
                "persist": persisted,
                "verification_required": bool(data.get("verification_required")),
                "collection_policy": data.get("collection_policy"),
            }
        )

    return {
        "ok": bool(results) and all(not item["verification_required"] for item in results),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="LUMENIS canonical XHS live collector")
    parser.add_argument("--keyword", action="append", required=True)
    parser.add_argument("--max-scroll", type=int, default=5)
    parser.add_argument("--max-details", type=int, default=20)
    parser.add_argument("--max-comment-pages", type=int, default=5)
    parser.add_argument("--cdp-url", default="")
    parser.add_argument("--account", default="XHS_RETINAUT")
    parser.add_argument("--domain-id", required=True)
    parser.add_argument("--product-id", required=True)
    focus = parser.add_mutually_exclusive_group(required=True)
    focus.add_argument("--subject-id")
    focus.add_argument("--brand-focus-id")
    parser.add_argument("--brand-key", required=True, help="与已审核主体过滤词库对应的精确 key")
    parser.add_argument("--no-comments", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    result = run_keywords(
        args.keyword,
        max_scroll=args.max_scroll,
        max_details=args.max_details,
        max_comment_pages=args.max_comment_pages,
        comments=not args.no_comments,
        cdp_url=args.cdp_url or None,
        account=args.account or None,
        domain_id=args.domain_id, product_id=args.product_id,
        subject_id=args.subject_id, brand_focus_id=args.brand_focus_id,
        brand_key=args.brand_key,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Legacy XHS CLI compatibility entrypoint.

This preserves the historical ``collector_v2.run_xhs_live`` command without
reintroducing the retired collector implementation.  All collection remains
owned by ``collector_v2.xhs.live_engine`` and its existing Evidence/Canonical
Data persistence path.
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
) -> dict[str, Any]:
    """Run the canonical XHS engine for multiple keywords.

    The wrapper is deliberately thin: it delegates collection, normalization,
    deduplication, subject filtering, Evidence and Canonical Data writes to the
    existing live engine.  No vendor or alternate browser path is introduced.
    """

    if subject_hit is None:
        try:
            from subject_rules import subject_hit_text

            subject_hit = subject_hit_text
        except Exception:
            subject_hit = lambda _text: False

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
        persisted = persist_live(data, subject_hit)
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
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

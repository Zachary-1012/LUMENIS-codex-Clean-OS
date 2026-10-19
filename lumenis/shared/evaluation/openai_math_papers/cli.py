"""One bounded local computation on a user-supplied JSON problem. No default samples."""

import argparse
import json
from pathlib import Path

from .core import Budget, MathInputError, ResourceBound
from .dispatch import execute


def main():
    a = argparse.ArgumentParser()
    a.add_argument("request", type=Path)
    a.add_argument("--seconds", type=float, default=20)
    a.add_argument("--max-items", type=int, default=10000)
    a.add_argument("--offline-review", action="store_true",
                   help="Explicit fixed-pin calculation only; current review not verified, not publishable")
    args = a.parse_args()
    try:
        if (
            args.request.is_symlink()
            or not args.request.is_file()
            or args.request.stat().st_size > 1_000_000
        ):
            raise MathInputError("INVALID_LOCAL_INPUT_FILE")
        obj = json.loads(
            args.request.read_text(encoding="utf-8"),
            parse_constant=lambda s: (_ for _ in ()).throw(
                MathInputError("NONFINITE_JSON")
            ),
        )
        print(
            json.dumps(
                execute(
                    obj, budget=Budget(seconds=args.seconds, max_items=args.max_items),
                    offline_review=args.offline_review
                ),
                ensure_ascii=False,
                allow_nan=False,
            )
        )
        return 0
    except ResourceBound as e:
        print(
            json.dumps(
                {
                    "state": "INCOMPLETE",
                    "reason": str(e),
                    "partial_result_accepted": False,
                }
            )
        )
        return 3
    except (MathInputError, ValueError, TypeError, KeyError, OSError) as e:
        print(
            json.dumps(
                {
                    "state": "INVALID_OR_UNAVAILABLE",
                    "error_type": type(e).__name__,
                    "reason": str(e) if isinstance(e, MathInputError) else "INPUT_OR_STORAGE_UNAVAILABLE",
                    "result_accepted": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

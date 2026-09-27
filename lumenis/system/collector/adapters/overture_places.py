"""Read local Overture Places Parquet rows as review candidates.

The reader returns normalized candidates only; it does not persist rows or
assert Canonical Truth. Each candidate retains upstream source metadata for
downstream license and attribution handling.
"""
from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


_OVERTURE_ATTRIBUTION = "Overture Maps Foundation, overturemaps.org"


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    as_py = getattr(value, "as_py", None)
    if callable(as_py):
        converted = as_py()
        return converted if isinstance(converted, Mapping) else {}
    return {}


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _clean_sources(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(source) for item in value if (source := _mapping(item))]


def _address_for_country(
    value: Any, country_code: str
) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(value, (list, tuple)):
        return None, "UNKNOWN"
    addresses = [dict(_mapping(item)) for item in value if _mapping(item)]
    matching = [
        item for item in addresses
        if (_text(item.get("country")) or "").upper() == country_code
    ]
    if matching:
        chosen = min(
            matching,
            key=lambda item: (
                -sum(bool(_text(item.get(field))) for field in ("freeform", "postcode", "locality")),
                json.dumps(item, sort_keys=True, default=str, ensure_ascii=False),
            ),
        )
        return chosen, "AVAILABLE"
    if any(_text(item.get("country")) for item in addresses):
        return None, "OUT_OF_SCOPE"
    return None, "UNKNOWN"


def _confidence(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    score = float(value)
    return score if math.isfinite(score) and 0 <= score <= 1 else None


def normalize_overture_place_row(
    row: Mapping[str, Any], *, release: str | None = None, country_code: str = "SG"
) -> dict[str, Any] | None:
    """Return one in-country mall or branded-place candidate; never persist it."""
    if not isinstance(row, Mapping):
        return None
    country_code = (_text(country_code) or "SG").upper()
    stable_id = _text(row.get("id"))
    if not stable_id:
        return None

    address, location_state = _address_for_country(row.get("addresses"), country_code)
    if location_state == "OUT_OF_SCOPE":
        return None
    names = _mapping(row.get("names"))
    brand = _mapping(row.get("brand"))
    brand_names = _mapping(brand.get("names"))
    taxonomy = _mapping(row.get("taxonomy"))
    name = _text(names.get("primary"))
    brand_name = _text(brand_names.get("primary"))
    basic_category = _text(row.get("basic_category"))
    primary_category = _text(taxonomy.get("primary")) or basic_category
    hierarchy = [text for item in taxonomy.get("hierarchy", []) if (text := _text(item))] \
        if isinstance(taxonomy.get("hierarchy"), (list, tuple)) else []
    alternates = [text for item in taxonomy.get("alternates", []) if (text := _text(item))] \
        if isinstance(taxonomy.get("alternates"), (list, tuple)) else []
    categories = {value.casefold() for value in [primary_category, basic_category, *hierarchy, *alternates] if value}
    kinds = []
    if "shopping_mall" in categories:
        kinds.append("shopping_mall")
    if brand_name:
        kinds.append("brand_place")
    if not kinds:
        return None

    confidence = _confidence(row.get("confidence"))
    sources = _clean_sources(row.get("sources"))
    licensed_sources = [item for item in sources if _text(item.get("license"))]
    license_state = (
        "NOT_AVAILABLE" if not licensed_sources else
        "AVAILABLE" if len(licensed_sources) == len(sources) else "PARTIAL"
    )
    field_states = {
        "name": "AVAILABLE" if name else "NOT_AVAILABLE",
        "brand": "AVAILABLE" if brand_name else "NOT_AVAILABLE",
        "category": "AVAILABLE" if primary_category else "NOT_AVAILABLE",
        "address": "AVAILABLE" if address and _text(address.get("freeform")) else "NOT_AVAILABLE",
        "postcode": "AVAILABLE" if address and _text(address.get("postcode")) else "NOT_AVAILABLE",
        "confidence": "AVAILABLE" if confidence is not None else "NOT_AVAILABLE",
        "location": "AVAILABLE" if location_state == "AVAILABLE" else "UNKNOWN",
    }
    return {
        "candidate_id": f"overture:{stable_id}",
        "stable_source_id": stable_id,
        "candidate_kinds": kinds,
        "name": name,
        "brand_name": brand_name,
        "category": primary_category,
        "basic_category": basic_category,
        "category_hierarchy": hierarchy,
        "category_alternates": alternates,
        "address": _text(address.get("freeform")) if address else None,
        "postcode": _text(address.get("postcode")) if address else None,
        "locality": _text(address.get("locality")) if address else None,
        "country_code": country_code if address else None,
        "confidence": confidence,
        "confidence_state": field_states["confidence"],
        "operating_status": _text(row.get("operating_status")),
        "field_states": field_states,
        "source_metadata": {
            "provider": "Overture Maps Places",
            "theme": "places",
            "release": _text(release),
            "release_state": "AVAILABLE" if _text(release) else "NOT_AVAILABLE",
            "suggested_citation": _OVERTURE_ATTRIBUTION,
            "upstream_sources": sources,
            "upstream_license_state": license_state,
        },
    }


def parse_overture_place_rows(
    rows: Iterable[Mapping[str, Any]], *, release: str | None = None, country_code: str = "SG"
) -> dict[str, Any]:
    """Normalize and deterministically deduplicate decoded Places rows by Overture id."""
    selected: dict[str, tuple[tuple[int, float, str], dict[str, Any]]] = {}
    counts = {"input": 0, "missing_id": 0, "out_of_scope": 0, "not_candidate": 0}
    normalized_country = (_text(country_code) or "SG").upper()
    for row in rows:
        counts["input"] += 1
        candidate = normalize_overture_place_row(
            row, release=release, country_code=normalized_country
        )
        if candidate is None:
            if not isinstance(row, Mapping) or not _text(row.get("id")):
                counts["missing_id"] += 1
            elif _address_for_country(row.get("addresses"), normalized_country)[1] == "OUT_OF_SCOPE":
                counts["out_of_scope"] += 1
            else:
                counts["not_candidate"] += 1
            continue
        serialized = json.dumps(row, sort_keys=True, default=str, ensure_ascii=False)
        completeness = sum(state == "AVAILABLE" for state in candidate["field_states"].values())
        score = candidate["confidence"] if candidate["confidence"] is not None else -1.0
        rank = (completeness, score, serialized)
        key = candidate["stable_source_id"]
        current = selected.get(key)
        if current is None or rank[:2] > current[0][:2] or (rank[:2] == current[0][:2] and serialized < current[0][2]):
            selected[key] = (rank, candidate)
    normalized = [selected[key][1] for key in sorted(selected)]
    candidates = [item for item in normalized if item["field_states"]["location"] == "AVAILABLE"]
    unlocated = [item for item in normalized if item["field_states"]["location"] == "UNKNOWN"]
    return {
        "candidates": candidates,
        "unlocated_candidates": unlocated,
        "counts": {
            **counts,
            "unknown_location": len(unlocated),
            "deduplicated": (
                counts["input"]
                - counts["missing_id"]
                - counts["out_of_scope"]
                - counts["not_candidate"]
                - len(candidates)
                - len(unlocated)
            ),
        },
    }


def read_overture_places_parquet(
    path: str | Path,
    *,
    release: str | None = None,
    country_code: str = "SG",
    batch_size: int = 2048,
) -> dict[str, Any]:
    """Read a literal local Parquet file in batches and normalize its rows."""
    if not isinstance(path, (str, Path)):
        raise TypeError("path must be a local path string or Path")
    raw_path = str(path)
    if (
        not raw_path
        or "://" in raw_path.casefold()
        or raw_path.startswith(("\\\\", "//"))
        or any(char in raw_path for char in "*?[]")
    ):
        raise ValueError("path must be a literal local Parquet file path")
    source = Path(raw_path)
    if not source.is_absolute() or source.suffix.casefold() != ".parquet":
        raise ValueError("path must be an absolute .parquet file path")
    source = source.resolve(strict=True)
    if not source.is_file():
        raise ValueError("path must identify a local Parquet file")
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")

    import duckdb

    connection = duckdb.connect(database=":memory:")
    try:
        relation = connection.read_parquet(str(source))
        columns = relation.columns

        def rows() -> Iterable[dict[str, Any]]:
            while batch := relation.fetchmany(batch_size):
                for values in batch:
                    yield dict(zip(columns, values))

        return parse_overture_place_rows(rows(), release=release, country_code=country_code)
    finally:
        connection.close()

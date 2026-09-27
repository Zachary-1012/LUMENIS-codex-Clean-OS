"""Exact CTH Subject and BMP BrandFocus membership checks for DB callers.

This module resolves identity only. A successful lookup is UNVERIFIED until a
separate Evidence-backed writer validates and persists the record.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Optional


SCOPE_STATUS_UNASSIGNED = "UNASSIGNED"
SCOPE_STATUS_UNVERIFIED = "UNVERIFIED"


class ScopeValidationError(ValueError):
    """A requested identity is invalid, unavailable, or belongs to another domain."""


@dataclass(frozen=True)
class ScopeDecision:
    subject_id: Optional[str] = None
    brand_focus_id: Optional[str] = None
    status: str = SCOPE_STATUS_UNASSIGNED
    evidence_ref: str = ""


def normalize_product_domain(product_id: Any, domain_id: Any = None) -> tuple[str, str]:
    """Normalize supported CTH/BMP compatibility identifiers to DB values."""
    products = {"CTH": "CTH", "BMP": "ZBMP", "ZBMP": "ZBMP"}
    domains = {"CTH": "cth", "BMP": "zbmp", "ZBMP": "zbmp"}
    raw_product = str(product_id or "").strip().upper()
    raw_domain = str(domain_id or "").strip().upper()
    product = products.get(raw_product) if raw_product else None
    domain = domains.get(raw_domain) if raw_domain else None
    if raw_product and product is None:
        raise ScopeValidationError(f"unsupported scope product_id: {product_id!r}")
    if raw_domain and domain is None:
        raise ScopeValidationError(f"unsupported scope domain_id: {domain_id!r}")
    if product is None and domain is None:
        raise ScopeValidationError("an exact CTH or BMP product/domain is required")
    if product is None:
        product = "CTH" if domain == "cth" else "ZBMP"
    expected_domain = "cth" if product == "CTH" else "zbmp"
    if domain is not None and domain != expected_domain:
        raise ScopeValidationError("scope product_id and domain_id conflict")
    return product, expected_domain


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if exists is None:
        raise ScopeValidationError("canonical Subject/BrandFocus registry is unavailable")
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _registry_member(conn: sqlite3.Connection, product: str, key: str):
    columns = _table_columns(conn, "lumenis_subject_registry")
    identity = "subject_id" if product == "CTH" else "brand_focus_id"
    required = {identity, "domain_id", "status"}
    if not required.issubset(columns):
        raise ScopeValidationError("canonical Subject/BrandFocus registry schema is unavailable")
    registry_domain = "CTH" if product == "CTH" else "BMP"
    return conn.execute(
        f"SELECT {identity}, domain_id, status FROM lumenis_subject_registry "
        f"WHERE {identity}=? AND domain_id=? LIMIT 1",
        (key, registry_domain),
    ).fetchone()


def _exact_key(value: Any, field: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ScopeValidationError(f"{field} must be a canonical registry key")
    key = value.strip()
    if not key:
        return None
    if len(key) > 256 or key != value:
        raise ScopeValidationError(f"{field} must be a canonical registry key")
    return key


def resolve_scope(
    conn: sqlite3.Connection,
    *,
    product_id: Any,
    domain_id: Any = None,
    subject_id: Any = None,
    brand_focus_id: Any = None,
    requested_status: Any = None,
) -> ScopeDecision:
    """Check explicit registry membership; never infer or claim Evidence proof."""
    product, _domain = normalize_product_domain(product_id, domain_id)
    subject = _exact_key(subject_id, "subject_id")
    brand = _exact_key(brand_focus_id, "brand_focus_id")
    requested = str(requested_status or "").strip().upper()
    if requested not in {"", SCOPE_STATUS_UNASSIGNED, SCOPE_STATUS_UNVERIFIED}:
        raise ScopeValidationError("identity lookup cannot promote scope to VERIFIED")
    if subject and brand:
        raise ScopeValidationError("a record may carry only one domain-specific scope key")
    if product == "CTH" and brand:
        raise ScopeValidationError("CTH records cannot carry brand_focus_id")
    if product == "ZBMP" and subject:
        raise ScopeValidationError("BMP records cannot carry subject_id")

    key = subject if product == "CTH" else brand
    if key is None:
        return ScopeDecision()
    row = _registry_member(conn, product, key)
    if row is None:
        raise ScopeValidationError("scope key is not present in the canonical registry")
    if str(row[2] or "").strip().lower() in {"archived", "disabled", "deleted"}:
        raise ScopeValidationError("scope key is archived or unavailable")
    return ScopeDecision(
        subject_id=subject,
        brand_focus_id=brand,
        status=SCOPE_STATUS_UNVERIFIED,
    )


__all__ = [
    "ScopeDecision",
    "ScopeValidationError",
    "SCOPE_STATUS_UNASSIGNED",
    "SCOPE_STATUS_UNVERIFIED",
    "normalize_product_domain",
    "resolve_scope",
]

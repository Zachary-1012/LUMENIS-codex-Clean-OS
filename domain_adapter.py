# -*- coding: utf-8 -*-
"""
ZBC Domain Adapter（双域核心扩展）
====================================
在 CanonicalRecord 与各域专属记录之间做安全转换，强制域字段隔离。

硬约束：
  - ZBMP 不读 CTH 专项字段（taikoo_hui_specific / xhs_subject_match 等）
  - CTH 不读 ZBMP 多品牌字段（multi_brand_config / brand_profiles 等）
  - 转换失败时抛 ValueError，禁止静默吞异常
  - 不修改原始 CanonicalRecord（返回新对象）
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from canonical_data import (
    CanonicalRecord,
    PRODUCT_CTH,
    PRODUCT_ZBMP,
    SOURCE_TYPE_NOTE,
    SOURCE_TYPE_WEB_MENTION,
    SOURCE_TYPE_COLLECTED,
)
from domain_isolation import (
    DOMAIN_CTH,
    DOMAIN_ZBMP,
    DOMAIN_SYSTEM,
    product_to_domain,
    domain_to_product,
    resolve_domain_identity,
)

# ---------------------------------------------------------------------------
# 域专属字段黑名单（转换时强制剥离）
# ---------------------------------------------------------------------------
# CTH 专项字段：ZBMP 适配器必须剥离
CTH_ONLY_FIELDS = {
    "taikoo_hui_specific",
    "xhs_subject_match",
    "cth_production_flag",
    "guangzhou_taikoo_hui_verified",
    "is_taikoo_verified",
    "subject_words_version",
    "cth_evidence_namespace",
}

# ZBMP 多品牌字段：CTH 适配器必须剥离
ZBMP_ONLY_FIELDS = {
    "multi_brand_config",
    "brand_profiles",
    "brand_directory",
    "campaign_id",
    "zbmp_tenant_id",
    "multi_subject_scope",
    "brand_permission_scope",
}


def _strip_fields(data: Dict[str, Any], forbidden: set) -> Dict[str, Any]:
    """从 dict 中剥离禁用字段，返回新 dict（不修改原对象）。"""
    return {k: v for k, v in data.items() if k not in forbidden}


# ---------------------------------------------------------------------------
# 域专属记录（轻量 dataclass，仅承载该域可见字段）
# ---------------------------------------------------------------------------
@dataclass
class ZBMPRecord:
    """ZBMP 域专属记录：多品牌平台视图，已剥离 CTH 专项字段。"""
    canonical_id: str = ""
    product_id: str = PRODUCT_ZBMP
    domain_id: str = DOMAIN_ZBMP
    subject_id: str = ""
    brand_key: str = ""
    source_platform: str = ""
    title: str = ""
    content: str = ""
    url: str = ""
    author_name: str = ""
    publish_datetime: str = ""
    captured_at: str = ""
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    risk_level: str = "low"
    risk_score: int = 0
    engagement_likes: Optional[int] = None
    engagement_comments: Optional[int] = None
    engagement_collects: Optional[int] = None
    engagement_shares: Optional[int] = None
    topics: str = "[]"
    tags: str = "[]"
    event_hint: str = ""
    source_type: str = SOURCE_TYPE_NOTE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


@dataclass
class CTHRecord:
    """CTH 域专属记录，已剥离 ZBMP 多品牌字段。"""
    canonical_id: str = ""
    product_id: str = PRODUCT_CTH
    domain_id: str = DOMAIN_CTH
    subject_id: str = ""
    brand_key: str = ""
    source_platform: str = ""
    title: str = ""
    content: str = ""
    url: str = ""
    author_name: str = ""
    publish_datetime: str = ""
    captured_at: str = ""
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    risk_level: str = "low"
    risk_score: int = 0
    engagement_likes: Optional[int] = None
    engagement_comments: Optional[int] = None
    engagement_collects: Optional[int] = None
    engagement_shares: Optional[int] = None
    topics: str = "[]"
    tags: str = "[]"
    event_hint: str = ""
    source_type: str = SOURCE_TYPE_NOTE
    # Retained for response compatibility only; it is never Subject scope or
    # Evidence/Permission proof and is omitted from scoped CTH API projections.
    is_taikoo_verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


# ---------------------------------------------------------------------------
# BaseDomainAdapter 抽象类
# ---------------------------------------------------------------------------
class BaseDomainAdapter(ABC):
    """域适配器抽象基类。

    子类必须实现：
      - to_domain(canonical_record) -> domain-specific record
      - from_domain(domain_record) -> CanonicalRecord
    """

    domain_id: str = ""
    product_id: str = ""
    forbidden_fields: set = set()

    @abstractmethod
    def to_domain(self, record: CanonicalRecord) -> Any:
        """将 CanonicalRecord 转换为域专属记录。必须剥离禁用字段。"""
        ...

    @abstractmethod
    def from_domain(self, domain_record: Any) -> CanonicalRecord:
        """将域专属记录转换回 CanonicalRecord。"""
        ...

    def _validate_domain(self, record: CanonicalRecord) -> None:
        """校验记录的域身份是否匹配本适配器。不匹配抛 ValueError。"""
        if not isinstance(record, CanonicalRecord):
            raise ValueError("a CanonicalRecord is required")
        try:
            domain_id, product_id = resolve_domain_identity(
                record.domain_id or None, record.product_id or None,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("CanonicalRecord domain/product identity is invalid") from exc
        if domain_id != self.domain_id or product_id != self.product_id:
            raise ValueError(
                f"Domain mismatch: adapter={self.domain_id}/{self.product_id}, "
                f"record={domain_id}/{product_id}"
            )

    def safe_to_dict(self, record: CanonicalRecord) -> Dict[str, Any]:
        """安全地将 CanonicalRecord 转为 dict，已剥离本域禁用字段。"""
        data = record.to_dict()
        return _strip_fields(data, self.forbidden_fields)


# ---------------------------------------------------------------------------
# ZBMPAdapter
# ---------------------------------------------------------------------------
class ZBMPAdapter(BaseDomainAdapter):
    """ZBMP 多品牌平台适配器。

    强制剥离 CTH 专项字段（taikoo_hui_specific / xhs_subject_match 等），
    确保 ZBMP 消费者无法访问 CTH 生产真相数据。
    """
    domain_id = DOMAIN_ZBMP
    product_id = PRODUCT_ZBMP
    forbidden_fields = CTH_ONLY_FIELDS

    def to_domain(self, record: CanonicalRecord) -> ZBMPRecord:
        """CanonicalRecord -> ZBMPRecord（剥离 CTH 专项字段）。"""
        self._validate_domain(record)
        data = self.safe_to_dict(record)
        return ZBMPRecord(
            canonical_id=data.get("canonical_id", ""),
            product_id=self.product_id,
            domain_id=self.domain_id,
            subject_id=data.get("subject_id", ""),
            brand_key=data.get("brand_key", ""),
            source_platform=data.get("source_platform", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            url=data.get("url", ""),
            author_name=data.get("author_name", ""),
            publish_datetime=data.get("publish_datetime", ""),
            captured_at=data.get("captured_at", ""),
            sentiment=data.get("sentiment", "neutral"),
            sentiment_score=data.get("sentiment_score", 0.0),
            risk_level=data.get("risk_level", "low"),
            risk_score=data.get("risk_score", 0),
            engagement_likes=data.get("engagement_likes"),
            engagement_comments=data.get("engagement_comments"),
            engagement_collects=data.get("engagement_collects"),
            engagement_shares=data.get("engagement_shares"),
            topics=data.get("topics", "[]"),
            tags=data.get("tags", "[]"),
            event_hint=data.get("event_hint", ""),
            source_type=data.get("source_type", SOURCE_TYPE_NOTE),
            metadata={k: v for k, v in data.items()
                      if k not in ZBMPRecord.__dataclass_fields__
                      and k not in self.forbidden_fields},
        )

    def from_domain(self, domain_record: ZBMPRecord) -> CanonicalRecord:
        """ZBMPRecord -> CanonicalRecord。"""
        if not isinstance(domain_record, ZBMPRecord):
            raise ValueError(f"Expected ZBMPRecord, got {type(domain_record).__name__}")
        data = domain_record.to_dict()
        rec = CanonicalRecord(
            canonical_id=data.get("canonical_id") or _new_id(),
            product_id=self.product_id,
            domain_id=self.domain_id,
            subject_id=data.get("subject_id", ""),
            source_platform=data.get("source_platform", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            url=data.get("url", ""),
            author_name=data.get("author_name", ""),
            publish_datetime=data.get("publish_datetime", ""),
            captured_at=data.get("captured_at", ""),
            sentiment=data.get("sentiment", "neutral"),
            sentiment_score=data.get("sentiment_score", 0.0),
            risk_level=data.get("risk_level", "low"),
            risk_score=data.get("risk_score", 0),
            engagement_likes=data.get("engagement_likes"),
            engagement_comments=data.get("engagement_comments"),
            engagement_collects=data.get("engagement_collects"),
            engagement_shares=data.get("engagement_shares"),
            topics=data.get("topics", "[]"),
            tags=data.get("tags", "[]"),
            event_hint=data.get("event_hint", ""),
            source_type=data.get("source_type", SOURCE_TYPE_NOTE),
        )
        return rec


# ---------------------------------------------------------------------------
# CTHAdapter
# ---------------------------------------------------------------------------
class CTHAdapter(BaseDomainAdapter):
    """CTH commerce-operations adapter.

    Strips ZBMP-only fields and carries the exact CTH Subject unchanged.
    Missing focus remains blank; this adapter does not select a reference venue.
    """
    domain_id = DOMAIN_CTH
    product_id = PRODUCT_CTH
    forbidden_fields = ZBMP_ONLY_FIELDS

    def to_domain(self, record: CanonicalRecord) -> CTHRecord:
        """CanonicalRecord -> CTHRecord（保留原 CTH Subject，不创建焦点）。"""
        self._validate_domain(record)
        data = self.safe_to_dict(record)
        return CTHRecord(
            canonical_id=data.get("canonical_id", ""),
            product_id=self.product_id,
            domain_id=self.domain_id,
            subject_id=data.get("subject_id") or "",
            brand_key=data.get("brand_key") or "",
            source_platform=data.get("source_platform", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            url=data.get("url", ""),
            author_name=data.get("author_name", ""),
            publish_datetime=data.get("publish_datetime", ""),
            captured_at=data.get("captured_at", ""),
            sentiment=data.get("sentiment", "neutral"),
            sentiment_score=data.get("sentiment_score", 0.0),
            risk_level=data.get("risk_level", "low"),
            risk_score=data.get("risk_score", 0),
            engagement_likes=data.get("engagement_likes"),
            engagement_comments=data.get("engagement_comments"),
            engagement_collects=data.get("engagement_collects"),
            engagement_shares=data.get("engagement_shares"),
            topics=data.get("topics", "[]"),
            tags=data.get("tags", "[]"),
            event_hint=data.get("event_hint", ""),
            source_type=data.get("source_type", SOURCE_TYPE_NOTE),
            is_taikoo_verified=bool(data.get("is_taikoo_verified", False)),
            metadata={k: v for k, v in data.items()
                      if k not in CTHRecord.__dataclass_fields__
                      and k not in self.forbidden_fields},
        )

    def from_domain(self, domain_record: CTHRecord) -> CanonicalRecord:
        """CTHRecord -> CanonicalRecord。"""
        if not isinstance(domain_record, CTHRecord):
            raise ValueError(f"Expected CTHRecord, got {type(domain_record).__name__}")
        try:
            domain_id, product_id = resolve_domain_identity(
                domain_record.domain_id or None, domain_record.product_id or None,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("CTHRecord domain/product identity is invalid") from exc
        if domain_id != self.domain_id or product_id != self.product_id:
            raise ValueError(
                f"Domain mismatch: adapter={self.domain_id}/{self.product_id}, "
                f"record={domain_id}/{product_id}"
            )
        data = domain_record.to_dict()
        rec = CanonicalRecord(
            canonical_id=data.get("canonical_id") or _new_id(),
            product_id=self.product_id,
            domain_id=self.domain_id,
            subject_id=data.get("subject_id") or "",
            source_platform=data.get("source_platform", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            url=data.get("url", ""),
            author_name=data.get("author_name", ""),
            publish_datetime=data.get("publish_datetime", ""),
            captured_at=data.get("captured_at", ""),
            sentiment=data.get("sentiment", "neutral"),
            sentiment_score=data.get("sentiment_score", 0.0),
            risk_level=data.get("risk_level", "low"),
            risk_score=data.get("risk_score", 0),
            engagement_likes=data.get("engagement_likes"),
            engagement_comments=data.get("engagement_comments"),
            engagement_collects=data.get("engagement_collects"),
            engagement_shares=data.get("engagement_shares"),
            topics=data.get("topics", "[]"),
            tags=data.get("tags", "[]"),
            event_hint=data.get("event_hint", ""),
            source_type=data.get("source_type", SOURCE_TYPE_NOTE),
        )
        return rec


# ---------------------------------------------------------------------------
# 适配器工厂 + 便捷函数
# ---------------------------------------------------------------------------
_ADAPTERS = {
    DOMAIN_CTH: CTHAdapter(),
    DOMAIN_ZBMP: ZBMPAdapter(),
}


def get_adapter(domain_id: str) -> BaseDomainAdapter:
    """按已知 domain_id 获取适配器；未知域或无适配器的域必须失败。"""
    normalized = domain_to_product(domain_id)
    canonical_domain = product_to_domain(normalized)
    try:
        return _ADAPTERS[canonical_domain]
    except KeyError as exc:
        raise ValueError(f"No domain adapter is registered for {canonical_domain}") from exc


def get_adapter_by_product(product_id: str) -> BaseDomainAdapter:
    """按 product_id 获取适配器。"""
    return get_adapter(product_to_domain(product_id))


def adapt_to_domain(record: CanonicalRecord, domain_id: str) -> Any:
    """便捷函数：将 CanonicalRecord 转换为指定域的专属记录。"""
    adapter = get_adapter(domain_id)
    return adapter.to_domain(record)


def _new_id() -> str:
    import uuid
    return f"can_{uuid.uuid4().hex[:16]}"

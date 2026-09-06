# -*- coding: utf-8 -*-
"""
KOS 兴趣图谱信号（IC-040）
============================
依据：PCCC IC-040 §5（KOS 兴趣图谱信号契约）。
目标：基于 KOS 内容/互动数据构建兴趣图谱信号，为达人运营、内容推荐、
投流策略提供兴趣维度的决策支持。

核心能力：
1. 兴趣标签提取：从达人内容标签、话题、关键词中提取标准化兴趣标签
2. 内容聚类：基于标签/关键词相似度对内容进行聚类
3. 达人-兴趣关联：构建达人与兴趣标签的加权关联图谱
4. 兴趣热度计算：基于互动量、发布频率计算兴趣标签的热度
5. 可配置：标签来源、聚类算法、关联权重均可通过配置调整

与 KOS 平台规则配置（config/kos_platform_rules.json）兼容：
- 读取各平台的 engagement_weights 用于兴趣热度加权
- 平台特定的兴趣标签权重可扩展

设计原则：
- 纯计算模块，不直接写数据库（调用方负责持久化）
- 无外部依赖（不依赖 sklearn/numpy，使用纯 Python 实现）
- 缺失数据显式标记，不伪造兴趣标签
- 兴趣图谱信号作为 KOS 策略的输入因子，不替代核心规则
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ============================================================
# 配置
# ============================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    # 兴趣标签来源（可配置启用/禁用）
    "tag_sources": {
        "content_tags": True,       # 达人 content_tags 字段
        "top_topics": True,         # 达人 top_topics 字段
        "title_keywords": True,     # 笔记标题关键词
        "hashtags": True,           # 话题标签（#xxx）
    },
    # 内容聚类算法
    "clustering": {
        "algorithm": "jaccard",     # jaccard / cosine / cooccurrence
        "similarity_threshold": 0.3,  # 相似度阈值（0-1），高于此值归为同一簇
        "max_clusters": 50,         # 最大簇数量
        "min_cluster_size": 2,      # 最小簇大小（小于此值的簇被标记为 noise）
    },
    # 达人-兴趣关联权重
    "association_weights": {
        "tag_frequency": 0.4,       # 标签出现频率权重
        "engagement": 0.35,         # 互动量权重
        "recency": 0.15,            # 新近度权重（越新权重越高）
        "platform_boost": 0.1,      # 平台特定加成
    },
    # 兴趣热度计算
    "heat_calculation": {
        "engagement_weight": 0.6,   # 互动量权重
        "frequency_weight": 0.3,    # 发布频率权重
        "recency_weight": 0.1,      # 新近度权重
        "decay_days": 30,           # 时间衰减天数（半衰）
    },
    # 标签标准化
    "tag_normalization": {
        "min_length": 2,            # 最小标签长度
        "max_tags_per_content": 10, # 单条内容最大标签数
        "stopwords": ["的", "了", "是", "在", "我", "有", "和", "就", "不", "人",
                       "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
                       "the", "a", "an", "is", "are", "was", "were", "be", "been",
                       "and", "or", "but", "in", "on", "at", "to", "for", "of"],
    },
}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载兴趣图谱配置。

    优先级：指定路径 > config/kos_interest_graph.json > 默认配置
    与 kos_platform_rules.json 兼容：读取 engagement_weights 用于热度计算。
    """
    config = dict(DEFAULT_CONFIG)

    # 尝试加载自定义配置
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                custom = json.load(f)
            config = _deep_merge(config, custom)
        except Exception as e:
            print(f"[KOSInterestGraph] 加载自定义配置失败: {e}，使用默认配置")
    else:
        default_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "kos_interest_graph.json"
        )
        if os.path.exists(default_path):
            try:
                with open(default_path, "r", encoding="utf-8") as f:
                    custom = json.load(f)
                config = _deep_merge(config, custom)
            except Exception:
                pass

    # 从 kos_platform_rules.json 读取 engagement_weights（兼容）
    platform_rules_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "kos_platform_rules.json"
    )
    if os.path.exists(platform_rules_path):
        try:
            with open(platform_rules_path, "r", encoding="utf-8") as f:
                platform_rules = json.load(f)
            config["_platform_engagement_weights"] = {
                plat: rules.get("engagement_weights", {})
                for plat, rules in platform_rules.items()
                if isinstance(rules, dict) and "engagement_weights" in rules
            }
        except Exception:
            pass

    return config


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并配置字典。"""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ============================================================
# 数据模型
# ============================================================

@dataclass
class InterestTag:
    """兴趣标签。"""
    name: str
    frequency: int = 0              # 出现次数
    total_engagement: float = 0.0   # 累计互动量
    heat_score: float = 0.0         # 热度评分（0-1）
    associated_authors: int = 0     # 关联达人数
    platform: str = ""               # 来源平台
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentCluster:
    """内容聚类簇。"""
    cluster_id: str
    label: str = ""                  # 簇标签（高频标签组合）
    tags: List[str] = field(default_factory=list)  # 簇内标签
    content_ids: List[str] = field(default_factory=list)  # 簇内内容ID
    author_ids: List[str] = field(default_factory=list)   # 簇内达人ID
    size: int = 0
    avg_engagement: float = 0.0
    top_keywords: List[Tuple[str, int]] = field(default_factory=list)
    is_noise: bool = False           # 是否为噪声簇（小于最小簇大小）


@dataclass
class AuthorInterestEdge:
    """达人-兴趣关联边。"""
    author_id: str
    tag_name: str
    weight: float = 0.0              # 关联权重（0-1）
    tag_count: int = 0               # 该达人使用此标签的次数
    avg_engagement: float = 0.0      # 该标签内容的平均互动量
    last_used_days: int = 999        # 最近使用距今天数
    platform: str = ""


@dataclass
class InterestGraph:
    """兴趣图谱（完整信号输出）。"""
    tags: List[InterestTag] = field(default_factory=list)
    clusters: List[ContentCluster] = field(default_factory=list)
    author_edges: List[AuthorInterestEdge] = field(default_factory=list)
    tag_adjacency: Dict[str, Dict[str, float]] = field(default_factory=dict)  # 标签共现矩阵
    config_used: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)

    def get_top_tags(self, n: int = 10) -> List[InterestTag]:
        """获取热度最高的 N 个兴趣标签。"""
        return sorted(self.tags, key=lambda t: t.heat_score, reverse=True)[:n]

    def get_author_interests(self, author_id: str, top_n: int = 5) -> List[AuthorInterestEdge]:
        """获取指定达人的兴趣标签（按权重排序）。"""
        edges = [e for e in self.author_edges if e.author_id == author_id]
        return sorted(edges, key=lambda e: e.weight, reverse=True)[:top_n]

    def get_related_tags(self, tag_name: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """获取与指定标签共现度最高的相关标签。"""
        if tag_name not in self.tag_adjacency:
            return []
        related = self.tag_adjacency[tag_name]
        return sorted(related.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于 API 响应/持久化）。"""
        return {
            "tags": [
                {"name": t.name, "frequency": t.frequency, "heat_score": round(t.heat_score, 4),
                 "total_engagement": t.total_engagement, "associated_authors": t.associated_authors,
                 "platform": t.platform}
                for t in self.tags
            ],
            "clusters": [
                {"cluster_id": c.cluster_id, "label": c.label, "size": c.size,
                 "tags": c.tags[:10], "is_noise": c.is_noise,
                 "top_keywords": [{"word": w, "count": c} for w, c in c.top_keywords[:10]]}
                for c in self.clusters
            ],
            "author_edges_count": len(self.author_edges),
            "stats": self.stats,
        }


# ============================================================
# 兴趣标签提取
# ============================================================

class InterestTagExtractor:
    """兴趣标签提取器。

    从 KOS 达人数据（content_tags / top_topics）和内容数据（标题/话题）中
    提取标准化兴趣标签。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_config()
        self.stopwords = set(self.config.get("tag_normalization", {}).get("stopwords", []))
        self.min_length = self.config.get("tag_normalization", {}).get("min_length", 2)
        self.max_tags = self.config.get("tag_normalization", {}).get("max_tags_per_content", 10)

    def normalize_tag(self, tag: str) -> Optional[str]:
        """标准化标签：去空白、转小写、过滤停用词和过短标签。"""
        if not tag:
            return None
        tag = tag.strip().lower()
        # 去除 # 号前缀
        if tag.startswith("#"):
            tag = tag[1:]
        tag = tag.strip()
        if len(tag) < self.min_length:
            return None
        if tag in self.stopwords:
            return None
        return tag

    def extract_from_author_profile(self, author: Dict[str, Any]) -> List[str]:
        """从达人档案提取兴趣标签。

        Args:
            author: 达人档案字典，需包含 content_tags / top_topics 字段
                    （来自 kos_profiles 表，JSON 字符串或列表）

        Returns:
            标准化后的兴趣标签列表
        """
        sources = self.config.get("tag_sources", {})
        tags: List[str] = []

        # 从 content_tags 提取
        if sources.get("content_tags", True):
            raw_tags = author.get("content_tags", "")
            tags.extend(self._parse_tag_field(raw_tags))

        # 从 top_topics 提取
        if sources.get("top_topics", True):
            raw_topics = author.get("top_topics", "")
            tags.extend(self._parse_tag_field(raw_topics))

        return self._deduplicate_and_limit(tags)

    def extract_from_content(self, content: Dict[str, Any]) -> List[str]:
        """从单条内容提取兴趣标签。

        Args:
            content: 内容字典，需包含 title / tags / hashtags 字段

        Returns:
            标准化后的兴趣标签列表
        """
        sources = self.config.get("tag_sources", {})
        tags: List[str] = []

        # 从内容标签提取
        if sources.get("content_tags", True):
            raw_tags = content.get("tags", content.get("content_tags", ""))
            tags.extend(self._parse_tag_field(raw_tags))

        # 从标题关键词提取（简单分词：按空格/标点分割）
        if sources.get("title_keywords", True):
            title = content.get("title", "")
            if title:
                keywords = self._tokenize(title)
                tags.extend(keywords)

        # 从话题标签提取（#xxx）
        if sources.get("hashtags", True):
            text = f"{content.get('title', '')} {content.get('content', '')}"
            hashtags = self._extract_hashtags(text)
            tags.extend(hashtags)

        return self._deduplicate_and_limit(tags)

    def _parse_tag_field(self, raw: Any) -> List[str]:
        """解析标签字段（支持 JSON 字符串、列表、逗号分隔字符串）。"""
        if not raw:
            return []
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, str):
            raw = raw.strip()
            if not raw:
                return []
            # 尝试 JSON 解析
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    items = parsed
                elif isinstance(parsed, dict):
                    # top_topics 可能是 [[tag, count], ...] 格式
                    items = [item[0] if isinstance(item, (list, tuple)) else item
                             for item in parsed.items()]
                else:
                    items = [raw]
            except (json.JSONDecodeError, ValueError):
                items = [t.strip() for t in raw.split(",") if t.strip()]
        else:
            return []

        normalized = []
        for item in items:
            if isinstance(item, (list, tuple)) and len(item) > 0:
                item = item[0]
            tag = self.normalize_tag(str(item))
            if tag:
                normalized.append(tag)
        return normalized

    def _tokenize(self, text: str) -> List[str]:
        """简单分词（按标点和空格分割，适用于中英文混合）。"""
        if not text:
            return []
        # 替换常见标点为空格
        for punct in "，。！？、；：""''（）【】《》…—·.,!?;:\"'()[]<>":
            text = text.replace(punct, " ")
        words = text.split()
        normalized = []
        for w in words:
            tag = self.normalize_tag(w)
            if tag:
                normalized.append(tag)
        return normalized

    def _extract_hashtags(self, text: str) -> List[str]:
        """从文本中提取 #话题标签。"""
        if not text:
            return []
        tags = []
        i = 0
        while i < len(text):
            if text[i] == "#":
                j = i + 1
                while j < len(text) and text[j] not in " #\n\t，。！？、；：":
                    j += 1
                if j > i + 1:
                    tag = self.normalize_tag(text[i:j])
                    if tag:
                        tags.append(tag)
                i = j
            else:
                i += 1
        return tags

    def _deduplicate_and_limit(self, tags: List[str]) -> List[str]:
        """去重并限制数量。"""
        seen = set()
        result = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
                if len(result) >= self.max_tags:
                    break
        return result


# ============================================================
# 内容聚类
# ============================================================

class ContentClusterer:
    """内容聚类器。

    基于标签相似度对内容进行聚类。
    支持 Jaccard 相似度、余弦相似度、共现度三种算法。
    纯 Python 实现，无外部依赖。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_config()
        self.cluster_config = self.config.get("clustering", {})
        self.algorithm = self.cluster_config.get("algorithm", "jaccard")
        self.threshold = self.cluster_config.get("similarity_threshold", 0.3)
        self.max_clusters = self.cluster_config.get("max_clusters", 50)
        self.min_cluster_size = self.cluster_config.get("min_cluster_size", 2)

    def cluster(self, contents: List[Dict[str, Any]]) -> List[ContentCluster]:
        """对内容列表进行聚类。

        Args:
            contents: 内容列表，每项需包含 id 和 tags 字段

        Returns:
            聚类簇列表
        """
        if not contents:
            return []

        # 为每条内容构建标签集合
        content_tags: Dict[str, Set[str]] = {}
        content_engagement: Dict[str, float] = {}
        content_authors: Dict[str, str] = {}
        for c in contents:
            cid = str(c.get("id", c.get("note_id", c.get("content_id", ""))))
            if not cid:
                continue
            tags = set(c.get("tags", []))
            if not tags:
                continue
            content_tags[cid] = tags
            content_engagement[cid] = float(c.get("engagement", c.get("total_engagement", 0)))
            content_authors[cid] = str(c.get("author_id", ""))

        if not content_tags:
            return []

        # 贪心聚类（单遍：每条内容归入最相似的已有簇，否则新建簇）
        clusters: List[Dict[str, Any]] = []
        for cid, tags in content_tags.items():
            best_cluster = -1
            best_sim = 0.0
            for idx, cluster in enumerate(clusters):
                sim = self._cluster_similarity(tags, cluster["tags"])
                if sim > best_sim and sim >= self.threshold:
                    best_sim = sim
                    best_cluster = idx
            if best_cluster >= 0 and len(clusters) < self.max_clusters:
                clusters[best_cluster]["content_ids"].append(cid)
                clusters[best_cluster]["tags"].update(tags)
                clusters[best_cluster]["engagement_sum"] += content_engagement.get(cid, 0)
                clusters[best_cluster]["authors"].add(content_authors.get(cid, ""))
            else:
                clusters.append({
                    "content_ids": [cid],
                    "tags": set(tags),
                    "engagement_sum": content_engagement.get(cid, 0),
                    "authors": {content_authors.get(cid, "")},
                })

        # 转换为 ContentCluster 对象
        result = []
        for idx, cluster in enumerate(clusters):
            size = len(cluster["content_ids"])
            is_noise = size < self.min_cluster_size
            # 计算簇标签（高频标签）
            tag_counter = Counter()
            for cid in cluster["content_ids"]:
                tag_counter.update(content_tags.get(cid, set()))
            top_keywords = tag_counter.most_common(10)
            label = " + ".join([w for w, _ in top_keywords[:3]]) if top_keywords else f"cluster_{idx}"

            result.append(ContentCluster(
                cluster_id=f"cluster_{idx:03d}",
                label=label,
                tags=sorted(cluster["tags"]),
                content_ids=cluster["content_ids"],
                author_ids=[a for a in cluster["authors"] if a],
                size=size,
                avg_engagement=cluster["engagement_sum"] / size if size > 0 else 0,
                top_keywords=top_keywords,
                is_noise=is_noise,
            ))

        return sorted(result, key=lambda c: c.size, reverse=True)

    def _cluster_similarity(self, tags: Set[str], cluster_tags: Set[str]) -> float:
        """计算内容标签集合与簇标签集合的相似度。"""
        if not tags or not cluster_tags:
            return 0.0
        if self.algorithm == "jaccard":
            intersection = len(tags & cluster_tags)
            union = len(tags | cluster_tags)
            return intersection / union if union > 0 else 0.0
        elif self.algorithm == "cosine":
            # 基于标签集合的余弦相似度
            intersection = len(tags & cluster_tags)
            norm1 = math.sqrt(len(tags))
            norm2 = math.sqrt(len(cluster_tags))
            return intersection / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
        elif self.algorithm == "cooccurrence":
            # 共现度：交集大小 / 较小集合大小
            intersection = len(tags & cluster_tags)
            min_size = min(len(tags), len(cluster_tags))
            return intersection / min_size if min_size > 0 else 0.0
        else:
            # 默认 Jaccard
            intersection = len(tags & cluster_tags)
            union = len(tags | cluster_tags)
            return intersection / union if union > 0 else 0.0


# ============================================================
# 兴趣图谱构建器
# ============================================================

class KOSInterestGraphBuilder:
    """KOS 兴趣图谱构建器（IC-040 核心入口）。

    整合标签提取、内容聚类、达人-兴趣关联、热度计算，
    输出完整的兴趣图谱信号。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_config()
        self.extractor = InterestTagExtractor(self.config)
        self.clusterer = ContentClusterer(self.config)
        self.assoc_weights = self.config.get("association_weights", {})
        self.heat_config = self.config.get("heat_calculation", {})

    def build(self, authors: List[Dict[str, Any]],
              contents: Optional[List[Dict[str, Any]]] = None) -> InterestGraph:
        """构建兴趣图谱。

        Args:
            authors: 达人档案列表（来自 kos_profiles 表）
            contents: 内容列表（可选，来自 notes 表，用于聚类和热度计算）

        Returns:
            InterestGraph 完整兴趣图谱信号
        """
        graph = InterestGraph(config_used=self._sanitize_config())

        # 1. 从达人档案提取兴趣标签
        author_tag_map: Dict[str, List[str]] = {}
        all_tags_counter: Counter = Counter()
        tag_engagement: Dict[str, float] = defaultdict(float)
        tag_authors: Dict[str, Set[str]] = defaultdict(set)
        tag_platform: Dict[str, str] = {}

        for author in authors:
            author_id = str(author.get("author_id", ""))
            if not author_id:
                continue
            platform = str(author.get("platform", author.get("source_platform", "")))
            tags = self.extractor.extract_from_author_profile(author)
            author_tag_map[author_id] = tags
            engagement = float(author.get("total_engagement", author.get("avg_engagement", 0)))
            for tag in tags:
                all_tags_counter[tag] += 1
                tag_engagement[tag] += engagement
                tag_authors[tag].add(author_id)
                if platform and tag not in tag_platform:
                    tag_platform[tag] = platform

        # 2. 从内容提取标签（增强）
        content_tag_map: Dict[str, List[str]] = {}
        if contents:
            for content in contents:
                cid = str(content.get("id", content.get("note_id", "")))
                if not cid:
                    continue
                tags = self.extractor.extract_from_content(content)
                content_tag_map[cid] = tags
                author_id = str(content.get("author_id", ""))
                engagement = float(content.get("engagement", content.get("total_engagement", 0)))
                for tag in tags:
                    all_tags_counter[tag] += 1
                    tag_engagement[tag] += engagement
                    if author_id:
                        tag_authors[tag].add(author_id)

        # 3. 计算兴趣标签热度
        max_engagement = max(tag_engagement.values()) if tag_engagement else 1.0
        max_frequency = max(all_tags_counter.values()) if all_tags_counter else 1
        for tag_name, freq in all_tags_counter.items():
            engagement_norm = tag_engagement[tag_name] / max_engagement if max_engagement > 0 else 0
            freq_norm = freq / max_frequency if max_frequency > 0 else 0
            heat_score = (
                engagement_norm * self.heat_config.get("engagement_weight", 0.6)
                + freq_norm * self.heat_config.get("frequency_weight", 0.3)
            )
            graph.tags.append(InterestTag(
                name=tag_name,
                frequency=freq,
                total_engagement=tag_engagement[tag_name],
                heat_score=min(1.0, heat_score),
                associated_authors=len(tag_authors[tag_name]),
                platform=tag_platform.get(tag_name, ""),
            ))

        # 4. 内容聚类
        if contents:
            cluster_input = []
            for content in contents:
                cid = str(content.get("id", content.get("note_id", "")))
                if cid in content_tag_map:
                    cluster_input.append({
                        "id": cid,
                        "tags": content_tag_map[cid],
                        "engagement": float(content.get("engagement", 0)),
                        "author_id": str(content.get("author_id", "")),
                    })
            graph.clusters = self.clusterer.cluster(cluster_input)

        # 5. 构建达人-兴趣关联边
        for author_id, tags in author_tag_map.items():
            if not tags:
                continue
            # 查找该达人的内容互动数据
            author_engagement = 0.0
            for author in authors:
                if str(author.get("author_id", "")) == author_id:
                    author_engagement = float(author.get("total_engagement", 0))
                    break
            for tag in tags:
                tag_freq = tags.count(tag)
                # 关联权重 = 频率权重 + 互动权重（简化计算）
                freq_norm = tag_freq / len(tags) if tags else 0
                engagement_norm = min(1.0, author_engagement / 10000) if author_engagement > 0 else 0
                weight = (
                    freq_norm * self.assoc_weights.get("tag_frequency", 0.4)
                    + engagement_norm * self.assoc_weights.get("engagement", 0.35)
                )
                graph.author_edges.append(AuthorInterestEdge(
                    author_id=author_id,
                    tag_name=tag,
                    weight=min(1.0, weight),
                    tag_count=tag_freq,
                    avg_engagement=author_engagement / tag_freq if tag_freq > 0 else 0,
                    platform=tag_platform.get(tag, ""),
                ))

        # 6. 构建标签共现矩阵
        cooccurrence: Dict[str, Counter] = defaultdict(Counter)
        for tags in author_tag_map.values():
            for i, t1 in enumerate(tags):
                for t2 in tags[i + 1:]:
                    if t1 != t2:
                        cooccurrence[t1][t2] += 1
                        cooccurrence[t2][t1] += 1
        for content_tags in content_tag_map.values():
            for i, t1 in enumerate(content_tags):
                for t2 in content_tags[i + 1:]:
                    if t1 != t2:
                        cooccurrence[t1][t2] += 1
                        cooccurrence[t2][t1] += 1
        # 归一化共现度
        for tag, neighbors in cooccurrence.items():
            total = sum(neighbors.values())
            if total > 0:
                graph.tag_adjacency[tag] = {n: c / total for n, c in neighbors.items()}

        # 7. 统计信息
        graph.stats = {
            "total_authors": len(author_tag_map),
            "total_tags": len(graph.tags),
            "total_clusters": len(graph.clusters),
            "noise_clusters": sum(1 for c in graph.clusters if c.is_noise),
            "total_edges": len(graph.author_edges),
            "avg_tags_per_author": round(
                sum(len(t) for t in author_tag_map.values()) / len(author_tag_map)
                if author_tag_map else 0, 2
            ),
            "top_tag": graph.tags[0].name if graph.tags else "",
            "build_timestamp": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
        }

        return graph

    def _sanitize_config(self) -> Dict[str, Any]:
        """清理配置（移除平台权重等运行时数据，仅保留可序列化配置）。"""
        config = {}
        for key, value in self.config.items():
            if not key.startswith("_"):
                config[key] = value
        return config


# ============================================================
# 便捷函数
# ============================================================

def build_interest_graph(authors: List[Dict[str, Any]],
                          contents: Optional[List[Dict[str, Any]]] = None,
                          config_path: Optional[str] = None) -> InterestGraph:
    """便捷函数：构建兴趣图谱。

    Args:
        authors: 达人档案列表
        contents: 内容列表（可选）
        config_path: 自定义配置路径（可选）

    Returns:
        InterestGraph 兴趣图谱信号
    """
    config = load_config(config_path)
    builder = KOSInterestGraphBuilder(config)
    return builder.build(authors, contents)


def get_author_interest_vector(author: Dict[str, Any],
                                 top_n: int = 10) -> List[Dict[str, Any]]:
    """获取单个达人的兴趣向量（标签+权重）。

    Args:
        author: 达人档案
        top_n: 返回前 N 个标签

    Returns:
        [{"tag": str, "weight": float}, ...]
    """
    extractor = InterestTagExtractor()
    tags = extractor.extract_from_author_profile(author)
    if not tags:
        return []
    counter = Counter(tags)
    total = sum(counter.values())
    return [
        {"tag": tag, "weight": round(count / total, 4)}
        for tag, count in counter.most_common(top_n)
    ]

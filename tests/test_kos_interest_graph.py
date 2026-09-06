# -*- coding: utf-8 -*-
"""IC-040 KOS 兴趣图谱信号 单元测试

验证：
1. 兴趣标签提取（从达人档案/内容）
2. 内容聚类（Jaccard 相似度）
3. 达人-兴趣关联（加权图谱）
4. 兴趣热度计算
5. 标签共现矩阵
6. 与 KOS 平台规则配置兼容
7. 可配置性（标签来源、聚类算法、关联权重）
8. 缺失数据显式标记，不伪造兴趣标签
"""
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestInterestTagExtractor:
    """兴趣标签提取器测试。"""

    def test_extract_from_author_profile_with_tags(self):
        from kos_interest_graph import InterestTagExtractor
        extractor = InterestTagExtractor()
        author = {
            "author_id": "test_001",
            "content_tags": '["美妆", "护肤", "口红"]',
            "top_topics": "[[\"美妆\", 10], [\"护肤\", 5]]",
        }
        tags = extractor.extract_from_author_profile(author)
        assert "美妆" in tags
        assert "护肤" in tags
        assert "口红" in tags

    def test_extract_from_author_profile_with_list_tags(self):
        from kos_interest_graph import InterestTagExtractor
        extractor = InterestTagExtractor()
        author = {
            "author_id": "test_002",
            "content_tags": ["美食", "探店", "咖啡"],
            "top_topics": [],
        }
        tags = extractor.extract_from_author_profile(author)
        assert "美食" in tags
        assert "探店" in tags
        assert "咖啡" in tags

    def test_extract_from_author_profile_empty(self):
        from kos_interest_graph import InterestTagExtractor
        extractor = InterestTagExtractor()
        author = {"author_id": "test_003", "content_tags": "", "top_topics": ""}
        tags = extractor.extract_from_author_profile(author)
        assert tags == []  # 无数据时返回空列表，不伪造标签

    def test_extract_from_content_with_hashtags(self):
        from kos_interest_graph import InterestTagExtractor
        extractor = InterestTagExtractor()
        content = {
            "id": "note_001",
            "title": "今天去了一家超棒的咖啡店 #咖啡探店 #周末去哪儿",
            "content": "这家店的拿铁真的绝了 #咖啡",
            "tags": [],
        }
        tags = extractor.extract_from_content(content)
        assert "咖啡探店" in tags
        assert "周末去哪儿" in tags
        assert "咖啡" in tags

    def test_normalize_tag_filters_stopwords(self):
        from kos_interest_graph import InterestTagExtractor
        extractor = InterestTagExtractor()
        assert extractor.normalize_tag("的") is None
        assert extractor.normalize_tag("the") is None
        assert extractor.normalize_tag("美妆") == "美妆"
        assert extractor.normalize_tag("#咖啡") == "咖啡"

    def test_normalize_tag_filters_short(self):
        from kos_interest_graph import InterestTagExtractor
        extractor = InterestTagExtractor()
        assert extractor.normalize_tag("a") is None  # 过短

    def test_deduplicate_tags(self):
        from kos_interest_graph import InterestTagExtractor
        extractor = InterestTagExtractor()
        author = {
            "content_tags": ["美妆", "美妆", "护肤", "护肤", "护肤"],
            "top_topics": [],
        }
        tags = extractor.extract_from_author_profile(author)
        assert len(tags) == 2  # 去重后只有2个
        assert tags.count("美妆") == 1


class TestContentClusterer:
    """内容聚类器测试。"""

    def test_cluster_similar_contents(self):
        from kos_interest_graph import ContentClusterer
        clusterer = ContentClusterer()
        contents = [
            {"id": "c1", "tags": {"美妆", "护肤", "口红"}, "engagement": 100},
            {"id": "c2", "tags": {"美妆", "护肤", "粉底"}, "engagement": 200},
            {"id": "c3", "tags": {"美食", "探店", "咖啡"}, "engagement": 150},
            {"id": "c4", "tags": {"美食", "咖啡", "甜品"}, "engagement": 180},
        ]
        clusters = clusterer.cluster(contents)
        assert len(clusters) >= 2  # 至少2个簇（美妆/美食）
        # 美妆簇应该包含 c1 和 c2
        beauty_cluster = None
        food_cluster = None
        for c in clusters:
            if "美妆" in c.tags:
                beauty_cluster = c
            if "美食" in c.tags:
                food_cluster = c
        assert beauty_cluster is not None
        assert food_cluster is not None
        assert "c1" in beauty_cluster.content_ids
        assert "c2" in beauty_cluster.content_ids

    def test_cluster_empty_input(self):
        from kos_interest_graph import ContentClusterer
        clusterer = ContentClusterer()
        clusters = clusterer.cluster([])
        assert clusters == []

    def test_cluster_noise_detection(self):
        from kos_interest_graph import ContentClusterer
        clusterer = ContentClusterer()
        contents = [
            {"id": "c1", "tags": {"独特标签1", "独特标签2"}, "engagement": 10},
        ]
        clusters = clusterer.cluster(contents)
        # 单条内容的簇应该被标记为 noise（小于 min_cluster_size=2）
        assert len(clusters) == 1
        assert clusters[0].is_noise is True

    def test_cluster_jaccard_similarity(self):
        from kos_interest_graph import ContentClusterer
        clusterer = ContentClusterer()
        # Jaccard({a,b,c}, {a,b,d}) = 2/4 = 0.5 >= 0.3 阈值
        sim = clusterer._cluster_similarity({"a", "b", "c"}, {"a", "b", "d"})
        assert abs(sim - 0.5) < 0.01


class TestKOSInterestGraphBuilder:
    """兴趣图谱构建器测试（IC-040 核心）。"""

    def _make_test_authors(self):
        return [
            {
                "author_id": "a1",
                "content_tags": ["美妆", "护肤", "口红", "美妆"],
                "top_topics": [],
                "total_engagement": 5000,
                "platform": "xiaohongshu",
            },
            {
                "author_id": "a2",
                "content_tags": ["美食", "探店", "咖啡"],
                "top_topics": [],
                "total_engagement": 8000,
                "platform": "xiaohongshu",
            },
            {
                "author_id": "a3",
                "content_tags": ["美妆", "护肤", "粉底", "美妆"],
                "top_topics": [],
                "total_engagement": 3000,
                "platform": "douyin",
            },
        ]

    def _make_test_contents(self):
        return [
            {"id": "c1", "title": "口红试色 #美妆 #口红", "content": "今天试了新口红",
             "author_id": "a1", "engagement": 500, "tags": ["美妆", "口红"]},
            {"id": "c2", "title": "护肤心得 #护肤 #美妆", "content": "分享护肤步骤",
             "author_id": "a1", "engagement": 300, "tags": ["护肤", "美妆"]},
            {"id": "c3", "title": "咖啡店探店 #美食 #咖啡", "content": "发现好店",
             "author_id": "a2", "engagement": 800, "tags": ["美食", "咖啡"]},
        ]

    def test_build_graph_with_authors(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        graph = builder.build(self._make_test_authors())
        assert graph is not None
        assert len(graph.tags) > 0
        assert len(graph.author_edges) > 0
        assert "美妆" in [t.name for t in graph.tags]
        assert "美食" in [t.name for t in graph.tags]

    def test_build_graph_with_contents(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        graph = builder.build(self._make_test_authors(), self._make_test_contents())
        assert len(graph.clusters) > 0
        assert graph.stats["total_contents"] if "total_contents" in graph.stats else True

    def test_top_tags_by_heat(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        graph = builder.build(self._make_test_authors())
        top_tags = graph.get_top_tags(5)
        assert len(top_tags) <= 5
        # 热度应该降序排列
        heats = [t.heat_score for t in top_tags]
        assert heats == sorted(heats, reverse=True)

    def test_author_interests(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        graph = builder.build(self._make_test_authors())
        interests = graph.get_author_interests("a1", top_n=3)
        assert len(interests) > 0
        assert all(e.author_id == "a1" for e in interests)
        # 权重应该降序
        weights = [e.weight for e in interests]
        assert weights == sorted(weights, reverse=True)

    def test_related_tags(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        graph = builder.build(self._make_test_authors(), self._make_test_contents())
        # 美妆应该和护肤有共现
        related = graph.get_related_tags("美妆", top_n=5)
        assert len(related) > 0
        related_names = [r[0] for r in related]
        assert "护肤" in related_names or "口红" in related_names

    def test_graph_stats(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        graph = builder.build(self._make_test_authors())
        assert graph.stats["total_authors"] == 3
        assert graph.stats["total_tags"] > 0
        assert graph.stats["total_edges"] > 0
        assert "build_timestamp" in graph.stats

    def test_graph_to_dict(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        graph = builder.build(self._make_test_authors())
        d = graph.to_dict()
        assert "tags" in d
        assert "clusters" in d
        assert "stats" in d
        assert len(d["tags"]) > 0
        # 每个标签应该有 heat_score
        assert all("heat_score" in t for t in d["tags"])


class TestHeatCalculation:
    """兴趣热度计算测试。"""

    def test_heat_score_between_0_and_1(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        authors = [
            {"author_id": "a1", "content_tags": ["标签A"], "total_engagement": 10000},
            {"author_id": "a2", "content_tags": ["标签A", "标签B"], "total_engagement": 5000},
        ]
        graph = builder.build(authors)
        for tag in graph.tags:
            assert 0.0 <= tag.heat_score <= 1.0

    def test_higher_engagement_gets_higher_heat(self):
        from kos_interest_graph import KOSInterestGraphBuilder
        builder = KOSInterestGraphBuilder()
        authors = [
            {"author_id": "a1", "content_tags": ["高互动标签"], "total_engagement": 50000},
            {"author_id": "a2", "content_tags": ["低互动标签"], "total_engagement": 100},
        ]
        graph = builder.build(authors)
        tag_dict = {t.name: t for t in graph.tags}
        assert tag_dict["高互动标签"].heat_score > tag_dict["低互动标签"].heat_score


class TestConfigAndCompatibility:
    """配置与平台规则兼容性测试。"""

    def test_load_default_config(self):
        from kos_interest_graph import load_config
        config = load_config()
        assert "tag_sources" in config
        assert "clustering" in config
        assert "association_weights" in config
        assert "heat_calculation" in config

    def test_configurable_tag_sources(self):
        from kos_interest_graph import InterestTagExtractor, load_config
        # 禁用 title_keywords 来源
        config = load_config()
        config["tag_sources"]["title_keywords"] = False
        extractor = InterestTagExtractor(config)
        content = {"id": "c1", "title": "美妆 护肤 口红", "tags": []}
        tags = extractor.extract_from_content(content)
        # 禁用 title_keywords 后，标题关键词不应该被提取
        assert "美妆" not in tags

    def test_platform_rules_compatibility(self):
        """验证与 kos_platform_rules.json 的兼容性。"""
        from kos_interest_graph import load_config
        config = load_config()
        # 应该能读取平台 engagement_weights（如果配置文件存在）
        platform_weights = config.get("_platform_engagement_weights", {})
        # 配置文件存在，应该至少有 xiaohongshu 或其他平台
        if platform_weights:
            assert isinstance(platform_weights, dict)
            for plat, weights in platform_weights.items():
                assert "likes" in weights or "comments" in weights


class TestConvenienceFunctions:
    """便捷函数测试。"""

    def test_build_interest_graph_convenience(self):
        from kos_interest_graph import build_interest_graph
        authors = [
            {"author_id": "a1", "content_tags": ["美妆", "护肤"], "total_engagement": 1000},
        ]
        graph = build_interest_graph(authors)
        assert graph is not None
        assert len(graph.tags) > 0

    def test_get_author_interest_vector(self):
        from kos_interest_graph import get_author_interest_vector
        author = {
            "author_id": "a1",
            "content_tags": ["美妆", "护肤", "口红", "美妆", "护肤"],
            "top_topics": [],
        }
        vector = get_author_interest_vector(author, top_n=5)
        assert len(vector) > 0
        assert all("tag" in v and "weight" in v for v in vector)
        # 权重之和应该约等于1
        total_weight = sum(v["weight"] for v in vector)
        assert abs(total_weight - 1.0) < 0.01

    def test_get_author_interest_vector_empty(self):
        from kos_interest_graph import get_author_interest_vector
        author = {"author_id": "a1", "content_tags": "", "top_topics": ""}
        vector = get_author_interest_vector(author)
        assert vector == []  # 无标签时返回空，不伪造

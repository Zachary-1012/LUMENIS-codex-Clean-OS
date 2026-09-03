# -*- coding: utf-8 -*-
"""c-TF-IDF 主题词提取测试（BERTopic 算法轻量落地）。"""
from scripts.topic_words import extract_topic_words, topic_label, tokenize


def test_tokenize_filters_stopwords_and_keeps_cn_terms():
    toks = tokenize("这个产品很好用，强烈推荐给大家，YSL小金条确实不错")
    assert "这个" not in toks and "大家" not in toks  # 停用词过滤
    assert any("小金" in t or "金条" in t for t in toks)  # 2-gram 覆盖
    assert "ysl" in toks  # 英文小写化整词


def test_extract_topic_words_highlights_distinctive_term():
    # 两文档都提"防晒"，其中一文档提"敏感肌"——防晒/防晒霜 2-gram 应高频
    docs = [
        "这款防晒霜真的不错，敏感肌也可以用，不油腻",
        "强烈推荐这款防晒，夏天必备，敏感肌友好",
    ]
    words = extract_topic_words(docs, top_k=8)
    assert words
    top = [w for w, _ in words[:5]]
    assert any("防晒" in w for w in top)  # 高频主题词居前
    assert any("敏感" in w or "感肌" in w for w, _ in words)  # 区分性词被保留


def test_topic_label_and_empty():
    label = topic_label(["这个产品很好用", "确实不错值得买"], top_k=3)
    assert isinstance(label, str) and label
    assert extract_topic_words([]) == []
    assert topic_label([]) == "未命名主题"

# -*- coding: utf-8 -*-
"""轻量 c-TF-IDF 主题词提取（研究落地：BERTopic 核心算法，零重依赖）。

BERTopic（MaartenGr/BERTopic, 7814★）用 BERT 聚类 + c-TF-IDF 提取可解释主题词。
本模块只提取其**可解释主题词算法**（c-TF-IDF：类内词频 × 逆类频率），
用纯标准库实现（连续中文字符串 + 英文单词作 token，配合停用词/长度过滤），
服务 ZBC 的 Topic 自动打标 / 事件摘要，不引入 sentence-transformers/torch 重依赖。

c-TF-IDF(w, C) = (tf_w / total_words_C) * log(1 + n_docs_C / df_w)
  其中 tf_w=词在类 C 的总词频，total_words_C=类 C 总词数，n_docs_C=类 C 文档数，df_w=含词文档数。
  高类内频率 + 低文档频率（词更聚焦于少数文档）-> 高分，即「最能代表该类」的词。

用法：
  from scripts.topic_words import extract_topic_words
  words = extract_topic_words(docs, top_k=8)   # [(word, score), ...]
"""
import math
import re

# 中文连续串 / 英文单词
_CN_RE = re.compile(r"[\u4e00-\u9fa5]+")
_EN_RE = re.compile(r"[a-zA-Z]{3,}")

# 中文弱连接字：2-gram 任一端为这些字则剔除（"的了也我可..."类虚字/助词）
WEAK_EDGE = set("的了也我可以不真很就是这那我你他上下来去在于和有被把对就吧呢吗啊让给又都到从着过以会能怎最再只")

# 通用中文停用词（舆情/平台高频噪声）
STOPWORDS = {
    "一个", "这个", "那个", "什么", "怎么", "我们", "你们", "他们", "自己", "没有",
    "就是", "真的", "但是", "因为", "所以", "可以", "还是", "已经", "不是", "一下",
    "看看", "觉得", "感觉", "知道", "应该", "可能", "现在", "今天", "时候",
    "大家", "分享", "内容", "笔记", "测评", "种草", "起来", "不能", "非常",
    "如果", "然后", "以及", "或者", "比较", "喜欢", "点赞", "收藏", "关注", "谢谢",
}


def tokenize(text):
    """返回小写化 token 列表。

    无词典方案：英文整词保留；中文用 2-gram + 弱连接字过滤
    （"防晒霜"->"防晒/晒霜"，"敏感肌"->"敏感/感肌"），剔除虚字端。
    过滤停用词与纯数字。
    """
    text = (text or "").lower()
    out = []
    for chunk in _CN_RE.findall(text):
        if len(chunk) < 2:
            continue
        for i in range(len(chunk) - 1):
            g = chunk[i:i + 2]
            if g in STOPWORDS or g[0] in WEAK_EDGE or g[1] in WEAK_EDGE:
                continue
            out.append(g)
    for w in _EN_RE.findall(text):
        if not w.isdigit():
            out.append(w)
    return out


def ngrams_of(text):
    """把一段中文专名拆成 2-gram 集合（用于把查询主体词从主题候选里剔除）。

    例："广州太古汇" -> {广州,州太,太古,古汇}；英文整词保留。
    """
    out = set()
    for chunk in _CN_RE.findall((text or "").lower()):
        for i in range(len(chunk) - 1):
            g = chunk[i:i + 2]
            if g[0] not in WEAK_EDGE and g[1] not in WEAK_EDGE:
                out.add(g)
        if len(chunk) >= 2:
            out.add(chunk)
    for w in _EN_RE.findall((text or "").lower()):
        out.add(w)
    return out


def extract_topic_words(docs, top_k=8, stop_terms=None):
    """对同一聚类的文档列表做 c-TF-IDF，返回 [(word, score)] 降序前 top_k。

    stop_terms: 需要从主题候选剔除的词集合（典型为查询主体词，如品牌专名
    "广州太古汇"的 2-gram）——主体词在每篇都高频，会污染主题，真正的主题应是
    "关于主体的什么事"（美食/服务/周年…），故剔除主体词本身。
    """
    stop = set(stop_terms or ())
    docs = [d for d in (docs or []) if d]
    if not docs:
        return []
    # 类内词频 + 文档频率 + 总词数
    tf = {}
    df = {}
    total_words = 0
    for doc in docs:
        seen = set()
        for w in tokenize(doc):
            if w in stop:
                continue
            tf[w] = tf.get(w, 0) + 1
            total_words += 1
            if w not in seen:
                df[w] = df.get(w, 0) + 1
                seen.add(w)
    if not tf:
        return []
    n_docs = len(docs)
    scored = []
    for w, tf_w in tf.items():
        freq = tf_w / total_words
        weight = freq * math.log(1.0 + n_docs / float(df.get(w, 1)))
        scored.append((w, round(weight, 6)))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:top_k]


def topic_label(docs, top_k=5, sep=" / ", stop_terms=None):
    """生成可读 Topic 标签：取 top_k 高分词拼接（供 Topic 展示/摘要）。"""
    words = extract_topic_words(docs, top_k=top_k, stop_terms=stop_terms)
    return sep.join(w for w, _ in words) if words else "未命名主题"

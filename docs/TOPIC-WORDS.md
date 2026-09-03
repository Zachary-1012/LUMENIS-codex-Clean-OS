# 轻量 c-TF-IDF 主题词提取 · 2026-09-03

> 研究来源：**BERTopic**（MaartenGr/BERTopic, 7814★, Apache-2.0）。
> 提取其核心**可解释主题词算法（c-TF-IDF：类内词频 × 逆类频率）**，纯标准库实现，
> 不引入 sentence-transformers/torch 重依赖，服务 ZBC 的 Topic 自动打标 / 事件摘要。

## 一、算法

c-TF-IDF(w, C) = (tf_w / total_words_C) * log(1 + n_docs_C / df_w)

- tf_w：词在聚类 C 的总词频；total_words_C：类总词数
- n_docs_C：类文档数；df_w：含词文档数
- 高类内频率 + 低文档频率（词更聚焦少数文档）-> 高分 = 最能代表该类

## 二、实现（scripts/topic_words.py）

- tokenize：无词典方案——英文整词保留；中文 2-gram + 弱连接字过滤（"防晒霜"->"防晒/晒霜"）
- extract_topic_words(docs, top_k)：c-TF-IDF 排序取前 k
- topic_label(docs, top_k)：生成可读 Topic 标签

## 三、验证

- 单测 3/3（停用词过滤 + 高频词居前 + 区分性词保留 + 空输入）
- 演示：防晒/感肌/敏感/晒霜/spf（正确识别主题词）
- 零重依赖：纯标准库（re/math）

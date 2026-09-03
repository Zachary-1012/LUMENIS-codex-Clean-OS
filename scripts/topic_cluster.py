# -*- coding: utf-8 -*-
"""Topic 聚类 → 事件标签（c-TF-IDF 落地事件摘要增强，只读不改 DB）。

服务基线 P1-B/P1-C：把 BERTopic 式可解释主题词算法应用到 events，
为事件生成可读 topic_label（供事件摘要/报告/UI 展示），内存增强、零写库风险。
"""
import json


def event_topic_labels(events, group_field="risk_level", top_k=5):
    """按分组字段对事件分组，每组用 c-TF-IDF 提取主题词。

    events: [ {title, summary, risk_level, ...} ]
    返回 [{group, label, words:[(w,score)]}]
    """
    from scripts.topic_words import extract_topic_words
    groups = {}
    for ev in events or []:
        key = (ev.get(group_field) or "unknown")
        text = " ".join(str(x) for x in (ev.get("title"), ev.get("summary")) if x)
        if not text.strip():
            continue
        groups.setdefault(key, []).append(text)
    out = []
    for key, docs in sorted(groups.items()):
        words = extract_topic_words(docs, top_k=top_k)
        label = " / ".join(w for w, _ in words) if words else "未命名主题"
        out.append({"group": key, "label": label, "words": words})
    return out


def enrich_events_with_labels(events, top_k=4):
    """给每个事件生成独立 topic_label（基于自身 title+summary 的 c-TF-IDF）。

    返回新的 dict 列表（每项含 topic_label 字段），不改原对象、不写 DB。
    供事件摘要/报告/UI 消费。
    """
    from scripts.topic_words import topic_label
    out = []
    for ev in events or []:
        text = " ".join(str(x) for x in (ev.get("title"), ev.get("summary")) if x)
        lbl = topic_label([text], top_k=top_k) if text.strip() else "未命名主题"
        item = dict(ev)
        item["topic_label"] = lbl
        out.append(item)
    return out


def main():
    """CLI：读 events 表，按 risk_level 输出主题标签 JSON。"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import database
    with database.get_db() as c:
        rows = c.execute(
            "SELECT event_key, title, summary, risk_level, fact_status FROM events ORDER BY event_key"
        ).fetchall()
    events = [dict(zip(("event_key", "title", "summary", "risk_level", "fact_status"), r)) for r in rows]
    labels = event_topic_labels(events, group_field="risk_level", top_k=5)
    print(json.dumps(labels, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""品牌诊断简报：定位框架(营销知识库) × ZBC 真实舆情数据。

输入品牌关键词，从 monitor.db 读取相关 notes/events，输出结构化洞察：
声量(相关笔记/事件/时间窗口)、情绪分布、风险事件、c-TF-IDF 主题词、
以及基于营销知识库的启发式定位建议(真需求对位/情绪锚点/风险提示)。

只读审计，不改 DB(数据零丢失)。CLI：python scripts/brand_insight.py "品牌关键词"
"""
import argparse
import json
import re
import sqlite3
import sys
from collections import Counter

from scripts.topic_words import extract_topic_words, tokenize


def _conn(db_path="data/monitor.db"):
    return sqlite3.connect(db_path)


def _like_cols(c, table):
    return [r[1] for r in c.execute("PRAGMA table_info(%s)" % table)]


def fetch_related(db_path, keyword, limit=300):
    """按关键词从 notes/events 拉相关记录（title/content/正文 模糊匹配）。"""
    kw = "%" + keyword + "%"
    out = {"notes": [], "events": []}
    c = _conn(db_path)
    try:
        try:
            ncols = _like_cols(c, "notes")
            text_cols = [x for x in ("title", "content", "summary", "text")
                         if x in ncols]
            if text_cols:
                where = " OR ".join("%s LIKE ?" % x for x in text_cols)
                sql = "SELECT * FROM notes WHERE %s LIMIT %d" % (where, limit)
                cols = [r[1] for r in c.execute("PRAGMA table_info(notes)")]
                rows = c.execute(sql, [kw] * len(text_cols)).fetchall()
                for r in rows:
                    out["notes"].append(dict(zip(cols, r)))
        except sqlite3.Error:
            pass
        try:
            ecols = _like_cols(c, "events")
            tcols = [x for x in ("title", "summary", "description") if x in ecols]
            if tcols and "event_id" in ecols:
                where = " OR ".join("%s LIKE ?" % x for x in tcols)
                sql = "SELECT * FROM events WHERE %s LIMIT %d" % (where, limit)
                cols = [r[1] for r in c.execute("PRAGMA table_info(events)")]
                rows = c.execute(sql, [kw] * len(tcols)).fetchall()
                for r in rows:
                    out["events"].append(dict(zip(cols, r)))
        except sqlite3.Error:
            pass
    finally:
        c.close()
    return out


def _cnt(items, k, v):
    return sum(str(x.get(k, "")).lower() == v for x in items)


def diagnose(db_path, keyword, top_k=6):
    data = fetch_related(db_path, keyword)
    notes, events = data["notes"], data["events"]
    n = len(notes)
    e = len(events)
    # 主题词：合并标题+正文喂 c-TF-IDF
    docs = []
    # 系统生成摘要的模板标记（含这些说明 body/content 不是用户原文，剔除防污染）
    _SYS_MARK = ("系统根据标题", "此内容为系统", "情绪分析", "风险等级", "互动数据",
                 "作者：", "发布时间：", "非原文正文")
    def _clean_body(x):
        b = str(x.get("body", "") or x.get("content", "") or "")
        if any(m in b for m in _SYS_MARK):
            return ""  # 是系统拼装摘要，非用户原文
        return b
    for x in notes:
        t = str(x.get("title", "") or "")
        body = _clean_body(x)
        # 标题是用户原话、主题信号最纯，重复一次加权；正文仅用真实原文
        docs.append(((t + " ") * 2 + body).strip())
    topics = []
    if docs:
        try:
            # 剔除查询主体词本身（品牌专名 2-gram），避免主体词高频污染主题：
            # 主题应是"关于主体的什么事"，而非主体名。
            from scripts.topic_words import ngrams_of
            # 自动扩展：找出 docs 中包含 keyword 的最高频完整品牌名（如 keyword=太古汇 → "广州太古汇"），
            # 对其全名 ngram 剔除，避免"广州/州太"等残片漏网成为主题。
            brand_full = keyword
            cnt = Counter()
            for d in docs:
                for seg in re.findall(r"[\u4e00-\u9fa5]{2,12}", d):
                    if keyword in seg:
                        cnt[seg] += 1
            if cnt:
                brand_full = max(cnt, key=lambda k: (len(k), cnt[k]))
            stop_terms = ngrams_of(brand_full)
            topics = extract_topic_words(docs, top_k=top_k, stop_terms=stop_terms)
            # 系统分析/平台度量类词，不是用户主题
            _noise = {"数据", "风险", "标题", "内容", "相关", "进行", "以及", "通过",
                      "低风", "中风", "高风", "中性", "情绪", "正向", "负向", "互动",
                      "点赞", "收藏", "评论", "转发", "粉丝", "浏览", "笔记", "作者",
                      "发布", "采集", "来源", "平台", "账号", "用户", "评分", "置信"}
            topics = [t for t in topics
                      if not (t[0] if isinstance(t, (tuple, list)) else str(t)) in _noise][:top_k]
        except Exception:
            topics = []
    sentiment = {"positive": _cnt(notes, "sentiment", "positive"),
                 "neutral": _cnt(notes, "sentiment", "neutral"),
                 "negative": _cnt(notes, "sentiment", "negative")}
    risk_events = []
    for x in events:
        if str(x.get("risk_level", "")).lower() in ("high", "medium"):
            risk_events.append({
                "title": x.get("title", ""), "risk": x.get("risk_level", ""),
                "topic": "", "summary": str(x.get("summary", ""))[:80]})
    neg_rate = round(sentiment["negative"] / n, 3) if n else 0.0

    # 定位建议（营销知识库启发式框架）
    advice = []
    if n == 0 and e == 0:
        advice.append("当前库内无该关键词相关记录：无法验证「真实需求对位」——先确认是品牌未发声还是采集未覆盖。")
    else:
        if topics:
            words = []
            for t in topics[:4]:
                words.append(t[0] if isinstance(t, (tuple, list)) else str(t))
            advice.append("用户真实讨论聚焦：「%s」——建议核对是否与你的定位一句话一致(不一致=定位与真实认知错位)。"
                          % "/".join(words))
        if neg_rate > 0.3:
            advice.append("负面占比 %.0f%% 偏高：先处理风险事件(危机止血)再谈增长，别在负面蓄水池上投放。"
                          % (neg_rate * 100))
        elif n >= 3:
            advice.append("情绪结构健康(负面 %.0f%%)：可进入「情绪锚点」经营，把讨论向品牌主张收敛。"
                          % (neg_rate * 100))
        if risk_events:
            advice.append("存在 %d 条高/中风险事件：建议先出应对口径(诚实立场)，再考虑借势放大。"
                          % len(risk_events))
        if n >= 5:
            advice.append("声量样本足够(≥%d)：可做「测-种-爆-续」全链路复盘，看首发势能是否形成。" % n)
    return {
        "keyword": keyword,
        "volume": {"notes": n, "events": e, "note_kind": "related"},
        "sentiment": sentiment,
        "negative_rate": neg_rate,
        "topics": topics,
        "risk_events": risk_events[:10],
        "advice": advice,
    }


def main():
    ap = argparse.ArgumentParser(description="品牌诊断简报(定位框架×舆情数据)")
    ap.add_argument("keyword", help="品牌/产品关键词")
    ap.add_argument("--db", default="data/monitor.db")
    ap.add_argument("--top", type=int, default=6)
    a = ap.parse_args()
    r = diagnose(a.db, a.keyword, a.top)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

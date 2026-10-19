# -*- coding: utf-8 -*-
"""LUMENIS BMP KOS intelligence compatibility adapter

能力：
1. classify_intent / analyze_comments_intent —— 意向评论分层（强/弱/无意向）
2. recognize_kos_identity / refresh_kos_identity —— KOS 号识别（证据加权，不虚构雇佣关系）
3. competitor_benchmark —— 竞品对标（复用 config/kos_monitor_profiles/hainan_cdf.json 实体消歧）

契约：
- 复用 kos_engine 的 DB 与表（notes / note_comments / kos_profiles），不重建内容库
- KOS 识别为候选分类（identity_label），不得无证据宣称雇佣/隶属关系
- 系统不得宣称已投流/已转化/已产生 ROI，除非存在对应真实数据
- 不保存任何 Cookie/Token/Session；全部基于公开采集数据
"""
from __future__ import annotations
import os, re, json, sqlite3
from pathlib import Path
from typing import Optional, List, Dict

from kos_engine import DB_PATH, _get_conn

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
PROFILE_PATH = Path(__file__).parent / "config" / "kos_monitor_profiles" / "hainan_cdf.json"

# 意向分层关键词（Phase A 第一版规则，后续可接 AI 校准）
_INTENT_STRONG = [
    "怎么买", "哪里买", "在哪买", "多少钱", "价格", "几折", "怎么预约", "怎么预订",
    "预约", "预订", "链接", "有货", "下单", "购买", "到店", "去逛", "怎么参加",
    "怎么联系", "加微信", "联系方式", "找谁", "几号", "怎么领", "活动怎么", "优惠券", "怎么申请",
]
_INTENT_WEAK = [
    "推荐", "适合", "好用吗", "怎么样", "值不值", "对比", "评测", "求分享", "第一次",
    "注意", "攻略", "体验", "值得", "买吗", "哪个好", "推不推荐",
]
# KOS 号识别：命名信号（作者昵称）
_KOS_NICK_SIGNALS = [
    "柜姐", "顾问", "导购", "店长", "员工", "专员", "销售", "主理人", "SA", "BA",
    "导购员", "营业员", "店员", "内购", "免税顾问", "KOS", "柜员",
]
# KOS 号识别：内容信号（笔记正文/标题）
_KOS_CONTENT_SIGNALS = [
    "云逛店", "门店", "专柜", "到店", "试用", "接待", "预约", "欢迎", "工号",
    "上班", "同事", "导购", "顾客", "试穿", "下单", "调货", "会员日", "员工",
]
# 竞品实体（默认取 hainan_cdf.json do_not_merge_without_evidence，可被 profile 覆盖）
_COMPETITOR_DEFAULT = ["海旅免税", "海旅", "深免", "中服免税", "中服", "海免"]


# ---------------------------------------------------------------------------
# 1. 意向评论分层
# ---------------------------------------------------------------------------
def classify_intent(comment_text: str) -> dict:
    """将单条评论按意图分层。

    返回：
        {"level": "strong|weak|none", "category": str, "matched_keywords": [], "confidence": float}
    """
    text = (comment_text or "").strip()
    if not text:
        return {"level": "none", "category": "NO_REPLY", "matched_keywords": [], "confidence": 0.0}
    strong = [kw for kw in _INTENT_STRONG if kw in text]
    if strong:
        return {"level": "strong", "category": "购买意向", "matched_keywords": strong, "confidence": 0.9}
    weak = [kw for kw in _INTENT_WEAK if kw in text]
    if weak:
        return {"level": "weak", "category": "咨询意向", "matched_keywords": weak, "confidence": 0.7}
    # 负面/风险优先于普通互动（复用 analyze_comments 口径）
    neg = [kw for kw in ["不好", "垃圾", "投诉", "骗", "假", "差评", "失望"] if kw in text]
    if neg:
        return {"level": "none", "category": "负面", "matched_keywords": neg, "confidence": 0.85}
    return {"level": "none", "category": "普通互动", "matched_keywords": [], "confidence": 0.6}


def analyze_comments_intent(note_id: str = "", author_id: str = "", limit: int = 50) -> dict:
    """意向评论分层分析（复用 note_comments 表）。

    返回：{"total", "by_level": {strong/weak/none: n}, "by_category": {...}, "comments": [{...intent...}]}
    """
    conn = _get_conn()
    conds, params = [], []
    if note_id:
        conds.append("note_id = ?"); params.append(note_id)
    if author_id:
        note_ids = [r[0] for r in conn.execute(
            "SELECT note_id FROM notes WHERE author_id = ?", (author_id,)).fetchall()]
        if note_ids:
            conds.append("note_id IN ({})".format(",".join("?" * len(note_ids))))
            params.extend(note_ids)
        else:
            conn.close()
            return {"total": 0, "by_level": {}, "by_category": {}, "comments": []}
    where = " WHERE " + " AND ".join(conds) if conds else ""
    total = conn.execute("SELECT COUNT(*) FROM note_comments{}".format(where), params).fetchone()[0]
    rows = conn.execute(
        "SELECT * FROM note_comments{} ORDER BY publish_time DESC LIMIT ?".format(where),
        params + [limit]).fetchall()
    conn.close()
    by_level = {"strong": 0, "weak": 0, "none": 0}
    by_category: Dict[str, int] = {}
    comments = []
    for r in rows:
        d = dict(r)
        content = d.get("content") or ""
        intent = classify_intent(content)
        d["intent_level"] = intent["level"]
        d["intent_category"] = intent["category"]
        d["intent_keywords"] = intent["matched_keywords"]
        by_level[intent["level"]] = by_level.get(intent["level"], 0) + 1
        by_category[intent["category"]] = by_category.get(intent["category"], 0) + 1
        comments.append(d)
    return {"total": total, "by_level": by_level, "by_category": by_category, "comments": comments}


# ---------------------------------------------------------------------------
# 2. KOS 号识别
# ---------------------------------------------------------------------------
def _load_profile() -> dict:
    """读取中免 KOS 监测配置（不存在时返回空 dict）。"""
    try:
        if PROFILE_PATH.exists():
            return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _author_notes(author_id: str, conn, limit: int = 30) -> List[dict]:
    rows = conn.execute(
        """SELECT title, content, subject_type, is_official, likes, comments, collects, shares
           FROM notes WHERE author_id = ? ORDER BY publish_datetime DESC LIMIT ?""",
        (author_id, limit)).fetchall()
    return [dict(r) for r in rows]


def recognize_kos_identity(author_id: str) -> dict:
    """基于证据识别作者是否为 KOS 候选号。

    规则（证据加权，>=2 类证据才判定 is_kos=True；不虚构雇佣关系）：
        - 命名信号：昵称含柜姐/顾问/导购/店长/员工/SA/BA 等
        - 内容信号：笔记标题/正文含云逛店/门店/专柜/到店/接待/预约 等
        - 重复品牌内容：>=2 篇笔记命中品牌 subject_terms
        - 官方标记：notes.is_official = 1
    返回：{"author_id", "identity_label", "is_kos", "evidence": {...}, "reasons": []}
    """
    conn = _get_conn()
    row = conn.execute(
        "SELECT author_id, author_nickname FROM kos_profiles WHERE author_id = ?",
        (author_id,)).fetchone()
    nickname = row["author_nickname"] if row else ""
    notes = _author_notes(author_id, conn)
    conn.close()

    profile = _load_profile()
    subject_terms = profile.get("subject_terms", []) or []
    brand_words = [w for w in subject_terms if w]

    nick_signal = [s for s in _KOS_NICK_SIGNALS if s and s.lower() in (nickname or "").lower()]
    content_signal: List[str] = []
    brand_hits = 0
    official = False
    for n in notes:
        blob = " ".join(filter(None, [n.get("title"), n.get("content")])) or ""
        for s in _KOS_CONTENT_SIGNALS:
            if s and s in blob and s not in content_signal:
                content_signal.append(s)
        if brand_words and any(w in blob for w in brand_words):
            brand_hits += 1
        if n.get("is_official"):
            official = True

    evidence = {
        "nick_signal": nick_signal,
        "content_signal": content_signal,
        "brand_hits": brand_hits,
        "official": official,
        "note_sample": len(notes),
    }
    reasons = []
    if nick_signal:
        reasons.append("昵称命中:{}".format("/".join(nick_signal)))
    if content_signal:
        reasons.append("内容信号:{}".format("/".join(content_signal[:4])))
    if brand_hits >= 2:
        reasons.append("重复品牌内容x{}".format(brand_hits))
    if official:
        reasons.append("官方标记")

    score = 0
    if nick_signal:
        score += 3
    if content_signal:
        score += 2
    if brand_hits >= 2:
        score += 2
    elif brand_hits >= 1:
        score += 1
    if official:
        score += 4

    # identity_label：KOS 候选 > OFFICIAL > 普通作者
    if official:
        identity_label = "OFFICIAL"
        is_kos = True
    elif score >= 3:
        identity_label = "KOS"
        is_kos = True
    elif brand_hits >= 1 or content_signal:
        identity_label = "KOC"
        is_kos = False
    else:
        identity_label = "UGC"
        is_kos = False

    return {
        "author_id": author_id,
        "identity_label": identity_label,
        "is_kos": bool(is_kos),
        "evidence": evidence,
        "reasons": reasons,
    }


def _ensure_identity_columns(conn):
    """幂等新增 kos_profiles 的 identity 列（不破坏既有列/数据）。"""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(kos_profiles)").fetchall()]
    if "identity_label" not in cols:
        conn.execute("ALTER TABLE kos_profiles ADD COLUMN identity_label TEXT DEFAULT 'UNKNOWN'")
    if "is_kos" not in cols:
        conn.execute("ALTER TABLE kos_profiles ADD COLUMN is_kos INTEGER DEFAULT 0")


def refresh_kos_identity(limit: int = 500) -> dict:
    """遍历 kos_profiles，回写 identity_label / is_kos（幂等）。"""
    conn = _get_conn()
    _ensure_identity_columns(conn)
    author_ids = [r[0] for r in conn.execute(
        "SELECT author_id FROM kos_profiles ORDER BY total_engagement DESC LIMIT ?", (limit,)).fetchall()]
    updated = {"KOS": 0, "KOC": 0, "OFFICIAL": 0, "UGC": 0, "UNKNOWN": 0}
    for aid in author_ids:
        res = recognize_kos_identity(aid)
        conn.execute(
            "UPDATE kos_profiles SET identity_label=?, is_kos=?, updated_at=datetime('now','localtime') WHERE author_id=?",
            (res["identity_label"], 1 if res["is_kos"] else 0, aid))
        updated[res["identity_label"]] = updated.get(res["identity_label"], 0) + 1
    conn.commit()
    total = len(author_ids)
    conn.close()
    return {"scanned": total, "distribution": updated}


# ---------------------------------------------------------------------------
# 3. 竞品对标
# ---------------------------------------------------------------------------
def _entity_stats(conn, terms: List[str]) -> dict:
    """统计命中任一 term 的笔记及其互动/评论意向。"""
    if not terms:
        return {"notes": 0, "authors": 0, "engagement": 0, "intent_strong": 0, "risk": 0}
    likes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    blob_sql = "title || ' ' || COALESCE(content,'') || ' ' || COALESCE(body,'')"
    like_sql = " OR ".join(["? LIKE '%' || ? || '%'"] * len(terms)) if terms else "1=0"
    cond = " OR ".join(["({}) LIKE ?".format(blob_sql)] * len(terms))
    params = []
    for t in terms:
        params.extend([t])
    where_terms = "(" + " OR ".join(["1=0"] * len(terms)) + ")"
    # 简化：用 instr 判断
    cond_sql = " OR ".join(["instr(" + blob_sql + ", ?) > 0"] * len(terms))
    params = terms
    rows = conn.execute(
        "SELECT COUNT(*) as n, COUNT(DISTINCT author_id) as a, "
        "COALESCE(SUM(likes+comments+collects+shares),0) as eng, "
        "SUM(CASE WHEN risk_level IN ('high','medium') THEN 1 ELSE 0 END) as r "
        "FROM notes WHERE " + cond_sql, params).fetchone()
    n, a, eng, r = rows["n"], rows["a"], rows["eng"], rows["r"]
    # 意向评论：取这些笔记的评论里强意向数
    strong = 0
    if n:
        note_ids = [x[0] for x in conn.execute(
            "SELECT note_id FROM notes WHERE " + cond_sql + " LIMIT 300", params).fetchall()]
        if note_ids:
            ph = ",".join("?" * len(note_ids))
            comments = [dict(x) for x in conn.execute(
                "SELECT content FROM note_comments WHERE note_id IN ({})".format(ph), note_ids).fetchall()]
            strong = sum(1 for c in comments if classify_intent(c.get("content") or "")["level"] == "strong")
    return {"notes": n, "authors": a, "engagement": int(eng or 0), "intent_strong": strong, "risk": int(r or 0)}


def competitor_benchmark(profile_path: Optional[str] = None) -> dict:
    """竞品对标：主品牌 vs 竞品实体（复用 hainan_cdf.json 消歧配置）。

    返回：{"brand": {...}, "competitors": {实体: stats}, "leader": "...", "ts"}
    """
    profile = _load_profile()
    if profile_path:
        try:
            profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
        except Exception:
            pass
    subject_terms = profile.get("subject_terms", []) or []
    competitors_raw = profile.get("entity_disambiguation", {}).get("do_not_merge_without_evidence", []) \
        or _COMPETITOR_DEFAULT
    # 竞品实体词规范化（去掉"不合并"注释里同义的重复项；过滤含修饰词的无效搜索词）
    _FILTER_WORDS = ("相关", "主体", "及", "相关主体", "其")
    competitors = []
    seen = set()
    for c in competitors_raw:
        c = (c or "").strip()
        if not c or len(c) > 8 or any(w in c for w in _FILTER_WORDS):
            continue
        if c not in seen and c not in subject_terms:
            seen.add(c)
            competitors.append(c)
    if not competitors:
        competitors = _COMPETITOR_DEFAULT

    conn = _get_conn()
    brand = _entity_stats(conn, subject_terms)
    comp_stats = {}
    for c in competitors:
        comp_stats[c] = _entity_stats(conn, [c])
    conn.close()

    def _score(s):
        return s["notes"] * 1 + s["engagement"] / 100.0 + s["intent_strong"] * 2 + s["authors"] * 0.5

    ranking = sorted([("brand", brand)] + [(k, v) for k, v in comp_stats.items()],
                     key=lambda x: _score(x[1]), reverse=True)
    leader = ranking[0][0] if ranking else "brand"
    return {
        "brand_name": profile.get("brand_display_name", "主品牌"),
        "brand": brand,
        "competitors": comp_stats,
        "ranking": [{"entity": k, "score": round(_score(v), 2)} for k, v in ranking],
        "leader": leader,
        "ts": os.environ.get("ZBC_RUN_TS", ""),
    }


if __name__ == "__main__":
    # 冒烟测试
    print("intent:", classify_intent("这个多少钱怎么买"))
    print("intent2:", classify_intent("好不好用"))
    print("benchmark:", json.dumps(competitor_benchmark(), ensure_ascii=False)[:400])
    print("refresh:", refresh_kos_identity(limit=50))


def read_scoped_benchmark(binding: dict) -> dict:
    """Compare explicit BrandFocus observations, never keyword-guessed entities.

    Results describe this source sample; no market-leader or composite-score
    claim is manufactured from unavailable reach, intent or conversion data.
    """
    from canonical_data import list_scoped_canonical
    from lumenis.shared.database import get_repository
    import math
    if (not isinstance(binding, dict) or binding.get("contract") != "lumenis.scope-read-binding.v1"
            or binding.get("domain_id") != "BMP" or binding.get("product_id") != "ZBMP"
            or binding.get("read_allowed") is not True or binding.get("scope_verified") is not True
            or binding.get("canonical_scope") not in {"FOCUS", "GLOBAL_ALL"}
            or (binding.get("canonical_scope") == "FOCUS" and not binding.get("brand_focus_id"))):
        raise ValueError("BMP_BENCHMARK_SCOPE_REQUIRED")
    focus = binding.get("brand_focus_id") if binding["canonical_scope"] == "FOCUS" else None
    with get_repository().connection(read_only=True, wal=False) as connection:
        material = list_scoped_canonical(connection, product_id="ZBMP", brand_focus_id=focus, limit=100)
    groups, unknown = {}, 0
    for row in material["records"]:
        identity = row.get("brand_focus_id")
        if not identity:
            unknown += 1
            continue
        group = groups.setdefault(identity, {"entity": identity, "record_count": 0,
            "engagement": 0, "engagement_unknown_count": 0, "score": None, "source_refs": []})
        group["record_count"] += 1
        values = [row.get("engagement_" + field) for field in ("likes", "comments", "collects", "shares")]
        if all(type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in values):
            if group["engagement"] is not None:
                group["engagement"] += sum(values)
        else:
            group["engagement_unknown_count"] += 1
            group["engagement"] = None
        group["source_refs"].append({"canonical_id": row["canonical_id"], "scope_evidence": row["scope_evidence"]})
    return {"ranking": sorted(groups.values(), key=lambda item: (-item["record_count"], item["entity"])),
        "leader": None, "comparison_state": "AVAILABLE" if len(groups) > 1 else "INSUFFICIENT_ENTITIES",
        "method": "signed-brand-focus-observation-counts:v1", "coverage": "NOT_VERIFIED",
        "truncated": bool(material.get("truncated")), "unknown_brand_focus_count": unknown,
        "source_count": len(material["records"]), "source_freshness": "UNKNOWN",
        "limitations": ["Source sample counts are not market share or campaign effectiveness.",
                        "Other BrandFocus records require their own authorized scope."]}

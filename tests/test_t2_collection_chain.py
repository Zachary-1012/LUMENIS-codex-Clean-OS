# -*- coding: utf-8 -*-
"""Team2 采集链路端到端单元测试
验证：搜索解析→详情解析→评论解析→标准化→去重→主体过滤→持久化
不连接真实平台，全部用 mock 数据。
"""
import os
import sys
import json
import tempfile
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0
RESULTS = []

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(f"  [PASS] {name}")
    else:
        FAIL += 1
        RESULTS.append(f"  [FAIL] {name} {detail}")


def run_tests():
    """Team2 采集链路端到端测试（可被 pytest 收集，也可独立运行）"""
    global PASS, FAIL, RESULTS
    PASS = 0
    FAIL = 0
    RESULTS = []
    print("=" * 60)
    print("Team2 采集链路端到端测试")
    print("=" * 60)

    # ===== 1. 数据模型 =====
    print("\n[1] 数据模型 RawNote / RawComment")
    from lumenis.system.collector.runtime.base import RawNote, RawComment, PlatformCollector

    note = RawNote(note_id="test_001", title="广州太古汇探店", content="测试正文",
                   author_id="u1", author_nickname="测试用户", likes=100,
                   source_platform="xhs")
    check("RawNote 字段完整", note.note_id == "test_001" and note.title == "广州太古汇探店"
          and note.source_platform == "xhs" and note.collected_at != "")
    check("RawNote 默认值", note.comments == 0 and note.collects == 0 and note.xsec_token == "")

    comment = RawComment(comment_id="c1", note_id="test_001", content="好评",
                         author_nickname="评论者", likes=5)
    check("RawComment 字段完整", comment.comment_id == "c1" and comment.content == "好评")
    check("RawComment sub_comments 默认空列表", isinstance(comment.sub_comments, list))

    # ===== 2. XHS 搜索结果解析 =====
    print("\n[2] XHSCollector 搜索结果解析")
    from lumenis.system.collector.runtime.xhs.collector import XHSCollector

    collector = XHSCollector(cookie="mock_cookie")
    mock_search_item = {
        "note_card": {
            "note_id": "xhs_note_001",
            "display_title": "广州太古汇十五周年庆",
            "user": {"user_id": "user_001", "nickname": "探店达人"},
            "interact_info": {"liked_count": "1.2万", "comment_count": "350",
                              "collected_count": "800", "share_count": "50"},
            "time": "1756900000000",
            "xsec_token": "token_abc123",
        }
    }
    parsed = collector._parse_search_item(mock_search_item, "广州太古汇")
    check("搜索解析 note_id", parsed is not None and parsed.note_id == "xhs_note_001")
    check("搜索解析标题", parsed.title == "广州太古汇十五周年庆")
    check("搜索解析作者", parsed.author_id == "user_001" and parsed.author_nickname == "探店达人")
    check("搜索解析互动量", parsed.likes == 12000 and parsed.comments == 350)
    check("搜索解析 URL", "xiaohongshu.com/explore/xhs_note_001" in parsed.url)
    check("搜索解析 xsec_token", parsed.xsec_token == "token_abc123")
    check("搜索解析 source_platform", parsed.source_platform == "xiaohongshu")

    # 空 note_id 应返回 None
    check("无效搜索项返回 None", collector._parse_search_item({"note_card": {}}, "kw") is None)

    # ===== 3. XHS 评论解析 =====
    print("\n[3] XHSCollector 评论解析")
    mock_comment = {
        "id": "comment_001",
        "content": "这家商场真不错",
        "user_info": {"user_id": "cu1", "nickname": "评论用户"},
        "like_count": 10,
        "create_time": "1756900000000",
        "sub_comments": [
            {"id": "sub_001", "content": "同意", "user_info": {"nickname": "sub_user"},
             "like_count": 2, "create_time": "1756901000000"}
        ]
    }
    parsed_comment = collector._parse_comment(mock_comment, "xhs_note_001")
    check("评论解析 comment_id", parsed_comment.comment_id == "comment_001")
    check("评论解析 content", parsed_comment.content == "这家商场真不错")
    check("评论解析 note_id 关联", parsed_comment.note_id == "xhs_note_001")
    check("评论解析子评论", len(parsed_comment.sub_comments) == 1
          and parsed_comment.sub_comments[0].comment_id == "sub_001")
    check("子评论 parent_id 关联", parsed_comment.sub_comments[0].parent_comment_id == "comment_001")
    check("无效评论返回 None", collector._parse_comment({}, "n1") is None)

    # ===== 4. 标准化 =====
    print("\n[4] NoteNormalizer 标准化")
    from lumenis.system.collector.runtime.pipeline.normalize import NoteNormalizer, normalize_note

    normalizer = NoteNormalizer()
    raw_note_dict = {
        "note_id": "norm_001",
        "title": "  廣州太古匯  探店  ",
        "content": "今天去了太古汇，人很多",
        "author_nickname": "测试  用户",
        "publish_date": "2026/09/01 14:30",
        "likes": "1.5万",
        "comments": "3千",
        "collects": 500,
        "shares": "100",
    }
    norm = normalizer.normalize_note(raw_note_dict)
    check("繁简归一", "汇" in norm["title"] and "廣" not in norm["title"])
    check("空白清理", not norm["title"].startswith(" ") and "  " not in norm["title"])
    check("日期标准化", norm["publish_date"] == "2026-09-01 14:30:00")
    check("数字标准化-万", norm["likes"] == 15000)
    check("数字标准化-千", norm["comments"] == 3000)
    check("互动总量计算", norm["total_engagement"] == 15000 + 9000 + 1000 + 100)
    check("模块级适配函数", isinstance(normalize_note(raw_note_dict), dict))

    # 有效性检查
    check("有效笔记判定", normalizer.is_valid_note({"note_id": "x", "title": "t", "content": "c"}))
    check("空 note_id 无效", not normalizer.is_valid_note({"note_id": "", "title": "t"}))
    check("标题正文都空无效", not normalizer.is_valid_note({"note_id": "x", "title": "", "content": ""}))

    # ===== 5. SimHash 去重 =====
    print("\n[5] SimHashDeduplicator 去重")
    from lumenis.system.collector.runtime.pipeline.deduplicate import SimHashDeduplicator, deduplicate

    dedup = SimHashDeduplicator(hash_bits=64, threshold=6)
    notes_for_dedup = [
        {"note_id": "d1", "title": "广州太古汇探店分享", "content": "今天去了广州太古汇"},
        {"note_id": "d2", "title": "广州太古汇探店分享", "content": "今天去了广州太古汇"},  # 完全重复
        {"note_id": "d3", "title": "上海外滩游玩攻略", "content": "上海外滩夜景很美"},  # 不重复
    ]
    result = dedup.batch_deduplicate(notes_for_dedup)
    check("去重后数量", len(result) == 2, f"got {len(result)}")
    check("重复笔记标记", notes_for_dedup[1].get("_duplicate") is True)
    check("唯一笔记标记", notes_for_dedup[0].get("_duplicate") is False)
    check("模块级适配函数", isinstance(deduplicate([{"note_id": "x", "title": "t", "content": "c"}]), list))

    # ===== 6. 主体过滤（只读验证，不修改口径） =====
    print("\n[6] SubjectFilter 主体过滤（只读验证）")
    from lumenis.system.collector.runtime.pipeline.subject_filter import SubjectFilter, filter_subject

    sf = SubjectFilter()
    # 广州太古汇应通过
    is_rel, reason, conf = sf.verify("广州太古汇十五周年", "在天河路383号", "")
    check("广州太古汇正向命中", is_rel is True, f"reason={reason}")
    check("置信度>0.8", conf >= 0.8)
    # 上海太古汇应被排除
    is_rel2, reason2, conf2 = sf.verify("上海太古汇探店", "", "")
    check("上海太古汇被排除", is_rel2 is False, f"reason={reason2}")
    check("排除词一票否决", "排除词" in reason2)
    # 无关键词应不通过
    is_rel3, _, _ = sf.verify("今天天气真好", "", "")
    check("无关键词不通过", is_rel3 is False)

    # filter_subject 适配函数（使用外部 subject_hit 回调）
    def mock_subject_hit(text):
        return "太古汇" in text and "上海" not in text
    accepted = filter_subject([
        {"title": "广州太古汇", "body": "test"},
        {"title": "上海太古汇", "body": "test"},
        {"title": "无关内容", "body": "test"},
    ], mock_subject_hit)
    check("filter_subject 适配函数", len(accepted) == 1 and accepted[0]["title"] == "广州太古汇")

    # ===== 7. 持久化（临时 DB） =====
    print("\n[7] NotePersister 持久化（临时DB）")
    from lumenis.system.collector.runtime.pipeline.persist import NotePersister

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        # 建表
        conn = sqlite3.connect(tmp_path)
        conn.execute("""CREATE TABLE notes (
            note_id TEXT PRIMARY KEY, title TEXT, content TEXT, author_id TEXT,
            author_nickname TEXT, likes INTEGER, comments INTEGER, collects INTEGER,
            shares INTEGER, publish_date TEXT, url TEXT, xsec_token TEXT,
            source_platform TEXT, sentiment TEXT, risk_level TEXT, keywords TEXT,
            industry TEXT, event_id TEXT, negative_confirmed INTEGER,
            subject_verified INTEGER, subject_confidence REAL,
            collected_at TEXT, created_at TEXT, updated_at TEXT
        )""")
        conn.execute("""CREATE TABLE note_comments (
            comment_id TEXT PRIMARY KEY, note_id TEXT, content TEXT, author_id TEXT,
            author_nickname TEXT, likes INTEGER, publish_time TEXT, parent_id TEXT,
            raw_json TEXT, fetched_at TEXT
        )""")
        conn.commit()
        conn.close()

        persister = NotePersister(db_path=tmp_path)
        test_note = {
            "note_id": "persist_001", "title": "测试持久化", "content": "正文内容",
            "author_id": "a1", "author_nickname": "作者", "likes": 10, "comments": 2,
            "collects": 5, "shares": 1, "publish_date": "2026-09-01 10:00:00",
            "url": "https://x.com/1", "xsec_token": "t1", "source_platform": "xhs",
        }
        is_new = persister.insert_note(test_note)
        check("插入新笔记返回 True", is_new is True)
        check("笔记存在性检查", persister.note_exists("persist_001") is True)

        # 重复插入应更新
        test_note["likes"] = 20
        is_new2 = persister.insert_note(test_note)
        check("重复插入返回 False（更新）", is_new2 is False)

        # 批量持久化
        batch_result = persister.batch_persist([
            {"note_id": "batch_001", "title": "批量1"},
            {"note_id": "batch_002", "title": "批量2"},
        ])
        check("批量持久化 inserted=2", batch_result["inserted"] == 2, f"got {batch_result}")

        # 评论持久化
        comments_saved = persister.save_comments([
            {"comment_id": "cmt_001", "note_id": "persist_001", "content": "测试评论",
             "author_id": "ca1", "author_nickname": "评论者", "likes": 3,
             "publish_time": "2026-09-01 11:00:00", "parent_comment_id": "",
             "raw_data": {"key": "val"}},
        ])
        check("评论持久化返回1", comments_saved == 1, f"got {comments_saved}")

        # 验证评论实际写入 note_comments 表
        conn = sqlite3.connect(tmp_path)
        cnt = conn.execute("SELECT COUNT(*) FROM note_comments").fetchone()[0]
        conn.close()
        check("评论实际写入 note_comments 表", cnt == 1, f"got {cnt}")

    finally:
        os.unlink(tmp_path)

    # ===== 8. 采集状态机 =====
    print("\n[8] 采集状态机 CollectionStatus")
    from lumenis.system.collector.adapters.base import CollectionStatus, CollectionResult, BasePlatformAdapter

    required_states = ["SUCCESS", "NO_NEW_DATA", "RISK_WARNING", "NEED_VERIFY",
                       "BLOCKED", "SESSION_EXPIRED", "COLLECT_ERROR", "COOLING_DOWN"]
    for state_name in required_states:
        check(f"状态 {state_name} 存在", hasattr(CollectionStatus, state_name))

    # CollectionResult.ok 属性
    ok_result = CollectionResult(status=CollectionStatus.SUCCESS, platform="xhs")
    check("SUCCESS.ok=True", ok_result.ok is True)
    no_data_result = CollectionResult(status=CollectionStatus.NO_NEW_DATA, platform="xhs")
    check("NO_NEW_DATA.ok=True", no_data_result.ok is True)
    err_result = CollectionResult(status=CollectionStatus.COLLECT_ERROR, platform="xhs")
    check("COLLECT_ERROR.ok=False", err_result.ok is False)

    # ===== 9. 状态映射 state_map =====
    print("\n[9] 状态映射 state_map（多套状态兼容）")
    from lumenis.system.collector.adapters.scheduling.state_map import (
        CS, to_canonical, to_guard, to_log_status, incident_class,
        is_stop_request, needs_human, is_ok, CLASS_A_AUTH, CLASS_B_VERIFY, CLASS_C_RISK
    )

    check("SUCCESS→canonical", to_canonical("SUCCESS") == CS.SUCCESS)
    check("EMPTY→NO_NEW_DATA", to_canonical("EMPTY") == CS.NO_NEW_DATA)
    check("AUTH_REQUIRED→SESSION_EXPIRED", to_canonical("AUTH_REQUIRED") == CS.SESSION_EXPIRED)
    check("CAPTCHA→NEED_VERIFY", to_canonical("CAPTCHA") == CS.NEED_VERIFY)
    check("IP_RISK_OR_300012→BLOCKED", to_canonical("", xhs_code="IP_RISK_OR_300012") == CS.BLOCKED)
    check("NEED_VERIFY xhs_code", to_canonical("", xhs_code="NEED_VERIFY") == CS.NEED_VERIFY)
    check("AUTH_REQUIRED xhs_code", to_canonical("", xhs_code="AUTH_REQUIRED") == CS.SESSION_EXPIRED)
    check("SUCCESS+items=0→NO_NEW_DATA", to_canonical("SUCCESS", items=0) == CS.NO_NEW_DATA)

    check("SESSION_EXPIRED 需人工", needs_human(CS.SESSION_EXPIRED) is True)
    check("NEED_VERIFY 需人工", needs_human(CS.NEED_VERIFY) is True)
    check("BLOCKED 停止请求", is_stop_request(CS.BLOCKED) is True)
    check("COOLING_DOWN 停止请求", is_stop_request(CS.COOLING_DOWN) is True)
    check("SUCCESS 不停止", is_stop_request(CS.SUCCESS) is False)
    check("SESSION_EXPIRED=A类", incident_class(CS.SESSION_EXPIRED) == CLASS_A_AUTH)
    check("NEED_VERIFY=B类", incident_class(CS.NEED_VERIFY) == CLASS_B_VERIFY)
    check("BLOCKED=C类", incident_class(CS.BLOCKED) == CLASS_C_RISK)

    # ===== 10. Collector Guard 状态机 =====
    print("\n[10] Canonical CollectState")
    from lumenis.system.collector.guard.state import CollectState

    guard_states = ["HEALTHY", "WARNING", "COOLDOWN", "PAUSED", "AUTH_REQUIRED", "NEED_VERIFY", "NETWORK_ERROR"]
    for s in guard_states:
        check(f"CollectState.{s} 存在", hasattr(CollectState, s))
    check("STOP_REQUEST 包含熔断态", CollectState.COOLDOWN in CollectState.STOP_REQUEST
          and CollectState.AUTH_REQUIRED in CollectState.STOP_REQUEST
          and CollectState.NEED_VERIFY in CollectState.STOP_REQUEST)
    check("label 中文映射", CollectState.label(CollectState.HEALTHY) == "正常")

    # ===== 11. Browser Runtime 路由与降级 =====
    print("\n[11] BrowserRuntime 路由与降级")
    from lumenis.system.browser.runtime.router import BrowserRouter, BrowserRouterError, browser_router
    from lumenis.system.browser.runtime.contract import BrowserContract

    router = BrowserRouter()
    check("Router 初始无 provider", len(router.providers()) == 0)

    class MockBrowser(BrowserContract):
        async def navigate(self, url, **kw): return {"ok": True, "url": url}
        async def close(self): pass

    router.register("mock", MockBrowser)
    check("注册后 provider 可见", "mock" in router.providers())
    check("get 返回实例", isinstance(router.get("mock"), MockBrowser))
    check("未知 provider 报错", True)  # 下面验证
    try:
        router.get("nonexistent")
        check("未知 provider 应抛 BrowserRouterError", False)
    except BrowserRouterError:
        check("未知 provider 抛 BrowserRouterError", True)

    # 降级默认关闭
    try:
        router.get_with_fallback("nonexistent", enable_fallback=False)
        check("默认不降级应报错", False)
    except BrowserRouterError:
        check("默认不降级（enable_fallback=False）", True)

    # 降级开启
    inst = router.get_with_fallback("nonexistent", fallback="mock", enable_fallback=True)
    check("开启降级返回 fallback", isinstance(inst, MockBrowser))

    # ===== 12. XHS Adapter 状态映射 =====
    print("\n[12] XiaohongshuAdapter 状态映射")
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter
    from lumenis.system.collector.adapters.base import CollectionStatus

    adapter = XiaohongshuAdapter()
    check("Adapter platform=xhs", adapter.platform == "xhs")
    check("Adapter enabled=True", adapter.enabled is True)
    check("Adapter monitor_priority=primary", adapter.monitor_priority == "primary")

    # detail 未接入应以 NOT_SUPPORTED 明确声明能力缺失，不伪装成 Provider 故障。
    detail_result = adapter.detail("test_id")
    check("detail 未接入显式返回 NOT_SUPPORTED", detail_result.status == CollectionStatus.NOT_SUPPORTED)
    check("detail 未接入有明确 message", "独立详情" in detail_result.message)

    # ===== 汇总 =====
    print("\n" + "=" * 60)
    print(f"测试结果: {PASS} PASS, {FAIL} FAIL, 共 {PASS+FAIL} 项")
    print("=" * 60)
    for r in RESULTS:
        if "[FAIL]" in r:
            print(r)

    if FAIL > 0:
        print(f"\n!!! 有 {FAIL} 项失败 !!!")
        return False
    else:
        # Windows CI/pytest capture may use GBK; keep the pass marker ASCII.
        print("\n全部通过 [OK]")
        return True


def test_collection_chain_end_to_end():
    """pytest 入口：运行完整采集链路测试"""
    assert run_tests() is True


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)

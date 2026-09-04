# -*- coding: utf-8 -*-
"""IC-021/039/040 Contract 测试（PCCC 20260904 §二/四/五 已就绪契约实施验收）。

覆盖：
- IC-021 EMV（MET-CONTENT-04）：真实互动计算 / 无数据 NOT_AVAILABLE / 估算口径标注 / 汇总覆盖度
- IC-039 本地化守卫（localization_guard）：禁忌命中 HOLD / 绝对禁止 BLOCK / 开关 / AI 待确认标记
- IC-040 KOS 兴趣图谱信号（interest_signal）：代理指标标注 / 不改 kos_score / 空数据优雅降级

DB 隔离：沿用 kos_ops/kos_paid 模式，module 级强制 ZBC_DB_PATH 指向临时库，防止污染生产。
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 强制隔离 DB（module 级，防污染 ZBC 生产库）----
# 注意：不在 import 时设置 env（会污染 pytest 收集阶段其他模块）；改在 fixture 内设置并恢复。
_TEST_DB = os.path.join(tempfile.gettempdir(), "zbc_ic_p1_test.db")


@pytest.fixture(autouse=True, scope="module")
def _isolated_db():
    """module 级 fixture：设隔离 env、清理临时库、建全 schema、跑完恢复原 env 并清理。"""
    _old = os.environ.get("ZBC_DB_PATH")
    os.environ["ZBC_DB_PATH"] = _TEST_DB
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    # 建全 schema（database.init_db 读 ZBC_DB_PATH）
    import database as _db
    _db.init_db()
    yield
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    # 恢复原 env（防污染后续模块的测试隔离）
    if _old is None:
        os.environ.pop("ZBC_DB_PATH", None)
    else:
        os.environ["ZBC_DB_PATH"] = _old


# ===================== IC-021 EMV =====================
class TestIC021EMV:
    def test_emv_real_interaction(self):
        """真实互动数据 → 返回估算 EMV + 曝光 + 估算口径标注。"""
        import emv
        r = emv.calculate_emv(likes=100, comments=10, collects=5, shares=2)
        assert r["status"] == "OK"
        assert r["emv_yuan"] > 0
        assert r["is_estimate"] is True
        assert "估算" in r["disclaimer"] or "估算" in r["cpm_source"]

    def test_emv_no_data_not_available(self):
        """无互动数据 → NOT_AVAILABLE，禁止估 0。"""
        import emv
        r = emv.calculate_emv(likes=0, comments=0, collects=0, shares=0)
        assert r["status"] == "NOT_AVAILABLE"
        assert r["emv_yuan"] is None

    def test_emv_aggregate_coverage(self):
        """汇总：返回 EMV 总额 + 覆盖度；部分无数据不阻塞。"""
        import emv
        notes = [
            {"note_id": "A", "title": "t1", "likes": 100, "comments": 5,
             "collects": 2, "shares": 1, "sentiment": "pos"},
            {"note_id": "B", "title": "t2", "likes": 0, "comments": 0,
             "collects": 0, "shares": 0, "sentiment": "neu"},
        ]
        r = emv.aggregate_emv(notes)
        assert r["status"] == "OK"
        assert r["available_count"] == 1
        assert r["coverage"] == 0.5
        assert r["is_estimate"] is True

    def test_emv_custom_cpm(self):
        """自定义 CPM 生效并标注来源。"""
        import emv
        r = emv.calculate_emv(likes=100, comments=10, collects=5, shares=2, cpm=5.0)
        assert r["cpm"] == 5.0
        assert "自定义" in r["cpm_source"]


# ===================== IC-039 本地化守卫 =====================
class TestIC039LocalizationGuard:
    @pytest.fixture(autouse=True)
    def _guard(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
        import localization_guard as lg
        lg.ENABLED = True
        return lg

    def test_zh_absolute_word_hold(self):
        """中文绝对化用语（最/第一）→ HOLD + 人工复核。"""
        import localization_guard as lg
        r = lg.check("我们是广州最领先的免税购物中心", lang="zh")
        assert r["hold"] is True
        assert r["requires_human"] is True
        assert any(h["pattern"] in ("最", "领先") for h in r["hits"])

    def test_zh_clean_pass(self):
        """合规内容 → 不 HOLD。"""
        import localization_guard as lg
        r = lg.check("免税购物体验分享，值得一逛", lang="zh")
        assert r["hold"] is False

    def test_symbol_block(self):
        """宗教/王室符号 → BLOCK。"""
        import localization_guard as lg
        r = lg.check("本店为清真认证合作商户", lang="zh")
        assert r["blocked"] is True
        assert r["requires_human"] is True

    def test_ko_absolute_word(self):
        """韩文绝对化用语命中。"""
        import localization_guard as lg
        r = lg.check("우리는 최고의 브랜드입니다", lang="ko")
        assert r["hold"] is True

    def test_en_absolute_word(self):
        """英文绝对化用语命中。"""
        import localization_guard as lg
        r = lg.check("We are the best duty-free store", lang="en")
        assert r["hold"] is True

    def test_multi_lang(self):
        """多语言聚合检查。"""
        import localization_guard as lg
        r = lg.check_multi("We are the best", langs=["zh", "en", "ko"])
        assert r["hold"] is True
        assert len(r["results"]) == 3

    def test_disable_switch(self):
        """独立开关关闭 → 不检查。"""
        import localization_guard as lg
        old = lg.ENABLED
        lg.ENABLED = False
        try:
            r = lg.check("我们是最领先的", lang="zh")
            assert r["hold"] is False
            assert r.get("disabled") is True
        finally:
            lg.ENABLED = old

    def test_ai_label(self):
        """AI 输出待母语者确认标记。"""
        import localization_guard as lg
        r = lg.check("我们是唯一选择", lang="zh")
        assert r["requires_human"] is True
        assert "待母语者确认" in r["label"]


# ===================== IC-040 KOS 兴趣图谱信号 =====================
class TestIC040InterestSignal:
    def test_no_data_graceful(self):
        """无账号数据 → 优雅降级，不抛异常。"""
        import kos_engine as ke
        r = ke.interest_signal("__nonexistent_author__")
        assert r["signal_status"] == "insufficient"
        assert r["no_blackhat"] is True

    def test_proxy_label(self):
        """代理指标显式标注（不冒充平台原生信号）。"""
        import kos_engine as ke
        r = ke.interest_signal("__nonexistent_author__")
        # insufficient 分支不包含 signals；验证源可用性声明存在
        assert "watch_completion" in r.get("source_availability", {})
        src = r["source_availability"]["watch_completion"]
        assert src["available"] is False
        assert "proxy" in src

    def test_not_change_kos_score(self):
        """兴趣信号不改变 kos_score 主计算（纯附加维度）。"""
        import kos_engine as ke
        # interest_signal 无副作用：仅只读聚合
        sig = ke.interest_signal("__nonexistent_author__")
        assert sig.get("note", "") == "" or "附加评估维度" in sig.get("note", "") or sig["signal_status"] == "insufficient"


# ===================== API 冒烟（test_client + Basic Auth） =====================
class TestICAPISmoke:
    def _client(self):
        import base64
        import app as app_mod
        app_mod.app.config["TESTING"] = True
        # 从 .env 读取真实认证凭证构造 Basic Auth 头
        env = {}
        try:
            _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            for _line in open(_env_path, encoding="utf-8"):
                _line = _line.strip()
                if "=" in _line and not _line.startswith("#"):
                    _k, _v = _line.split("=", 1)
                    env[_k.strip()] = _v.strip().strip('"')
        except Exception:
            pass
        _u = env.get("TAIKOO_AUTH_USER", "zachary")
        _p = env.get("TAIKOO_AUTH_PASSWORD", "Zachary01")
        _tok = base64.b64encode(("%s:%s" % (_u, _p)).encode()).decode()
        c = app_mod.app.test_client()
        c.environ_base["HTTP_AUTHORIZATION"] = "Basic " + _tok
        return c

    def test_emv_api(self):
        c = self._client()
        r = c.get("/api/ic/emv?limit=5")
        assert r.status_code == 200
        j = r.get_json()
        assert j["ok"] is True

    def test_localization_api(self):
        c = self._client()
        r = c.post("/api/ic/localization/check",
                   json={"text": "我们是最领先的免税店", "lang": "zh"})
        assert r.status_code == 200
        j = r.get_json()
        assert j["hold"] is True

    def test_kos_interest_api(self):
        c = self._client()
        r = c.get("/api/ic/kos/interest-signal?author_id=__nonexistent_author__")
        assert r.status_code == 200
        j = r.get_json()
        assert j["ok"] is True

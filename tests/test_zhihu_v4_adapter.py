# -*- coding: utf-8 -*-
"""
知乎 v4 adapter 单元测试（全 mock，不实际访问知乎 API）
"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from v4_upgrade.adapters.zhihu import ZhihuAdapter


def _mock_response(json_data):
    resp = MagicMock()
    resp.json.return_value = json_data
    return resp


class TestZhihuAdapterSearch:

    @patch("v4_upgrade.adapters.zhihu.requests.get")
    def test_search_answer_success(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [
                {"object": {
                    "type": "answer", "id": "a1",
                    "question": {"id": "q1", "title": "广州太古汇怎么样？"},
                    "excerpt": "<p>很好的商场</p>",
                    "author": {"id": 1, "name": "答主A"},
                    "voteup_count": 500, "comment_count": 30,
                    "created_time": 1700000000,
                }},
            ]
        })
        ad = ZhihuAdapter()
        result = ad.search("广州太古汇", max_results=10)
        assert result.success is True
        assert result.raw_count == 1
        assert result.notes[0].title == "广州太古汇怎么样？"
        assert result.notes[0].content == "很好的商场"
        assert result.notes[0].author == "答主A"
        assert result.notes[0].likes == 500
        assert result.notes[0].comments == 30
        assert result.notes[0].url == "https://www.zhihu.com/question/q1/answer/a1"
        assert result.notes[0].source_platform == "zhihu"
        assert result.notes[0].publish_date.startswith("2023-")

    @patch("v4_upgrade.adapters.zhihu.requests.get")
    def test_search_article_success(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [
                {"object": {
                    "type": "article", "id": "art1",
                    "title": "深度分析", "excerpt": "文章摘要",
                    "author": {"id": 2, "name": "作者B"},
                    "voteup_count": 100, "comment_count": 10,
                    "created": 1700000100,
                    "url": "https://zhuanlan.zhihu.com/p/art1",
                }},
            ]
        })
        ad = ZhihuAdapter()
        result = ad.search("test", max_results=5)
        assert result.success is True
        assert result.notes[0].title == "深度分析"
        assert result.notes[0].url == "https://zhuanlan.zhihu.com/p/art1"

    @patch("v4_upgrade.adapters.zhihu.requests.get")
    def test_search_question_success(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [
                {"object": {
                    "type": "question", "id": "q2",
                    "title": "这是一个问题", "excerpt": "",
                    "author": {"id": 3, "name": "提问者"},
                    "answer_count": 5,
                }},
            ]
        })
        ad = ZhihuAdapter()
        result = ad.search("test", max_results=5)
        assert result.success is True
        assert result.notes[0].comments == 5
        assert result.notes[0].url == "https://www.zhihu.com/question/q2"

    @patch("v4_upgrade.adapters.zhihu.requests.get")
    def test_search_empty(self, mock_get):
        mock_get.return_value = _mock_response({"data": []})
        ad = ZhihuAdapter()
        result = ad.search("不存在", max_results=5)
        assert result.success is True
        assert len(result.notes) == 0

    @patch("v4_upgrade.adapters.zhihu.requests.get")
    def test_search_api_error(self, mock_get):
        mock_get.return_value = _mock_response({"error": {"message": "参数错误", "code": 100}})
        ad = ZhihuAdapter()
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "API错误" in result.error

    def test_search_empty_keyword(self):
        ad = ZhihuAdapter()
        result = ad.search("", max_results=5)
        assert result.success is False
        assert "关键词" in result.error

    @patch("v4_upgrade.adapters.zhihu.requests.get")
    def test_search_exception(self, mock_get):
        mock_get.side_effect = RuntimeError("网络中断")
        ad = ZhihuAdapter()
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "异常" in result.error

    @patch("v4_upgrade.adapters.zhihu.requests.get")
    def test_search_max_results(self, mock_get):
        items = [{"object": {"type": "question", "id": str(i), "title": f"q{i}",
                             "answer_count": 0}} for i in range(10)]
        mock_get.return_value = _mock_response({"data": items})
        ad = ZhihuAdapter()
        result = ad.search("test", max_results=3)
        assert len(result.notes) == 3

    @patch("v4_upgrade.adapters.zhihu.requests.get")
    def test_search_skips_unknown_types(self, mock_get):
        mock_get.return_value = _mock_response({
            "data": [
                {"object": {"type": "live", "id": "l1"}},
                {"object": {"type": "answer", "id": "a1",
                            "question": {"id": "q1", "title": "有效回答"},
                            "excerpt": "内容", "author": {"name": "x"},
                            "voteup_count": 0, "comment_count": 0}},
            ]
        })
        ad = ZhihuAdapter()
        result = ad.search("test", max_results=5)
        assert len(result.notes) == 1
        assert result.notes[0].title == "有效回答"


class TestZhihuAdapterUtils:

    def test_clean_html(self):
        assert ZhihuAdapter._clean_html("<p>hello</p>") == "hello"
        assert ZhihuAdapter._clean_html("") == ""
        assert ZhihuAdapter._clean_html(None) == ""

    def test_ts_to_iso(self):
        assert ZhihuAdapter._ts_to_iso(1700000000).startswith("2023-11-14")
        assert ZhihuAdapter._ts_to_iso(None) == ""
        assert ZhihuAdapter._ts_to_iso("bad") == ""


class TestZhihuAdapterRegistry:

    def test_registry_has_zhihu(self):
        from v4_upgrade.adapters.registry import registry, register_default_adapters
        register_default_adapters()
        ad = registry.get("zhihu")
        assert ad is not None
        assert ad.platform_name == "zhihu"

    def test_adapter_has_circuit_breaker(self):
        ad = ZhihuAdapter()
        assert ad.breaker is not None
        assert ad.rate_limiter is not None

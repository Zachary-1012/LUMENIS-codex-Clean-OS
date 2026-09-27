"""Source names are independent of the search query and of scope permission."""
import sqlite3

import pytest


@pytest.mark.parametrize("domain,name,other,text,expected", [
    ("cth", "深圳万象城", "深圳湾万象城", "深圳湾万象城的高端业态", False),
    ("cth", "深圳万象城", "深圳湾万象城", "罗湖深圳万象城探店", True),
    ("cth", "广州太古汇", "上海兴业太古汇", "上海兴业太古汇活动", False),
    ("cth", "广州太古汇", "上海兴业太古汇", "广州太古汇的活动", True),
    ("bmp", "Nike", "Adidas", "NIKE presents a new campaign", True),
    ("bmp", "Nike", "Adidas", "nikelab is not an explicit Nike entity reference".split(" is")[0], False),
    ("bmp", "Le Labo", "Aesop", "LE  LABO 香水", True),
    ("bmp", "Nike", "Nike", "Nike campaign", False),
])
def test_source_entity_mention_is_not_supplied_by_query(tmp_path, monkeypatch, domain, name, other, text, expected):
    from lumenis.system.collector.adapters.secondary_collection import _prelaunch_entity_mentions

    db = tmp_path / "registry.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE lumenis_subject_registry(subject_id TEXT, brand_focus_id TEXT, name_zh TEXT, name_en TEXT, domain_id TEXT, status TEXT)")
        conn.executemany("INSERT INTO lumenis_subject_registry VALUES(?,?,?,?,?,?)", [
            ("SUBJ-1", "BRAND-1" if domain == "bmp" else None, name, name, domain.upper(), "configured"),
            ("SUBJ-2", "BRAND-2" if domain == "bmp" else None, other, other, domain.upper(), "configured"),
        ])
    monkeypatch.setenv("ZBC_DB_PATH", str(db))
    result = _prelaunch_entity_mentions([
        {"content_id": "1", "title": text, "source_keyword": name,
         "matched_keywords": name, "author_nickname": name},
    ], {"domain_id": domain, "subject_id": "SUBJ-1" if domain == "cth" else None,
        "brand_focus_id": "BRAND-1" if domain == "bmp" else None})[0]
    assert (result["status"] == "EXACT_NAME_MENTION") is expected
    assert len(result["source_text_sha256"]) == 64
    assert result["source_id"] == "1"

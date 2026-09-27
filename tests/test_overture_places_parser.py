from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from lumenis.system.collector.adapters.overture_places import (
    parse_overture_place_rows,
    read_overture_places_parquet,
)


class _ArrowStructScalar:
    def __init__(self, value):
        self.value = value

    def as_py(self):
        return self.value


def _row(**changes):
    row = {
        "id": "gers-place-01",
        "names": {"primary": "Harbour Centre"},
        "basic_category": "shopping_mall",
        "taxonomy": {
            "primary": "shopping_mall",
            "hierarchy": ["shopping", "shopping_mall"],
            "alternates": [],
        },
        "brand": {"names": {"primary": "Harbour Group"}},
        "addresses": [{
            "country": "SG", "locality": "Singapore",
            "freeform": "1 Marina Boulevard", "postcode": "018989",
        }],
        "confidence": 0.87,
        "operating_status": "open",
        "sources": [{"dataset": "example", "license": "CDLA-Permissive-2.0", "record_id": "r1"}],
    }
    row.update(changes)
    return row


def test_normalizes_singapore_mall_brand_and_source_metadata():
    result = parse_overture_place_rows([_row()], release="2026-09-23.1")

    assert len(result["candidates"]) == 1
    candidate = result["candidates"][0]
    assert candidate["candidate_id"] == "overture:gers-place-01"
    assert candidate["stable_source_id"] == "gers-place-01"
    assert candidate["candidate_kinds"] == ["shopping_mall", "brand_place"]
    assert candidate["name"] == "Harbour Centre"
    assert candidate["brand_name"] == "Harbour Group"
    assert candidate["category"] == "shopping_mall"
    assert candidate["address"] == "1 Marina Boulevard"
    assert candidate["postcode"] == "018989"
    assert candidate["confidence"] == 0.87
    assert candidate["source_metadata"]["release"] == "2026-09-23.1"
    assert candidate["source_metadata"]["upstream_sources"][0]["license"] == "CDLA-Permissive-2.0"
    assert candidate["field_states"]["location"] == "AVAILABLE"


def test_missing_values_stay_unknown_and_do_not_become_zero():
    row = _row(confidence=None, addresses=[], sources=[])
    result = parse_overture_place_rows([row])
    candidate = result["unlocated_candidates"][0]

    assert candidate["confidence"] is None
    assert candidate["confidence_state"] == "NOT_AVAILABLE"
    assert candidate["address"] is None
    assert candidate["postcode"] is None
    assert candidate["field_states"]["location"] == "UNKNOWN"
    assert candidate["source_metadata"]["upstream_license_state"] == "NOT_AVAILABLE"
    assert candidate["source_metadata"]["release_state"] == "NOT_AVAILABLE"


def test_dedup_is_order_independent_and_reports_duplicate_count():
    sparse = _row(confidence=0.4, addresses=[{"country": "SG"}], sources=[])
    rich = _row(confidence=0.9)
    forward = parse_overture_place_rows([sparse, rich])
    reverse = parse_overture_place_rows([rich, sparse])

    assert forward == reverse
    assert len(forward["candidates"]) == 1
    assert forward["candidates"][0]["confidence"] == 0.9
    assert forward["counts"]["deduplicated"] == 1


def test_foreign_rows_are_excluded_and_unknown_location_is_explicit():
    foreign = _row(addresses=[{"country": "MY", "postcode": "50000"}])
    unknown = _row(id="gers-place-02", addresses=[])
    missing_id = _row(id=" ")
    result = parse_overture_place_rows([foreign, unknown, missing_id])

    assert result["candidates"] == []
    assert [row["stable_source_id"] for row in result["unlocated_candidates"]] == ["gers-place-02"]
    assert result["unlocated_candidates"][0]["country_code"] is None
    assert result["unlocated_candidates"][0]["field_states"]["location"] == "UNKNOWN"
    assert result["counts"] == {
        "input": 3, "missing_id": 1, "out_of_scope": 1,
        "not_candidate": 0, "unknown_location": 1, "deduplicated": 0,
    }


def test_country_code_is_parameterized_and_arrow_address_scalars_are_mapped():
    row = _row(addresses=[_ArrowStructScalar({
        "country": "my", "locality": "Kuala Lumpur", "postcode": "50000",
        "freeform": "1 Jalan Example",
    })])

    result = parse_overture_place_rows([row], country_code="MY")

    assert result["candidates"][0]["country_code"] == "MY"
    assert result["candidates"][0]["postcode"] == "50000"
    assert result["counts"]["out_of_scope"] == 0


def test_reads_local_parquet_file_in_batches_to_singapore_candidates(tmp_path: Path):
    parquet_path = tmp_path / "overture_sg.parquet"
    escaped_path = str(parquet_path).replace("'", "''")
    connection = duckdb.connect(database=":memory:")
    try:
        connection.execute(f"""
            COPY (
                SELECT
                    id,
                    {{'primary': name}} AS names,
                    'shopping_mall' AS basic_category,
                    {{'primary': 'shopping_mall', 'hierarchy': ['shopping', 'shopping_mall'],
                     'alternates': []::VARCHAR[]}} AS taxonomy,
                    {{'names': {{'primary': 'Harbour Group'}}}} AS brand,
                    [{{'country': 'SG', 'locality': 'Singapore',
                      'freeform': '1 Marina Boulevard', 'postcode': '018989'}}] AS addresses,
                    0.87::DOUBLE AS confidence,
                    'open' AS operating_status,
                    [{{'dataset': 'example', 'license': 'CDLA-Permissive-2.0',
                      'record_id': 'source-1'}}] AS sources
                FROM (VALUES ('gers-place-01', 'Harbour Centre'),
                             ('gers-place-02', 'Bay Centre')) AS input(id, name)
            ) TO '{escaped_path}' (FORMAT PARQUET)
        """)
    finally:
        connection.close()

    result = read_overture_places_parquet(
        parquet_path, release="2026-09-23.1", batch_size=1
    )

    assert [item["stable_source_id"] for item in result["candidates"]] == [
        "gers-place-01", "gers-place-02",
    ]
    assert result["candidates"][0]["name"] == "Harbour Centre"
    assert result["candidates"][0]["postcode"] == "018989"
    assert result["candidates"][0]["confidence"] == 0.87
    assert result["candidates"][0]["source_metadata"]["upstream_sources"][0]["license"] == "CDLA-Permissive-2.0"
    assert result["counts"]["input"] == 2


def test_local_parquet_reader_rejects_remote_and_glob_paths():
    with pytest.raises(ValueError, match="literal local"):
        read_overture_places_parquet("https://example.invalid/places.parquet")
    with pytest.raises(ValueError, match="literal local"):
        read_overture_places_parquet("C:\\temp\\*.parquet")

"""CSV dialect regressions; pinned public UCI sample is local, never fetched by tests."""
import csv
import hashlib
import io
import os
from pathlib import Path

import pytest

from lumenis.importer.parser import parse_file


def parse(tmp_path, raw):
    path = tmp_path / 'source.csv'
    path.write_bytes(raw)
    result = parse_file(str(path))
    assert path.read_bytes() == raw
    assert result.metadata['source_fingerprint'] == hashlib.sha256(raw).hexdigest()
    assert result.metadata['original_bytes_modified'] is False
    return result


@pytest.mark.parametrize('delimiter', [',', ';', '\t'])
@pytest.mark.parametrize('encoding', ['utf-8', 'utf-8-sig', 'utf-16', 'utf-32', 'gb18030'])
def test_dialects_encoding_missing_quote_multiline_preserve(tmp_path, delimiter, encoding):
    rows = [['名称', 'description', 'amount', 'missing'],
            ['甲', 'Quoted ,;\t and "double" quote\r\nsecond line', '=SUM(A1:A2)', ''],
            ['乙', 'plain', '0', '']]
    stream = io.StringIO(newline='')
    csv.writer(stream, delimiter=delimiter, lineterminator='\r\n').writerows(rows)
    result = parse(tmp_path, stream.getvalue().encode(encoding))
    assert result.tables == [rows]
    assert result.metadata['csv_delimiter'] == delimiter
    assert result.metadata['csv_column_count'] == 4
    assert result.metadata['csv_missing_cell_count'] == 2
    assert result.metadata['csv_dialect_state'] == 'inferred_unique_rectangular'


@pytest.mark.parametrize('raw', [b'a,b;c\n1,2;3\n', b'a\tb,c\n1\t2,3\n'])
def test_ambiguous_dialect_rejected(tmp_path, raw):
    with pytest.raises(ValueError, match='CSV_DIALECT_AMBIGUOUS'):
        parse(tmp_path, raw)


@pytest.mark.parametrize('raw', [b'a,b\n1,2,3\n', b'a;b\n1;2;3\n', b'a\tb\n1\t2\t3\n'])
def test_ragged_columns_rejected_not_padded_or_flattened(tmp_path, raw):
    with pytest.raises(ValueError, match='CSV_COLUMNS_INCONSISTENT'):
        parse(tmp_path, raw)


@pytest.mark.parametrize('raw', [b'a,b\n"unterminated,2\n', b'a;b\n"x"oops;2\n', b'a;b\n1;"unterminated\n'])
def test_malformed_quotes_not_successful_single_column(tmp_path, raw):
    with pytest.raises(ValueError, match='CSV_'):
        parse(tmp_path, raw)


def test_existing_comma_text_contract_blank_records_and_single_column(tmp_path):
    result = parse(tmp_path, b'a,b\r\n1,\r\n\r\n2,0\r\n')
    assert result.tables == [[['a', 'b'], ['1', ''], [], ['2', '0']]]
    assert result.text == 'a,b\n1,\n\n2,0'
    assert result.metadata['csv_blank_record_count'] == 1
    assert result.metadata['csv_missing_cell_count'] == 1
    single = parse(tmp_path, b'name\nalpha\nbeta\n')
    assert single.tables == [[['name'], ['alpha'], ['beta']]]
    assert single.metadata['csv_dialect_state'] == 'single_column_or_empty'


@pytest.mark.parametrize('raw', [b'', b'a\x00b,c\n1,2', b'\xff\xfea'])
def test_invalid_encoding_binary_empty_rejected(tmp_path, raw):
    with pytest.raises(ValueError, match='DOCUMENT_TEXT_'):
        parse(tmp_path, raw)


def test_bounded_large_and_field_size_fail_honestly(tmp_path):
    with pytest.raises(ValueError, match='DOCUMENT_TEXT_SIZE_INVALID'):
        parse(tmp_path, b'a' * (8 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match='CSV_DIALECT_UNDETERMINED'):
        parse(tmp_path, b'a,b\n' + b'x' * (csv.field_size_limit()+1) + b',2\n')


def test_original_formula_cells_are_not_executed(tmp_path):
    result = parse(tmp_path, b'name;formula\na;=1+1\nb;@SUM(A1:A2)\nc;+CMD\nd;-10\n')
    assert [r[1] for r in result.tables[0][1:]] == ['=1+1', '@SUM(A1:A2)', '+CMD', '-10']


def test_official_facebook_original_when_provided(tmp_path):
    source = os.environ.get('LUMENIS_REAL_FACEBOOK_CSV') or (
        Path(__file__).parent / 'fixtures' / 'uci_facebook_metrics' / 'dataset_Facebook.csv'
    )
    raw = Path(source).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '666ec82952b7ce90b464f5a87ec4f0fe92d9a63208f2fcb2d0443cb5f31c3f4c'
    result = parse(tmp_path, raw)
    rows = result.tables[0]
    assert len(rows) == 501 and {len(row) for row in rows} == {19}
    assert result.metadata['csv_missing_cell_count'] == 6
    records = [dict(zip(rows[0], row)) for row in rows[1:]]
    assert {key:sum(r[key]=='' for r in records) for key in ['Paid','like','share']} == {'Paid':1,'like':1,'share':4}
    assert {typ:sum(r['Type']==typ for r in records) for typ in ['Link','Photo','Status','Video']} == {'Link':22,'Photo':426,'Status':45,'Video':7}


def test_official_facebook_override_missing_fails_not_skips(tmp_path, monkeypatch):
    monkeypatch.setenv('LUMENIS_REAL_FACEBOOK_CSV', str(tmp_path / 'missing.csv'))
    with pytest.raises(FileNotFoundError):
        test_official_facebook_original_when_provided(tmp_path)


def test_official_facebook_override_wrong_bytes_rejected(tmp_path, monkeypatch):
    source = tmp_path / 'wrong.csv'
    source.write_bytes(b'name;value\nsynthetic;1\n')
    monkeypatch.setenv('LUMENIS_REAL_FACEBOOK_CSV', str(source))
    with pytest.raises(AssertionError):
        test_official_facebook_original_when_provided(tmp_path)

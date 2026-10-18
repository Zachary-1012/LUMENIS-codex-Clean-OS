"""Structured data originals are treated as bounded text, never executed."""

import hashlib
import pytest
from lumenis.importer.parser import parse_file


@pytest.mark.parametrize("suffix", ["json", "xml", "xbrl"])
def test_structured_document_preserves_original_fingerprint(tmp_path, suffix):
    raw = (
        b'{"unit":"CNY","value":0}'
        if suffix == "json"
        else b"<root><value>0</value></root>"
    )
    path = tmp_path / ("source." + suffix)
    path.write_bytes(raw)
    parsed = parse_file(str(path))
    assert parsed.text == raw.decode()
    assert parsed.metadata["source_fingerprint"] == hashlib.sha256(raw).hexdigest()
    assert parsed.metadata["network_mode"] == "local_only"
    assert path.read_bytes() == raw

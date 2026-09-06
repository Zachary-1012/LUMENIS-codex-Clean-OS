import pytest

from osai_engine.canonical_data import create_entity, Source, validate_entity
from osai_engine.evidence_graph import EvidenceGraph


def test_canonical_entity_requires_product_subject_scope_provenance_hash():
    with pytest.raises(ValueError):
        create_entity("source", product_id="CTH")


def test_canonical_entity_accepts_complete_identity():
    entity = create_entity(
        "source", product_id="CTH", subject_id="taikoo-hui", scope="production",
        provenance="xhs:search", content_hash="abc123", source_type="xiaohongshu"
    )
    assert entity.canonical_id.startswith("src_")
    assert validate_entity(entity)["valid"] is True


def test_evidence_graph_rejects_unknown_relation_and_self_edge():
    graph = EvidenceGraph()
    a = graph.add_node("source", "src_1")
    b = graph.add_node("evidence", "ev_1")
    with pytest.raises(ValueError):
        graph.add_edge(a.node_id, b.node_id, "unknown")
    with pytest.raises(ValueError):
        graph.add_edge(a.node_id, a.node_id, "derived_from")


def test_evidence_graph_traces_derived_source():
    graph = EvidenceGraph()
    source = graph.add_node("source", "src_1")
    evidence = graph.add_node("evidence", "ev_1")
    finding = graph.add_node("finding", "find_1")
    graph.add_edge(evidence.node_id, source.node_id, "derived_from")
    graph.add_edge(finding.node_id, evidence.node_id, "derived_from")
    sources = graph.trace_to_source(finding.node_id)
    assert [n.canonical_id for n in sources] == ["src_1"]

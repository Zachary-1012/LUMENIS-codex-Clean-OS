import pytest
from tests.test_growth_learning_exchange import journey, transition, enqueue
from tests.test_saved_document_workflow import workspace
from lumenis.shared.learning import contribution as learning


def test_stage_requires_exact_approval(journey):
    j=journey
    out=enqueue(j)
    with pytest.raises((ValueError, PermissionError)):
        transition(j,out,'stage',approved=False)


def test_deleted_canonical_source_cannot_create_derivatives(journey):
    j=journey
    with j['repo'].transaction() as con:
        con.execute('DELETE FROM canonical_data WHERE source_id=?', (j['source']['source_id'],))
    with pytest.raises((ValueError, PermissionError, RuntimeError, LookupError)):
        transition(j,j['candidate'],'review')

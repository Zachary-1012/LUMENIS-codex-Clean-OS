import json
import pytest
from lumenis.shared.evaluation.openai_math_papers.core import Budget, MathInputError, ResourceBound
from lumenis.shared.evaluation.openai_math_papers.matching_113 import Graph
from lumenis.system.ai_gateway.research.openai_math_papers.train import load_data, topology_isomorphic


def test_permuted_multigraph_topology():
    a = Graph.read({'vertices': 4, 'edges': [[0,1],[0,1],[2,3],[1,2]]})
    b = Graph.read({'vertices': 4, 'edges': [[3,0],[2,1],[3,0],[0,2]]})
    assert topology_isomorphic(a, b, Budget())
    c = Graph.read({'vertices': 4, 'edges': [[0,1],[1,2],[2,3],[3,0]]})
    assert not topology_isomorphic(a, c, Budget())


def test_cross_split_permutation_rejected_even_changed_features(tmp_path):
    a = {'id':'a','split':'train','group_id':'a','origin':'DECLARED_SYNTHETIC_MATH',
         'graph':{'vertices':4,'edges':[[0,1],[1,2],[2,3],[3,0]]},
         'features':[[1],[2],[3],[4]],'target':[0,2]}
    b = {**a,'id':'b','split':'holdout','group_id':'b','features':[[4],[5],[6],[7]],
         'graph':{'vertices':4,'edges':[[3,0],[2,3],[1,2],[0,1]]}}
    p=tmp_path/'data.jsonl'
    p.write_text('\n'.join(json.dumps(x) for x in [a,b]))
    with pytest.raises(MathInputError, match='CROSS_SPLIT_TOPOLOGY_LEAKAGE'):
        load_data(p)


def test_different_vertex_counts_are_independent():
    assert not topology_isomorphic(Graph(4, ((0,1),(2,3))), Graph(6, ((0,1),(2,3),(4,5))), Budget())


def test_audit_budget_fails_closed():
    with pytest.raises(ResourceBound):
        topology_isomorphic(Graph(4, ((0,1),(2,3))), Graph(4, ((0,1),(2,3))), Budget(max_steps=1))

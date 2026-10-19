"""Exact CURRENT display checks; independent of Git/clone publication state.

The standalone static gate covers full validate(). These unit tests extract its
actual _require arguments and exercise the original predicate against real docs.
"""
import ast
import inspect
import pytest
from scripts.audit_tools import verify_codex_takeover_governance as gate

CHAIN = 'Platform-native Source → Source/Evidence/Canonical → OEVIRA presentation → Open Original → Return'


def check_current(document, text, label):
    calls = [node for node in ast.walk(ast.parse(inspect.getsource(inspect.unwrap(gate.validate))))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == '_require'
             and any(k.arg == 'label' and isinstance(k.value, ast.Constant)
                     and k.value.value == label for k in node.keywords)]
    assert len(calls) == 1
    call = calls[0]
    assert isinstance(call.args[0], ast.Name) and call.args[0].id == document
    markers = [ast.literal_eval(argument) for argument in call.args[1:]]
    gate._require(text, *markers, label=label)


def test_current_display_markers_pass_original_predicates():
    for document, label in [('architecture', 'CURRENT product architecture'),
                            ('experience', 'CURRENT Experience Constitution'),
                            ('source_index', 'CURRENT source owner index')]:
        check_current(document, gate._read(document), label)


@pytest.mark.parametrize('broken', [
    CHAIN.replace('OEVIRA presentation', 'LUMENIS presentation'),
    CHAIN.replace('Platform-native Source → ', ''),
    CHAIN.replace('Source/Evidence/Canonical → ', ''),
    CHAIN.replace(' → Open Original', ''),
    CHAIN.replace(' → Return', ''),
    CHAIN.replace('Open Original → Return', 'Return → Open Original'),
])
def test_changed_or_broken_display_chain_fails_original_predicate(broken):
    architecture = gate._read('architecture')
    assert architecture.count(CHAIN) == 1
    with pytest.raises(AssertionError, match='CURRENT product architecture'):
        check_current('architecture', architecture.replace(CHAIN, broken), 'CURRENT product architecture')


@pytest.mark.parametrize('document,current,obsolete,label', [
    ('experience', 'OEVIRA SourceTarget v1', 'LUMENIS SourceTarget v1', 'CURRENT Experience Constitution'),
    ('source_index', 'OEVIRA Source Owner Index', 'LUMENIS Source Owner Index', 'CURRENT source owner index'),
])
def test_obsolete_display_title_is_not_an_alternative(document, current, obsolete, label):
    original = gate._read(document)
    assert current in original
    with pytest.raises(AssertionError, match=label):
        check_current(document, original.replace(current, obsolete), label)

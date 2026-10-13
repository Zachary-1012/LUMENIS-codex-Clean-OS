"""Bounded, value-free shape diagnostics for ALREADY authorized parsed JSON.

Python adaptation of the shape/key-observation idea in SiteSnapshotter's
shapeOf / collectJsonKeys / detectPagination (commit ecbe61af5004f6efa493749a623fbd98ab307a37).
This is NOT a verbatim port. The traversal, budgets, allowlist, exact-name hints,
sampling and comparison contracts below are new. See vendor/lumenis-reuse-notices/Dvurechensky-MIT.txt.
It neither acquires data nor authorizes its use, never returns scalar values,
and is not an Evidence store, business parser or pagination executor.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable

MAX_INPUT = 1024 * 1024
SECRET = re.compile(r'auth|password|passwd|secret|token|cookie|session|csrf|xsrf|api.?key|credential|storage', re.I)
KEY = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')
PAGINATION = frozenset({'page', 'per_page', 'pageSize', 'limit', 'offset', 'cursor', 'next', 'prev', 'total', 'has_more', 'hasMore'})
DEFAULT_KEYS = frozenset({'data', 'items', 'results', 'aweme_info', 'aweme_detail',
    'statistics', 'aweme_id', 'create_time', 'desc', 'digg_count', 'comment_count',
    'collect_count', 'share_count', 'play_count', 'status_code', 'has_more', 'cursor',
    'offset', 'page', 'total', 'likes', 'comments', 'shares', 'views', 'id'})


def summarize(value: Any, allowed_keys: Iterable[str] = DEFAULT_KEYS, *,
              max_depth: int = 8, max_nodes: int = 4096,
              max_array: int = 20, max_object: int = 128) -> dict:
    """Return observed types/paths only. Input must come from an approved caller.

    Only exact built-in JSON types are traversed: no getters, custom mappings or
    serialization of arbitrary objects. Limits also protect direct in-memory use.
    Keys not explicitly allowed, and all secret-looking keys, are discarded.
    """
    for number, ceiling in ((max_depth, 32), (max_nodes, 16384), (max_array, 100), (max_object, 256)):
        if type(number) is not int or not 1 <= number <= ceiling:
            raise ValueError('Invalid diagnostic budget')
    supplied_keys = list(allowed_keys)
    if len(supplied_keys) > 256:
        raise ValueError('Too many allowed keys')
    allow = frozenset(k for k in supplied_keys if type(k) is str and KEY.fullmatch(k) and not SECRET.search(k))
    stack = [(value, '', 0, frozenset())]
    types: dict[str, set[str]] = {}
    hints: set[str] = set()
    limits: set[str] = set()
    nodes = 0
    omitted = False
    sampled = False
    while stack:
        if nodes >= max_nodes:
            limits.add('NODE_LIMIT')
            break
        node, path, depth, ancestors = stack.pop()
        nodes += 1
        t = type(node)
        if node is None:
            label = 'null'
        elif t is bool:
            label = 'boolean'
        elif t is int:
            label = 'integer'
        elif t is float:
            label = 'number' if math.isfinite(node) else 'invalid_nonfinite'
        elif t is str:
            label = 'string'
        elif t is list:
            label = 'array'
        elif t is dict:
            label = 'object'
        else:
            label = 'unsupported'
            limits.add('NON_JSON_TYPE')
        types.setdefault(path or '/', set()).add(label)
        if t not in (list, dict):
            continue
        if id(node) in ancestors:
            limits.add('CYCLE')
            continue
        if depth >= max_depth and node:
            limits.add('DEPTH_LIMIT')
            continue
        lineage = ancestors | {id(node)}
        remaining = max_nodes - nodes
        if t is list:
            count = min(len(node), max_array, remaining)
            if len(node) > count:
                sampled = True
                limits.add('ARRAY_SAMPLE_LIMIT' if len(node) > max_array else 'NODE_LIMIT')
            # Union observed element types, not just element zero as upstream.
            for item in reversed(node[:count]):
                stack.append((item, path + '/[]', depth + 1, lineage))
        else:
            accepted = []
            for i, (key, child) in enumerate(node.items()):
                if i >= max_object:
                    limits.add('OBJECT_KEY_LIMIT')
                    break
                if type(key) is not str or key not in allow:
                    omitted = True
                    continue
                child_path = path + '/' + key
                if key in PAGINATION:
                    hints.add(child_path)
                accepted.append((child, child_path, depth + 1, lineage))
                if len(accepted) >= remaining:
                    if remaining == 0:
                        accepted.clear()
                    limits.add('NODE_LIMIT')
                    break
            stack.extend(reversed(accepted))
    paths = {key: sorted(vals) for key, vals in sorted(types.items())}
    encoded = json.dumps(paths, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return {'schema': 'lumenis.response-shape.v1', 'classification': 'DERIVATIVE_DIAGNOSTIC_ONLY',
            'scope': 'ALLOWLISTED_OBSERVED_SAMPLE_NOT_FULL_SCHEMA', 'paths': paths,
            'shape_sha256': hashlib.sha256(encoded).hexdigest(),
            'pagination_hints': sorted(hints), 'pagination_state': 'HINT_ONLY_NO_FETCH',
            'values_included': False, 'unknown_metrics_filled': False,
            'visited_nodes': nodes, 'filtered_keys_present': omitted,
            'array_sampled': sampled, 'limits_hit': sorted(limits)}


def compare(before: dict, after: dict) -> dict:
    """Differences in observations are NOT proof that a platform changed schema."""
    for value in (before, after):
        if value.get('schema') != 'lumenis.response-shape.v1':
            raise ValueError('Unsupported shape format')
    old, new = before['paths'], after['paths']
    return {'classification': 'DERIVATIVE_DIAGNOSTIC_ONLY',
            'newly_observed_paths': sorted(new.keys() - old.keys()),
            'not_observed_in_current_sample': sorted(old.keys() - new.keys()),
            'observed_type_changes': [
                {'path': p, 'before_types': old[p], 'after_types': new[p]}
                for p in sorted(old.keys() & new.keys()) if old[p] != new[p]],
            'interpretation': 'SAMPLE_DIFFERENCE_NOT_CONFIRMED_SCHEMA_CHANGE',
            'limited_sample': bool(before['limits_hit'] or after['limits_hit'])}


def _load(path: Path) -> Any:
    if not path.is_file() or path.is_symlink():
        raise ValueError('Expected explicit regular JSON file')
    with path.open('rb') as stream:
        data = stream.read(MAX_INPUT + 1)
    if len(data) > MAX_INPUT:
        raise ValueError('Input exceeds 1 MiB')
    def reject_constant(_value: str):
        raise ValueError('Nonfinite JSON is not supported')
    def unique_keys(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('Duplicate JSON key')
            result[k] = v
        return result
    return json.loads(data.decode('utf-8-sig'), parse_constant=reject_constant,
                      object_pairs_hook=unique_keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--compare-input', type=Path,
                        help='Optional second already authorized response JSON; outputs shapes and sample differences')
    args = parser.parse_args()
    try:
        first = summarize(_load(args.input))
        result = first
        if args.compare_input:
            second = summarize(_load(args.compare_input))
            result = {'before': first, 'after': second, 'comparison': compare(first, second)}
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        # JSON parse error strings can contain private values; report class only.
        print(json.dumps({'status': 'NOT_VERIFIED', 'error_class': type(exc).__name__}), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())


# LUMENIS integration, 2026-10-13: invocation-local observations and an
# independently validated upper-adapter boundary. No network or persistence.
_DIAGNOSTIC_LIMIT = 64 * 1024
_COUNTER_LIMIT = 2**31 - 1
_SHAPE_SCHEMA = 'lumenis.response-shape.v1'
_SHAPE_CLASS = 'DERIVATIVE_DIAGNOSTIC_ONLY'
_SHAPE_SCOPE = 'ALLOWLISTED_OBSERVED_SAMPLE_NOT_FULL_SCHEMA'
_SHAPE_LIMITS = frozenset({'NODE_LIMIT', 'DEPTH_LIMIT', 'ARRAY_SAMPLE_LIMIT',
                          'OBJECT_KEY_LIMIT', 'CYCLE', 'NON_JSON_TYPE'})
_SHAPE_TYPES = frozenset({'null', 'boolean', 'integer', 'number', 'string',
                         'array', 'object', 'invalid_nonfinite', 'unsupported'})
_COUNTER_NAMES = frozenset({'matching_responses_observed', 'json_objects_observed',
                           'parse_failures', 'shape_samples'})


def _diagnostic_bytes(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=True, allow_nan=False).encode('ascii')


class SearchShapeDiagnostics:
    """One search invocation, at most eight inspections and four unique shapes."""

    def __init__(self) -> None:
        self._counters = dict.fromkeys(_COUNTER_NAMES, 0)
        self._shapes: list[dict] = []
        self._processed = 0
        self._limited = False
        self._unavailable = False

    def _increment(self, key: str) -> None:
        if self._counters[key] == _COUNTER_LIMIT:
            self._limited = True
        else:
            self._counters[key] += 1

    def response_observed(self) -> None:
        self._increment('matching_responses_observed')

    def parse_failed(self) -> None:
        self._increment('parse_failures')

    def observe_json(self, value: Any) -> None:
        self._increment('json_objects_observed')
        if self._processed >= 8:
            self._limited = True
            return
        self._processed += 1
        try:
            shape = summarize(value)
            if shape['limits_hit']:
                self._limited = True
            for old in self._shapes:
                if old['shape_sha256'] == shape['shape_sha256']:
                    # A repeated shape must not erase sampling/omission limits.
                    old['limits_hit'] = sorted(set(old['limits_hit']) | set(shape['limits_hit']))
                    old['filtered_keys_present'] |= shape['filtered_keys_present']
                    old['array_sampled'] |= shape['array_sampled']
                    old['visited_nodes'] = max(old['visited_nodes'], shape['visited_nodes'])
                    return
            if len(self._shapes) == 4:
                self._limited = True
                return
            # Reserve space for all later bounded counter and flag changes.
            candidate = self.snapshot()
            candidate['shape_samples'].append(shape)
            if len(_diagnostic_bytes(candidate)) > _DIAGNOSTIC_LIMIT - 2048:
                self._limited = True
                return
            self._shapes.append(shape)
            self._counters['shape_samples'] = len(self._shapes)
        except Exception:
            # Diagnostics must never affect the authoritative business result.
            self._unavailable = True

    def snapshot(self) -> dict:
        status = ('LIMIT_REACHED' if self._limited else
                  'DIAGNOSTIC_UNAVAILABLE' if self._unavailable else
                  'OBSERVED' if self._counters['matching_responses_observed'] else
                  'NOT_OBSERVED')
        return json.loads(json.dumps({
            'schema': _SHAPE_SCHEMA, 'classification': _SHAPE_CLASS,
            'scope': _SHAPE_SCOPE, 'status': status,
            'counters': dict(self._counters), 'shape_samples': self._shapes,
            'limits_hit': ['LIMIT_REACHED'] if self._limited else [],
            'values_included': False, 'unknown_metrics_filled': False,
            'pagination_state': 'HINT_ONLY_NO_FETCH',
        }))


def _checked_shape(shape: Any) -> dict:
    fields = {'schema', 'classification', 'scope', 'paths', 'shape_sha256',
              'pagination_hints', 'pagination_state', 'values_included',
              'unknown_metrics_filled', 'visited_nodes', 'filtered_keys_present',
              'array_sampled', 'limits_hit'}
    if type(shape) is not dict or len(shape) != len(fields) or any(type(k) is not str for k in shape) or set(shape) != fields:
        raise ValueError('Invalid shape fields')
    if (any(type(shape[k]) is not str for k in ('schema', 'classification', 'scope', 'pagination_state'))
            or shape['schema'] != _SHAPE_SCHEMA or shape['classification'] != _SHAPE_CLASS
            or shape['scope'] != _SHAPE_SCOPE or shape['pagination_state'] != 'HINT_ONLY_NO_FETCH'):
        raise ValueError('Invalid shape identity')
    for k in ('values_included', 'unknown_metrics_filled'):
        if shape[k] is not False:
            raise ValueError('Values are forbidden')
    if any(type(shape[k]) is not bool for k in ('filtered_keys_present', 'array_sampled')):
        raise ValueError('Invalid shape flags')
    if type(shape['visited_nodes']) is not int or not 1 <= shape['visited_nodes'] <= 4096:
        raise ValueError('Invalid node budget')
    paths = shape['paths']
    if type(paths) is not dict or not 1 <= len(paths) <= 4096:
        raise ValueError('Invalid paths')
    for path, labels in paths.items():
        if type(path) is not str or len(path) > 520 or not path.startswith('/'):
            raise ValueError('Invalid path')
        parts = path.split('/')[1:]
        if path != '/' and (len(parts) > 8 or any(k not in DEFAULT_KEYS and k != '[]' for k in parts)):
            raise ValueError('Unapproved path')
        if (type(labels) is not list or not 1 <= len(labels) <= len(_SHAPE_TYPES)
                or any(type(k) is not str or k not in _SHAPE_TYPES for k in labels)
                or labels != sorted(set(labels))):
            raise ValueError('Invalid types')
    hints = shape['pagination_hints']
    if (type(hints) is not list or len(hints) > 4096
            or any(type(p) is not str or len(p) > 520 or not p.startswith('/')
                   or len(p.split('/')[1:]) > 8
                   or any(k not in DEFAULT_KEYS and k != '[]' for k in p.split('/')[1:])
                   or p.rsplit('/', 1)[-1] not in PAGINATION for p in hints)):
        raise ValueError('Invalid pagination hints')
    limits = shape['limits_hit']
    if (type(limits) is not list or len(limits) > len(_SHAPE_LIMITS)
            or any(type(x) is not str or x not in _SHAPE_LIMITS for x in limits)):
        raise ValueError('Invalid limits')
    digest = hashlib.sha256(json.dumps(paths, sort_keys=True, separators=(',', ':')).encode('utf8')).hexdigest()
    if type(shape['shape_sha256']) is not str or shape['shape_sha256'] != digest:
        raise ValueError('Invalid shape digest')
    return shape


def validate_acquisition_diagnostics(value: Any) -> dict:
    """Reject untrusted fields/values; never echo input or serialize custom types."""
    try:
        fields = {'schema', 'classification', 'scope', 'status', 'counters',
                  'shape_samples', 'limits_hit', 'values_included',
                  'unknown_metrics_filled', 'pagination_state'}
        if type(value) is not dict or len(value) != len(fields) or any(type(k) is not str for k in value) or set(value) != fields:
            return {}
        if (any(type(value[k]) is not str for k in ('schema', 'classification', 'scope', 'pagination_state'))
                or value['schema'] != _SHAPE_SCHEMA or value['classification'] != _SHAPE_CLASS
                or value['scope'] != _SHAPE_SCOPE or value['pagination_state'] != 'HINT_ONLY_NO_FETCH'
                or type(value['status']) is not str or value['status'] not in
                {'NOT_OBSERVED', 'OBSERVED', 'LIMIT_REACHED', 'DIAGNOSTIC_UNAVAILABLE'}
                or value['values_included'] is not False or value['unknown_metrics_filled'] is not False):
            return {}
        counts, shapes = value['counters'], value['shape_samples']
        if (type(counts) is not dict or len(counts) != 4 or any(type(k) is not str for k in counts) or set(counts) != _COUNTER_NAMES
                or any(type(n) is not int or not 0 <= n <= _COUNTER_LIMIT for n in counts.values())
                or type(shapes) is not list or len(shapes) > 4 or counts['shape_samples'] != len(shapes)
                or counts['json_objects_observed'] < len(shapes)):
            return {}
        if (type(value['limits_hit']) is not list or len(value['limits_hit']) > 1
                or any(type(x) is not str for x in value['limits_hit'])
                or value['limits_hit'] not in ([], ['LIMIT_REACHED'])):
            return {}
        if (value['status'] == 'LIMIT_REACHED') != bool(value['limits_hit']):
            return {}
        for shape in shapes:
            _checked_shape(shape)
        if len({s['shape_sha256'] for s in shapes}) != len(shapes):
            return {}
        encoded = _diagnostic_bytes(value)
        if len(encoded) > _DIAGNOSTIC_LIMIT:
            return {}
        return json.loads(encoded)
    except Exception:
        return {}

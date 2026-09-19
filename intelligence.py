"""Compatibility import surface for the retired root AI Gateway owner.

Canonical owner: lumenis.system.ai_gateway.core.
The module object is aliased, rather than copying symbols, so monkeypatching and
runtime state remain single-owner as well.
"""
import sys as _sys
from lumenis.system.ai_gateway import core as _canonical_core

_sys.modules[__name__] = _canonical_core

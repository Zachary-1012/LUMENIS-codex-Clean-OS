"""Transitional import surface for the retired root migration owner.

Canonical owner: lumenis.shared.database.migrations.
This file contains no migration definitions. Delete it after remaining
CLI/import callers have moved to the canonical package.
"""
from lumenis.shared.database.migrations import *  # noqa: F401,F403

if __name__ == "__main__":
    main()

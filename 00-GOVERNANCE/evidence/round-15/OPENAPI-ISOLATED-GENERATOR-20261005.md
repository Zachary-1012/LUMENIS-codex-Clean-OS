# Isolated OpenAPI contract generator — 2026-10-05

## Problem

`openapi_spec.py` can build the route contract only after Flask has registered
the active URL map. Importing `app` in an ordinary workstation environment may
initialize the default SQLite path even though the route map itself needs no
business data. That can create WAL/SHM sidecars and block the repository's
protected-database test seed gate.

## Current behavior

Running `python openapi_spec.py` now uses a fresh-process-only, disposable data
root before importing `app`:

- `ZBC_DB_PATH`, Evidence DB path, data directory and logs point to a temporary
  location;
- the temporary schema is migrated before Flask routes are inspected;
- guardian startup remains disabled for this generator; and
- no default repository database, production Cookie/session, collector,
  scheduler, browser, training or external service is used.

The normal outputs remain the existing canonical files:
`docs/API-OPENAPI-SPEC.json` and `docs/API-ROUTE-MATRIX.md`. The generator does
not define product behavior or a second API authority.

## Verification

`tests/test_openapi_spec.py` now launches the CLI into temporary output files,
checks that both artifacts are generated, and confirms the protected
`data/monitor.db` plus its sidecar state are byte-for-byte unchanged when it
exists. In a clean GitHub checkout where that ignored workstation database is
absent, the same test confirms the generator leaves it absent and uses only its
own disposable schema.

The isolated OpenAPI suite passed seven cases locally with no background-thread
leak. A direct CLI generation into temporary output paths reported 839 API
routes and 863 operations. No production database migration, checkpoint,
collection, browser action, GPU action or remote request was performed.

## Limit

This is an engineering-documentation isolation repair. It does not establish
live API behavior, a product release, runtime health or user acceptance.

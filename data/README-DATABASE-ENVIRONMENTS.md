# Database environments

P0-C defines three physically separate runtime zones:

- `data/production/` — new production placements; the historical `data/monitor.db`
  remains a compatibility path until an approved cutover.
- `data/test/` — local non-pytest test databases only.
- `data/experiment/` — experiments and disposable analysis copies only.

Pytest does not use any of these repository directories. It forces `ZBC_DB_PATH`
to an operating-system temporary directory and verifies protected database
hash/mtime values before and after the session.

Database files stay ignored by Git. Moving, deleting, restoring, repairing, or
overwriting a production candidate requires a separate approval.

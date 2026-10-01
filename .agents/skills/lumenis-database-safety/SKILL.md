---
name: lumenis-database-safety
description: Must use for any LUMENIS database, SQLite, schema, migration, repository, persistence, canonical-data, backup, restore, or DB-path task.
---
# Database Safety
Canonical business DB is data/monitor.db selected through ZBC_DB_PATH and opened via lumenis/shared/database abstractions. Never create a module-local business DB or second migration/repository authority. Preserve state semantics instead of missing->0. Tests use isolated/disposable DBs. Do not destructively alter real production data without evidence and approval. Supabase is not the canonical LUMENIS DB unless a future approved architecture decision changes that.

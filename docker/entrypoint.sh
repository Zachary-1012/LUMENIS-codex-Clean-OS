#!/bin/sh
# Z-Brand Core container entrypoint.
# Ensures state dirs exist and the DB path is exported before launch.
# Collection stays OFF unless explicitly enabled (Staging uses --no-scheduler
# via compose override). This script never seeds production credentials.
set -e

: "${ZBC_DB_PATH:=/app/data/monitor.db}"
export ZBC_DB_PATH

mkdir -p /app/data /app/logs

for runtime_dir in /app/data /app/logs; do
    if [ ! -w "$runtime_dir" ]; then
        printf '[entrypoint] UID/GID 10001:10001 cannot write %s; align the mounted volume ownership with the image runtime user.\n' "$runtime_dir" >&2
        exit 73
    fi
done

echo "[entrypoint] ZBC_ENV=${ZBC_ENV:-production} DB=${ZBC_DB_PATH} args=$*"
exec "$@"

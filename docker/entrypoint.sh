#!/bin/sh
# Z-Brand Core container entrypoint.
# Ensures state dirs exist and the DB path is exported before launch.
# Collection stays OFF unless explicitly enabled (Staging uses --no-scheduler
# via compose override). This script never seeds production credentials.
set -e

: "${ZBC_DB_PATH:=/app/data/monitor.db}"
export ZBC_DB_PATH

mkdir -p /app/data /app/logs

echo "[entrypoint] ZBC_ENV=${ZBC_ENV:-production} DB=${ZBC_DB_PATH} args=$*"
exec "$@"

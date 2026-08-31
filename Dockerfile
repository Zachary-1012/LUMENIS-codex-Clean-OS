# =====================================================================
# Z-Brand Core / CTH-POMS  -  Container image (Staging/Production parity)
# ---------------------------------------------------------------------
# Design notes (intentionally conservative, see docs/governance/DOCKER-STAGING.md):
# - Base python:3.12-slim; Flask + SQLite, no stack replacement.
# - No browser is baked into the image. Platform collection talks to an
#   external/remote CDP endpoint (XHS_CDP_URL). Staging never collects.
# - Runtime DB path is injected via ZBC_DB_PATH (database.py reads it), so the
#   image stays stateless and the SQLite file lives on a mounted volume.
# - Default CMD mirrors the locally-verified launch path (python app.py).
#   A production WSGI server (gunicorn) is a documented later hardening step,
#   not enabled until it is actually tested.
# Build:  docker build -t zbrand-core:latest .
# =====================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    ZBC_DB_PATH=/app/data/monitor.db

WORKDIR /app

# Minimal OS deps: curl for HEALTHCHECK, CA certs for HTTPS / paid proxy.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code (see .dockerignore for what is excluded).
COPY . .

RUN mkdir -p /app/data /app/logs

EXPOSE 8201

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS "http://127.0.0.1:${TAIKOO_PORT:-8201}/healthz" || exit 1

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "8201"]

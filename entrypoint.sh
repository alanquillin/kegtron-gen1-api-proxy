#! /bin/sh
set -e

if [ "${KEGTRON_PROXY_ROLE}" = "scanner" ]; then
    poetry run python scan.py
fi

if [ "${KEGTRON_PROXY_ROLE}" = "api" ]; then
    poetry run alembic upgrade head && \
    poetry run python src/app.py
fi

#! /bin/sh
set -e

if [ "${RUN_ENV}" = "dev" ]; then
    export FLASK_ENV="development"
    export KEGTRON_PROXY_LOG_LEVEL="DEBUG"
fi

if [ "${KEGTRON_PROXY_ROLE}" = "scanner" ]; then
    poetry run python scan.py
fi

if [ "${KEGTRON_PROXY_ROLE}" = "api" ]; then
    poetry run alembic upgrade head && \
    poetry run python api.py
fi

#!make
ROOT_PY3 := python3

POETRY := $(shell which poetry)
POETRY_VARS :=
ifeq ($(shell uname -s),Darwin)
	HOMEBREW_OPENSSL_DIR := $(shell brew --prefix openssl)
	POETRY_VARS += CFLAGS="-I$(HOMEBREW_OPENSSL_DIR)/include"
	POETRY_VARS += LDFLAGS="-L$(HOMEBREW_OPENSSL_DIR)/lib"
endif

ifeq ($(shell uname -p),arm)
	POETRY_VARS += arch -arm64
endif

BLACK := $(POETRY) run black
ISORT := $(POETRY) run isort
PYLINT := $(POETRY) run pylint
PYTEST := $(POETRY) run pytest
PYTHON := $(POETRY) run python3
ALEMBIC := $(POETRY) run alembic


ifeq ($(POETRY),)
$(error Poetry is not installed and is required)
endif


ifneq ("$(wildcard .env)","")
    include .env
	export $(shell sed 's/=.*//' .env)
endif

export KEGTRON_PROXY_CONFIG_BASE_DIR=$(CURDIR)/config
export KEGTRON_SCANNER_CONFIG_BASE_DIR=$(CURDIR)/config
export KEGTRON_PROXY_DB_BASE_DIR=$(CURDIR)/data
export KEGTRON_SCANNER_DB_BASE_DIR=$(CURDIR)/data
export KEGTRON_PROXY_STATIC_FILES_DIR=$(CURDIR)/src/static
export KEGTRON_PROXY_ENV=development


.PHONY: depends update-depends run-dev-local run-local lint format create-migration test test-unit test-api test-integration test-coverage

# dependency targets

depends: 
	$(POETRY_VARS) $(POETRY) install --no-root
	

update-depends:
	$(POETRY_VARS) $(POETRY) update

# Targets for running the app

seed_data: export PYTHONPATH=$(CURDIR)/src:$PYTHONPATH
seed_data:
	$(PYTHON) data/seed_data.py

run-debug: export KEGTRON_PROXY_LOG_LEVEL=DEBUG
run-debug: run-db-migrations seed_data
	$(PYTHON) src/app.py

run: run-db-migrations
	$(PYTHON) src/app.py

scan:
	$(PYTHON) src/scan.py 

scan_debug: export KEGTRON_SCANNER_LOG_LEVEL=DEBUG
scan-debug:
	$(PYTHON) src/scan.py

# Testing and Syntax targets

test: test-unit test-api test-integration

test-unit:
	$(PYTEST) test/unit

test-api:
	$(PYTEST) test/api

test-integration:
	$(PYTEST) test/integration -v

test-integration-auth:
	$(PYTEST) test/integration/test_auth_integration.py -v

test-integration-quick:
	$(PYTEST) test/integration -x --tb=short

test-coverage:
	$(PYTEST) test --cov=src --cov-report=term-missing --cov-report=html:htmlcov

test-watch:
	$(PYTEST) test -f

lint:
	$(ISORT) --check-only src
	$(PYLINT) --output-format=colorized src
	$(BLACK) --check src

format:
	$(ISORT) src
	$(BLACK) src

# Migrations

create-migration: 
	$(ALEMBIC) revision --autogenerate -m @1

run-db-migrations:
	$(ALEMBIC) upgrade head

# Help target
help:
	@echo "Available make targets:"
	@echo ""
	@echo "  Dependencies:"
	@echo "    depends           - Install project dependencies"
	@echo "    update-depends    - Update project dependencies"
	@echo ""
	@echo "  Running the app:"
	@echo "    run               - Run the app locally"
	@echo "    run-debug         - Run the app in development mode with debug logging"
	@echo "    scan              - Run the scanner"
	@echo "    scan-debug        - Run the scanner with debug logging"
	@echo ""
	@echo "  Testing:"
	@echo "    test              - Run all tests"
	@echo "    test-unit         - Run unit tests only"
	@echo "    test-api          - Run API tests (mocked)"
	@echo "    test-integration  - Run integration tests against real API server"
	@echo "    test-coverage     - Run all tests with coverage report"
	@echo "    test-watch        - Run tests in watch mode"
	@echo ""
	@echo "  Code quality:"
	@echo "    lint              - Run linters (isort, pylint, black)"
	@echo "    format            - Format code with isort and black"
	@echo ""
	@echo "  Database:"
	@echo "    create-migration  - Create a new database migration"
	@echo "    run-db-migrations - Run database migrations"
	@echo "    seed_data         - Seed the database with test data"

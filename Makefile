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
else
export KEGTRON_PROXY_CONFIG_BASE_DIR=$(CURDIR)/config
export KEGTRON_SCANNER_CONFIG_BASE_DIR=$(CURDIR)/config
export KEGTRON_PROXY_DB_BASE_DIR=$(CURDIR)/data
export KEGTRON_SCANNER_DB_BASE_DIR=$(CURDIR)/data
export KEGTRON_PROXY_STATIC_FILES_DIR=$(CURDIR)/src/static
endif


.PHONY: depends update-depends run-dev-local run-local lint format create-migration

# dependency targets

depends: 
	$(POETRY_VARS) $(POETRY) install --no-root
	

update-depends:
	$(POETRY_VARS) $(POETRY) update

# Targets for running the app

seed_data: export PYTHONPATH=$(CURDIR)/src:$PYTHONPATH
seed_data:
	$(PYTHON) data/seed_data.py

run-dev-local: run-db-migrations seed_data
	$(PYTHON) src/api.py --log DEBUG

run-local: run-db-migrations
	$(PYTHON) src/api.py

scan:
	$(PYTHON) src/scan.py 

scan-dev:
	$(PYTHON) src/scan.py --log DEBUG

# Testing and Syntax targets

lint:
	$(ISORT) --check-only src
	pushd ./src && $(PYLINT) . && popd
	$(BLACK) --check src

format:
	$(ISORT) src
	$(BLACK) src

# Migrations

create-migration: 
	$(ALEMBIC) revision --autogenerate -m @1

run-db-migrations:
	$(ALEMBIC) upgrade head

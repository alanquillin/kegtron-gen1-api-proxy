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

TAG_LATEST := false
DOCKER_IMAGE ?= kegtron-v1-api-proxy
DOCKER_IMAGE_TAG_DEV ?= dev
DOCKER := $(shell which docker)
IMAGE_REPOSITORY := alanquillin
REPOSITORY_IMAGE ?= $(DOCKER_IMAGE)
PLATFORMS ?= linux/amd64,linux/arm64,linux/arm

ifeq ($(POETRY),)
$(error Poetry is not installed and is required)
endif

# ifeq ($(DOCKER),)
# $(error Docker is not installed and is required)
# endif

ifneq ("$(wildcard .env)","")
    include .env
	export $(shell sed 's/=.*//' .env)
endif

ifeq ($(TAG_LATEST),true)
override DOCKER_BUILD_ARGS += -t $(IMAGE_REPOSITORY)/$(REPOSITORY_IMAGE):latest
endif

.PHONY: depends update-depends run-dev-local run-local lint format #create-migration

# dependency targets

depends: 
	$(POETRY_VARS) $(POETRY) install --no-root && \
	$(POETRY_VARS) $(POETRY) run pip install "flask[async]" && \
	$(POETRY_VARS) $(POETRY) run pip install -U bleak
	

update-depends:
	$(POETRY_VARS) $(POETRY) update && \
	$(POETRY_VARS) $(POETRY) run pip install -U "flask[async]" && \
	$(POETRY_VARS) $(POETRY) run pip install -U bleak


# dev

build-dev: depends
	$(DOCKER) build $(DOCKER_BUILD_ARGS) --build-arg build_for=dev -t $(DOCKER_IMAGE):$(DOCKER_IMAGE_TAG_DEV) .

# Targets for running the app

run-dev-local: 
	$(PYTHON) src/api.py --log DEBUG

run-local:
	$(PYTHON) src/api.py

scan:
	$(PYTHON) src/scan.py 

scan-dev:
	$(PYTHON) src/scan.py --log DEBUG

# run-db-migrations:
# 	./migrate.sh upgrade head

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
	alembic revision --autogenerate -m "description"

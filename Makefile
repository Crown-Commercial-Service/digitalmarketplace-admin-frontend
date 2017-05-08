SHELL := /bin/bash
VIRTUALENV_ROOT := $(shell [ -z $$VIRTUAL_ENV ] && echo $$(pwd)/venv || echo $$VIRTUAL_ENV)
DM_ENVIRONMENT ?= development

ifeq ($(DM_ENVIRONMENT),development)
	GULP_ENVIRONMENT := development
else
	GULP_ENVIRONMENT := production
endif

run_all: requirements npm_install frontend_build run_app

run_app: show_environment virtualenv
	${VIRTUALENV_ROOT}/bin/python application.py runserver

virtualenv:
	[ -z $$VIRTUAL_ENV ] && [ ! -d venv ] && virtualenv venv || true

upgrade_pip: virtualenv
	${VIRTUALENV_ROOT}/bin/pip install --upgrade pip

requirements: virtualenv upgrade_pip requirements.txt
	${VIRTUALENV_ROOT}/bin/pip install -r requirements.txt

requirements_for_test: virtualenv upgrade_pip requirements_for_test.txt
	${VIRTUALENV_ROOT}/bin/pip install -r requirements_for_test.txt

npm_install: package.json
	npm install

frontend_build:
	npm run --silent frontend-build:${GULP_ENVIRONMENT}

test: show_environment test_pep8 test_python

test_pep8: virtualenv
	${VIRTUALENV_ROOT}/bin/pep8 .

test_python: virtualenv
	${VIRTUALENV_ROOT}/bin/py.test ${PYTEST_ARGS}

show_environment:
	@echo "Environment variables in use:"
	@env | grep DM_ || true

docker-build:
	$(if ${RELEASE_NAME},,$(eval export RELEASE_NAME=$(shell git describe)))
	@echo "Building a docker image for ${RELEASE_NAME}..."
	docker build --pull -t digitalmarketplace/admin-frontend --build-arg release_name=${RELEASE_NAME} .
	docker tag digitalmarketplace/admin-frontend digitalmarketplace/admin-frontend:${RELEASE_NAME}

docker-push:
	$(if ${RELEASE_NAME},,$(eval export RELEASE_NAME=$(shell git describe)))
	docker push digitalmarketplace/admin-frontend:${RELEASE_NAME}

.PHONY: run_all run_app virtualenv requirements requirements_for_test npm_install frontend_build test test_pep8 test_python show_environment docker-build docker-push
